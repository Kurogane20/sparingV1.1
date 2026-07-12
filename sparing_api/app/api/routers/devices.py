from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from datetime import datetime, timezone, timedelta
from app.core.db import get_db
from app.api.deps import require_roles, get_viewer_site_uids, get_current_user
from app.models.models import Site, SensorDevice, SensorData, MaintenanceLog, User
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceOut, MaintenanceLogCreate, MaintenanceLogOut, DeviceHealthOut
from app.utils.device_health import compute_health_status

router = APIRouter()

@router.post("", dependencies=[Depends(require_roles("admin","operator"))])
async def create_device(data: DeviceCreate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Site).where(Site.uid==data.site_uid))
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(400, "Invalid site_uid")
    d = SensorDevice(site_id=site.id, name=data.name, modbus_addr=data.modbus_addr, model=data.model, serial_no=data.serial_no, is_active=data.is_active)
    db.add(d); await db.commit(); await db.refresh(d)
    return {"ok": True, "id": d.id}

@router.get("", response_model=list[DeviceOut])
async def list_devices(site_uid: str | None = None, db: AsyncSession = Depends(get_db), viewer_uids: list[str] = Depends(get_viewer_site_uids)):
    stmt = select(SensorDevice)
    if site_uid:
        res = await db.execute(select(Site).where(Site.uid==site_uid))
        site = res.scalar_one_or_none()
        if not site:
            return []
        stmt = stmt.where(SensorDevice.site_id==site.id)
        if viewer_uids and site_uid not in viewer_uids:
            return []
    res = await db.execute(stmt.order_by(SensorDevice.id.desc()))
    out = []
    for d in res.scalars().all():
        # Match this device's readings by numeric id OR the string device_uid
        # (serial_no/name), mirroring the /devices/{id}/health endpoint.
        conditions = [SensorData.device_id == d.id]
        if d.serial_no:
            conditions.append(SensorData.device_uid == d.serial_no)
        elif d.name:
            conditions.append(SensorData.device_uid == d.name)
        last_seen = (await db.execute(
            select(func.max(SensorData.ts)).where(or_(*conditions))
        )).scalar_one_or_none()
        out.append(DeviceOut(
            id=d.id, site_id=d.site_id, name=d.name, modbus_addr=d.modbus_addr,
            model=d.model, serial_no=d.serial_no, is_active=d.is_active,
            last_seen=last_seen, status=compute_health_status(last_seen),
        ))
    return out

@router.get("/{id}", response_model=DeviceOut)
async def get_device(id: int, db: AsyncSession = Depends(get_db), viewer_uids: list[str] = Depends(get_viewer_site_uids)):
    res = await db.execute(select(SensorDevice).where(SensorDevice.id==id))
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Not found")
    if viewer_uids:
        site = (await db.execute(select(Site).where(Site.id==d.site_id))).scalar_one_or_none()
        if site and site.uid not in viewer_uids:
            raise HTTPException(403, "Forbidden")
    return DeviceOut(id=d.id, site_id=d.site_id, name=d.name, modbus_addr=d.modbus_addr, model=d.model, serial_no=d.serial_no, is_active=d.is_active)

@router.patch("/{id}", dependencies=[Depends(require_roles("admin","operator"))])
async def update_device(id: int, data: DeviceUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SensorDevice).where(SensorDevice.id==id))
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Not found")
    for k,v in data.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    await db.commit()
    return {"ok": True}

@router.delete("/{id}", dependencies=[Depends(require_roles("admin"))])
async def delete_device(id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete: set is_active to False instead of deleting from database"""
    res = await db.execute(select(SensorDevice).where(SensorDevice.id==id))
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Not found")
    # Soft delete to preserve data integrity
    d.is_active = False
    await db.commit()
    return {"ok": True, "message": "Device deactivated"}


@router.get("/{id}/health", response_model=DeviceHealthOut)
async def get_device_health(
    id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    d = (await db.execute(select(SensorDevice).where(SensorDevice.id == id))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Not found")

    if viewer_uids:
        _site = (await db.execute(select(Site).where(Site.id == d.site_id))).scalar_one_or_none()
        if _site and _site.uid not in viewer_uids:
            raise HTTPException(403, "Forbidden")

    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    # Build device filter with fallback to device_uid when device_id is NULL
    conditions = [SensorData.device_id == id]
    if d.serial_no:
        conditions.append(SensorData.device_uid == d.serial_no)
    elif d.name:
        conditions.append(SensorData.device_uid == d.name)
    device_filter = or_(*conditions)

    last_seen: datetime | None = (await db.execute(
        select(func.max(SensorData.ts)).where(device_filter)
    )).scalar_one_or_none()

    count_24h = (await db.execute(
        select(func.count(SensorData.id)).where(
            device_filter, SensorData.ts >= cutoff_24h
        )
    )).scalar_one() or 0

    count_7d = (await db.execute(
        select(func.count(SensorData.id)).where(
            device_filter, SensorData.ts >= cutoff_7d
        )
    )).scalar_one() or 0

    last_calibration_at: datetime | None = (await db.execute(
        select(MaintenanceLog.performed_at)
        .where(MaintenanceLog.device_id == id, MaintenanceLog.type == "calibration")
        .order_by(MaintenanceLog.performed_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    next_calibration_at: datetime | None = (await db.execute(
        select(MaintenanceLog.next_due_at)
        .where(
            MaintenanceLog.device_id == id,
            MaintenanceLog.type == "calibration",
            MaintenanceLog.next_due_at.isnot(None),
        )
        .order_by(MaintenanceLog.performed_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    return DeviceHealthOut(
        device_id=id,
        last_seen=last_seen,
        status=compute_health_status(last_seen),
        data_count_24h=count_24h,
        data_count_7d=count_7d,
        last_calibration_at=last_calibration_at,
        next_calibration_at=next_calibration_at,
    )


@router.get("/{id}/maintenance", response_model=list[MaintenanceLogOut])
async def list_maintenance_logs(
    id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    d = (await db.execute(select(SensorDevice).where(SensorDevice.id == id))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Not found")

    if viewer_uids:
        _site = (await db.execute(select(Site).where(Site.id == d.site_id))).scalar_one_or_none()
        if _site and _site.uid not in viewer_uids:
            raise HTTPException(403, "Forbidden")

    result = await db.execute(
        select(MaintenanceLog, User.name.label("performer_name"))
        .outerjoin(User, User.id == MaintenanceLog.performed_by_user_id)
        .where(MaintenanceLog.device_id == id)
        .order_by(MaintenanceLog.performed_at.desc())
    )
    rows = result.all()
    return [
        MaintenanceLogOut(
            id=log.id,
            device_id=log.device_id,
            type=log.type,
            notes=log.notes,
            performed_by_user_id=log.performed_by_user_id,
            performed_by_name=performer_name,
            performed_at=log.performed_at,
            next_due_at=log.next_due_at,
            created_at=log.created_at,
        )
        for log, performer_name in rows
    ]


@router.post("/{id}/maintenance", response_model=MaintenanceLogOut,
             dependencies=[Depends(require_roles("admin", "operator"))])
async def add_maintenance_log(
    id: int,
    data: MaintenanceLogCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    d = (await db.execute(select(SensorDevice).where(SensorDevice.id == id))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Not found")

    log = MaintenanceLog(
        device_id=id,
        type=data.type,
        notes=data.notes,
        performed_by_user_id=user.id,
        performed_at=data.performed_at,
        next_due_at=data.next_due_at,
        created_at=datetime.now(timezone.utc),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    performer = (await db.execute(select(User).where(User.id == user.id))).scalar_one_or_none()
    return MaintenanceLogOut(
        id=log.id,
        device_id=log.device_id,
        type=log.type,
        notes=log.notes,
        performed_by_user_id=log.performed_by_user_id,
        performed_by_name=performer.name if performer else None,
        performed_at=log.performed_at,
        next_due_at=log.next_due_at,
        created_at=log.created_at,
    )


@router.delete("/{id}/maintenance/{log_id}",
               dependencies=[Depends(require_roles("admin", "operator"))])
async def delete_maintenance_log(
    id: int,
    log_id: int,
    db: AsyncSession = Depends(get_db),
):
    log = (await db.execute(
        select(MaintenanceLog).where(
            MaintenanceLog.id == log_id,
            MaintenanceLog.device_id == id,
        )
    )).scalar_one_or_none()
    if not log:
        raise HTTPException(404, "Log not found")
    await db.delete(log)
    await db.commit()
    return {"ok": True}
