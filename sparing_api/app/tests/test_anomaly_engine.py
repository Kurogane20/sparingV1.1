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
