from pydantic import BaseModel
from datetime import datetime

# --- AlertRule schemas ---

class AlertRuleCreate(BaseModel):
    field: str
    warning_min: float | None = None
    warning_max: float | None = None
    danger_min: float | None = None
    danger_max: float | None = None
    is_active: bool = True

class AlertRuleUpdate(BaseModel):
    warning_min: float | None = None
    warning_max: float | None = None
    danger_min: float | None = None
    danger_max: float | None = None
    is_active: bool | None = None

class AlertRuleOut(BaseModel):
    id: int
    site_id: int
    field: str
    warning_min: float | None
    warning_max: float | None
    danger_min: float | None
    danger_max: float | None
    is_active: bool

# --- Alert schemas ---

class AlertOut(BaseModel):
    id: int
    site_id: int
    site_uid: str
    site_name: str
    device_uid: str | None
    field: str
    value: float
    threshold_type: str
    status: str
    triggered_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by_user_id: int | None
    category: str = "compliance"
    anomaly_type: str | None = None
    detail: str | None = None

class AlertCountOut(BaseModel):
    count: int
