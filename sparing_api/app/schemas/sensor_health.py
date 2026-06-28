from pydantic import BaseModel
from datetime import datetime


class SensorHealthOut(BaseModel):
    field: str
    status: str
    anomaly_type: str | None = None
    reason: str | None = None
    last_value: float | None = None
    updated_at: datetime | None = None
