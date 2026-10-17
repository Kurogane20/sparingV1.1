"""Pure, deterministic helpers for monitoring chart time series.

This module deliberately knows nothing about SQLAlchemy or FastAPI.  Rows are
normalised once, and all downstream calculations operate on that same accepted
sample definition so chart points cannot disagree with summary statistics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.utils.monitoring_config import (
    ALLOWED_RESOLUTIONS_SECONDS,
    DEFAULT_CADENCE_SECONDS,
    DEFAULT_MAX_CHART_POINTS,
    DEFAULT_MAX_RANGE_DAYS,
)
from app.utils.quality import parse_quality_fields
from app.utils.time import as_utc


@dataclass(frozen=True)
class NormalizedReading:
    ts: datetime
    row_id: int | None
    values: Mapping[str, float | None]
    quality_flag: str | None = None
    op_status: int | None = None
    classification: str = "accepted"
    # Fields the quality classification applies to; None = whole row (legacy flag).
    flagged_fields: frozenset[str] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ts", as_utc(self.ts))
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    @property
    def status(self) -> str:
        return self.classification

    def flags_field(self, field: str) -> bool:
        """True when this row's quality classification applies to `field`."""
        if self.classification not in {"sensor_error", "check_required"}:
            return False
        return self.flagged_fields is None or field in self.flagged_fields


@dataclass(frozen=True)
class BucketPoint:
    ts: datetime
    avg: float | None
    min: float | None
    max: float | None
    count: int

    @property
    def value(self) -> float | None:
        return self.avg

    @property
    def timestamp(self) -> datetime:
        return self.ts


@dataclass(frozen=True)
class AvailabilitySummary:
    expected_slots: int
    delivered_slots: int
    missing_slots: int
    availability_pct: float
    leading_missing: int = 0
    internal_missing: int = 0
    trailing_missing: int = 0
    active_expected_slots: int = 0
    active_missing_slots: int = 0
    active_from: datetime | None = None
    active_to: datetime | None = None

    @property
    def availability(self) -> float:
        return self.availability_pct

    @property
    def expected(self) -> int:
        return self.expected_slots

    @property
    def delivered(self) -> int:
        return self.delivered_slots

    @property
    def missing(self) -> int:
        return self.missing_slots


@dataclass(frozen=True)
class TimeseriesWindow:
    date_from: datetime
    date_to: datetime
    effective_to: datetime
    preset: str
    timezone_name: str


def _row_attr(row: object, name: str, default=None):
    if isinstance(row, Mapping):
        return row.get(name, default)
    return getattr(row, name, default)


def _finite_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _plausible(field_name: str, value: float | None) -> bool:
    """Reject only hard-invalid physical values; anomaly flags remain visible."""
    if value is None:
        return True
    if field_name == "ph":
        return 0.0 <= value <= 14.0
    if field_name in {"tss", "debit", "cod", "nh3n", "rh", "noise", "co", "so2", "no2", "o3", "pm25", "pm10", "tvoc", "current", "voltage"}:
        return value >= 0.0
    if field_name == "wind_speed_kmh":
        return value >= 0.0
    if field_name == "wind_deg":
        return 0.0 <= value <= 360.0
    return True


def normalize_sensor_rows(
    rows: Iterable[object], *, fields: Sequence[str]
) -> tuple[list[NormalizedReading], list[str]]:
    """Normalize timestamps/values and deterministically repair duplicate times.

    For duplicate timestamps the row with the greatest numeric id wins (the
    latest input row wins when ids are absent/tied), matching the database's
    insertion identity while remaining deterministic for plain test objects.
    """
    materialized = list(rows)
    warnings: list[str] = []
    candidates: list[tuple[datetime, int, NormalizedReading]] = []
    invalid_ts = False
    out_of_order = False
    previous: datetime | None = None
    for position, row in enumerate(materialized):
        raw_ts = _row_attr(row, "ts")
        try:
            ts = as_utc(raw_ts)
            if ts is None:
                raise ValueError
        except (AttributeError, TypeError, ValueError, OverflowError):
            invalid_ts = True
            continue
        if previous is not None and ts < previous:
            out_of_order = True
        previous = ts
        values = {}
        for name in fields:
            number = _finite_number(_row_attr(row, name))
            values[name] = number if _plausible(name, number) else None
        raw_id = _row_attr(row, "id")
        try:
            row_id = int(raw_id) if raw_id is not None else None
        except (TypeError, ValueError):
            row_id = None
        candidates.append((ts, position, NormalizedReading(
            ts=ts,
            row_id=row_id,
            values=values,
            quality_flag=_row_attr(row, "quality_flag"),
            flagged_fields=parse_quality_fields(_row_attr(row, "quality_fields")),
            op_status=_row_attr(row, "op_status"),
            classification=(
                "operational" if _row_attr(row, "op_status") is not None
                else "sensor_error" if str(_row_attr(row, "quality_flag") or "").lower()
                == "sensor_error"
                else "check_required" if str(_row_attr(row, "quality_flag") or "").lower() in {
                    "anomaly", "spike", "rapid_change", "rapid-change", "check_required"
                }
                else "accepted"
            ),
        )))
    if invalid_ts:
        warnings.append("invalid_timestamps_dropped")
    if out_of_order:
        warnings.append("timestamps_sorted")
    candidates.sort(key=lambda item: (item[0], item[1]))
    deduped: list[NormalizedReading] = []
    duplicate = False
    index = 0
    while index < len(candidates):
        ts = candidates[index][0]
        group = []
        while index < len(candidates) and candidates[index][0] == ts:
            group.append(candidates[index])
            index += 1
        if len(group) > 1:
            duplicate = True
        # id is the primary tie breaker; position gives deterministic fallback.
        winner = max(group, key=lambda item: (item[2].row_id is not None, item[2].row_id or -1, item[1]))
        deduped.append(winner[2])
    if duplicate:
        warnings.append("duplicate_timestamps_repaired")
    return deduped, warnings


def _coerce_window_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    try:
        return as_utc(value)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("invalid_datetime") from None


def _coerce_custom_boundary_dt(value: datetime | None, zone: ZoneInfo) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=zone).astimezone(timezone.utc)
    return _coerce_window_dt(value)


def resolve_timeseries_window(
    preset: str = "today",
    timezone_name: str = "Asia/Jakarta",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    now_utc: datetime | None = None,
    max_range_days: int = DEFAULT_MAX_RANGE_DAYS,
) -> TimeseriesWindow:
    """Resolve a local-calendar preset/custom exclusive range into UTC."""
    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("invalid_timezone") from None
    now = _coerce_window_dt(now_utc) or datetime.now(timezone.utc)
    key = (preset or "today").lower().replace("-", "_")
    if key in {"custom", "range"}:
        start = _coerce_custom_boundary_dt(date_from, zone)
        end = _coerce_custom_boundary_dt(date_to, zone)
        if start is None or end is None:
            raise ValueError("custom_range_required")
    elif key in {"today", "day"}:
        local_now = now.astimezone(zone)
        local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = local_start.astimezone(timezone.utc)
        end = now
    else:
        durations = {
            "1h": timedelta(hours=1), "hour": timedelta(hours=1), "last_1h": timedelta(hours=1),
            "6h": timedelta(hours=6), "last_6h": timedelta(hours=6),
            "12h": timedelta(hours=12), "last_12h": timedelta(hours=12),
            "24h": timedelta(days=1), "last_24h": timedelta(days=1), "day_24h": timedelta(days=1),
            "7d": timedelta(days=7), "last_7d": timedelta(days=7), "last_7_days": timedelta(days=7),
            "30d": timedelta(days=30), "last_30d": timedelta(days=30), "last_30_days": timedelta(days=30),
        }
        if key not in durations:
            raise ValueError("invalid_preset")
        end = now
        start = end - durations[key]
    if end <= start:
        raise ValueError("invalid_range")
    if (end - start).total_seconds() > max_range_days * 86400:
        raise ValueError("range_too_large")
    return TimeseriesWindow(start, end, min(end, now), key, timezone_name)


def choose_resolution_seconds(
    duration_seconds: float,
    *,
    max_points: int = DEFAULT_MAX_CHART_POINTS,
    cadence_seconds: int = DEFAULT_CADENCE_SECONDS,
) -> int:
    if duration_seconds <= 0:
        return next(
            (
                resolution
                for resolution in ALLOWED_RESOLUTIONS_SECONDS
                if resolution >= cadence_seconds
            ),
            ALLOWED_RESOLUTIONS_SECONDS[-1],
        )
    if max_points <= 0 or cadence_seconds <= 0:
        raise ValueError("invalid_max_points")
    for resolution in ALLOWED_RESOLUTIONS_SECONDS:
        if (
            resolution >= cadence_seconds
            and math.ceil(duration_seconds / resolution) <= max_points
        ):
            return resolution
    raise ValueError("max_points_unachievable")


def _accepted_value(row: object, field: str, sensor_error_timestamps: set[datetime] | None = None) -> tuple[datetime | None, float | None]:
    try:
        ts = as_utc(_row_attr(row, "ts"))
    except (AttributeError, TypeError, ValueError):
        return None, None
    if ts is None or _row_attr(row, "op_status") is not None:
        return ts, None
    if sensor_error_timestamps and ts in {as_utc(t) for t in sensor_error_timestamps}:
        return ts, None
    values = _row_attr(row, "values", {})
    value = values.get(field) if isinstance(values, Mapping) else _row_attr(row, field)
    return ts, value if _plausible(field, _finite_number(value)) else None


def _range_rows(rows: Iterable[object], field: str, date_from: datetime, date_to: datetime, sensor_error_timestamps: set[datetime] | None = None) -> list[tuple[datetime, float]]:
    start, end = as_utc(date_from), as_utc(date_to)
    result = []
    for row in rows:
        ts, value = _accepted_value(row, field, sensor_error_timestamps)
        if ts is not None and start <= ts < end and value is not None:
            result.append((ts, float(value)))
    return result


def aggregate_field_points(
    rows: Iterable[object], field: str, date_from: datetime, date_to: datetime,
    resolution_seconds: int,
    sensor_error_timestamps: set[datetime] | None = None,
) -> list[BucketPoint]:
    start, end = as_utc(date_from), as_utc(date_to)
    if resolution_seconds <= 0 or end <= start:
        return []
    slots = math.ceil((end - start).total_seconds() / resolution_seconds)
    grouped: list[list[float]] = [[] for _ in range(slots)]
    for ts, value in _range_rows(rows, field, start, end, sensor_error_timestamps):
        index = int((ts - start).total_seconds() // resolution_seconds)
        if 0 <= index < slots:
            grouped[index].append(value)
    points = []
    for index, values in enumerate(grouped):
        bucket_ts = start + timedelta(seconds=index * resolution_seconds)
        points.append(BucketPoint(
            ts=bucket_ts,
            avg=sum(values) / len(values) if values else None,
            min=min(values) if values else None,
            max=max(values) if values else None,
            count=len(values),
        ))
    return points


def compute_field_statistics(
    rows: Iterable[object], field: str, sensor_error_timestamps: set[datetime] | None = None,
    date_from: datetime | None = None, date_to: datetime | None = None,
) -> dict | None:
    values: list[float]
    if date_from is not None and date_to is not None:
        values = [v for _, v in _range_rows(rows, field, date_from, date_to, sensor_error_timestamps)]
    else:
        values = []
        for row in rows:
            _, value = _accepted_value(row, field, sensor_error_timestamps)
            if value is not None:
                values.append(float(value))
    if not values:
        return None
    values.sort()
    return {"count": len(values), "avg": sum(values) / len(values), "min": values[0], "max": values[-1]}


def compute_field_availability(
    rows: Iterable[object], field: str, date_from: datetime, date_to: datetime,
    cadence_seconds: int, sensor_error_timestamps: set[datetime] | None = None,
    effective_to: datetime | None = None,
) -> AvailabilitySummary:
    start, end = as_utc(date_from), as_utc(date_to)
    if effective_to is not None:
        resolved_end = as_utc(effective_to)
        if resolved_end is not None:
            end = min(end, resolved_end)
    if cadence_seconds <= 0 or end <= start:
        return AvailabilitySummary(0, 0, 0, 100.0)
    expected = math.ceil((end - start).total_seconds() / cadence_seconds)
    delivered_slots = {
        int((ts - start).total_seconds() // cadence_seconds)
        for ts, _ in _range_rows(rows, field, start, end, sensor_error_timestamps)
    }
    delivered_slots = {slot for slot in delivered_slots if 0 <= slot < expected}
    missing = expected - len(delivered_slots)
    if not delivered_slots:
        return AvailabilitySummary(expected, 0, expected, 0.0, leading_missing=expected)
    first, last = min(delivered_slots), max(delivered_slots)
    leading = first
    trailing = expected - last - 1
    internal = max(0, (last - first + 1) - len(delivered_slots))
    active_expected = last - first + 1
    return AvailabilitySummary(
        expected_slots=expected,
        delivered_slots=len(delivered_slots),
        missing_slots=missing,
        availability_pct=(len(delivered_slots) / expected * 100.0) if expected else 100.0,
        leading_missing=leading,
        internal_missing=internal,
        trailing_missing=trailing,
        active_expected_slots=active_expected,
        active_missing_slots=active_expected - len(delivered_slots),
        active_from=start + timedelta(seconds=first * cadence_seconds),
        active_to=start + timedelta(seconds=(last + 1) * cadence_seconds),
    )
