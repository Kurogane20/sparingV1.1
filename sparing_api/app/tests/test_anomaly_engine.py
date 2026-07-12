from app.utils.anomaly_engine import check_implausible, AnomalyResult, PLAUSIBLE_RANGES, IN_SCOPE_FIELDS


def test_in_scope_fields_exact():
    assert IN_SCOPE_FIELDS == ["ph", "tss", "cod", "nh3n", "temp", "debit"]
    assert "voltage" not in PLAUSIBLE_RANGES
    assert "current" not in PLAUSIBLE_RANGES


def test_implausible_ph_above_range():
    r = check_implausible("ph", 13.9)
    assert isinstance(r, AnomalyResult)
    assert r.anomaly_type == "implausible"
    assert r.severity == "danger"


def test_implausible_ph_in_range_is_none():
    assert check_implausible("ph", 7.5) is None


def test_implausible_tss_below_zero():
    r = check_implausible("tss", -3.0)
    assert r is not None and r.anomaly_type == "implausible"


def test_implausible_boundary_inclusive():
    # exactly on the boundary is NOT implausible
    assert check_implausible("ph", 2.0) is None
    assert check_implausible("ph", 12.0) is None


def test_implausible_unknown_field_is_none():
    assert check_implausible("voltage", 9999.0) is None


def test_implausible_none_value_is_none():
    assert check_implausible("ph", None) is None


from datetime import datetime, timedelta
from app.utils.anomaly_engine import check_flatline


def _series(start, minutes_step, values):
    return [(start + timedelta(minutes=i * minutes_step), v) for i, v in enumerate(values)]


def test_flatline_stuck_value_over_window():
    start = datetime(2026, 6, 1, 0, 0, 0)
    # 9 identical readings, 2 min apart => spans 16 min (>= 15 min)
    samples = _series(start, 2, [7.2] * 9)
    r = check_flatline(samples, "ph")
    assert r is not None and r.anomaly_type == "flatline" and r.severity == "danger"


def test_flatline_varying_values_not_flagged():
    start = datetime(2026, 6, 1, 0, 0, 0)
    samples = _series(start, 2, [7.2, 7.3, 7.2, 7.4, 7.1, 7.2, 7.3, 7.2, 7.5])
    assert check_flatline(samples, "ph") is None


def test_flatline_window_too_short_not_flagged():
    start = datetime(2026, 6, 1, 0, 0, 0)
    samples = _series(start, 2, [7.2, 7.2, 7.2])  # spans only 4 min
    assert check_flatline(samples, "ph") is None


def test_flatline_too_few_samples_not_flagged():
    start = datetime(2026, 6, 1, 0, 0, 0)
    assert check_flatline(_series(start, 2, [7.2]), "ph") is None
    assert check_flatline([], "ph") is None


from app.utils.anomaly_engine import check_spike, _mad


def test_mad_basic():
    # median=3, abs devs=[2,1,0,1,2] median=1
    assert _mad([1, 2, 3, 4, 5]) == 1


def test_spike_obvious_outlier_flagged():
    history = [7.0, 7.1, 6.9, 7.0, 7.2, 6.8, 7.1, 7.0, 6.9, 7.1]
    r = check_spike(12.0, history, "ph")
    assert r is not None and r.anomaly_type == "spike" and r.severity == "warning"


def test_spike_normal_value_not_flagged():
    history = [7.0, 7.1, 6.9, 7.0, 7.2, 6.8, 7.1, 7.0, 6.9, 7.1]
    assert check_spike(7.05, history, "ph") is None


def test_spike_insufficient_history_not_flagged():
    assert check_spike(99.0, [7.0, 7.1, 6.9], "ph") is None


def test_spike_small_delta_below_min_abs_not_flagged():
    # flat history (mad=0); tiny delta below per-field min abs delta -> not flagged
    history = [7.0] * 12
    assert check_spike(7.2, history, "ph") is None  # ph min abs delta = 1.0


def test_spike_flat_history_large_delta_flagged():
    history = [7.0] * 12
    r = check_spike(10.0, history, "ph")  # delta 3.0 > min abs 1.0
    assert r is not None and r.anomaly_type == "spike"


from app.utils.anomaly_engine import check_drift


def test_drift_sustained_shift_flagged():
    baseline = [100.0] * 50
    recent = [140.0] * 20   # +40% shift, > 25%
    r = check_drift(recent, baseline, "cod")
    assert r is not None and r.anomaly_type == "drift" and r.severity == "warning"


def test_drift_stable_not_flagged():
    baseline = [100.0] * 50
    recent = [103.0] * 20   # +3%
    assert check_drift(recent, baseline, "cod") is None


def test_drift_empty_windows_not_flagged():
    assert check_drift([], [100.0], "cod") is None
    assert check_drift([100.0], [], "cod") is None


def test_drift_tiny_baseline_floor_prevents_false_positive():
    # baseline near zero would explode pct; floor keeps it sane
    baseline = [0.1] * 50
    recent = [0.3] * 20
    assert check_drift(recent, baseline, "cod") is None  # cod floor = 10.0


from datetime import timezone as _tz
from app.utils.anomaly_engine import _as_utc


def test_as_utc_naive_treated_as_utc():
    naive = datetime(2026, 6, 1, 12, 0, 0)
    aware = _as_utc(naive)
    assert aware.tzinfo == _tz.utc
    # must be comparable with an aware datetime without raising
    assert aware < datetime.now(_tz.utc)


def test_as_utc_already_aware_unchanged():
    aware = datetime(2026, 6, 1, 12, 0, 0, tzinfo=_tz.utc)
    assert _as_utc(aware) is aware


from app.utils.anomaly_engine import scan_batch


def _stable(n):
    """Alternating small noise around 7.0 — a realistic stable pH series."""
    base = [7.0, 7.1, 6.9, 7.05, 6.95]
    return [base[i % len(base)] for i in range(n)]


def test_scan_batch_flags_spike_inside_batch():
    start = datetime(2026, 6, 1, 0, 0, 0)
    # 15 old stable readings + a 5-reading burst whose 2nd value spikes
    values = _stable(15) + [7.0, 12.0, 7.1, 7.0, 6.9]
    samples = _series(start, 2, values)
    new_since = samples[15][0]  # burst starts at index 15
    hits = scan_batch(samples, new_since, "ph")
    assert len(hits) == 1
    ts, value, result = hits[0]
    assert value == 12.0
    assert result.anomaly_type == "spike"


def test_scan_batch_implausible_wins_over_spike():
    start = datetime(2026, 6, 1, 0, 0, 0)
    values = _stable(15) + [7.0, 13.5, 7.1]  # 13.5 > plausible max 12
    samples = _series(start, 2, values)
    hits = scan_batch(samples, samples[15][0], "ph")
    assert len(hits) == 1
    assert hits[0][2].anomaly_type == "implausible"


def test_scan_batch_stable_batch_no_hits():
    start = datetime(2026, 6, 1, 0, 0, 0)
    samples = _series(start, 2, _stable(30))
    assert scan_batch(samples, samples[25][0], "ph") == []


def test_scan_batch_old_outlier_not_reevaluated():
    start = datetime(2026, 6, 1, 0, 0, 0)
    # outlier sits in the OLD part of the window; the new burst is stable
    values = _stable(5) + [12.0] + _stable(10) + [7.0, 7.1, 7.0]
    samples = _series(start, 2, values)
    hits = scan_batch(samples, samples[16][0], "ph")
    assert hits == []


def test_scan_batch_insufficient_history_no_spike():
    start = datetime(2026, 6, 1, 0, 0, 0)
    # whole window IS the burst — fewer than SPIKE_MIN_POINTS priors
    samples = _series(start, 2, [7.0, 7.1, 12.0, 7.0])
    assert scan_batch(samples, samples[0][0], "ph") == []
