from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime
from typing import List
from app.core.db import get_db
from app.api.deps import get_current_user, get_viewer_site_uids
from app.models.models import Site, SensorData, SensorDevice
from app.schemas.common import Page
from app.schemas.data import DataOut

router = APIRouter()

@router.get("", response_model=Page)
async def list_data(
    db: AsyncSession = Depends(get_db),
    viewer_uids: List[str] = Depends(get_viewer_site_uids),
    site_uid: str | None = None,
    device_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    order: str = "desc",
    page: int = 1,
    per_page: int = 50,
    fields: str | None = None,
    interval: str = "raw",
):
    if per_page < 1 or per_page > 500:
        raise HTTPException(400, "per_page out of range")
    if interval not in ("raw", "hourly", "daily"):
        raise HTTPException(400, "interval must be raw|hourly|daily")
    if interval != "raw" and date_from is None:
        raise HTTPException(400, "date_from wajib untuk interval agregasi")
    stmt = select(SensorData)
    cnt = select(func.count(SensorData.id))
    site_id = None
    if site_uid:
        res = await db.execute(select(Site).where(Site.uid==site_uid))
        site = res.scalar_one_or_none()
        if not site:
            return {"total": 0, "page": page, "per_page": per_page, "items": []}
        site_id = site.id
        if viewer_uids and site_uid not in viewer_uids:
            return {"total": 0, "page": page, "per_page": per_page, "items": []}
        stmt = stmt.where(SensorData.site_id==site.id)
        cnt = cnt.where(SensorData.site_id==site.id)
    elif viewer_uids:
        # No explicit site chosen: a viewer must still be confined to their sites,
        # otherwise omitting site_uid would expose every site's data (raw or aggregated).
        allowed = (await db.execute(select(Site.id).where(Site.uid.in_(viewer_uids)))).scalars().all()
        allowed = list(allowed)
        if not allowed:
            return {"total": 0, "page": page, "per_page": per_page, "items": []}
        stmt = stmt.where(SensorData.site_id.in_(allowed))
        cnt = cnt.where(SensorData.site_id.in_(allowed))
    if device_id:
        stmt = stmt.where(SensorData.device_id==device_id)
        cnt = cnt.where(SensorData.device_id==device_id)
    if date_from:
        stmt = stmt.where(SensorData.ts >= date_from)
        cnt = cnt.where(SensorData.ts >= date_from)
    if date_to:
        stmt = stmt.where(SensorData.ts < date_to)
        cnt = cnt.where(SensorData.ts < date_to)

    if interval != "raw":
        # Python-side bucketing: dialect-portable (MySQL prod / SQLite tests) and
        # windows are small (date_from is mandatory). Anomaly-flagged rows are
        # excluded from averages entirely (retained only in raw mode for audit).
        NUMERIC_FIELDS = ("ph", "tss", "debit", "nh3n", "cod", "temp", "rh",
                          "wind_speed_kmh", "wind_deg", "noise", "co", "so2", "no2",
                          "o3", "pm25", "pm10", "tvoc", "voltage", "current")
        agg_rows = (await db.execute(
            stmt.where(SensorData.quality_flag.is_(None)).order_by(SensorData.ts.asc())
        )).scalars().all()
        buckets: dict = {}
        for r in agg_rows:
            ts = r.ts
            key = ts.replace(minute=0, second=0, microsecond=0) if interval == "hourly" \
                else ts.replace(hour=0, minute=0, second=0, microsecond=0)
            b = buckets.setdefault(key, {"count": 0, "sums": {}, "ns": {}})
            b["count"] += 1
            for f in NUMERIC_FIELDS:
                v = getattr(r, f)
                if v is not None:
                    b["sums"][f] = b["sums"].get(f, 0.0) + v
                    b["ns"][f] = b["ns"].get(f, 0) + 1
        keys = sorted(buckets.keys(), reverse=(order.lower() == "desc"))
        agg_total = len(keys)
        page_keys = keys[(page - 1) * per_page: (page - 1) * per_page + per_page]
        agg_selected = set(f.strip() for f in fields.split(",") if f.strip()) if fields else None
        agg_items = []
        for k in page_keys:
            b = buckets[k]
            d = {"ts": k.isoformat(), "count": b["count"]}
            for f in NUMERIC_FIELDS:
                d[f] = round(b["sums"][f] / b["ns"][f], 3) if b["ns"].get(f) else None
            if agg_selected:
                d = {kk: vv for kk, vv in d.items() if kk in agg_selected or kk in ("ts", "count")}
            agg_items.append(d)
        return {"total": agg_total, "page": page, "per_page": per_page, "items": agg_items}

    total = (await db.execute(cnt)).scalar_one()
    order_by = SensorData.ts.desc() if order.lower()=="desc" else SensorData.ts.asc()
    rows = (await db.execute(stmt.order_by(order_by).offset((page-1)*per_page).limit(per_page))).scalars().all()

    selected = None
    if fields:
        selected = set([f.strip() for f in fields.split(",") if f.strip()])

    items = []
    for r in rows:
        d = DataOut(
            id=r.id, site_id=r.site_id, device_id=r.device_id, ts=r.ts,
            ph=r.ph, tss=r.tss, debit=r.debit, nh3n=r.nh3n, cod=r.cod, temp=r.temp, rh=r.rh,
            wind_speed_kmh=r.wind_speed_kmh, wind_deg=r.wind_deg, noise=r.noise,
            co=r.co, so2=r.so2, no2=r.no2, o3=r.o3, pm25=r.pm25, pm10=r.pm10, tvoc=r.tvoc,
            voltage=r.voltage, current=r.current, quality_flag=r.quality_flag,
            op_status=r.op_status
        ).model_dump()
        if selected:
            d = {k:v for k,v in d.items() if k in selected or k in ("id","ts","site_id","device_id","quality_flag","op_status")}
        items.append(d)

    return {"total": total, "page": page, "per_page": per_page, "items": items}

@router.get("/last")
async def last_record(site_uid: str, db: AsyncSession = Depends(get_db), viewer_uids: List[str] = Depends(get_viewer_site_uids)):
    res = await db.execute(select(Site).where(Site.uid==site_uid))
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(404, "Site not found")
    if viewer_uids and site_uid not in viewer_uids:
        raise HTTPException(403, "Forbidden")
    row = (await db.execute(select(SensorData).where(SensorData.site_id==site.id).order_by(SensorData.ts.desc()).limit(1))).scalar_one_or_none()
    if not row:
        return {}
    return {
        "id": row.id, "ts": row.ts, "site_id": row.site_id, "device_id": row.device_id,
        "ph": row.ph, "tss": row.tss, "debit": row.debit, "temp": row.temp, "rh": row.rh,
        "cod": row.cod, "nh3n": row.nh3n, "voltage": row.voltage, "current": row.current,
        "wind_speed_kmh": row.wind_speed_kmh, "wind_deg": row.wind_deg, "noise": row.noise,
        "co": row.co, "so2": row.so2, "no2": row.no2, "o3": row.o3,
        "pm25": row.pm25, "pm10": row.pm10, "tvoc": row.tvoc,
        "quality_flag": row.quality_flag,
        "op_status": row.op_status,
    }
