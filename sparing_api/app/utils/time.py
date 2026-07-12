from datetime import datetime, timezone


def as_utc(dt: datetime | None) -> datetime | None:
    """Normalize a datetime to timezone-aware UTC for safe comparison.

    MySQL DATETIME columns come back offset-naive (no tz is stored) even though
    the app always writes UTC — comparing such a value against
    datetime.now(timezone.utc) raises TypeError. Use this wherever a stored
    timestamp is compared or formatted. None passes through so callers can guard.

    This is the single source of truth; to_utc() (for ingest) delegates here.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_utc(dt: datetime | None) -> datetime:
    """Coerce a datetime to aware UTC for storage; None becomes 'now'."""
    return as_utc(dt) if dt is not None else datetime.now(timezone.utc)
