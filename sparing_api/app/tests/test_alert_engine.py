import pytest
from unittest.mock import MagicMock
from app.utils.alert_engine import _is_violated, _determine_threshold_type

def test_is_violated_upper_limit():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _is_violated(120.0, rule, "warning") is False
    assert _is_violated(160.0, rule, "warning") is True
    assert _is_violated(210.0, rule, "danger") is True

def test_is_violated_range():
    rule = MagicMock(warning_min=6.5, warning_max=8.5, danger_min=6.0, danger_max=9.0)
    assert _is_violated(7.2, rule, "warning") is False   # within range
    assert _is_violated(6.2, rule, "warning") is True    # below min
    assert _is_violated(9.1, rule, "danger") is True     # above max
    assert _is_violated(6.05, rule, "danger") is False   # within danger range

def test_determine_threshold_type_danger():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _determine_threshold_type(210.0, rule) == "danger"

def test_determine_threshold_type_warning():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _determine_threshold_type(160.0, rule) == "warning"

def test_determine_threshold_type_normal():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _determine_threshold_type(100.0, rule) is None
