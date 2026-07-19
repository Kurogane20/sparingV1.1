from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from app.core.db import get_db
from app.api.deps import get_current_user, get_viewer_site_uids
from app.models.models import Alert, Site, User
from app.schemas.alert import AlertOut, AlertCountOut, AlertActionIn

router = APIRouter()


async def _build_alert_out(alert: Alert, db: AsyncSession) -> AlertOut:
    site_result = await db.execute(select(Site).where(Site.id == alert.site_id))
    site = site_result.scalar_one_or_none()
    followup_by_name = None
    if alert.followup_by_user_id:
        ures = await db.execute(select(User).where(User.id == alert.followup_by_user_id))
        u = ures.scalar_one_or_none()
        followup_by_name = u.name if u else None
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
        category=getattr(alert, "category", "compliance"),
        anomaly_type=alert.anomaly_type,
        detail=alert.detail,
        followup_note=alert.followup_note,
        followup_by_name=followup_by_name,
        followup_at=alert.followup_at,
        resolved_at=alert.resolved_at,
    )


@router.get("/count", response_model=AlertCountOut)
async def get_alert_count(
    status: str = Query(default="active"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    stmt = select(func.count(Alert.id)).where(Alert.status == status)
    if user._role == "viewer":
        if not viewer_uids:
            return AlertCountOut(count=0)
        site_ids_result = await db.execute(
            select(Site.id).where(Site.uid.in_(viewer_uids))
        )
        site_ids = list(site_ids_result.scalars().all())
        stmt = stmt.where(Alert.site_id.in_(site_ids))
    result = await db.execute(stmt)
    return AlertCountOut(count=result.scalar_one() or 0)


@router.get("")
async def list_alerts(
    status: str = Query(default="active"),
    site_uid: str | None = Query(default=None),
    category: str | None = Query(default=None),
    threshold_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    page: int | None = Query(default=None, ge=1),
    per_page: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    """Bare list (existing behavior) when `page` is absent; {items,total,page,per_page}
    wrapper when `page` is given (Alarm page). Filters are additive."""
    conds = []
    if status != "all":
        conds.append(Alert.status == status)
    if category:
        conds.append(Alert.category == category)
    if threshold_type:
        conds.append(Alert.threshold_type == threshold_type)
    if date_from:
        conds.append(Alert.triggered_at >= date_from)
    if date_to:
        conds.append(Alert.triggered_at < date_to)

    if user._role == "viewer":
        if not viewer_uids:
            return {"items": [], "total": 0, "page": page, "per_page": per_page} if page else []
        if site_uid and site_uid not in viewer_uids:
            raise HTTPException(403, "Forbidden")

    if site_uid:
        site_result = await db.execute(select(Site).where(Site.uid == site_uid))
        site = site_result.scalar_one_or_none()
        if site:
            conds.append(Alert.site_id == site.id)
    elif user._role == "viewer":
        site_ids_result = await db.execute(select(Site.id).where(Site.uid.in_(viewer_uids)))
        conds.append(Alert.site_id.in_(list(site_ids_result.scalars().all())))

    stmt = select(Alert).where(*conds).order_by(Alert.triggered_at.desc())

    if page is None:
        rows = (await db.execute(stmt.limit(limit))).scalars().all()
        return [await _build_alert_out(a, db) for a in rows]

    total = (await db.execute(select(func.count(Alert.id)).where(*conds))).scalar_one()
    rows = (await db.execute(stmt.offset((page - 1) * per_page).limit(per_page))).scalars().all()
    items = [await _build_alert_out(a, db) for a in rows]
    return {"items": items, "total": total, "page": page, "per_page": per_page}


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
    body: AlertActionIn | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Close an alert. A follow-up note is mandatory (SOP: no closure without a record)."""
    note = ((body.note if body else None) or "").strip()
    if not note:
        raise HTTPException(400, "Catatan tindak lanjut wajib diisi")
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    now = datetime.now(timezone.utc)
    alert.status = "resolved"
    alert.resolved_at = now
    alert.followup_note = note
    alert.followup_by_user_id = user.id
    if alert.followup_at is None:
        alert.followup_at = now
    await db.commit()
    return {"ok": True}


@router.patch("/{alert_id}/followup")
async def followup_alert(
    alert_id: int,
    body: AlertActionIn | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark an alert as being worked on (Dalam tindak lanjut). Note optional at this stage."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    now = datetime.now(timezone.utc)
    alert.status = "acknowledged"
    alert.acknowledged_at = now
    alert.followup_at = now
    alert.followup_by_user_id = user.id
    if body and body.note and body.note.strip():
        alert.followup_note = body.note.strip()
    await db.commit()
    return {"ok": True}
