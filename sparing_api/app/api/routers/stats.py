"""Aggregate statistics for the v2 dashboard/analytics.

Intentionally uncached: results are viewer-scoped, and a process-global TTL
cache keyed naively would leak admin-scoped numbers to viewers (and poison the
test harness). The windowed COUNT/DATE queries are cheap at this fleet size.
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_viewer_site_uids
from app.models.models import Site, SensorData, AlertRule

router = APIRouter()

READINGS_PER_SITE_PER_HOUR = 30  # devices deliver hourly bursts of ~30 readings


async def _scoped_sites(db: AsyncSession, viewer_uids: list[str]) -> list[Site]:
    q = select(Site).where(Site.is_active == True)
    if viewer_uids:
        q = q.where(Site.uid.in_(viewer_uids))
    return list((await db.execute(q)).scalars().all())


@router.get("/completeness")
async def completeness(
    hours: int = Query(default=24, ge=1, le=1080),
    db: AsyncSession = Depends(get_db),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    sites = await _scoped_sites(db, viewer_uids)
    site_ids = [s.id for s in sites]
    actual = 0
    if site_ids:
        actual = (await db.execute(
            select(func.count(SensorData.id)).where(
                SensorData.site_id.in_(site_ids),
                SensorData.ts >= since,
            )
        )).scalar_one()
    expected = len(site_ids) * READINGS_PER_SITE_PER_HOUR * hours
    pct = 0.0 if expected == 0 else min(100.0, round(actual * 100.0 / expected, 1))
    return {"actual": actual, "expected": expected, "pct": pct, "hours": hours}


async def _compliance_window(db: AsyncSession, rules, t_from: datetime, t_to: datetime):
    """(checks, violations) for every reading x its site's active danger rule.
    Readings flagged as anomalies are excluded (spec: excluded from computations,
    retained for audit)."""
    checks, violations = 0, 0
    for rule in rules:
        col = getattr(SensorData, rule.field, None)
        if col is None:
            continue
        base = (
            SensorData.site_id == rule.site_id,
            col.isnot(None),
            SensorData.quality_flag.is_(None),
            SensorData.ts >= t_from,
            SensorData.ts < t_to,
        )
        checks += (await db.execute(select(func.count(SensorData.id)).where(*base))).scalar_one()
        vio = []
        if rule.danger_min is not None:
            vio.append(col < rule.danger_min)
        if rule.danger_max is not None:
            vio.append(col > rule.danger_max)
        if vio:
            violations += (await db.execute(
                select(func.count(SensorData.id)).where(*base, or_(*vio))
            )).scalar_one()
    return checks, violations


def _pct(checks: int, violations: int) -> float:
    return 100.0 if checks == 0 else round(100.0 * (1 - violations / checks), 1)


@router.get("/compliance")
async def compliance(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    prev_since = since - timedelta(days=days)
    sites = await _scoped_sites(db, viewer_uids)
    site_ids = [s.id for s in sites]
    rules = []
    if site_ids:
        rules = list((await db.execute(
            select(AlertRule).where(AlertRule.site_id.in_(site_ids), AlertRule.is_active == True)
        )).scalars().all())
    checks, violations = await _compliance_window(db, rules, since, now)
    prev_checks, prev_violations = await _compliance_window(db, rules, prev_since, since)
    cur, prev = _pct(checks, violations), _pct(prev_checks, prev_violations)
    return {
        "compliance_pct": cur, "prev_pct": prev, "delta_pct": round(cur - prev, 1),
        "checked": checks, "violations": violations, "days": days,
    }
