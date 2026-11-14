"""Server-side liveness inference for field loggers.

A dead logger cannot announce its own death, so absence of heartbeats is the
signal. Liveness is judged on the server-recorded `last_heartbeat_at`, never on
the logger's own clock — a Pi with skewed time must not appear alive or dead
incorrectly.

The scheduler runs on one worker (scheduler lock), but every write stays idempotent: incidents are keyed by a unique open_key, and sensor alerts are found with `.first()` so historical duplicates can never raise.
"""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger as applog
from app.models.models import Alert, LoggerStatus, Site
from app.utils.logger_incidents import (close_open_incident, import_down_history,
                                        recompute_causes, sync_incidents)

DOWN_AFTER_MINUTES = 10          # silence threshold before a logger counts as down
SENSOR_FAIL_MINUTES = 15         # a sensor failing this long raises a warning
LOGGER_DOWN_FIELD = "logger_down"
LOGGER_CATEGORY = "logger"
AUTO_RESOLVE_NOTE = "Pulih otomatis — logger kembali mengirim heartbeat"
SENSOR_RECOVER_NOTE = "Pulih otomatis — sensor kembali terbaca normal"


def _as_utc(dt: "datetime | None") -> "datetime | None":
    """MySQL returns naive UTC; normalise before comparing against aware now."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _active_alert(db: AsyncSession, site_id: int, field: str):
    return (await db.execute(
        select(Alert).where(
            Alert.site_id == site_id,
            Alert.field == field,
            Alert.category == LOGGER_CATEGORY,
            Alert.status == "active",
        ).limit(1)
    )).scalars().first()


async def scan_logger_liveness(db: AsyncSession) -> int:
    """Flip silent loggers to 'down' and raise one alert each; also raise warnings
    for sensors that have been failing longer than SENSOR_FAIL_MINUTES.

    Returns the number of loggers newly marked down.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=DOWN_AFTER_MINUTES)
    rows = (await db.execute(
        select(LoggerStatus, Site).join(Site, Site.id == LoggerStatus.site_id)
        .where(Site.is_active == True)
    )).all()

    flipped = 0
    for st, site in rows:
        last = _as_utc(st.last_heartbeat_at)
        silent = last is None or last < cutoff

        if silent:
            if st.state != "down":
                st.state = "down"
                st.state_since = now
                flipped += 1
            # The logger_down alarm belongs to the `down` incident (sync_incidents below).
            continue

        # Logger is reporting — make sure the state reflects that.
        if st.state != "alive":
            st.state = "alive"
            st.state_since = now

        # Persistent sensor failure (the heartbeat stamps sensor_fail_since).
        fail_since = _as_utc(st.sensor_fail_since)
        if fail_since is not None and fail_since < now - timedelta(minutes=SENSOR_FAIL_MINUTES):
            for name in ("ph", "tss", "debit", "cod", "nh3n"):
                if getattr(st, f"{name}_ok") is False:
                    field = f"sensor_{name}"
                    if await _active_alert(db, site.id, field) is None:
                        db.add(Alert(
                            site_id=site.id, device_uid=None, field=field,
                            value=0.0, threshold_type="warning", status="active",
                            triggered_at=now, category=LOGGER_CATEGORY,
                            detail=f"Sensor {name.upper()} gagal dibaca sejak {fail_since:%H:%M} UTC",
                        ))

    await db.commit()
    if flipped:
        applog.warning("logger liveness: %d logger(s) marked down", flipped)
    # Incidents and their alarms (logger_down included) follow the diagnosis.
    await import_down_history(db, now)
    await sync_incidents(db, now)
    await recompute_causes(db, now)
    return flipped


async def resolve_logger_down_alert(db: AsyncSession, site_id: int, now: datetime) -> None:
    """Auto-resolve on heartbeat return.

    Closing the open `down` incident resolves its alarm with the inferred cause.
    Any logger_down alarm still active after that (one raised twice before
    incidents existed) gets the generic system note, so recovery is never
    blocked by the mandatory-note rule that governs manual closure of alarms.
    """
    await close_open_incident(db, site_id, "down", now)
    await db.execute(
        update(Alert).where(
            Alert.site_id == site_id,
            Alert.field == LOGGER_DOWN_FIELD,
            Alert.category == LOGGER_CATEGORY,
            Alert.status == "active",
        ).values(status="resolved", resolved_at=now, followup_note=AUTO_RESOLVE_NOTE)
    )
    await db.commit()


async def resolve_sensor_alerts(db: AsyncSession, site_id: int, now: datetime) -> None:
    """Auto-resolve sensor warnings once every sensor reads OK again.

    Without this the warning would stay active forever after the sensor
    recovered, steadily eroding the alarm list's signal — every other alert
    category in this codebase self-resolves on recovery.
    """
    await db.execute(
        update(Alert).where(
            Alert.site_id == site_id,
            Alert.field.like("sensor\\_%", escape="\\"),
            Alert.category == LOGGER_CATEGORY,
            Alert.status == "active",
        ).values(status="resolved", resolved_at=now, followup_note=SENSOR_RECOVER_NOTE)
    )
    await db.commit()
