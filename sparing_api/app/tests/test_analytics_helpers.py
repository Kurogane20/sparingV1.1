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


# ── compute_stats / percentile (#18) ────────────────────────────────
from app.utils.analytics_helpers import compute_stats, percentile, integrate_uptime


def test_compute_stats_basic():
    s = compute_stats([1, 2, 3, 4, 5])
    assert s["count"] == 5
    assert s["avg"] == 3.0
    assert s["min"] == 1.0 and s["max"] == 5.0
    assert s["median"] == 3.0


def test_compute_stats_percentiles():
    vals = list(range(1, 101))  # 1..100
    s = compute_stats(vals)
    # linear interp: p95 index = 0.95*99 = 94.05 -> vals[94]=95 + 0.05*(96-95)
    assert round(s["p95"], 2) == 95.05
    # p99 index = 0.99*99 = 98.01 -> vals[98]=99 + 0.01*(100-99)
    assert round(s["p99"], 2) == 99.01


def test_compute_stats_ignores_none_and_empty():
    assert compute_stats([]) is None
    assert compute_stats([None, None]) is None
    s = compute_stats([None, 4.0, None])
    assert s["count"] == 1 and s["avg"] == 4.0 and s["std_dev"] == 0.0


def test_percentile_edges():
    assert percentile([], 95) == 0.0
    assert percentile([7.0], 95) == 7.0


# ── integrate_uptime (#20) ──────────────────────────────────────────
def test_uptime_all_up_no_transitions():
    assert integrate_uptime([], _t(0), _t(60), initial_up=True) == 1.0


def test_uptime_all_down_no_transitions():
    assert integrate_uptime([], _t(0), _t(60), initial_up=True) == 1.0
    assert integrate_uptime([], _t(0), _t(60), initial_up=False) == 0.0


def test_uptime_half_down():
    # up from 0..30, goes down at 30, stays down to 60 => 50%
    frac = integrate_uptime([(_t(30), False)], _t(0), _t(60), initial_up=True)
    assert frac == 0.5


def test_uptime_down_then_recover():
    # down 0..15 (initial down), up at 15..60 => 45/60 = 0.75
    frac = integrate_uptime([(_t(15), True)], _t(0), _t(60), initial_up=False)
    assert frac == 0.75


def test_uptime_zero_window():
    assert integrate_uptime([], _t(0), _t(0), initial_up=False) == 1.0
