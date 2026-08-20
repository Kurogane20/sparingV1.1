from datetime import date, datetime, timezone, timedelta
from app.utils.report_helpers import (
    make_period_label, calculate_trend, compliance_pct, group_exceedance_events,
)


def _t(minute):
    return datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc) + timedelta(minutes=minute)


def test_exceedance_empty():
    assert group_exceedance_events([]) == []


def test_exceedance_consecutive_rows_are_one_event():
    rows = [(_t(0), 250, "above_max", 200),
            (_t(2), 260, "above_max", 200),
            (_t(4), 255, "above_max", 200)]
    events = group_exceedance_events(rows)
    assert len(events) == 1
    ev = events[0]
    assert ev["reading_count"] == 3
    assert ev["peak_value"] == 260          # worst (highest) above max
    assert ev["duration_minutes"] == 4.0
    assert ev["start_ts"] == _t(0) and ev["end_ts"] == _t(4)


def test_exceedance_large_gap_splits_events():
    rows = [(_t(0), 250, "above_max", 200),
            (_t(2), 255, "above_max", 200),
            (_t(40), 300, "above_max", 200)]  # 38-min gap → new event
    events = group_exceedance_events(rows, gap_minutes=15)
    assert len(events) == 2
    assert events[0]["reading_count"] == 2
    assert events[1]["reading_count"] == 1
    assert events[1]["peak_value"] == 300


def test_exceedance_limit_type_change_splits_events():
    rows = [(_t(0), 5.0, "below_min", 6.0),
            (_t(2), 5.5, "below_min", 6.0),
            (_t(4), 9.5, "above_max", 9.0)]
    events = group_exceedance_events(rows)
    assert len(events) == 2
    assert events[0]["limit_type"] == "below_min"
    assert events[0]["peak_value"] == 5.0    # worst (lowest) below min
    assert events[1]["limit_type"] == "above_max"

def test_period_label_full_month():
    assert make_period_label(date(2025, 1, 1), date(2025, 1, 31)) == "Januari 2025"

def test_period_label_custom_range():
    result = make_period_label(date(2025, 1, 5), date(2025, 1, 20))
    assert "5 Jan" in result and "20 Jan" in result

def test_trend_stable():
    assert calculate_trend(7.0, 7.2) == "stable"

def test_trend_increasing():
    assert calculate_trend(5.0, 7.0) == "increasing"

def test_trend_decreasing():
    assert calculate_trend(7.0, 5.0) == "decreasing"

def test_trend_zero_base():
    assert calculate_trend(0, 5.0) == "stable"

def test_trend_none():
    assert calculate_trend(None, 5.0) == "stable"

def test_compliance_full():
    assert compliance_pct(100, 0) == 100.0

def test_compliance_partial():
    assert compliance_pct(10, 2) == 80.0

def test_compliance_zero_total():
    assert compliance_pct(0, 0) == 100.0
