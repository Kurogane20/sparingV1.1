from pydantic import BaseModel
from datetime import datetime

# --- AlertRule schemas ---

class AlertRuleCreate(BaseModel):
    field: str
    warning_min: float | None = None
    warning_max: float | None = None
    danger_min: float | None = None
    danger_max: float | None = None
    reference_label: str | None = None
    regulation: str | None = None
    is_active: bool = True

class AlertRuleUpdate(BaseModel):
    warning_min: float | None = None
    warning_max: float | None = None
    danger_min: float | None = None
    danger_max: float | None = None
    reference_label: str | None = None
    regulation: str | None = None
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
    reference_label: str | None = None
    regulation: str | None = None
    updated_at: datetime
    updated_by_user_id: int | None = None

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
    followup_note: str | None = None
    followup_by_name: str | None = None
    followup_at: datetime | None = None
    resolved_at: datetime | None = None

class AlertCountOut(BaseModel):
    count: int

class AlertActionIn(BaseModel):
    note: str | None = None
