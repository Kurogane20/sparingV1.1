from datetime import datetime, timezone, timedelta

from app.utils.analytics_helpers import find_data_gaps, integrate_volume


def _t(minute):
    return datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=minute)


# ── find_data_gaps ──────────────────────────────────────────────────
def test_gaps_none_when_regular():
    ts = [_t(0), _t(2), _t(4), _t(6)]  # steady 2-min cadence
    assert find_data_gaps(ts, interval_seconds=120) == []


def test_gaps_single_missing_tolerated():
    # 2 -> 6 is 4 min = 2*interval; not strictly greater than threshold → no gap
    ts = [_t(0), _t(2), _t(6), _t(8)]
    assert find_data_gaps(ts, interval_seconds=120, gap_factor=2.0) == []


def test_gaps_detects_and_estimates_missing():
    ts = [_t(0), _t(2), _t(30), _t(32)]  # 28-min hole after _t(2)
    gaps = find_data_gaps(ts, interval_seconds=120)
    assert len(gaps) == 1
    g = gaps[0]
    assert g["gap_start"] == _t(2) and g["gap_end"] == _t(30)
    assert g["duration_minutes"] == 28.0
    assert g["missing_estimate"] == 13   # round(1680/120)-1 = 14-1


def test_gaps_unsorted_input_is_sorted():
    ts = [_t(30), _t(0), _t(2)]
    gaps = find_data_gaps(ts, interval_seconds=120)
    assert len(gaps) == 1 and gaps[0]["gap_start"] == _t(2)


def test_gaps_empty_and_single():
    assert find_data_gaps([]) == []
    assert find_data_gaps([_t(0)]) == []


# ── integrate_volume ────────────────────────────────────────────────
def test_volume_constant_flow():
    # 10 L/min held for 10 minutes = 100 L
    samples = [(_t(0), 10.0), (_t(5), 10.0), (_t(10), 10.0)]
    assert integrate_volume(samples) == 100.0


def test_volume_trapezoidal_ramp():
    # 0 -> 10 L/min over 10 min: avg 5 L/min * 10 min = 50 L
    samples = [(_t(0), 0.0), (_t(10), 10.0)]
    assert integrate_volume(samples, max_gap_minutes=60) == 50.0


def test_volume_skips_offline_gap():
    # a 2h gap must not fabricate volume across the offline stretch
    samples = [(_t(0), 10.0), (_t(2), 10.0), (_t(122), 10.0), (_t(124), 10.0)]
    # only the two 2-min stretches count: 10*2 + 10*2 = 40 L
    assert integrate_volume(samples, max_gap_minutes=15) == 40.0


def test_volume_ignores_nulls_and_short_input():
    assert integrate_volume([]) == 0.0
    assert integrate_volume([(_t(0), None), (_t(2), 10.0)]) == 0.0
