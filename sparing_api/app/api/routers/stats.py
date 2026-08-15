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


async def _scoped_sites(db: AsyncSession, viewer_uids: list[str],
                        site_uid: str | None = None) -> list[Site]:
    q = select(Site).where(Site.is_active == True)
    if viewer_uids:
        q = q.where(Site.uid.in_(viewer_uids))
    if site_uid:
        # Narrow to a single site (still bounded by the viewer scope above, so a
        # viewer can't scope to a site they aren't assigned to).
        q = q.where(Site.uid == site_uid)
    return list((await db.execute(q)).scalars().all())


@router.get("/completeness")
async def completeness(
    hours: int = Query(default=24, ge=1, le=1080),
    site_uid: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    now = datetime.now(timezone.utc)
    # `date_from` (e.g. today 00:00 WIB in UTC) starts the actual-count window at a
    # fixed instant instead of a rolling `now - hours`; the target stays 30*hours
    # (a full day), so today's card reads as a progress bar that fills through the day.
    if date_from is not None:
        since = date_from if date_from.tzinfo else date_from.replace(tzinfo=timezone.utc)
    else:
        since = now - timedelta(hours=hours)
    sites = await _scoped_sites(db, viewer_uids, site_uid)
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
            SensorData.op_status.is_(None),
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
    site_uid: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    prev_since = since - timedelta(days=days)
    sites = await _scoped_sites(db, viewer_uids, site_uid)
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


@router.get("/compliance-daily")
async def compliance_daily(
    month: str = Query(..., description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    try:
        year, mon = int(month[:4]), int(month[5:7])
        start = datetime(year, mon, 1, tzinfo=timezone.utc)
    except (ValueError, IndexError):
        raise HTTPException(400, "month harus berformat YYYY-MM")
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if mon == 12 else \
          datetime(year, mon + 1, 1, tzinfo=timezone.utc)

    sites = await _scoped_sites(db, viewer_uids)
    site_ids = [s.id for s in sites]
    day_expr = func.date(SensorData.ts)

    def _norm(d) -> str:  # SQLite returns 'YYYY-MM-DD' strings, MySQL date objects
        return d if isinstance(d, str) else d.isoformat()

    data_days, danger_days, warning_days = set(), set(), set()
    if site_ids:
        # Only real measurements make a day "ok" — a day containing nothing but
        # operational-status rows (calibration/stopped/malfunction) must not be
        # reported as fully compliant, since nothing was actually measured.
        rows = (await db.execute(
            select(day_expr).where(SensorData.site_id.in_(site_ids),
                                   SensorData.op_status.is_(None),
                                   SensorData.ts >= start, SensorData.ts < end)
            .group_by(day_expr)
        )).all()
        data_days = {_norm(r[0]) for r in rows}

        rules = list((await db.execute(
            select(AlertRule).where(AlertRule.site_id.in_(site_ids), AlertRule.is_active == True)
        )).scalars().all())
        for rule in rules:
            col = getattr(SensorData, rule.field, None)
            if col is None:
                continue
            base = (SensorData.site_id == rule.site_id, col.isnot(None),
                    SensorData.quality_flag.is_(None),
                    SensorData.op_status.is_(None),
                    SensorData.ts >= start, SensorData.ts < end)
            for level, bucket in (("danger", danger_days), ("warning", warning_days)):
                conds = []
                mn, mx = getattr(rule, f"{level}_min"), getattr(rule, f"{level}_max")
                if mn is not None:
                    conds.append(col < mn)
                if mx is not None:
                    conds.append(col > mx)
                if conds:
                    hit = (await db.execute(
                        select(day_expr).where(*base, or_(*conds)).group_by(day_expr)
                    )).all()
                    bucket.update(_norm(r[0]) for r in hit)

    days = []
    d = start
    while d < end:
        key = d.date().isoformat()
        if key in danger_days:
            status = "violation"
        elif key in warning_days:
            status = "warning"
        elif key in data_days:
            status = "ok"
        else:
            status = "none"
        days.append({"date": key, "status": status})
        d += timedelta(days=1)
    return {"month": month, "days": days}
