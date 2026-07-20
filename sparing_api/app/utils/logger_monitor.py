"""Server-side liveness inference for field loggers.

A dead logger cannot announce its own death, so absence of heartbeats is the
signal. Liveness is judged on the server-recorded `last_heartbeat_at`, never on
the logger's own clock — a Pi with skewed time must not appear alive or dead
incorrectly.

Both gunicorn workers run this on a schedule, so every write is idempotent:
one active alert per (site, field), found with `.first()` rather than
`scalar_one_or_none` so historical duplicates can never raise.
"""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger as applog
from app.models.models import Alert, LoggerStatus, Site

DOWN_AFTER_MINUTES = 10          # silence threshold before a logger counts as down
SENSOR_FAIL_MINUTES = 15         # a sensor failing this long raises a warning
LOGGER_DOWN_FIELD = "logger_down"
LOGGER_CATEGORY = "logger"
AUTO_RESOLVE_NOTE = "Pulih otomatis — logger kembali mengirim heartbeat"


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
            if await _active_alert(db, site.id, LOGGER_DOWN_FIELD) is None:
                minutes = 999.0 if last is None else round((now - last).total_seconds() / 60, 1)
                detail = ("Belum pernah mengirim heartbeat" if last is None
                          else f"Tidak ada heartbeat selama {minutes:.0f} menit")
                db.add(Alert(
                    site_id=site.id, device_uid=None, field=LOGGER_DOWN_FIELD,
                    value=minutes, threshold_type="danger", status="active",
                    triggered_at=now, category=LOGGER_CATEGORY, detail=detail,
                ))
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
    return flipped


async def resolve_logger_down_alert(db: AsyncSession, site_id: int, now: datetime) -> None:
    """Auto-resolve on heartbeat return.

    Writes a system note so recovery is never blocked by the mandatory-note rule
    that governs manual closure of alarms.
    """
    await db.execute(
        update(Alert).where(
            Alert.site_id == site_id,
            Alert.field == LOGGER_DOWN_FIELD,
            Alert.category == LOGGER_CATEGORY,
            Alert.status == "active",
        ).values(status="resolved", resolved_at=now, followup_note=AUTO_RESOLVE_NOTE)
    )
    await db.commit()
