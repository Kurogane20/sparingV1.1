from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from app.core.db import get_db
from app.api.deps import get_current_user, get_viewer_site_uids
from app.models.models import Alert, Site, User
from app.schemas.alert import AlertOut, AlertCountOut

router = APIRouter()


async def _build_alert_out(alert: Alert, db: AsyncSession) -> AlertOut:
    site_result = await db.execute(select(Site).where(Site.id == alert.site_id))
    site = site_result.scalar_one_or_none()
    return AlertOut(
        id=alert.id,
        site_id=alert.site_id,
        site_uid=site.uid if site else "",
        site_name=site.name if site else "",
        device_uid=alert.device_uid,
        field=alert.field,
        value=alert.value,
        threshold_type=alert.threshold_type,
        status=alert.status,
        triggered_at=alert.triggered_at,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by_user_id=alert.acknowledged_by_user_id,
    )


@router.get("/count", response_model=AlertCountOut)
async def get_alert_count(
    status: str = Query(default="active"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    stmt = select(func.count(Alert.id)).where(Alert.status == status)
    if viewer_uids:
        site_ids_result = await db.execute(
            select(Site.id).where(Site.uid.in_(viewer_uids))
        )
        site_ids = list(site_ids_result.scalars().all())
        stmt = stmt.where(Alert.site_id.in_(site_ids))
    result = await db.execute(stmt)
    return AlertCountOut(count=result.scalar_one() or 0)


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    status: str = Query(default="active"),
    site_uid: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    stmt = select(Alert).where(Alert.status == status)

    if site_uid:
        site_result = await db.execute(select(Site).where(Site.uid == site_uid))
        site = site_result.scalar_one_or_none()
        if site:
            stmt = stmt.where(Alert.site_id == site.id)
    elif viewer_uids:
        site_ids_result = await db.execute(
            select(Site.id).where(Site.uid.in_(viewer_uids))
        )
        site_ids = list(site_ids_result.scalars().all())
        stmt = stmt.where(Alert.site_id.in_(site_ids))

    stmt = stmt.order_by(Alert.triggered_at.desc()).limit(limit)
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    return [await _build_alert_out(a, db) for a in alerts]


@router.patch("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by_user_id = user.id
    await db.commit()
    return {"ok": True}


@router.patch("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = "resolved"
    await db.commit()
    return {"ok": True}
