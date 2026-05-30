from datetime import date
from app.utils.report_helpers import make_period_label, calculate_trend, compliance_pct

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
