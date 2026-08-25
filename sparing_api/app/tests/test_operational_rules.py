from datetime import datetime, timedelta, timezone

from app.utils.operational_rules import (
    FlowRuleConfig,
    RapidChangeRuleConfig,
    ThresholdConfig,
    derive_flow_events,
    derive_rapid_change_events,
)


def _t(minute: int) -> datetime:
    return datetime(2026, 8, 25, tzinfo=timezone.utc) + timedelta(minutes=minute)


def _rapid(**overrides) -> RapidChangeRuleConfig:
    values = dict(
        window_seconds=600,
        min_points=3,
        abs_delta=5.0,
        percent_delta=None,
        minimum_baseline=1.0,
        trigger_mode="any",
        cooldown_seconds=0,
    )
    values.update(overrides)
    return RapidChangeRuleConfig(**values)


def _flow(**overrides) -> FlowRuleConfig:
    values = dict(
        no_flow_threshold=0.0,
        low_flow_threshold=2.0,
        recovery_threshold=3.0,
        hold_seconds=120,
        cooldown_seconds=0,
    )
    values.update(overrides)
    return FlowRuleConfig(**values)


def test_rapid_change_uses_minimum_baseline_floor():
    rule = _rapid(abs_delta=None, percent_delta=50.0, minimum_baseline=1.0, trigger_mode="all")
    samples = [(_t(0), 0.01), (_t(2), 0.02), (_t(4), 0.01), (_t(6), 0.4)]
    assert derive_rapid_change_events(samples, rule, field="tss") == []


def test_rapid_change_supports_absolute_only_and_preserves_signed_peak_context():
    events = derive_rapid_change_events(
        [(_t(0), 10.0), (_t(2), 10.0), (_t(4), 10.0), (_t(6), 16.0)],
        _rapid(),
        field="tss",
    )
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "rapid_change"
    assert event.direction == "up"
    assert event.delta == 6.0
    assert event.context == {"baseline": 10.0, "percent_delta": 60.0, "value": 16.0}
    assert event.start_at == event.end_at == _t(6)


def test_rapid_change_supports_percent_only():
    events = derive_rapid_change_events(
        [(_t(0), 10.0), (_t(2), 10.0), (_t(4), 10.0), (_t(6), 16.0)],
        _rapid(abs_delta=None, percent_delta=50.0),
        field="tss",
    )
    assert [event.delta for event in events] == [6.0]


def test_rapid_change_any_and_all_ignore_unset_detectors_but_all_requires_every_configured_detector():
    samples = [(_t(0), 10.0), (_t(2), 10.0), (_t(4), 10.0), (_t(6), 16.0)]
    assert derive_rapid_change_events(samples, _rapid(abs_delta=7.0, percent_delta=50.0), field="tss")
    assert derive_rapid_change_events(samples, _rapid(abs_delta=7.0, percent_delta=50.0, trigger_mode="all"), field="tss") == []
    assert derive_rapid_change_events(samples, _rapid(abs_delta=5.0, percent_delta=None, trigger_mode="all"), field="tss")


def test_rapid_change_requires_enough_prior_points_and_groups_only_consecutive_same_direction_hits():
    samples = [
        (_t(0), 10.0), (_t(2), 10.0), (_t(4), 10.0),
        (_t(6), 16.0), (_t(8), 18.0), (_t(10), 10.0), (_t(12), 4.0),
    ]
    events = derive_rapid_change_events(samples, _rapid(), field="tss")
    assert [(event.direction, event.start_at, event.end_at, event.delta) for event in events] == [
        ("up", _t(6), _t(8), 8.0),
        ("down", _t(12), _t(12), -6.0),
    ]
    assert derive_rapid_change_events(samples[:3], _rapid(), field="tss") == []


def test_rapid_change_cooldown_is_scoped_to_direction_and_events_are_deterministically_ordered():
    samples = [
        (_t(0), 10.0), (_t(2), 10.0), (_t(4), 10.0), (_t(6), 16.0),
        (_t(8), 10.0), (_t(10), 16.0), (_t(12), 10.0), (_t(14), 4.0),
    ]
    events = derive_rapid_change_events(samples, _rapid(cooldown_seconds=300), field="tss")
    assert [(event.direction, event.start_at) for event in events] == [("up", _t(6)), ("down", _t(14))]
    assert [event.event_id for event in events] == sorted(event.event_id for event in events)


def test_flow_zero_is_data_and_becomes_no_flow_only_after_hold_duration():
    events, final_state = derive_flow_events(
        [(_t(0), 0.0), (_t(1), 0.0), (_t(2), 0.0)], [], flow_rule=_flow(),
        tss_change_rule=None, tss_threshold=None,
    )
    assert [(event.event_type, event.start_at) for event in events] == [("no_flow", _t(0))]
    assert final_state == "no_flow"


def test_flow_drop_no_flow_hysteretic_restore_and_cooldown_do_not_chatter():
    samples = [
        (_t(0), 4.0), (_t(2), 4.0),  # initial flowing
        (_t(4), 1.0), (_t(6), 1.0),  # held low flow
        (_t(8), 0.0), (_t(10), 0.0),  # held no flow
        (_t(12), 2.5), (_t(14), 2.5),  # below recovery: remain no flow
        (_t(16), 3.0), (_t(18), 3.0),  # held restore
        (_t(20), 2.5), (_t(22), 2.5),  # hysteresis gap: remain flowing
    ]
    events, final_state = derive_flow_events(samples, [], flow_rule=_flow(), tss_change_rule=None, tss_threshold=None)
    assert [(event.event_type, event.label, event.start_at) for event in events] == [
        ("flow_drop", "Flow Drop", _t(4)),
        ("no_flow", "No Flow", _t(8)),
        ("flow_restored", "Flow Restored", _t(16)),
    ]
    assert final_state == "flowing"


def test_low_flow_tss_check_requires_a_significant_tss_rapid_event_overlap():
    debit = [(_t(0), 4.0), (_t(2), 4.0), (_t(4), 1.0), (_t(6), 1.0)]
    tss_present_but_stable = [(_t(0), 10.0), (_t(2), 10.0), (_t(4), 10.0), (_t(6), 10.0)]
    tss_change = [(_t(0), 10.0), (_t(2), 10.0), (_t(4), 10.0), (_t(6), 30.0)]
    rapid = _rapid(abs_delta=10.0, percent_delta=None, cooldown_seconds=120)
    ordinary, _ = derive_flow_events(debit, tss_present_but_stable, flow_rule=_flow(), tss_change_rule=rapid, tss_threshold=None)
    checked, _ = derive_flow_events(
        debit, tss_change, flow_rule=_flow(), tss_change_rule=rapid,
        tss_threshold=ThresholdConfig(danger_max=20.0),
    )
    assert [event.event_type for event in ordinary] == ["flow_drop"]
    compound = [event for event in checked if event.event_type == "low_flow_tss_check"]
    assert len(compound) == 1
    assert compound[0].status == "check_required"
    assert compound[0].label == "Perlu Pemeriksaan"
    assert compound[0].severity == "critical"
    assert "regulation" not in compound[0].context


def test_low_flow_tss_check_uses_the_rapid_event_cooldown_as_its_overlap_interval():
    debit = [(_t(0), 4.0), (_t(2), 4.0), (_t(10), 1.0), (_t(12), 1.0)]
    tss_change = [(_t(0), 10.0), (_t(2), 10.0), (_t(4), 10.0), (_t(6), 30.0)]
    events, _ = derive_flow_events(
        debit, tss_change, flow_rule=_flow(),
        tss_change_rule=_rapid(abs_delta=10.0, percent_delta=None, cooldown_seconds=300),
        tss_threshold=ThresholdConfig(danger_max=50.0),
    )
    compound = next(event for event in events if event.event_type == "low_flow_tss_check")
    assert (compound.start_at, compound.end_at, compound.severity, compound.status) == (
        _t(10), _t(11), "warning", "check_required"
    )


def test_low_flow_tss_check_uses_active_held_state_when_flow_drop_is_in_cooldown():
    debit = [
        (_t(0), 4.0), (_t(2), 4.0),  # initial flowing
        (_t(4), 1.0), (_t(6), 1.0),  # emitted Flow Drop
        (_t(8), 3.0), (_t(10), 3.0),  # emitted restore
        (_t(12), 1.0), (_t(14), 1.0),  # held second low-flow state, alert cooldown
    ]
    tss_change = [
        (_t(0), 10.0), (_t(2), 10.0), (_t(4), 10.0),
        (_t(6), 10.0), (_t(8), 10.0), (_t(10), 10.0), (_t(14), 30.0),
    ]
    events, final_state = derive_flow_events(
        debit, tss_change, flow_rule=_flow(cooldown_seconds=900),
        tss_change_rule=_rapid(abs_delta=10.0, percent_delta=None),
        tss_threshold=ThresholdConfig(danger_max=50.0),
    )
    assert [event.event_type for event in events if event.event_type == "flow_drop"] == ["flow_drop"]
    compound = [event for event in events if event.event_type == "low_flow_tss_check"]
    assert len(compound) == 1
    assert compound[0].start_at == _t(14)
    assert compound[0].context["debit"]["flow_state"] == "low_flow"
    assert final_state == "low_flow"
