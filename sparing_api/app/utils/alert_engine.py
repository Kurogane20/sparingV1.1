import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.models.models import AlertRule, Alert, Site, User, ViewerSite
from app.core.logging import logger
from app.utils.time import as_utc

# System note stamped on auto-resolved alerts: recovery must never be blocked
# by the mandatory-note rule that applies to manual closure.
AUTO_RESOLVE_NOTE = "Pulih otomatis — nilai kembali normal"

DEFAULT_ALERT_RULES = [
    {"field": "ph",    "warning_min": 6.5, "warning_max": 8.5, "danger_min": 6.0,  "danger_max": 9.0},
    {"field": "tss",   "warning_min": None, "warning_max": 150, "danger_min": None, "danger_max": 200},
    {"field": "cod",   "warning_min": None, "warning_max": 200, "danger_min": None, "danger_max": 300},
    {"field": "nh3n",  "warning_min": None, "warning_max": 7,   "danger_min": None, "danger_max": 10},
    {"field": "temp",  "warning_min": None, "warning_max": 30,  "danger_min": None, "danger_max": 35},
    {"field": "noise", "warning_min": None, "warning_max": 60,  "danger_min": None, "danger_max": 70},
    {"field": "pm25",  "warning_min": None, "warning_max": 35,  "danger_min": None, "danger_max": 65},
    {"field": "pm10",  "warning_min": None, "warning_max": 100, "danger_min": None, "danger_max": 150},
]


def _is_violated(value: float, rule, level: str) -> bool:
    mn = getattr(rule, f"{level}_min")
    mx = getattr(rule, f"{level}_max")
    if mn is None and mx is None:
        return False
    if mn is not None and mx is not None:
        return value < mn or value > mx
    if mx is not None:
        return value > mx
    return value < mn


def _determine_threshold_type(value: float, rule) -> str | None:
    if _is_violated(value, rule, "danger"):
        return "danger"
    if _is_violated(value, rule, "warning"):
        return "warning"
    return None


async def seed_default_rules(
    site_id: int, db: AsyncSession, updated_by_user_id: int | None = None
) -> None:
    now = datetime.now(timezone.utc)
    for rule_def in DEFAULT_ALERT_RULES:
        rule = AlertRule(
            site_id=site_id,
            field=rule_def["field"],
            warning_min=rule_def["warning_min"],
            warning_max=rule_def["warning_max"],
            danger_min=rule_def["danger_min"],
            danger_max=rule_def["danger_max"],
            is_active=True,
            created_at=now,
            updated_at=now,
            updated_by_user_id=updated_by_user_id,
        )
        db.add(rule)


async def trigger_alerts(
    site_id: int,
    site_uid: str,
    device_uid: str | None,
    data: dict,
    measurement_ts: datetime | None = None,
) -> None:
    """Check data against active AlertRules. Creates its own DB session — safe for asyncio.create_task()."""
    from app.core.db import SessionLocal
    try:
        async with SessionLocal() as db:
            rules_result = await db.execute(
                select(AlertRule).where(
                    AlertRule.site_id == site_id,
                    AlertRule.is_active == True,
                )
            )
            rules = rules_result.scalars().all()

            event_ts = as_utc(measurement_ts) or datetime.now(timezone.utc)
            new_alerts = []
            changed = False

            for rule in rules:
                value = data.get(rule.field)
                if value is None:
                    continue

                threshold_type = _determine_threshold_type(float(value), rule)

                # One active compliance alert per (site, field) — a persisting
                # breach must not spawn a new alert every cycle. `.first()` keeps
                # this robust against historical duplicates.
                existing = (await db.execute(
                    select(Alert).where(
                        Alert.site_id == site_id,
                        Alert.field == rule.field,
                        Alert.category == "compliance",
                        Alert.status == "active",
                    ).limit(1)
                )).scalars().first()

                if threshold_type is None:
                    # Back within limits — resolve the active alert (recovery).
                    if existing is not None:
                        await db.execute(
                            update(Alert).where(
                                Alert.site_id == site_id,
                                Alert.field == rule.field,
                                Alert.category == "compliance",
                                Alert.status == "active",
                            ).values(
                                status="resolved",
                                resolved_at=datetime.now(timezone.utc),
                                # coalesce keeps an operator's in-progress note
                                followup_note=func.coalesce(Alert.followup_note, AUTO_RESOLVE_NOTE),
                            )
                        )
                        changed = True
                    continue

                if existing is not None:
                    # Still breaching; keep one alert, just track level/value.
                    if existing.threshold_type != threshold_type:
                        existing.threshold_type = threshold_type
                        existing.value = float(value)
                        existing.triggered_at = event_ts
                        changed = True
                    continue

                db.add(Alert(
                    site_id=site_id,
                    device_uid=device_uid,
                    field=rule.field,
                    value=float(value),
                    threshold_type=threshold_type,
                    status="active",
                    triggered_at=event_ts,
                ))
                new_alerts.append(rule.field)
                changed = True

            if changed:
                await db.commit()
            if new_alerts:
                from app.utils.email import send_alert_emails
                asyncio.create_task(send_alert_emails(site_id, site_uid, data))

    except Exception:
        logger.exception(f"Alert engine failed for site {site_uid}")


OFFLINE_RECOVERED_NOTE = "Otomatis: data kembali diterima"
OFFLINE_DUPLICATE_NOTE = "Otomatis: duplikat alarm offline digabung"


def _auto_resolve(alert: Alert, note: str, now: datetime) -> None:
    alert.status = "resolved"
    alert.resolved_at = now
    alert.followup_note = alert.followup_note or note
    if alert.followup_at is None:
        alert.followup_at = now


async def check_offline_devices(db: AsyncSession) -> None:
    """Keep exactly one open offline alert per offline site.

    A site whose newest data is older than the shared offline threshold (kept
    in sync with the device health badge) gets one alert, however long it
    stays offline; duplicates left by earlier versions collapse into the
    oldest. When data arrives again its open offline alerts resolve on their
    own. Idempotent, so the first run after a deploy also cleans history."""
    try:
        from app.models.models import SensorData
        from app.utils.device_health import WARNING_MAX_MINUTES
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=WARNING_MAX_MINUTES)

        last_ts = (
            select(SensorData.site_id, func.max(SensorData.ts).label("last_ts"))
            .group_by(SensorData.site_id)
            .subquery()
        )
        sites = (await db.execute(
            select(Site.id, last_ts.c.last_ts)
            .outerjoin(last_ts, last_ts.c.site_id == Site.id)
            .where(Site.is_active == True)
        )).all()
        open_alerts = (await db.execute(
            select(Alert).where(
                Alert.field == "device_offline",
                Alert.status.in_(("active", "acknowledged")),
            ).order_by(Alert.triggered_at, Alert.id)
        )).scalars().all()
        open_by_site: dict[int, list[Alert]] = {}
        for alert in open_alerts:
            open_by_site.setdefault(alert.site_id, []).append(alert)

        created = resolved = 0
        for site_id, last in sites:
            alerts = open_by_site.get(site_id, [])
            offline = last is None or as_utc(last) < cutoff
            if offline and not alerts:
                db.add(Alert(
                    site_id=site_id,
                    device_uid=None,
                    field="device_offline",
                    value=0.0,
                    threshold_type="danger",
                    status="active",
                    triggered_at=now,
                ))
                created += 1
            elif offline:
                for duplicate in alerts[1:]:
                    _auto_resolve(duplicate, OFFLINE_DUPLICATE_NOTE, now)
                    resolved += 1
            else:
                for alert in alerts:
                    _auto_resolve(alert, OFFLINE_RECOVERED_NOTE, now)
                    resolved += 1

        if created or resolved:
            await db.commit()
            logger.warning(
                f"Offline device alerts: {created} created, {resolved} auto-resolved"
            )

    except Exception:
        logger.exception("Offline device check failed")
