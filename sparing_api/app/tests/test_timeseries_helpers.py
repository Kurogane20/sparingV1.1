from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.utils.timeseries_helpers import (
    aggregate_field_points,
    choose_resolution_seconds,
    compute_field_availability,
    compute_field_statistics,
    normalize_sensor_rows,
    resolve_timeseries_window,
)


def _t(minutes=0):
    return datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes)


def test_normalize_preserves_zero_repairs_nonfinite_and_deduplicates():
    rows = [
        SimpleNamespace(id=1, ts=_t(), ph=0.0, tss=float("nan"), debit=float("inf"), quality_flag=None, op_status=None),
        SimpleNamespace(id=2, ts=_t(), ph=7.0, tss=8.0, debit=0.0, quality_flag="anomaly", op_status=None),
    ]
    normalized, warnings = normalize_sensor_rows(rows, fields=("ph", "tss", "debit"))
    assert len(normalized) == 1
    assert normalized[0].values == {"ph": 7.0, "tss": 8.0, "debit": 0.0}
    assert warnings == ["duplicate_timestamps_repaired"]
    assert normalized[0].quality_flag == "anomaly"


def test_normalize_sorts_and_skips_invalid_timestamps_and_naive_is_utc():
    rows = [
        SimpleNamespace(id=2, ts=_t(2).replace(tzinfo=None), ph=2),
        SimpleNamespace(id=1, ts=_t(), ph=1),
        SimpleNamespace(id=3, ts="bad", ph=3),
        SimpleNamespace(id=4, ts=None, ph=4),
    ]
    normalized, warnings = normalize_sensor_rows(rows, fields=("ph",))
    assert [r.row_id for r in normalized] == [1, 2]
    assert normalized[1].ts.tzinfo == timezone.utc
    assert "invalid_timestamps_dropped" in warnings


def test_resolve_window_uses_site_timezone_for_today_and_caps_future():
    now = datetime(2026, 8, 25, 5, 0, tzinfo=timezone.utc)
    window = resolve_timeseries_window("today", timezone_name="Asia/Jakarta", now_utc=now)
    assert window.date_from == datetime(2026, 8, 24, 17, tzinfo=timezone.utc)
    assert window.date_to == now
    assert window.effective_to == now


def test_resolve_window_custom_is_exclusive_and_validates_timezone_and_cap():
    now = datetime(2026, 8, 25, tzinfo=timezone.utc)
    start = datetime(2026, 7, 1, tzinfo=timezone.utc)
    end = datetime(2026, 8, 25, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="invalid_timezone"):
        resolve_timeseries_window("custom", timezone_name="No/Such", date_from=start, date_to=end, now_utc=now)
    with pytest.raises(ValueError, match="range_too_large"):
        resolve_timeseries_window("custom", timezone_name="UTC", date_from=start, date_to=end, now_utc=now, max_range_days=31)
    w = resolve_timeseries_window("custom", timezone_name="UTC", date_from=_t(), date_to=_t(10), now_utc=now)
    assert w.date_from == _t() and w.date_to == _t(10)


def test_resolution_stays_within_point_limit_and_allowed_values():
    assert choose_resolution_seconds(3600, max_points=720) == 60
    result = choose_resolution_seconds(31 * 86400, max_points=720)
    assert result in {60, 300, 900, 3600, 21600, 86400}
    assert result * 720 >= 31 * 86400


def test_aggregation_is_anchored_and_contains_empty_buckets_and_stats_are_full_range():
    rows = [
        SimpleNamespace(ts=_t(), values={"debit": 0.0}, op_status=None),
        SimpleNamespace(ts=_t(2), values={"debit": 2.0}, op_status=None),
        SimpleNamespace(ts=_t(12), values={"debit": 10.0}, op_status=None),
    ]
    buckets = aggregate_field_points(rows, field="debit", date_from=_t(), date_to=_t(15), resolution_seconds=300)
    assert [p.ts for p in buckets] == [_t(), _t(5), _t(10)]
    assert buckets[0].count == 2 and buckets[0].avg == 1.0
    assert buckets[1].count == 0 and buckets[1].avg is None
    stats = compute_field_statistics(rows, field="debit")
    assert stats["count"] == 3 and stats["max"] == 10.0 and stats["avg"] == 4.0


def test_availability_counts_leading_internal_trailing_slots_and_zero_delivery():
    rows = [
        SimpleNamespace(ts=_t(2), values={"debit": 0.0}, op_status=None),
        SimpleNamespace(ts=_t(6), values={"debit": 1.0}, op_status=None),
    ]
    summary = compute_field_availability(rows, field="debit", date_from=_t(), date_to=_t(10), cadence_seconds=120)
    assert summary.expected_slots == 5
    assert summary.delivered_slots == 2
    assert summary.missing_slots == 3
    assert summary.leading_missing == 1 and summary.internal_missing == 1 and summary.trailing_missing == 1


def test_legacy_anomaly_is_explicit_check_required_and_stays_in_statistics():
    rows = [SimpleNamespace(id=1, ts=_t(), ph=7.0, quality_flag="anomaly", op_status=None)]
    normalized, _ = normalize_sensor_rows(rows, fields=("ph",))
    # An anomaly is a review classification, not an invalid/missing sample.
    assert normalized[0].classification == "check_required"
    assert compute_field_statistics(normalized, "ph")["count"] == 1


def test_op_status_and_explicit_sensor_error_are_excluded_but_zero_is_delivered():
    rows = [
        SimpleNamespace(ts=_t(), values={"debit": 0.0}, op_status=None),
        SimpleNamespace(ts=_t(2), values={"debit": 4.0}, op_status=-2),
        SimpleNamespace(ts=_t(4), values={"debit": 5.0}, op_status=None),
    ]
    assert compute_field_statistics(rows, "debit", sensor_error_timestamps={_t(4)}) is not None
    assert compute_field_statistics(rows, "debit", sensor_error_timestamps={_t(4)})["count"] == 1


def test_availability_uses_effective_end_for_future_requested_range():
    rows = [SimpleNamespace(ts=_t(), values={"debit": 0.0}, op_status=None)]
    summary = compute_field_availability(
        rows, "debit", _t(), _t(20), cadence_seconds=120, effective_to=_t(4)
    )
    assert summary.expected_slots == 2
    assert summary.delivered_slots == 1
    assert summary.missing_slots == 1


def test_resolution_rejects_when_allowed_resolutions_cannot_meet_limit():
    with pytest.raises(ValueError, match="max_points_unachievable"):
        choose_resolution_seconds(31 * 86400, max_points=1)


def test_normalized_values_mapping_is_immutable():
    rows, _ = normalize_sensor_rows([SimpleNamespace(ts=_t(), ph=7.0)], fields=("ph",))
    with pytest.raises(TypeError):
        rows[0].values["ph"] = 8.0
