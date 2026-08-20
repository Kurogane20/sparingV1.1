from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from datetime import datetime, timezone, timedelta
from app.core.db import get_db
from app.api.deps import require_roles, get_viewer_site_uids, get_current_user
from app.models.models import Site, SensorDevice, SensorData, MaintenanceLog, User
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceOut, MaintenanceLogCreate, MaintenanceLogOut, DeviceHealthOut
from app.utils.device_health import compute_health_status

router = APIRouter()


def _device_data_filter(d: "SensorDevice"):
    """SQL filter selecting a device's own sensor_data.

    Primary match is the numeric FK (device_id == d.id), which is reliably set on
    current data. The device_uid (serial_no/name) fallback covers legacy NULL-FK
    rows but MUST be constrained to the device's own site — device names are not
    unique across sites, so an unscoped match bleeds the whole fleet's readings
    into every device's status.
    """
    conditions = [SensorData.device_id == d.id]
    uid = d.serial_no or d.name
    if uid:
        conditions.append(and_(SensorData.site_id == d.site_id,
                               SensorData.device_uid == uid))
    return or_(*conditions)

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
        # Match this device's readings by numeric id, OR — for legacy rows with a
        # NULL device_id — by the string device_uid but ONLY within this device's
        # own site. Device names/serials are NOT unique across sites (every site's
        # device is literally "DEVICE-001"), so an unscoped device_uid match makes
        # every device inherit the whole fleet's newest reading. Mirror this in
        # /devices/{id}/health.
        last_seen = (await db.execute(
            select(func.max(SensorData.ts)).where(_device_data_filter(d))
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

    # Same site-scoped filter as list_devices (device names aren't unique across
    # sites, so the device_uid fallback must be constrained to this device's site).
    device_filter = _device_data_filter(d)

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

    # #14: the nearest upcoming maintenance due date across ALL maintenance types,
    # and whether it (or the calibration) is overdue. A due date in the past with
    # no later maintenance means the work hasn't been done yet.
    next_maintenance_due_at: datetime | None = (await db.execute(
        select(func.min(MaintenanceLog.next_due_at))
        .where(
            MaintenanceLog.device_id == id,
            MaintenanceLog.next_due_at.isnot(None),
            MaintenanceLog.next_due_at >= now,
        )
    )).scalar_one_or_none()
    # If nothing is upcoming, fall back to the latest past due date (so overdue is visible).
    if next_maintenance_due_at is None:
        next_maintenance_due_at = (await db.execute(
            select(func.max(MaintenanceLog.next_due_at))
            .where(MaintenanceLog.device_id == id, MaintenanceLog.next_due_at.isnot(None))
        )).scalar_one_or_none()

    def _aware(dt):
        return None if dt is None else (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc))

    nm = _aware(next_maintenance_due_at)
    nc = _aware(next_calibration_at)
    days_until_due = (nm - now).days if nm is not None else None
    maintenance_overdue = nm is not None and nm < now
    calibration_overdue = nc is not None and nc < now

    return DeviceHealthOut(
        device_id=id,
        last_seen=last_seen,
        status=compute_health_status(last_seen),
        data_count_24h=count_24h,
        data_count_7d=count_7d,
        last_calibration_at=last_calibration_at,
        next_calibration_at=next_calibration_at,
        next_maintenance_due_at=next_maintenance_due_at,
        days_until_due=days_until_due,
        maintenance_overdue=maintenance_overdue,
        calibration_overdue=calibration_overdue,
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
            field=log.field,
            before_value=log.before_value,
            after_value=log.after_value,
            offset=log.offset,
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

    # Derive the offset from before/after when the caller didn't supply one.
    offset = data.offset
    if offset is None and data.before_value is not None and data.after_value is not None:
        offset = data.after_value - data.before_value

    log = MaintenanceLog(
        device_id=id,
        type=data.type,
        notes=data.notes,
        performed_by_user_id=user.id,
        performed_at=data.performed_at,
        next_due_at=data.next_due_at,
        field=data.field,
        before_value=data.before_value,
        after_value=data.after_value,
        offset=offset,
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
        field=log.field,
        before_value=log.before_value,
        after_value=log.after_value,
        offset=log.offset,
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
