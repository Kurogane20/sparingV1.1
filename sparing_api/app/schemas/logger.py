from datetime import datetime

from pydantic import BaseModel


class LoggerStatusOut(BaseModel):
    site_id: int
    site_uid: str
    site_name: str
    state: str
    state_since: datetime | None = None
    last_heartbeat_at: datetime | None = None
    minutes_since_heartbeat: float | None = None
    logger_version: str | None = None
    uptime_s: int | None = None
    op_status: int | None = None
    ph_ok: bool | None = None
    tss_ok: bool | None = None
    debit_ok: bool | None = None
    cod_ok: bool | None = None
    nh3n_ok: bool | None = None
    consec_fail: int | None = None
    internet_ok: bool | None = None
    last_send_ok_mm: bool | None = None
    last_send_ok_klhk: bool | None = None
    buffer_depth: int | None = None
    daily_sent: int | None = None
    cpu_temp: float | None = None
    cpu_pct: float | None = None
    mem_pct: float | None = None
    disk_pct: float | None = None


class LoggerEventOut(BaseModel):
    id: int
    site_id: int
    site_uid: str
    site_name: str
    event_uid: str
    type: str
    ts: datetime
    received_at: datetime
    severity: str
    detail: str | None = None
