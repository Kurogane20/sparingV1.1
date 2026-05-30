import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import AlertRule, Alert, Site, User, ViewerSite
from app.core.logging import logger

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


async def seed_default_rules(site_id: int, db: AsyncSession) -> None:
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
        )
        db.add(rule)
    await db.commit()


async def trigger_alerts(
    site_id: int,
    site_uid: str,
    device_uid: str | None,
    data: dict,
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

            now = datetime.now(timezone.utc)
            dedup_cutoff = now - timedelta(minutes=30)
            new_alerts = []

            for rule in rules:
                value = data.get(rule.field)
                if value is None:
                    continue

                threshold_type = _determine_threshold_type(float(value), rule)
                if threshold_type is None:
                    continue

                existing = await db.execute(
                    select(Alert).where(
                        Alert.site_id == site_id,
                        Alert.field == rule.field,
                        Alert.status == "active",
                        Alert.triggered_at >= dedup_cutoff,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                alert = Alert(
                    site_id=site_id,
                    device_uid=device_uid,
                    field=rule.field,
                    value=float(value),
                    threshold_type=threshold_type,
                    status="active",
                    triggered_at=now,
                )
                db.add(alert)
                new_alerts.append(rule.field)

            if new_alerts:
                await db.commit()
                from app.utils.email import send_alert_emails
                asyncio.create_task(send_alert_emails(site_id, site_uid, data))

    except Exception:
        logger.exception(f"Alert engine failed for site {site_uid}")


async def check_offline_devices(db: AsyncSession) -> None:
    """Create offline-device alerts for sites with no data in >60 minutes."""
    try:
        from sqlalchemy import text
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
        dedup_cutoff = cutoff

        result = await db.execute(
            text("""
                SELECT s.id, s.uid
                FROM sites s
                WHERE s.is_active = 1
                  AND (
                    SELECT MAX(sd.ts) FROM sensor_data sd WHERE sd.site_id = s.id
                  ) < :cutoff
                  AND NOT EXISTS (
                    SELECT 1 FROM alerts a
                    WHERE a.site_id = s.id
                      AND a.field = 'device_offline'
                      AND a.status = 'active'
                      AND a.triggered_at >= :dedup_cutoff
                  )
            """),
            {"cutoff": cutoff, "dedup_cutoff": dedup_cutoff},
        )
        rows = result.fetchall()

        now = datetime.now(timezone.utc)
        for row in rows:
            alert = Alert(
                site_id=row.id,
                device_uid=None,
                field="device_offline",
                value=0.0,
                threshold_type="danger",
                status="active",
                triggered_at=now,
            )
            db.add(alert)

        if rows:
            await db.commit()
            logger.warning(f"Offline device alerts created for {len(rows)} sites")

    except Exception:
        logger.exception("Offline device check failed")
