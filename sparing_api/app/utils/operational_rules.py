"""Pure, deterministic operational-monitoring event derivation.

The functions here accept only value/timestamp series and immutable rule
configuration.  Database and API orchestration deliberately belong elsewhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field, replace
from datetime import datetime, timedelta, timezone
from statistics import median
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class RapidChangeRuleConfig:
    window_seconds: int
    min_points: int
    abs_delta: float | None
    percent_delta: float | None
    minimum_baseline: float | None = None
    trigger_mode: str = "any"
    cooldown_seconds: int = 0


@dataclass(frozen=True)
class FlowRuleConfig:
    no_flow_threshold: float
    low_flow_threshold: float
    recovery_threshold: float
    hold_seconds: int = 0
    cooldown_seconds: int = 0


@dataclass(frozen=True)
class ThresholdConfig:
    """Configured operational bounds; ``None`` means the bound is absent."""

    warning_min: float | None = None
    warning_max: float | None = None
    danger_min: float | None = None
    danger_max: float | None = None


@dataclass(frozen=True)
class DerivedEvent:
    event_id: str
    event_type: str
    field: str
    start_at: datetime
    end_at: datetime
    direction: str | None
    severity: str
    status: str
    label: str
    delta: float | None = None
    context: Mapping[str, object] = dataclass_field(default_factory=lambda: MappingProxyType({}))


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalised_samples(samples: list[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
    """Return a timestamp-stable sequence without mutating caller data."""
    return [
        (timestamp, value)
        for timestamp, value, _ in sorted(
            ((_utc(timestamp), float(value), index) for index, (timestamp, value) in enumerate(samples)),
            key=lambda point: (point[0], point[2]),
        )
    ]


def _event_id(event_type: str, field: str, start_at: datetime, direction: str | None = None) -> str:
    suffix = f":{direction}" if direction is not None else ""
    return f"{event_type}:{field}:{start_at.isoformat()}{suffix}"


def _frozen_context(context: Mapping[str, object]) -> Mapping[str, object]:
    """Freeze nested mapping contexts so returned events have no mutable state."""
    return MappingProxyType({
        key: _frozen_context(value) if isinstance(value, Mapping) else value
        for key, value in context.items()
    })


def _rapid_hit(delta: float, percent: float, rule: RapidChangeRuleConfig) -> bool:
    detectors: list[bool] = []
    if rule.abs_delta is not None:
        detectors.append(abs(delta) >= rule.abs_delta)
    if rule.percent_delta is not None:
        detectors.append(percent >= rule.percent_delta)
    if not detectors:
        return False
    return all(detectors) if rule.trigger_mode == "all" else any(detectors)


@dataclass(frozen=True)
class _RapidHit:
    timestamp: datetime
    direction: str
    delta: float
    baseline: float
    percent: float
    value: float


@dataclass(frozen=True)
class _FlowInterval:
    """A held flow state, retained even when its alert is in cooldown."""

    state: str
    start_at: datetime
    end_at: datetime
    value: float


def derive_rapid_change_events(
    samples: list[tuple[datetime, float]], rule: RapidChangeRuleConfig, *, field: str
) -> list[DerivedEvent]:
    """Derive rapid-change intervals using a median of strictly prior values."""
    points = _normalised_samples(samples)
    groups: list[list[_RapidHit]] = []
    active: list[_RapidHit] | None = None
    for index, (timestamp, value) in enumerate(points):
        cutoff = timestamp - timedelta(seconds=rule.window_seconds)
        prior_values = [prior_value for prior_ts, prior_value in points[:index] if prior_ts >= cutoff]
        hit: _RapidHit | None = None
        if len(prior_values) >= rule.min_points:
            baseline = float(median(prior_values))
            delta = value - baseline
            floor = rule.minimum_baseline if rule.minimum_baseline is not None else 0.0
            denominator = max(abs(baseline), floor)
            percent = abs(delta) / denominator * 100.0 if denominator else 0.0
            if _rapid_hit(delta, percent, rule):
                hit = _RapidHit(timestamp, "up" if delta >= 0 else "down", delta, baseline, percent, value)
        if hit is None:
            if active is not None:
                groups.append(active)
                active = None
        elif active is not None and active[-1].direction == hit.direction:
            active.append(hit)
        else:
            if active is not None:
                groups.append(active)
            active = [hit]
    if active is not None:
        groups.append(active)

    last_emitted_end: dict[str, datetime] = {}
    events: list[DerivedEvent] = []
    for group_number, group in enumerate(groups):
        start_at, end_at = group[0].timestamp, group[-1].timestamp
        direction = group[0].direction
        previous_end = last_emitted_end.get(direction)
        if previous_end is not None and start_at < previous_end + timedelta(seconds=rule.cooldown_seconds):
            continue
        peak = max(group, key=lambda hit: (abs(hit.delta), hit.timestamp))
        events.append(DerivedEvent(
            event_id=f"{_event_id('rapid_change', field, start_at, direction)}:{group_number:04d}",
            event_type="rapid_change",
            field=field,
            start_at=start_at,
            end_at=end_at,
            direction=direction,
            severity="warning",
            status="active",
            label="Rapid Change",
            delta=peak.delta,
            context=_frozen_context({
                "baseline": peak.baseline,
                "percent_delta": peak.percent,
                "value": peak.value,
            }),
        ))
        last_emitted_end[direction] = end_at
    return events


def _desired_flow_state(value: float, current: str | None, rule: FlowRuleConfig) -> str:
    """Classify value with state-dependent recovery hysteresis."""
    if current == "no_flow":
        return "flowing" if value >= rule.recovery_threshold else "no_flow"
    if current == "low_flow":
        if value <= rule.no_flow_threshold:
            return "no_flow"
        return "flowing" if value >= rule.recovery_threshold else "low_flow"
    if current == "flowing":
        if value <= rule.no_flow_threshold:
            return "no_flow"
        return "low_flow" if value <= rule.low_flow_threshold else "flowing"
    if value <= rule.no_flow_threshold:
        return "no_flow"
    return "low_flow" if value <= rule.low_flow_threshold else "flowing"


def _flow_event(state: str, start_at: datetime, end_at: datetime, value: float) -> DerivedEvent | None:
    details = {
        "low_flow": ("flow_drop", "Flow Drop", "warning"),
        "no_flow": ("no_flow", "No Flow", "danger"),
        "flowing": ("flow_restored", "Flow Restored", "info"),
    }
    event_type, label, severity = details[state]
    if state == "flowing":
        # The initial steady-flow state is not an operator event.
        return None
    return DerivedEvent(
        event_id=_event_id(event_type, "debit", start_at), event_type=event_type,
        field="debit", start_at=start_at, end_at=end_at, direction=None,
        severity=severity, status="active", label=label,
        context=MappingProxyType({"value": value, "flow_state": state}),
    )


def _flow_restored_event(start_at: datetime, end_at: datetime, value: float) -> DerivedEvent:
    return DerivedEvent(
        event_id=_event_id("flow_restored", "debit", start_at), event_type="flow_restored",
        field="debit", start_at=start_at, end_at=end_at, direction=None,
        severity="info", status="active", label="Flow Restored",
        context=MappingProxyType({"value": value, "flow_state": "flowing"}),
    )


def _danger_violated(value: float, threshold: ThresholdConfig | None) -> bool:
    return threshold is not None and (
        (threshold.danger_min is not None and value < threshold.danger_min)
        or (threshold.danger_max is not None and value > threshold.danger_max)
    )


def _overlaps(flow_interval: _FlowInterval, tss_event: DerivedEvent, cooldown_seconds: int) -> bool:
    rapid_end = tss_event.end_at + timedelta(seconds=cooldown_seconds)
    return flow_interval.start_at <= rapid_end and tss_event.start_at <= flow_interval.end_at


def _compound_event(
    flow_interval: _FlowInterval,
    tss_event: DerivedEvent,
    threshold: ThresholdConfig | None,
    cooldown_seconds: int,
) -> DerivedEvent:
    tss_value = float(tss_event.context["value"])
    severity = "critical" if _danger_violated(tss_value, threshold) else "warning"
    start_at = max(flow_interval.start_at, tss_event.start_at)
    return DerivedEvent(
        event_id=_event_id("low_flow_tss_check", "debit+tss", start_at),
        event_type="low_flow_tss_check", field="debit", start_at=start_at,
        end_at=min(flow_interval.end_at, tss_event.end_at + timedelta(seconds=cooldown_seconds)), direction=None,
        severity=severity, status="check_required", label="Perlu Pemeriksaan",
        context=_frozen_context({
            "debit": {"value": flow_interval.value, "flow_state": flow_interval.state},
            "tss": dict(tss_event.context),
            "tss_event_id": tss_event.event_id,
        }),
    )


def derive_flow_events(
    debit_samples: list[tuple[datetime, float]],
    tss_samples: list[tuple[datetime, float]],
    *,
    flow_rule: FlowRuleConfig,
    tss_change_rule: RapidChangeRuleConfig | None,
    tss_threshold: ThresholdConfig | None,
) -> tuple[list[DerivedEvent], str | None]:
    """Derive held debit states and correlated TSS checks without I/O."""
    state: str | None = None
    candidate: str | None = None
    candidate_started_at: datetime | None = None
    events: list[DerivedEvent] = []
    flow_intervals: list[_FlowInterval] = []
    last_emitted_at: dict[str, datetime] = {}
    active_event_index: int | None = None
    active_interval_index: int | None = None
    last_timestamp: datetime | None = None

    for timestamp, value in _normalised_samples(debit_samples):
        last_timestamp = timestamp
        desired = _desired_flow_state(value, state, flow_rule)
        if desired == state:
            candidate = None
            candidate_started_at = None
            continue
        if desired != candidate:
            candidate = desired
            candidate_started_at = timestamp
        if timestamp - candidate_started_at < timedelta(seconds=flow_rule.hold_seconds):
            continue
        previous = state
        if active_interval_index is not None:
            flow_intervals[active_interval_index] = replace(
                flow_intervals[active_interval_index], end_at=timestamp
            )
        if active_event_index is not None:
            events[active_event_index] = replace(events[active_event_index], end_at=timestamp)
            active_event_index = None
        state = desired
        start_at = candidate_started_at
        candidate = None
        candidate_started_at = None
        flow_intervals.append(_FlowInterval(state, start_at, timestamp, value))
        active_interval_index = len(flow_intervals) - 1
        if state == "flowing" and previous is not None:
            event = _flow_restored_event(start_at, timestamp, value)
        else:
            event = _flow_event(state, start_at, timestamp, value)
        if event is not None:
            previous_event_at = last_emitted_at.get(event.event_type)
            if previous_event_at is None or start_at >= previous_event_at + timedelta(seconds=flow_rule.cooldown_seconds):
                events.append(event)
                last_emitted_at[event.event_type] = start_at
                active_event_index = len(events) - 1

    if active_event_index is not None and last_timestamp is not None:
        events[active_event_index] = replace(events[active_event_index], end_at=last_timestamp)
    if active_interval_index is not None and last_timestamp is not None:
        flow_intervals[active_interval_index] = replace(
            flow_intervals[active_interval_index], end_at=last_timestamp
        )

    if tss_change_rule is not None:
        tss_events = derive_rapid_change_events(tss_samples, tss_change_rule, field="tss")
        for flow_interval in flow_intervals:
            if flow_interval.state not in {"low_flow", "no_flow"}:
                continue
            # A held low/no-flow interval gets one compound check: this avoids
            # chatter while retaining state evidence even if its alert is cooled down.
            overlap = next(
                (event for event in tss_events if _overlaps(flow_interval, event, tss_change_rule.cooldown_seconds)),
                None,
            )
            if overlap is not None:
                events.append(_compound_event(
                    flow_interval, overlap, tss_threshold, tss_change_rule.cooldown_seconds
                ))

    return sorted(events, key=lambda event: (event.start_at, event.event_id)), state
