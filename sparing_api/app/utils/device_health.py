from datetime import datetime, timezone
from app.utils.time import as_utc

# Devices ingest in hourly bursts, so thresholds allow for a missed cycle:
# online within ~1.5h, warning up to ~2.5h, offline beyond. Single source of
# truth — the /devices API and the offline-alert job both derive from these.
ONLINE_MAX_MINUTES = 90
WARNING_MAX_MINUTES = 150


def compute_health_status(last_seen: datetime | None) -> str:
    """Return 'online', 'warning', 'offline', or 'unknown' based on last_seen."""
    if last_seen is None:
        return "unknown"
    last_seen = as_utc(last_seen)
    diff_minutes = (datetime.now(timezone.utc) - last_seen).total_seconds() / 60
    if diff_minutes < ONLINE_MAX_MINUTES:
        return "online"
    if diff_minutes < WARNING_MAX_MINUTES:
        return "warning"
    return "offline"
