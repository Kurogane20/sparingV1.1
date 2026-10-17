"""Daily figures follow the site's calendar day, not the UTC day."""
from datetime import date, datetime, timedelta, timezone

from app.utils.local_day import local_day_bounds, site_utc_offset


def test_site_offset_follows_site_timezone():
    at = datetime(2026, 7, 1, tzinfo=timezone.utc)
    assert site_utc_offset("Asia/Jakarta", at) == timedelta(hours=7)
    assert site_utc_offset("Asia/Makassar", at) == timedelta(hours=8)
    assert site_utc_offset("Asia/Jayapura", at) == timedelta(hours=9)


def test_unknown_or_missing_timezone_falls_back_to_wib():
    at = datetime(2026, 7, 1, tzinfo=timezone.utc)
    assert site_utc_offset(None, at) == timedelta(hours=7)
    assert site_utc_offset("Mars/Olympus", at) == timedelta(hours=7)


def test_local_day_bounds_run_midnight_to_midnight_local_time():
    start, end = local_day_bounds(date(2026, 7, 2), date(2026, 7, 3), "Asia/Jakarta")
    assert start == datetime(2026, 7, 1, 17, 0, tzinfo=timezone.utc)   # 2 Jul 00:00 WIB
    assert end == datetime(2026, 7, 3, 17, 0, tzinfo=timezone.utc)     # 4 Jul 00:00 WIB (exclusive)
