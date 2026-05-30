from datetime import datetime, timezone

def compute_health_status(last_seen: datetime | None) -> str:
    """Return 'online', 'warning', 'offline', or 'unknown' based on last_seen timestamp."""
    if last_seen is None:
        return "unknown"
    diff_minutes = (datetime.now(timezone.utc) - last_seen).total_seconds() / 60
    if diff_minutes < 15:
        return "online"
    if diff_minutes < 60:
        return "warning"
    return "offline"
