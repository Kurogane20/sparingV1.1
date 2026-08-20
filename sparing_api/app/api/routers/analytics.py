"""Advanced analytics endpoints (audit Priority 2): data-gap detection and
debit→volume integration. Read-only, viewer-scoped."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_current_user, get_viewer_site_uids
from app.models.models import Site, SensorData
from app.utils.analytics_helpers import find_data_gaps, integrate_volume

router = APIRouter()

DEFAULT_INTERVAL_SECONDS = 120  # SPARING cadence: a reading every ~2 minutes


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
