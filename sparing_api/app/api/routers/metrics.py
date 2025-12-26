from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.core.db import get_db
from app.api.deps import get_viewer_site_uids
from app.models.models import Site, SensorData
from app.core.cache import cache, cache_key, CACHE_TTL_METRICS, CACHE_TTL_LAST_DATA

router = APIRouter()


@router.get("/sites/{uid}/stats/last-seen")
async def last_seen(
    uid: str,
    db: AsyncSession = Depends(get_db),
    viewer_uids: list[str] = Depends(get_viewer_site_uids)
):
    """Get last data timestamp for a site."""
    # Check cache first
    cached = await cache.get(cache_key("last_seen", uid))
    if cached is not None:
        return cached
    
    res = await db.execute(select(Site).where(Site.uid == uid))
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(404, "Site not found")
    if viewer_uids and uid not in viewer_uids:
        raise HTTPException(403, "Forbidden")
    
    row = (await db.execute(
        select(func.max(SensorData.ts)).where(SensorData.site_id == site.id)
    )).scalar_one_or_none()
    
    result = {"site_uid": uid, "last_ts": row}
    await cache.set(cache_key("last_seen", uid), result, CACHE_TTL_LAST_DATA)
    return result


@router.get("/sites/{uid}/metrics")
async def site_metrics(
    uid: str,
    date_from: Optional[datetime] = Query(None, description="Start date (default: today)"),
    date_to: Optional[datetime] = Query(None, description="End date (default: now)"),
    fields: Optional[str] = Query(None, description="Comma-separated fields to include"),
    db: AsyncSession = Depends(get_db),
    viewer_uids: list[str] = Depends(get_viewer_site_uids)
):
    """
    Get aggregated metrics (avg, min, max) for a site.
    Now includes: pH, TSS, COD, NH3N, Debit, Temperature
    """
    # Check permissions
    res = await db.execute(select(Site).where(Site.uid == uid))
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(404, "Site not found")
    if viewer_uids and uid not in viewer_uids:
        raise HTTPException(403, "Forbidden")
    
    # Default date range: today
    now = datetime.now(timezone.utc)
    if date_from is None:
        date_from = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    if date_to is None:
        date_to = now
    
    # Cache key based on parameters
    cache_key_str = cache_key("metrics", uid, date_from.isoformat(), date_to.isoformat())
    cached = await cache.get(cache_key_str)
    if cached is not None:
        return cached
    
    # Build query for all sensor parameters
    q = await db.execute(
        select(
            # pH
            func.avg(SensorData.ph).label("ph_avg"),
            func.min(SensorData.ph).label("ph_min"),
            func.max(SensorData.ph).label("ph_max"),
            func.count(SensorData.ph).label("ph_count"),
            # TSS
            func.avg(SensorData.tss).label("tss_avg"),
            func.min(SensorData.tss).label("tss_min"),
            func.max(SensorData.tss).label("tss_max"),
            # COD
            func.avg(SensorData.cod).label("cod_avg"),
            func.min(SensorData.cod).label("cod_min"),
            func.max(SensorData.cod).label("cod_max"),
            # NH3N
            func.avg(SensorData.nh3n).label("nh3n_avg"),
            func.min(SensorData.nh3n).label("nh3n_min"),
            func.max(SensorData.nh3n).label("nh3n_max"),
            # Debit
            func.avg(SensorData.debit).label("debit_avg"),
            func.min(SensorData.debit).label("debit_min"),
            func.max(SensorData.debit).label("debit_max"),
            # Temperature
            func.avg(SensorData.temp).label("temp_avg"),
            func.min(SensorData.temp).label("temp_min"),
            func.max(SensorData.temp).label("temp_max"),
            # Data count
            func.count(SensorData.id).label("total_records"),
        ).where(
            SensorData.site_id == site.id,
            SensorData.ts >= date_from,
            SensorData.ts <= date_to
        )
    )
    
    row = q.one()
    
    # Build response
    metrics = {
        "ph": {
            "avg": round(row.ph_avg, 2) if row.ph_avg else None,
            "min": round(row.ph_min, 2) if row.ph_min else None,
            "max": round(row.ph_max, 2) if row.ph_max else None,
        },
        "tss": {
            "avg": round(row.tss_avg, 1) if row.tss_avg else None,
            "min": round(row.tss_min, 1) if row.tss_min else None,
            "max": round(row.tss_max, 1) if row.tss_max else None,
        },
        "cod": {
            "avg": round(row.cod_avg, 1) if row.cod_avg else None,
            "min": round(row.cod_min, 1) if row.cod_min else None,
            "max": round(row.cod_max, 1) if row.cod_max else None,
        },
        "nh3n": {
            "avg": round(row.nh3n_avg, 2) if row.nh3n_avg else None,
            "min": round(row.nh3n_min, 2) if row.nh3n_min else None,
            "max": round(row.nh3n_max, 2) if row.nh3n_max else None,
        },
        "debit": {
            "avg": round(row.debit_avg, 1) if row.debit_avg else None,
            "min": round(row.debit_min, 1) if row.debit_min else None,
            "max": round(row.debit_max, 1) if row.debit_max else None,
        },
        "temp": {
            "avg": round(row.temp_avg, 1) if row.temp_avg else None,
            "min": round(row.temp_min, 1) if row.temp_min else None,
            "max": round(row.temp_max, 1) if row.temp_max else None,
        },
    }
    
    # Filter by requested fields if specified
    if fields:
        requested = set(f.strip().lower() for f in fields.split(","))
        metrics = {k: v for k, v in metrics.items() if k in requested}
    
    result = {
        "site_uid": uid,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_records": row.total_records,
        "metrics": metrics,
    }
    
    # Cache result
    await cache.set(cache_key_str, result, CACHE_TTL_METRICS)
    
    return result
