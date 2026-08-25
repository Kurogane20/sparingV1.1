from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    AlertRule,
    LoggerEvent,
    OperationalRule,
    SensorData,
    SensorHealth,
    Site,
    SiteMonitoringConfig,
)
from app.schemas.timeseries import (
    FieldStatistics,
    TimeseriesMeta,
    TimeseriesPoint,
    TimeseriesResponse,
    TimeseriesSeries,
    TimeseriesThreshold,
)
from app.utils.monitoring_config import (
    DEFAULT_CADENCE_SECONDS,
    DEFAULT_MAX_CHART_POINTS,
    DEFAULT_MAX_RANGE_DAYS,
    PARAMETER_META,
)
from app.utils.time import as_utc
from app.utils.timeseries_helpers import (
    AvailabilitySummary,
    NormalizedReading,
    aggregate_field_points,
    choose_resolution_seconds,
    compute_field_availability,
    compute_field_statistics,
    normalize_sensor_rows,
    resolve_timeseries_window,
)


@dataclass(frozen=True)
class _SnapshotInputs:
    sensor_rows: list[object]
    alert_rules: list[AlertRule]
    operational_rules: list[OperationalRule]
    sensor_health: list[SensorHealth]
    logger_events: list[LoggerEvent]


async def _load_snapshot_inputs(
    db: AsyncSession,
    *,
    site_id: int,
    fields: tuple[str, ...],
    date_from: datetime,
    date_to: datetime,
) -> _SnapshotInputs:
    sensor_columns = [
        SensorData.id,
        SensorData.ts,
        SensorData.quality_flag,
        SensorData.op_status,
        *(getattr(SensorData, field) for field in fields),
    ]
    sensor_rows = list((await db.execute(
        select(*sensor_columns).where(
            SensorData.site_id == site_id,
            SensorData.ts >= date_from,
            SensorData.ts < date_to,
        ).order_by(SensorData.ts.asc(), SensorData.id.asc())
    )).all())
    alert_rules = list((await db.scalars(
        select(AlertRule).where(
            AlertRule.site_id == site_id,
            AlertRule.is_active.is_(True),
            AlertRule.field.in_(fields),
        )
    )).all())
    operational_rules = list((await db.scalars(
        select(OperationalRule).where(
            OperationalRule.site_id == site_id,
            OperationalRule.is_active.is_(True),
        )
    )).all())
    sensor_health = list((await db.scalars(
        select(SensorHealth).where(
            SensorHealth.site_id == site_id,
            SensorHealth.field.in_(fields),
            SensorHealth.updated_at >= date_from,
            SensorHealth.updated_at < date_to,
        )
    )).all())
    logger_events = list((await db.scalars(
        select(LoggerEvent).where(
            LoggerEvent.site_id == site_id,
            LoggerEvent.ts >= date_from,
            LoggerEvent.ts < date_to,
        ).order_by(LoggerEvent.ts.asc(), LoggerEvent.id.asc())
    )).all())
    return _SnapshotInputs(
        sensor_rows=sensor_rows,
        alert_rules=alert_rules,
        operational_rules=operational_rules,
        sensor_health=sensor_health,
        logger_events=logger_events,
    )


def _sensor_error_timestamps(
    health_rows: list[SensorHealth], fields: tuple[str, ...]
) -> dict[str, set[datetime]]:
    errors = {field: set() for field in fields}
    explicit_error_types = {"implausible", "sensor_error", "sensor_fail", "malfunction"}
    for health in health_rows:
        if (
            health.field in errors
            and str(health.status).lower() == "bad"
            and str(health.anomaly_type or "").lower() in explicit_error_types
        ):
            errors[health.field].add(as_utc(health.updated_at))
    return errors


def _field_samples(
    rows: list[NormalizedReading], field: str, sensor_errors: set[datetime]
) -> list[tuple[NormalizedReading, float]]:
    return [
        (row, float(row.values[field]))
        for row in rows
        if row.op_status is None
        and row.ts not in sensor_errors
        and row.values.get(field) is not None
    ]


def _accepted_measurement_rows(
    rows: list[NormalizedReading],
    fields: tuple[str, ...],
    sensor_errors: dict[str, set[datetime]],
) -> list[NormalizedReading]:
    error_timestamps = {
        timestamp
        for field_errors in sensor_errors.values()
        for timestamp in field_errors
    }
    return [
        row
        for row in rows
        if row.op_status is None
        and row.ts not in error_timestamps
        and any(row.values.get(field) is not None for field in fields)
    ]


def _current_quality(
    samples: list[tuple[NormalizedReading, float]], sensor_errors: set[datetime]
) -> str | None:
    current_row = samples[-1][0] if samples else None
    latest_error = max(sensor_errors, default=None)
    if latest_error is not None and (current_row is None or latest_error >= current_row.ts):
        return "sensor_error"
    if current_row is None:
        return None
    return "valid" if current_row.classification == "accepted" else current_row.classification


def _field_status(
    current: float | None,
    current_quality: str | None,
    alert_rule: AlertRule | None,
    operational_rule: OperationalRule | None,
) -> str:
    if current_quality == "sensor_error":
        return "sensor_error"
    if current is None:
        return "no_data"

    def outside(minimum: float | None, maximum: float | None) -> bool:
        return ((minimum is not None and current < minimum)
                or (maximum is not None and current > maximum))

    if alert_rule is not None and outside(alert_rule.danger_min, alert_rule.danger_max):
        return "critical"
    if (
        operational_rule is not None
        and operational_rule.rule_type == "flow_state"
        and operational_rule.no_flow_threshold is not None
        and current <= operational_rule.no_flow_threshold
    ):
        return "no_flow"
    if (
        (alert_rule is not None and outside(alert_rule.warning_min, alert_rule.warning_max))
        or current_quality == "check_required"
    ):
        return "warning"
    return "normal"


def _threshold(field: str, rule: AlertRule | None) -> TimeseriesThreshold:
    metadata = PARAMETER_META[field]
    if rule is None:
        return TimeseriesThreshold(
            warning_min=None,
            warning_max=None,
            danger_min=None,
            danger_max=None,
            unit=metadata["unit"],
            label=metadata["label"],
            regulation=None,
            source="unconfigured",
        )
    return TimeseriesThreshold(
        warning_min=rule.warning_min,
        warning_max=rule.warning_max,
        danger_min=rule.danger_min,
        danger_max=rule.danger_max,
        unit=metadata["unit"],
        label=rule.reference_label or metadata["label"],
        regulation=rule.regulation,
        source="site_alert_rule",
    )


def _overall_availability(
    rows: list[NormalizedReading],
    *,
    date_from: datetime,
    effective_to: datetime,
    cadence_seconds: int,
) -> AvailabilitySummary:
    if cadence_seconds <= 0 or effective_to <= date_from:
        return AvailabilitySummary(0, 0, 0, 100.0)
    expected = math.ceil((effective_to - date_from).total_seconds() / cadence_seconds)
    delivered_slots = {
        int((row.ts - date_from).total_seconds() // cadence_seconds)
        for row in rows
        if row.op_status is None and date_from <= row.ts < effective_to
    }
    delivered_slots = {slot for slot in delivered_slots if 0 <= slot < expected}
    missing = expected - len(delivered_slots)
    if not delivered_slots:
        return AvailabilitySummary(expected, 0, missing, 0.0, leading_missing=expected)
    first, last = min(delivered_slots), max(delivered_slots)
    return AvailabilitySummary(
        expected_slots=expected,
        delivered_slots=len(delivered_slots),
        missing_slots=missing,
        availability_pct=len(delivered_slots) / expected * 100.0,
        leading_missing=first,
        internal_missing=max(0, last - first + 1 - len(delivered_slots)),
        trailing_missing=expected - last - 1,
    )


def _rounded(value: float | None, field: str) -> float | None:
    return None if value is None else round(value, PARAMETER_META[field]["decimals"])


async def build_timeseries_response(
    db: AsyncSession,
    *,
    site: Site,
    preset: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    fields: tuple[str, ...],
    max_points: int | None,
    now_utc: datetime | None = None,
) -> TimeseriesResponse:
    config = await db.scalar(
        select(SiteMonitoringConfig).where(SiteMonitoringConfig.site_id == site.id)
    )
    cadence_seconds = config.cadence_seconds if config else DEFAULT_CADENCE_SECONDS
    configured_max_points = config.max_chart_points if config else DEFAULT_MAX_CHART_POINTS
    max_range_days = config.max_range_days if config else DEFAULT_MAX_RANGE_DAYS
    if max_points is not None and max_points <= 0:
        raise ValueError("invalid_max_points")
    effective_max_points = min(max_points or configured_max_points, configured_max_points)
    range_preset = "custom" if date_from is not None or date_to is not None else (preset or "today")
    try:
        window = resolve_timeseries_window(
            range_preset,
            timezone_name=site.timezone,
            date_from=date_from,
            date_to=date_to,
            now_utc=now_utc,
            max_range_days=max_range_days,
        )
    except ValueError as exc:
        if str(exc) == "range_too_large":
            raise ValueError(f"range_too_large:max_range_days={max_range_days}") from None
        raise

    resolution_seconds = choose_resolution_seconds(
        (window.date_to - window.date_from).total_seconds(), max_points=effective_max_points
    )
    generated_at = as_utc(now_utc or datetime.now(timezone.utc))
    snapshot = await _load_snapshot_inputs(
        db,
        site_id=site.id,
        fields=fields,
        date_from=window.date_from,
        date_to=window.date_to,
    )
    normalized_rows, normalization_warnings = normalize_sensor_rows(
        snapshot.sensor_rows, fields=fields
    )
    sensor_errors = _sensor_error_timestamps(snapshot.sensor_health, fields)
    accepted_measurement_rows = _accepted_measurement_rows(
        normalized_rows, fields, sensor_errors
    )
    rules_by_field = {rule.field: rule for rule in snapshot.alert_rules}
    flow_rules_by_field = {
        rule.field: rule
        for rule in snapshot.operational_rules
        if rule.rule_type == "flow_state"
    }
    overall = _overall_availability(
        accepted_measurement_rows,
        date_from=window.date_from,
        effective_to=window.effective_to,
        cadence_seconds=cadence_seconds,
    )

    series: dict[str, TimeseriesSeries] = {}
    statistics: dict[str, FieldStatistics] = {}
    field_samples: dict[str, list[tuple[NormalizedReading, float]]] = {}
    for field in fields:
        samples = _field_samples(normalized_rows, field, sensor_errors[field])
        field_samples[field] = samples
        raw_stats = compute_field_statistics(
            normalized_rows,
            field,
            sensor_error_timestamps=sensor_errors[field],
            date_from=window.date_from,
            date_to=window.date_to,
        )
        availability = compute_field_availability(
            normalized_rows,
            field,
            window.date_from,
            window.date_to,
            cadence_seconds,
            sensor_error_timestamps=sensor_errors[field],
            effective_to=window.effective_to,
        )
        current_row, current = samples[-1] if samples else (None, None)
        current_quality = _current_quality(samples, sensor_errors[field])
        statistics[field] = FieldStatistics(
            current=_rounded(current, field),
            current_ts=current_row.ts if current_row else None,
            current_quality=current_quality,
            avg=_rounded(raw_stats["avg"], field) if raw_stats else None,
            min=_rounded(raw_stats["min"], field) if raw_stats else None,
            max=_rounded(raw_stats["max"], field) if raw_stats else None,
            count=raw_stats["count"] if raw_stats else 0,
            availability_pct=round(availability.availability_pct, 1),
            status=_field_status(
                current,
                current_quality,
                rules_by_field.get(field),
                flow_rules_by_field.get(field),
            ),
        )

    has_usable_data = any(field_samples.values())
    for field in fields:
        points = []
        if has_usable_data:
            points = [
                TimeseriesPoint(
                    ts=point.ts,
                    value=_rounded(point.value, field),
                    min=_rounded(point.min, field),
                    max=_rounded(point.max, field),
                    count=point.count,
                )
                for point in aggregate_field_points(
                    normalized_rows,
                    field,
                    window.date_from,
                    window.date_to,
                    resolution_seconds,
                    sensor_error_timestamps=sensor_errors[field],
                )
            ]
        series[field] = TimeseriesSeries(
            label=PARAMETER_META[field]["label"],
            unit=PARAMETER_META[field]["unit"],
            points=points,
        )

    partial_reasons: list[str] = []
    if has_usable_data:
        if overall.missing_slots:
            partial_reasons.append("missing_intervals")
        if (
            accepted_measurement_rows
            and window.effective_to - accepted_measurement_rows[-1].ts
            > timedelta(seconds=(config.stale_after_seconds if config else 5400))
        ):
            partial_reasons.append("stale_tail")
        if any(not field_samples[field] for field in fields):
            partial_reasons.append("field_missing")

    return TimeseriesResponse(
        meta=TimeseriesMeta(
            site_uid=site.uid,
            timezone=site.timezone,
            date_from=window.date_from,
            date_to=window.date_to,
            generated_at=generated_at,
            rules_evaluated_at=generated_at,
            cadence_seconds=cadence_seconds,
            resolution_seconds=resolution_seconds,
            is_aggregated=resolution_seconds > cadence_seconds,
            max_points=effective_max_points,
            availability_pct=round(overall.availability_pct, 1),
            is_partial=bool(partial_reasons),
            partial_reasons=partial_reasons,
            normalization_warnings=normalization_warnings,
        ),
        series=series,
        statistics=statistics,
        thresholds={field: _threshold(field, rules_by_field.get(field)) for field in fields},
        events=[],
        event_total=0,
    )
