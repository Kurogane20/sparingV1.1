from __future__ import annotations

import math
from dataclasses import dataclass, replace
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
    TimeseriesEvent,
    TimeseriesEventContext,
    TimeseriesPoint,
    TimeseriesResponse,
    TimeseriesSeries,
    TimeseriesThreshold,
)
from app.utils.monitoring_config import (
    DEFAULT_CADENCE_SECONDS,
    DEFAULT_MAX_CHART_POINTS,
    DEFAULT_MAX_RANGE_DAYS,
    MAX_TIMESERIES_EVENTS,
    PARAMETER_META,
)
from app.utils.operational_rules import (
    FlowRuleConfig,
    RapidChangeRuleConfig,
    ThresholdConfig,
    derive_flow_events,
    derive_rapid_change_events,
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
    sensor_predecessor: object | None
    alert_rules: list[AlertRule]
    operational_rules: list[OperationalRule]
    sensor_health: list[SensorHealth]
    logger_events: list[LoggerEvent]


@dataclass(frozen=True)
class _EventCandidate:
    id: str
    ts: datetime
    end_ts: datetime | None
    type: str
    field: str | None
    severity: str
    direction: str | None
    label: str
    context: TimeseriesEventContext


@dataclass(frozen=True)
class _StatusDetails:
    code: str
    label: str
    reason: str
    severity: str


_STATUS_DETAILS = {
    "sensor_error": _StatusDetails(
        "sensor_error", "Kesalahan Sensor", "explicit_sensor_error", "critical"
    ),
    "no_data": _StatusDetails(
        "no_data", "Tidak Ada Data", "no_finite_measurement", "warning"
    ),
    "stale": _StatusDetails(
        "no_data", "Tidak Ada Data", "stale_measurement", "warning"
    ),
    "critical": _StatusDetails(
        "critical", "Kritis", "danger_threshold_violated", "critical"
    ),
    "no_flow": _StatusDetails(
        "no_flow", "Aliran Terhenti", "no_flow_threshold_violated", "warning"
    ),
    "warning_threshold": _StatusDetails(
        "warning", "Peringatan", "warning_threshold_violated", "warning"
    ),
    "quality_check": _StatusDetails(
        "warning", "Peringatan", "quality_check_required", "warning"
    ),
    "rapid_change": _StatusDetails(
        "warning", "Peringatan", "rapid_change_detected", "warning"
    ),
    "low_flow": _StatusDetails(
        "warning", "Peringatan", "low_flow_detected", "warning"
    ),
    "normal": _StatusDetails(
        "normal", "Normal", "within_configured_limits", "info"
    ),
}

_SEVERITY_SORT = {"critical": 0, "warning": 1, "info": 2}
_MAJOR_GAP_MIN_MISSING_SLOTS = 3


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
    sensor_predecessor = (await db.execute(
        select(*sensor_columns).where(
            SensorData.site_id == site_id,
            SensorData.ts < date_from,
        ).order_by(SensorData.ts.desc(), SensorData.id.desc()).limit(1)
    )).first()
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
        sensor_predecessor=sensor_predecessor,
        alert_rules=alert_rules,
        operational_rules=operational_rules,
        sensor_health=sensor_health,
        logger_events=logger_events,
    )


def _sensor_error_timestamps(
    health_rows: list[SensorHealth], fields: tuple[str, ...]
) -> dict[str, set[datetime]]:
    errors = {field: set() for field in fields}
    for health in health_rows:
        if (
            health.field in errors
            and str(health.status).lower() == "bad"
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


def _hard_invalid_timestamps(
    raw_rows: list[object],
    normalized_rows: list[NormalizedReading],
    fields: tuple[str, ...],
) -> dict[str, set[datetime]]:
    normalized_by_timestamp = {row.ts: row for row in normalized_rows}
    invalid = {field: set() for field in fields}
    for raw_row in raw_rows:
        timestamp = as_utc(raw_row.ts)
        normalized = normalized_by_timestamp.get(timestamp)
        if normalized is None:
            continue
        for field in fields:
            if getattr(raw_row, field) is not None and normalized.values[field] is None:
                invalid[field].add(timestamp)
    return invalid


def _current_field_observation(
    rows: list[NormalizedReading],
    field: str,
    sensor_errors: set[datetime],
    hard_invalid: set[datetime],
) -> tuple[datetime | None, float | None, str | None]:
    candidates: list[tuple[datetime, int, float | None, str]] = []
    for row in rows:
        if row.op_status == -3 or row.ts in sensor_errors or row.ts in hard_invalid:
            candidates.append((row.ts, 1, None, "sensor_error"))
        elif row.op_status is None and row.values.get(field) is not None:
            quality = (
                "valid" if row.classification == "accepted" else row.classification
            )
            candidates.append((row.ts, 0, float(row.values[field]), quality))
    candidates.extend(
        (timestamp, 1, None, "sensor_error") for timestamp in sensor_errors
    )
    if not candidates:
        return None, None, None
    timestamp, _, value, quality = max(candidates, key=lambda item: (item[0], item[1]))
    return timestamp, value, quality


def _field_status_details(
    current: float | None,
    current_quality: str | None,
    alert_rule: AlertRule | None,
    event_reason: str | None,
    is_stale: bool,
) -> _StatusDetails:
    if current_quality == "sensor_error":
        return _STATUS_DETAILS["sensor_error"]
    if current is None:
        return _STATUS_DETAILS["no_data"]
    if is_stale:
        return _STATUS_DETAILS["stale"]

    def outside(minimum: float | None, maximum: float | None) -> bool:
        return ((minimum is not None and current < minimum)
                or (maximum is not None and current > maximum))

    if alert_rule is not None and outside(alert_rule.danger_min, alert_rule.danger_max):
        return _STATUS_DETAILS["critical"]
    if event_reason == "no_flow_active":
        return _STATUS_DETAILS["no_flow"]
    if alert_rule is not None and outside(alert_rule.warning_min, alert_rule.warning_max):
        return _STATUS_DETAILS["warning_threshold"]
    if current_quality == "check_required":
        return _STATUS_DETAILS["quality_check"]
    if event_reason == "rapid_change_detected":
        return _STATUS_DETAILS["rapid_change"]
    if event_reason == "low_flow_detected":
        return _STATUS_DETAILS["low_flow"]
    return _STATUS_DETAILS["normal"]


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


def _event_id(
    site_uid: str,
    source: str,
    rule_key: str,
    field: str | None,
    timestamp: datetime,
) -> str:
    return ":".join(
        (site_uid, source, rule_key, field or "-", as_utc(timestamp).isoformat())
    )


def _normalise_severity(value: str | None) -> str:
    severity = str(value or "info").lower()
    if severity in {"critical", "error", "danger"}:
        return "critical"
    if severity in {"warning", "warn"}:
        return "warning"
    return "info"


def _threshold_violation(
    value: float, rule: AlertRule
) -> tuple[str, str] | None:
    if rule.danger_min is not None and value < rule.danger_min:
        return "danger", "down"
    if rule.danger_max is not None and value > rule.danger_max:
        return "danger", "up"
    if rule.warning_min is not None and value < rule.warning_min:
        return "warning", "down"
    if rule.warning_max is not None and value > rule.warning_max:
        return "warning", "up"
    return None


def _missing_slots_between(
    previous: datetime, current: datetime, cadence_seconds: int
) -> int:
    if cadence_seconds <= 0:
        return 0
    return max(
        0,
        int((current - previous).total_seconds() // cadence_seconds) - 1,
    )


def _is_major_gap(
    previous: datetime, current: datetime, cadence_seconds: int
) -> bool:
    return (
        _missing_slots_between(previous, current, cadence_seconds)
        >= _MAJOR_GAP_MIN_MISSING_SLOTS
    )


def _major_gap_boundaries(
    rows: list[NormalizedReading], cadence_seconds: int
) -> tuple[datetime, ...]:
    return tuple(
        current.ts
        for previous, current in zip(rows, rows[1:])
        if _is_major_gap(previous.ts, current.ts, cadence_seconds)
    )


def _threshold_events(
    site_uid: str,
    samples_by_field: dict[str, list[tuple[NormalizedReading, float]]],
    predecessor_samples: dict[str, tuple[NormalizedReading, float] | None],
    rules_by_field: dict[str, AlertRule],
    continuity_breaks: tuple[datetime, ...],
) -> list[_EventCandidate]:
    events: list[_EventCandidate] = []
    for field in sorted(samples_by_field):
        rule = rules_by_field.get(field)
        if rule is None:
            continue
        predecessor = predecessor_samples.get(field)
        previous_row = predecessor[0] if predecessor is not None else None
        active_index: int | None = None
        active_key = (
            _threshold_violation(predecessor[1], rule)
            if predecessor is not None
            else None
        )
        for row, value in samples_by_field[field]:
            if (
                previous_row is not None
                and any(
                    previous_row.ts < boundary <= row.ts
                    for boundary in continuity_breaks
                )
            ):
                active_index = None
                active_key = None
            violation = _threshold_violation(value, rule)
            if violation is None:
                active_index = None
                active_key = None
                previous_row = row
                continue
            level, direction = violation
            key = (level, direction)
            if active_key == key:
                if active_index is not None:
                    events[active_index] = replace(events[active_index], end_ts=row.ts)
                previous_row = row
                continue
            severity = "critical" if level == "danger" else "warning"
            level_label = "Bahaya" if level == "danger" else "Peringatan"
            events.append(
                _EventCandidate(
                    id=_event_id(site_uid, f"threshold_{level}", str(rule.id), field, row.ts),
                    ts=row.ts,
                    end_ts=row.ts,
                    type=f"threshold_{level}",
                    field=field,
                    severity=severity,
                    direction=direction,
                    label=f"Pelanggaran Ambang {level_label} {PARAMETER_META[field]['label']}",
                    context=TimeseriesEventContext(current=value),
                )
            )
            active_index = len(events) - 1
            active_key = key
            previous_row = row
    return events


def _row_events(
    site_uid: str,
    rows: list[NormalizedReading],
) -> list[_EventCandidate]:
    events: list[_EventCandidate] = []
    op_labels = {
        -1: ("Operasi Dihentikan", "warning"),
        -2: ("Kalibrasi", "info"),
        -3: ("Gangguan Perangkat", "critical"),
    }
    for row in rows:
        if row.op_status is not None:
            label, severity = op_labels.get(
                row.op_status, ("Status Operasional", "warning")
            )
            events.append(
                _EventCandidate(
                    id=_event_id(site_uid, "op_status", str(row.op_status), None, row.ts),
                    ts=row.ts,
                    end_ts=None,
                    type="op_status",
                    field=None,
                    severity=severity,
                    direction=None,
                    label=label,
                    context=TimeseriesEventContext(current=float(row.op_status)),
                )
            )
        if str(row.quality_flag or "").lower() in {
            "anomaly",
            "spike",
            "rapid_change",
            "rapid-change",
            "check_required",
        }:
            events.append(
                _EventCandidate(
                    id=_event_id(site_uid, "sensor_anomaly", "quality_flag", None, row.ts),
                    ts=row.ts,
                    end_ts=None,
                    type="sensor_anomaly",
                    field=None,
                    severity="warning",
                    direction=None,
                    label="Anomali Sensor",
                    context=TimeseriesEventContext(),
                )
            )
    return events


def _logger_events(
    site_uid: str, logger_rows: list[LoggerEvent]
) -> list[_EventCandidate]:
    labels = {
        "sensor_fail": "Kegagalan Sensor",
        "sensor_recover": "Sensor Pulih",
        "logger_offline": "Logger Terputus",
        "logger_online": "Logger Terhubung",
    }
    return [
        _EventCandidate(
            id=_event_id(site_uid, logger.type, logger.event_uid, None, logger.ts),
            ts=as_utc(logger.ts),
            end_ts=None,
            type=logger.type,
            field=None,
            severity=_normalise_severity(logger.severity),
            direction=None,
            label=labels.get(logger.type, logger.type.replace("_", " ").title()),
            context=TimeseriesEventContext(
                interval_seconds=int(
                    (as_utc(logger.received_at) - as_utc(logger.ts)).total_seconds()
                )
            ),
        )
        for logger in logger_rows
    ]


def _rapid_rule_config(rule: OperationalRule | None) -> RapidChangeRuleConfig | None:
    if rule is None or rule.window_seconds is None or rule.min_points is None:
        return None
    return RapidChangeRuleConfig(
        window_seconds=rule.window_seconds,
        min_points=rule.min_points,
        abs_delta=rule.abs_delta,
        percent_delta=rule.percent_delta,
        minimum_baseline=rule.minimum_baseline,
        trigger_mode=rule.trigger_mode or "any",
        cooldown_seconds=rule.cooldown_seconds or 0,
    )


def _flow_rule_config(rule: OperationalRule | None) -> FlowRuleConfig | None:
    if (
        rule is None
        or rule.no_flow_threshold is None
        or rule.low_flow_threshold is None
        or rule.recovery_threshold is None
    ):
        return None
    return FlowRuleConfig(
        no_flow_threshold=rule.no_flow_threshold,
        low_flow_threshold=rule.low_flow_threshold,
        recovery_threshold=rule.recovery_threshold,
        hold_seconds=rule.hold_seconds or 0,
        cooldown_seconds=rule.cooldown_seconds or 0,
    )


def _operational_events(
    *,
    site_uid: str,
    samples_by_field: dict[str, list[tuple[NormalizedReading, float]]],
    operational_rules: list[OperationalRule],
    alert_rules: dict[str, AlertRule],
) -> tuple[list[_EventCandidate], dict[str, str]]:
    events: list[_EventCandidate] = []
    current_reasons: dict[str, str] = {}
    rapid_rules = {
        rule.field: rule
        for rule in operational_rules
        if rule.rule_type == "rapid_change"
    }
    for field in sorted(rapid_rules):
        config = _rapid_rule_config(rapid_rules[field])
        if config is None or field not in samples_by_field:
            continue
        samples = [(row.ts, value) for row, value in samples_by_field[field]]
        for event in derive_rapid_change_events(samples, config, field=field):
            point_count = sum(
                event.start_at - timedelta(seconds=config.window_seconds) <= timestamp <= event.start_at
                for timestamp, _ in samples
            )
            events.append(
                _EventCandidate(
                    id=_event_id(
                        site_uid, event.event_type, str(rapid_rules[field].id), field, event.start_at
                    ),
                    ts=event.start_at,
                    end_ts=event.end_at,
                    type=event.event_type,
                    field=field,
                    severity="warning",
                    direction=event.direction,
                    label="Perubahan Cepat",
                    context=TimeseriesEventContext(
                        baseline=float(event.context["baseline"]),
                        current=float(event.context["value"]),
                        delta=event.delta,
                        percent=float(event.context["percent_delta"]),
                        points=point_count,
                    ),
                )
            )
            if samples and event.end_at == samples[-1][0]:
                current_reasons[field] = "rapid_change_detected"

    flow_rule = next(
        (rule for rule in operational_rules if rule.rule_type == "flow_state" and rule.field == "debit"),
        None,
    )
    flow_config = _flow_rule_config(flow_rule)
    if flow_config is None or "debit" not in samples_by_field:
        return events, current_reasons

    compound_rule = next(
        (
            rule
            for rule in operational_rules
            if rule.rule_type == "low_flow_tss"
            and rule.field == "debit"
            and rule.secondary_field == "tss"
        ),
        None,
    )
    tss_rule = rapid_rules.get("tss") if compound_rule is not None else None
    tss_change_config = _rapid_rule_config(tss_rule)
    tss_alert = alert_rules.get("tss")
    tss_threshold = (
        ThresholdConfig(
            warning_min=tss_alert.warning_min,
            warning_max=tss_alert.warning_max,
            danger_min=tss_alert.danger_min,
            danger_max=tss_alert.danger_max,
        )
        if tss_alert is not None
        else None
    )
    derived, flow_state = derive_flow_events(
        [(row.ts, value) for row, value in samples_by_field["debit"]],
        [(row.ts, value) for row, value in samples_by_field.get("tss", [])],
        flow_rule=flow_config,
        tss_change_rule=tss_change_config,
        tss_threshold=tss_threshold,
    )
    labels = {
        "flow_drop": "Penurunan Aliran",
        "no_flow": "Aliran Terhenti",
        "flow_restored": "Aliran Pulih",
        "low_flow_tss_check": "Perlu Pemeriksaan TSS saat Aliran Rendah",
    }
    for event in derived:
        source_rule = compound_rule if event.event_type == "low_flow_tss_check" else flow_rule
        context_value = event.context.get("value")
        if event.event_type == "low_flow_tss_check":
            context_value = event.context["tss"]["value"]
        events.append(
            _EventCandidate(
                id=_event_id(
                    site_uid,
                    event.event_type,
                    str(source_rule.id),
                    event.field,
                    event.start_at,
                ),
                ts=event.start_at,
                end_ts=event.end_at,
                type=event.event_type,
                field=event.field,
                severity=(
                    "critical"
                    if event.event_type == "low_flow_tss_check" and event.severity == "critical"
                    else "info" if event.event_type == "flow_restored" else "warning"
                ),
                direction=event.direction,
                label=labels[event.event_type],
                context=TimeseriesEventContext(
                    current=float(context_value) if context_value is not None else None
                ),
            )
        )
    if flow_state == "low_flow":
        current_reasons["debit"] = "low_flow_detected"
    elif flow_state == "no_flow":
        current_reasons["debit"] = "no_flow_active"
    return events, current_reasons


def _major_gap_events(
    site_uid: str,
    rows: list[NormalizedReading],
    cadence_seconds: int,
) -> list[_EventCandidate]:
    if cadence_seconds <= 0:
        return []
    events: list[_EventCandidate] = []
    for previous, current in zip(rows, rows[1:]):
        missing_slots = _missing_slots_between(
            previous.ts, current.ts, cadence_seconds
        )
        if missing_slots < _MAJOR_GAP_MIN_MISSING_SLOTS:
            continue
        start = previous.ts + timedelta(seconds=cadence_seconds)
        end = current.ts - timedelta(seconds=cadence_seconds)
        events.append(
            _EventCandidate(
                id=_event_id(site_uid, "data_gap", f"cadence-{cadence_seconds}", None, start),
                ts=start,
                end_ts=end,
                type="data_gap",
                field=None,
                severity="warning",
                direction=None,
                label="Kesenjangan Data Utama",
                context=TimeseriesEventContext(
                    interval_seconds=missing_slots * cadence_seconds
                ),
            )
        )
    return events


def _cap_events(
    events: list[_EventCandidate],
) -> tuple[list[TimeseriesEvent], int, bool]:
    unique = {event.id: event for event in events}
    uncapped = list(unique.values())
    ranked = sorted(
        uncapped,
        key=lambda event: (
            _SEVERITY_SORT[event.severity],
            -event.ts.timestamp(),
            event.type,
            event.field or "",
            event.id,
        ),
    )
    retained = ranked[:MAX_TIMESERIES_EVENTS]
    retained.sort(
        key=lambda event: (
            event.ts,
            _SEVERITY_SORT[event.severity],
            event.type,
            event.field or "",
            event.id,
        )
    )
    return (
        [
            TimeseriesEvent(
                id=event.id,
                ts=event.ts,
                end_ts=event.end_ts,
                type=event.type,
                field=event.field,
                severity=event.severity,
                direction=event.direction,
                label=event.label,
                context=event.context,
            )
            for event in retained
        ],
        len(uncapped),
        len(uncapped) > MAX_TIMESERIES_EVENTS,
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
    predecessor_rows, _ = normalize_sensor_rows(
        [snapshot.sensor_predecessor] if snapshot.sensor_predecessor is not None else [],
        fields=fields,
    )
    sensor_errors = _sensor_error_timestamps(snapshot.sensor_health, fields)
    hard_invalid = _hard_invalid_timestamps(
        snapshot.sensor_rows, normalized_rows, fields
    )
    accepted_measurement_rows = _accepted_measurement_rows(
        normalized_rows, fields, sensor_errors
    )
    rules_by_field = {rule.field: rule for rule in snapshot.alert_rules}
    overall = _overall_availability(
        accepted_measurement_rows,
        date_from=window.date_from,
        effective_to=window.effective_to,
        cadence_seconds=cadence_seconds,
    )

    series: dict[str, TimeseriesSeries] = {}
    statistics: dict[str, FieldStatistics] = {}
    field_samples = {
        field: _field_samples(normalized_rows, field, sensor_errors[field])
        for field in fields
    }
    predecessor_samples = {}
    for field in fields:
        samples = _field_samples(predecessor_rows, field, set())
        predecessor_samples[field] = samples[-1] if samples else None
    continuity_rows = sorted(
        [*predecessor_rows, *normalized_rows], key=lambda row: row.ts
    )
    continuity_breaks = _major_gap_boundaries(
        continuity_rows, cadence_seconds
    )
    event_candidates = [
        *_threshold_events(
            site.uid,
            field_samples,
            predecessor_samples,
            rules_by_field,
            continuity_breaks,
        ),
        *_row_events(site.uid, normalized_rows),
        *_logger_events(site.uid, snapshot.logger_events),
    ]
    operational_events, current_event_reasons = _operational_events(
        site_uid=site.uid,
        samples_by_field=field_samples,
        operational_rules=snapshot.operational_rules,
        alert_rules=rules_by_field,
    )
    event_candidates.extend(operational_events)
    event_candidates.extend(
        _major_gap_events(site.uid, normalized_rows, cadence_seconds)
    )
    events, event_total, events_truncated = _cap_events(event_candidates)

    for field in fields:
        samples = field_samples[field]
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
        current_ts, current, current_quality = _current_field_observation(
            normalized_rows,
            field,
            sensor_errors[field],
            hard_invalid[field],
        )
        stale_after_seconds = config.stale_after_seconds if config else 5400
        is_stale = (
            current_ts is not None
            and window.effective_to - current_ts
            > timedelta(seconds=stale_after_seconds)
        )
        status = _field_status_details(
            current,
            current_quality,
            rules_by_field.get(field),
            current_event_reasons.get(field),
            is_stale,
        )
        statistics[field] = FieldStatistics(
            current=_rounded(current, field),
            current_ts=current_ts,
            current_quality=current_quality,
            avg=_rounded(raw_stats["avg"], field) if raw_stats else None,
            min=_rounded(raw_stats["min"], field) if raw_stats else None,
            max=_rounded(raw_stats["max"], field) if raw_stats else None,
            count=raw_stats["count"] if raw_stats else 0,
            availability_pct=round(availability.availability_pct, 1),
            status=status.code,
            status_label=status.label,
            status_reason=status.reason,
            status_severity=status.severity,
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
    if events_truncated:
        partial_reasons.append("events_truncated")

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
        events=events,
        event_total=event_total,
    )
