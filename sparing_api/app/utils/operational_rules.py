"""Pure, deterministic operational-monitoring event derivation.

The functions here accept only value/timestamp series and immutable rule
configuration.  Database and API orchestration deliberately belong elsewhere.
"""
from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass, field as dataclass_field, replace
from datetime import datetime, timedelta, timezone
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
    point_count: int | None = None
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
    points: int


@dataclass(frozen=True)
class RapidChangeDetection:
    """Grouped event output plus the unsuppressed state of the latest point."""

    events: tuple[DerivedEvent, ...]
    current_direction: str | None


@dataclass(frozen=True)
class FlowStateInterval:
    """A held flow state, retained even when its alert is in cooldown."""

    state: str
    start_at: datetime
    end_at: datetime
    value: float


@dataclass(frozen=True)
class FlowStateDetection:
    events: tuple[DerivedEvent, ...]
    final_state: str | None
    intervals: tuple[FlowStateInterval, ...]


class _SlidingMedian:
    """Exact median with O(log W) updates and O(W) bounded storage.

    Two heaps provide constant-time median reads.  Expired entries use lazy
    deletion, with periodic heap rebuilding to keep physical storage bounded
    by the active trailing window rather than the full input range.
    """

    def __init__(self) -> None:
        self._lower: list[tuple[float, int]] = []
        self._upper: list[tuple[float, int]] = []
        self._side: dict[int, str] = {}
        self._values: dict[int, float] = {}
        self._removed: set[int] = set()
        self._lower_size = 0
        self._upper_size = 0

    def __len__(self) -> int:
        return self._lower_size + self._upper_size

    def _prune(self, heap: list[tuple[float, int]]) -> None:
        while heap and heap[0][1] in self._removed:
            _, sample_id = heapq.heappop(heap)
            self._removed.discard(sample_id)

    def _rebalance(self) -> None:
        self._prune(self._lower)
        self._prune(self._upper)
        while self._lower_size > self._upper_size + 1:
            neg_value, sample_id = heapq.heappop(self._lower)
            value = -neg_value
            heapq.heappush(self._upper, (value, sample_id))
            self._side[sample_id] = "upper"
            self._lower_size -= 1
            self._upper_size += 1
            self._prune(self._lower)
        while self._lower_size < self._upper_size:
            value, sample_id = heapq.heappop(self._upper)
            heapq.heappush(self._lower, (-value, sample_id))
            self._side[sample_id] = "lower"
            self._upper_size -= 1
            self._lower_size += 1
            self._prune(self._upper)

    def _compact_if_needed(self) -> None:
        active = len(self)
        if len(self._lower) + len(self._upper) <= 2 * active + 64:
            return
        ordered = sorted((value, sample_id) for sample_id, value in self._values.items())
        lower_count = (len(ordered) + 1) // 2
        lower = ordered[:lower_count]
        upper = ordered[lower_count:]
        self._lower = [(-value, sample_id) for value, sample_id in lower]
        self._upper = list(upper)
        heapq.heapify(self._lower)
        heapq.heapify(self._upper)
        self._side = {
            sample_id: "lower" if index < lower_count else "upper"
            for index, (_, sample_id) in enumerate(ordered)
        }
        self._removed.clear()
        self._lower_size = lower_count
        self._upper_size = len(upper)

    def add(self, sample_id: int, value: float) -> None:
        self._prune(self._lower)
        self._values[sample_id] = value
        if not self._lower or value <= -self._lower[0][0]:
            heapq.heappush(self._lower, (-value, sample_id))
            self._side[sample_id] = "lower"
            self._lower_size += 1
        else:
            heapq.heappush(self._upper, (value, sample_id))
            self._side[sample_id] = "upper"
            self._upper_size += 1
        self._rebalance()

    def remove(self, sample_id: int) -> None:
        side = self._side.pop(sample_id)
        self._values.pop(sample_id, None)
        self._removed.add(sample_id)
        if side == "lower":
            self._lower_size -= 1
            self._prune(self._lower)
        else:
            self._upper_size -= 1
            self._prune(self._upper)
        self._rebalance()
        self._compact_if_needed()

    def median(self) -> float:
        if not len(self):
            raise ValueError("median requires an active sample")
        self._prune(self._lower)
        self._prune(self._upper)
        if self._lower_size == self._upper_size:
            return (-self._lower[0][0] + self._upper[0][0]) / 2.0
        return -self._lower[0][0]


def derive_rapid_change_detection(
    samples: list[tuple[datetime, float]], rule: RapidChangeRuleConfig, *, field: str
) -> RapidChangeDetection:
    """Derive grouped events and latest raw hit in O(N log W) time.

    ``W`` is the number of prior samples within ``window_seconds``.  Each
    sample enters and leaves the deque/median structure once; no full prefix
    or full prior history is scanned.
    """
    points = _normalised_samples(samples)
    window: deque[tuple[int, datetime]] = deque()
    medians = _SlidingMedian()
    groups: list[list[_RapidHit]] = []
    active: list[_RapidHit] | None = None
    current_direction: str | None = None
    for sample_id, (timestamp, value) in enumerate(points):
        cutoff = timestamp - timedelta(seconds=rule.window_seconds)
        while window and window[0][1] < cutoff:
            expired_id, _ = window.popleft()
            medians.remove(expired_id)
        hit: _RapidHit | None = None
        if len(medians) >= rule.min_points:
            baseline = medians.median()
            delta = value - baseline
            floor = rule.minimum_baseline if rule.minimum_baseline is not None else 0.0
            denominator = max(abs(baseline), floor)
            percent = abs(delta) / denominator * 100.0 if denominator else 0.0
            if _rapid_hit(delta, percent, rule):
                hit = _RapidHit(
                    timestamp,
                    "up" if delta >= 0 else "down",
                    delta,
                    baseline,
                    percent,
                    value,
                    len(medians) + 1,
                )
        current_direction = hit.direction if hit is not None else None
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
        medians.add(sample_id, value)
        window.append((sample_id, timestamp))
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
            point_count=peak.points,
            context=_frozen_context({
                "baseline": peak.baseline,
                "percent_delta": peak.percent,
                "value": peak.value,
            }),
        ))
        last_emitted_end[direction] = end_at
    return RapidChangeDetection(tuple(events), current_direction)


def derive_rapid_change_events(
    samples: list[tuple[datetime, float]], rule: RapidChangeRuleConfig, *, field: str
) -> list[DerivedEvent]:
    """Backward-compatible event-only wrapper around the shared detector."""
    return list(derive_rapid_change_detection(samples, rule, field=field).events)


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


def _overlaps(flow_interval: FlowStateInterval, tss_event: DerivedEvent, cooldown_seconds: int) -> bool:
    rapid_end = tss_event.end_at + timedelta(seconds=cooldown_seconds)
    return flow_interval.start_at <= rapid_end and tss_event.start_at <= flow_interval.end_at


def _compound_event(
    flow_interval: FlowStateInterval,
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
            "tss": {
                "baseline": tss_event.context["baseline"],
                "current": tss_event.context["value"],
                "delta": tss_event.delta,
                "percent": tss_event.context["percent_delta"],
            },
            "tss_event_id": tss_event.event_id,
        }),
    )


def derive_flow_state_events(
    debit_samples: list[tuple[datetime, float]],
    *,
    flow_rule: FlowRuleConfig,
    max_gap_seconds: float | None = None,
) -> FlowStateDetection:
    """Derive held debit states, resetting state across continuity breaks."""
    state: str | None = None
    candidate: str | None = None
    candidate_started_at: datetime | None = None
    events: list[DerivedEvent] = []
    flow_intervals: list[FlowStateInterval] = []
    last_emitted_at: dict[str, datetime] = {}
    active_event_index: int | None = None
    active_interval_index: int | None = None
    last_timestamp: datetime | None = None

    for timestamp, value in _normalised_samples(debit_samples):
        if (
            max_gap_seconds is not None
            and last_timestamp is not None
            and (timestamp - last_timestamp).total_seconds() > max_gap_seconds
        ):
            if active_interval_index is not None:
                flow_intervals[active_interval_index] = replace(
                    flow_intervals[active_interval_index], end_at=last_timestamp
                )
            if active_event_index is not None:
                events[active_event_index] = replace(
                    events[active_event_index], end_at=last_timestamp
                )
            state = None
            candidate = None
            candidate_started_at = None
            active_event_index = None
            active_interval_index = None
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
        flow_intervals.append(FlowStateInterval(state, start_at, timestamp, value))
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

    return FlowStateDetection(
        tuple(sorted(events, key=lambda event: (event.start_at, event.event_id))),
        state,
        tuple(flow_intervals),
    )


def derive_low_flow_tss_events(
    flow_intervals: tuple[FlowStateInterval, ...],
    tss_events: tuple[DerivedEvent, ...],
    *,
    tss_threshold: ThresholdConfig | None,
    cooldown_seconds: int,
) -> list[DerivedEvent]:
    """Correlate already-derived flow and TSS states without re-running them."""
    compound: list[DerivedEvent] = []
    for flow_interval in flow_intervals:
        if flow_interval.state not in {"low_flow", "no_flow"}:
            continue
        overlap = next(
            (
                event
                for event in tss_events
                if _overlaps(flow_interval, event, cooldown_seconds)
            ),
            None,
        )
        if overlap is not None:
            compound.append(
                _compound_event(
                    flow_interval, overlap, tss_threshold, cooldown_seconds
                )
            )
    return compound


def derive_flow_events(
    debit_samples: list[tuple[datetime, float]],
    tss_samples: list[tuple[datetime, float]],
    *,
    flow_rule: FlowRuleConfig,
    tss_change_rule: RapidChangeRuleConfig | None,
    tss_threshold: ThresholdConfig | None,
    max_gap_seconds: float | None = None,
) -> tuple[list[DerivedEvent], str | None]:
    """Backward-compatible combined wrapper for pure detector consumers."""
    flow = derive_flow_state_events(
        debit_samples,
        flow_rule=flow_rule,
        max_gap_seconds=max_gap_seconds,
    )
    events = list(flow.events)
    if tss_change_rule is not None:
        rapid = derive_rapid_change_detection(
            tss_samples, tss_change_rule, field="tss"
        )
        events.extend(
            derive_low_flow_tss_events(
                flow.intervals,
                rapid.events,
                tss_threshold=tss_threshold,
                cooldown_seconds=tss_change_rule.cooldown_seconds,
            )
        )
    return sorted(events, key=lambda event: (event.start_at, event.event_id)), flow.final_state
