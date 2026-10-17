"""Calendar days in the site's own timezone.

Readings are stored in UTC. A "day" on the compliance heatmap or in a report is
the site's local calendar day (00:00–24:00 WIB/WITA/WIT), not the UTC day, which
in WIB ran 07:00–07:00 and put a breach at 03:00 WIB on the previous day.

Indonesian zones have no DST, so a fixed offset per site is exact; for zones
that do, the offset at the start of the window is used.
"""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func

DEFAULT_SITE_TIMEZONE = "Asia/Jakarta"


def site_utc_offset(timezone_name: str | None, at: datetime) -> timedelta:
    try:
        zone = ZoneInfo(timezone_name or DEFAULT_SITE_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo(DEFAULT_SITE_TIMEZONE)
    return zone.utcoffset(at.replace(tzinfo=None)) or timedelta(0)


def local_midnight_utc(day: date, offset: timedelta) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc) - offset


def local_day_bounds(first_day: date, last_day: date, timezone_name: str | None) -> tuple[datetime, datetime]:
    """[local midnight of first_day, local midnight after last_day) in UTC."""
    offset = site_utc_offset(timezone_name, datetime(first_day.year, first_day.month, first_day.day))
    return (
        local_midnight_utc(first_day, offset),
        local_midnight_utc(last_day + timedelta(days=1), offset),
    )


def local_date_expr(column, offset: timedelta, dialect: str):
    """SQL expression for the local calendar date ('YYYY-MM-DD') of a UTC column."""
    minutes = int(offset.total_seconds() // 60)
    if dialect == "mysql":
        # Numeric offsets need no MySQL time-zone tables.
        sign = "+" if minutes >= 0 else "-"
        hours, mins = divmod(abs(minutes), 60)
        return func.date(func.convert_tz(column, "+00:00", f"{sign}{hours:02d}:{mins:02d}"))
    if dialect == "sqlite":
        return func.date(column, f"{minutes:+d} minutes")
    return func.date(column)
