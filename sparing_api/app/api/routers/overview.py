"""Command-center overview: every site's live status in one admin-only call.

Aggregates online/logger status, compliance, active alarms, today's completeness,
and the latest parameter values per site. Admin-only — it deliberately spans ALL
sites (no viewer scoping), so it must never be exposed to viewers/operators.
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import require_roles
from app.models.models import Site, SensorData, AlertRule, Alert, LoggerStatus
from app.utils.device_health import compute_health_status
from app.api.routers.stats import _compliance_window, _pct, READINGS_PER_SITE_PER_HOUR

router = APIRouter()

LAST_PARAM_FIELDS = ["ph", "tss", "cod", "nh3n", "debit"]


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _wib_midnight_utc(now: datetime) -> datetime:
    """Start of today in WIB (UTC+7), expressed as a UTC instant."""
    wib = now + timedelta(hours=7)
    wib_mid = wib.replace(hour=0, minute=0, second=0, microsecond=0)
    return wib_mid - timedelta(hours=7)


@router.get("", dependencies=[Depends(require_roles("admin"))])
async def overview(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    since_today = _wib_midnight_utc(now)
    hours_elapsed = max(1.0, (now - since_today).total_seconds() / 3600.0)

    sites = list((await db.execute(
        select(Site).where(Site.is_active == True).order_by(Site.name)
    )).scalars().all())

    # ── Bulk lookups (avoid per-site round-trips for shared data) ──────
    alarm_rows = (await db.execute(
        select(Alert.site_id, Alert.threshold_type, func.count(Alert.id))
        .where(Alert.status == "active")
        .group_by(Alert.site_id, Alert.threshold_type)
    )).all()
    active_by_site: dict[int, int] = {}
    danger_by_site: dict[int, int] = {}
    for site_id, ttype, cnt in alarm_rows:
        active_by_site[site_id] = active_by_site.get(site_id, 0) + cnt
        if ttype == "danger":
            danger_by_site[site_id] = danger_by_site.get(site_id, 0) + cnt

    logger_rows = (await db.execute(select(LoggerStatus))).scalars().all()
    logger_by_site = {ls.site_id: ls for ls in logger_rows}

    rules = list((await db.execute(
        select(AlertRule).where(AlertRule.is_active == True)
    )).scalars().all())
    rules_by_site: dict[int, list] = {}
    for r in rules:
        rules_by_site.setdefault(r.site_id, []).append(r)

    items = []
    online_count = 0
    total_active_alarms = 0
    sites_with_danger = 0
    compliance_values = []

    for site in sites:
        # Latest real reading (op_status rows are markers, not measurements)
        last_row = (await db.execute(
            select(SensorData).where(
                SensorData.site_id == site.id,
                SensorData.op_status.is_(None),
            ).order_by(SensorData.ts.desc()).limit(1)
        )).scalar_one_or_none()

        last_seen = _aware(last_row.ts) if last_row else None
        status = compute_health_status(last_seen)
        if status == "online":
            online_count += 1

        last_values = {}
        if last_row:
            for f in LAST_PARAM_FIELDS:
                last_values[f] = getattr(last_row, f)

        active = active_by_site.get(site.id, 0)
        danger = danger_by_site.get(site.id, 0)
        total_active_alarms += active
        if danger > 0:
            sites_with_danger += 1

        # Compliance over the last 24h using this site's danger rules
        site_rules = rules_by_site.get(site.id, [])
        checks, violations = await _compliance_window(db, site_rules, since_24h, now)
        compliance_pct = _pct(checks, violations) if checks > 0 else None
        if compliance_pct is not None:
            compliance_values.append(compliance_pct)

        # Today's completeness (measurements only, since WIB midnight)
        actual_today = (await db.execute(
            select(func.count(SensorData.id)).where(
                SensorData.site_id == site.id,
                SensorData.op_status.is_(None),
                SensorData.ts >= since_today,
            )
        )).scalar_one() or 0
        expected_today = READINGS_PER_SITE_PER_HOUR * hours_elapsed
        completeness_pct = min(100.0, round(actual_today * 100.0 / expected_today, 1)) if expected_today else 0.0

        ls = logger_by_site.get(site.id)
        items.append({
            "uid": site.uid,
            "name": site.name,
            "status": status,                       # online | warning | offline | unknown
            "last_seen": last_seen.isoformat() if last_seen else None,
            "last_values": last_values,
            "active_alarms": active,
            "danger_alarms": danger,
            "compliance_pct": compliance_pct,       # null when no rules/data
            "completeness_pct": completeness_pct,
            "logger_state": ls.state if ls else None,
            "logger_last_heartbeat_at": _aware(ls.last_heartbeat_at).isoformat() if ls and ls.last_heartbeat_at else None,
        })

    avg_compliance = round(sum(compliance_values) / len(compliance_values), 1) if compliance_values else None
    return {
        "generated_at": now.isoformat(),
        "totals": {
            "site_count": len(sites),
            "online_count": online_count,
            "offline_count": len(sites) - online_count,
            "total_active_alarms": total_active_alarms,
            "sites_with_danger": sites_with_danger,
            "avg_compliance_pct": avg_compliance,
        },
        "sites": items,
    }
