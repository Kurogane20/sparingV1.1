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
