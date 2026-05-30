from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class DeviceCreate(BaseModel):
    site_uid: str
    name: str
    modbus_addr: int | None = None
    model: str | None = None
    serial_no: str | None = None
    is_active: bool = True

class DeviceUpdate(BaseModel):
    name: str | None = None
    modbus_addr: int | None = None
    model: str | None = None
    serial_no: str | None = None
    is_active: bool | None = None

class DeviceOut(BaseModel):
    id: int
    site_id: int
    name: str
    modbus_addr: int | None = None
    model: str | None = None
    serial_no: str | None = None
    is_active: bool

class MaintenanceLogCreate(BaseModel):
    type: str  # calibration | repair | inspection | note
    notes: str | None = None
    performed_at: datetime
    next_due_at: datetime | None = None

class MaintenanceLogOut(BaseModel):
    id: int
    device_id: int
    type: str
    notes: str | None
    performed_by_user_id: int | None
    performed_by_name: str | None
    performed_at: datetime
    next_due_at: datetime | None
    created_at: datetime

class DeviceHealthOut(BaseModel):
    device_id: int
    last_seen: datetime | None
    status: str  # online | warning | offline | unknown
    data_count_24h: int
    data_count_7d: int
    last_calibration_at: datetime | None = None
    next_calibration_at: datetime | None = None
