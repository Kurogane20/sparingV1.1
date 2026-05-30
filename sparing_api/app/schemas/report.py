from pydantic import BaseModel
from datetime import datetime

class BakuMutuOut(BaseModel):
    min: float | None
    max: float | None
    unit: str

class StatsOut(BaseModel):
    avg: float | None
    min: float | None
    max: float | None
    std_dev: float | None
    count: int

class ParameterReportOut(BaseModel):
    field: str
    label: str
    baku_mutu: BakuMutuOut
    stats: StatsOut
    compliance_pct: float
    violation_count: int
    trend: str

class DailySummaryOut(BaseModel):
    date: str  # YYYY-MM-DD
    ph_avg: float | None = None
    tss_avg: float | None = None
    cod_avg: float | None = None
    nh3n_avg: float | None = None
    debit_avg: float | None = None
    temp_avg: float | None = None

class ViolationOut(BaseModel):
    ts: datetime
    field: str
    value: float
    limit_type: str  # above_max | below_min
    limit: float

class ReportSummaryOut(BaseModel):
    total_records: int
    compliance_overall: float
    overall_status: str

class ReportOut(BaseModel):
    site: dict
    period: dict
    generated_at: datetime
    summary: ReportSummaryOut
    parameters: list[ParameterReportOut]
    daily_summary: list[DailySummaryOut]
    violations: list[ViolationOut]
