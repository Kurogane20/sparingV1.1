"""Advanced analytics endpoints (audit Priority 2): data-gap detection and
debit→volume integration. Read-only, viewer-scoped."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_current_user, get_viewer_site_uids
from app.models.models import Site, SensorData, LoggerStatus, LoggerEvent
from app.utils.analytics_helpers import (
    find_data_gaps, integrate_volume, compute_stats, integrate_uptime,
)

router = APIRouter()

DEFAULT_INTERVAL_SECONDS = 120  # SPARING cadence: a reading every ~2 minutes
STAT_FIELDS = ["ph", "tss", "cod", "nh3n", "debit", "temp"]

# logger_events type -> state transition
LOGGER_UP_TYPES = {"started"}
LOGGER_DOWN_TYPES = {"stopped", "logger_down"}
INTERNET_UP_TYPES = {"net_up"}
INTERNET_DOWN_TYPES = {"net_down"}


async def _resolve_site(db: AsyncSession, site_uid: str, viewer_uids: list[str]) -> Site:
    site = (await db.execute(select(Site).where(Site.uid == site_uid))).scalar_one_or_none()
    if not site:
        raise HTTPException(404, "Site not found")
    if viewer_uids and site_uid not in viewer_uids:
        raise HTTPException(403, "Forbidden")
    return site


def _parse_range(date_from: datetime | None, date_to: datetime | None) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    t_to = (date_to if date_to else now)
    t_from = (date_from if date_from else t_to.replace(hour=0, minute=0, second=0, microsecond=0))
    t_from = t_from if t_from.tzinfo else t_from.replace(tzinfo=timezone.utc)
    t_to = t_to if t_to.tzinfo else t_to.replace(tzinfo=timezone.utc)
    if t_from > t_to:
        raise HTTPException(400, "date_from must not be after date_to")
    return t_from, t_to


@router.get("/gaps")
async def data_gaps(
    site_uid: str = Query(...),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    interval_seconds: int = Query(default=DEFAULT_INTERVAL_SECONDS, ge=1, le=86400),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    """Missing-data gaps for a site in the range. Counts only real measurements
    (op_status rows are transmitted markers, not readings)."""
    site = await _resolve_site(db, site_uid, viewer_uids)
    t_from, t_to = _parse_range(date_from, date_to)

    rows = (await db.execute(
        select(SensorData.ts).where(
            SensorData.site_id == site.id,
            SensorData.op_status.is_(None),
            SensorData.ts >= t_from,
            SensorData.ts <= t_to,
        ).order_by(SensorData.ts.asc())
    )).all()
    timestamps = [r[0] if r[0].tzinfo else r[0].replace(tzinfo=timezone.utc) for r in rows]

    gaps = find_data_gaps(timestamps, interval_seconds=interval_seconds)
    return {
        "site_uid": site_uid,
        "interval_seconds": interval_seconds,
        "reading_count": len(timestamps),
        "gap_count": len(gaps),
        "total_missing_estimate": sum(g["missing_estimate"] for g in gaps),
        "gaps": gaps,
    }


@router.get("/volume")
async def total_volume(
    site_uid: str = Query(...),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    max_gap_minutes: float = Query(default=15.0, gt=0, le=1440),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    """Total discharged volume from the debit series (L/min → litres), integrated
    trapezoidally. Offline stretches longer than max_gap_minutes are not
    integrated across (no invented volume)."""
    site = await _resolve_site(db, site_uid, viewer_uids)
    t_from, t_to = _parse_range(date_from, date_to)

    rows = (await db.execute(
        select(SensorData.ts, SensorData.debit).where(
            SensorData.site_id == site.id,
            SensorData.op_status.is_(None),
            SensorData.debit.isnot(None),
            SensorData.ts >= t_from,
            SensorData.ts <= t_to,
        ).order_by(SensorData.ts.asc())
    )).all()
    samples = [((ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)), debit) for ts, debit in rows]

    litres = integrate_volume(samples, max_gap_minutes=max_gap_minutes)
    return {
        "site_uid": site_uid,
        "sample_count": len(samples),
        "total_liters": round(litres, 1),
        "total_m3": round(litres / 1000.0, 3),
    }


@router.get("/statistics")
async def statistics(
    site_uid: str = Query(...),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    """#18: full-range statistics (median/P95/P99/std) per parameter, computed over
    EVERY reading in the window — not a client-side chart sample. Excludes anomaly-
    flagged and operational-status rows so aggregates reflect valid measurements."""
    site = await _resolve_site(db, site_uid, viewer_uids)
    t_from, t_to = _parse_range(date_from, date_to)

    fields = {}
    for field in STAT_FIELDS:
        col = getattr(SensorData, field)
        rows = (await db.execute(
            select(col).where(
                SensorData.site_id == site.id,
                SensorData.op_status.is_(None),
                SensorData.quality_flag.is_(None),
                col.isnot(None),
                SensorData.ts >= t_from,
                SensorData.ts <= t_to,
            )
        )).all()
        s = compute_stats([r[0] for r in rows])
        if s is None:
            fields[field] = None
        else:
            fields[field] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()}
    return {"site_uid": site_uid, "fields": fields}


async def _uptime_pct(db, site_id, t_from, t_to, up_types, down_types) -> float | None:
    """Reconstruct uptime% from logger_events transitions. Returns None when there
    is no evidence at all (no events in/before the window)."""
    all_types = up_types | down_types
    # State at window start = the last relevant transition before t_from.
    prior = (await db.execute(
        select(LoggerEvent.type).where(
            LoggerEvent.site_id == site_id,
            LoggerEvent.type.in_(all_types),
            LoggerEvent.ts < t_from,
        ).order_by(LoggerEvent.ts.desc()).limit(1)
    )).scalar_one_or_none()
    in_window = (await db.execute(
        select(LoggerEvent.ts, LoggerEvent.type).where(
            LoggerEvent.site_id == site_id,
            LoggerEvent.type.in_(all_types),
            LoggerEvent.ts >= t_from,
            LoggerEvent.ts <= t_to,
        ).order_by(LoggerEvent.ts.asc())
    )).all()
    if prior is None and not in_window:
        return None
    # No prior evidence -> assume it was up at window start (no recorded downtime).
    initial_up = True if prior is None else (prior in up_types)
    transitions = [
        ((ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)), (typ in up_types))
        for ts, typ in in_window
    ]
    return integrate_uptime(transitions, t_from, t_to, initial_up)


@router.get("/availability")
async def availability(
    site_uid: str = Query(...),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    """#20: logger & internet availability% over the window, reconstructed from
    logger_events transitions (distinct from data completeness)."""
    site = await _resolve_site(db, site_uid, viewer_uids)
    t_from, t_to = _parse_range(date_from, date_to)

    logger_up = await _uptime_pct(db, site.id, t_from, t_to, LOGGER_UP_TYPES, LOGGER_DOWN_TYPES)
    internet_up = await _uptime_pct(db, site.id, t_from, t_to, INTERNET_UP_TYPES, INTERNET_DOWN_TYPES)

    def _pct(frac):
        return None if frac is None else round(frac * 100.0, 1)

    return {
        "site_uid": site_uid,
        "logger_uptime_pct": _pct(logger_up),
        "internet_uptime_pct": _pct(internet_up),
    }


@router.get("/transmission")
async def transmission(
    site_uid: str = Query(...),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    """#21: transmission summary. We store send FAILURES (send_fail events) plus the
    latest snapshot, but not historical success counts — so estimated_success_rate
    is an ESTIMATE against the expected send cadence and is labelled as such."""
    from sqlalchemy import func
    site = await _resolve_site(db, site_uid, viewer_uids)
    t_from, t_to = _parse_range(date_from, date_to)

    failures = (await db.execute(
        select(func.count(LoggerEvent.id)).where(
            LoggerEvent.site_id == site.id,
            LoggerEvent.type == "send_fail",
            LoggerEvent.ts >= t_from,
            LoggerEvent.ts <= t_to,
        )
    )).scalar_one() or 0

    status = (await db.execute(
        select(LoggerStatus).where(LoggerStatus.site_id == site.id)
    )).scalar_one_or_none()

    # Estimate: one send cycle per interval; success ≈ expected - failures.
    window_min = (t_to - t_from).total_seconds() / 60.0
    expected = max(1, round(window_min / (DEFAULT_INTERVAL_SECONDS / 60.0)))
    est_rate = round(max(0.0, (expected - failures) / expected) * 100.0, 1)

    return {
        "site_uid": site_uid,
        "failure_count": failures,
        "expected_sends_estimate": expected,
        "estimated_success_rate": est_rate,
        "last_send_ok_mm": status.last_send_ok_mm if status else None,
        "last_send_ok_klhk": status.last_send_ok_klhk if status else None,
        "buffer_depth": status.buffer_depth if status else None,
        "daily_sent": status.daily_sent if status else None,
    }
