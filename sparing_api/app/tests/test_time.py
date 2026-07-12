from datetime import datetime, timezone, timedelta
from app.utils.time import as_utc, to_utc


def test_as_utc_none_passes_through():
    assert as_utc(None) is None


def test_as_utc_naive_treated_as_utc():
    naive = datetime(2026, 6, 1, 12, 0, 0)
    result = as_utc(naive)
    assert result.tzinfo == timezone.utc
    # comparable with an aware now() without raising
    assert result < datetime.now(timezone.utc)


def test_as_utc_aware_non_utc_converted():
    wib = timezone(timedelta(hours=7))
    dt = datetime(2026, 6, 1, 19, 0, 0, tzinfo=wib)  # 19:00 WIB == 12:00 UTC
    result = as_utc(dt)
    assert result.tzinfo == timezone.utc
    assert result.hour == 12


def test_to_utc_none_becomes_now():
    result = to_utc(None)
    assert result.tzinfo == timezone.utc
    assert abs((datetime.now(timezone.utc) - result).total_seconds()) < 5


def test_to_utc_naive_treated_as_utc():
    naive = datetime(2026, 6, 1, 12, 0, 0)
    assert to_utc(naive) == datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
