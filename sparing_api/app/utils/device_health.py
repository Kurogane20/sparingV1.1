from datetime import datetime, timezone
from app.utils.time import as_utc

def compute_health_status(last_seen: datetime | None) -> str:
    """Return 'online', 'warning', 'offline', or 'unknown' based on last_seen timestamp."""
    if last_seen is None:
        return "unknown"
    last_seen = as_utc(last_seen)
    diff_minutes = (datetime.now(timezone.utc) - last_seen).total_seconds() / 60
    if diff_minutes < 15:
        return "online"
    if diff_minutes < 60:
        return "warning"
    return "offline"
