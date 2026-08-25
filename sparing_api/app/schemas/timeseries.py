from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TimeseriesMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_uid: str
    timezone: str
    date_from: datetime
    date_to: datetime
    generated_at: datetime
    rules_evaluated_at: datetime
    cadence_seconds: int
    resolution_seconds: int
    is_aggregated: bool
    max_points: int
    availability_pct: float
    is_partial: bool
    partial_reasons: list[str] = Field(default_factory=list)
    normalization_warnings: list[str] = Field(default_factory=list)


class TimeseriesPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: datetime
    value: float | None
    min: float | None
    max: float | None
    count: int


class TimeseriesSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    unit: str
    points: list[TimeseriesPoint] = Field(default_factory=list)


class FieldStatistics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current: float | None
    current_ts: datetime | None
    current_quality: str | None
    avg: float | None
    min: float | None
    max: float | None
    count: int
    availability_pct: float
    status: str
    status_label: str
    status_reason: str
    status_severity: str


class TimeseriesThreshold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    warning_min: float | None
    warning_max: float | None
    danger_min: float | None
    danger_max: float | None
    unit: str
    label: str
    regulation: str | None
    source: str


class TimeseriesEventContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline: float | None = None
    current: float | None = None
    delta: float | None = None
    percent: float | None = None
    interval_seconds: int | None = None
    points: int | None = None


class TimeseriesEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    ts: datetime
    end_ts: datetime | None
    type: str
    field: str | None
    severity: str
    direction: str | None
    label: str
    context: TimeseriesEventContext


class TimeseriesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: TimeseriesMeta
    series: dict[str, TimeseriesSeries]
    statistics: dict[str, FieldStatistics]
    thresholds: dict[str, TimeseriesThreshold]
    events: list[TimeseriesEvent] = Field(default_factory=list)
    event_total: int
