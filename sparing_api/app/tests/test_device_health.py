from datetime import datetime, timezone, timedelta
from app.utils.device_health import compute_health_status

# Thresholds are tuned for hourly-burst ingest: online < 90 min, warning < 150 min.


def _ago(minutes: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def test_health_online_recent():
    assert compute_health_status(_ago(5)) == "online"


def test_health_online_within_a_burst_cycle():
    # a healthy device may last report ~1h ago (between hourly bursts)
    assert compute_health_status(_ago(65)) == "online"


def test_health_warning():
    assert compute_health_status(_ago(120)) == "warning"


def test_health_offline():
    assert compute_health_status(_ago(200)) == "offline"


def test_health_unknown():
    assert compute_health_status(None) == "unknown"


def test_health_boundary_online():
    assert compute_health_status(_ago(89)) == "online"


def test_health_boundary_warning():
    assert compute_health_status(_ago(90)) == "warning"


def test_health_boundary_offline():
    assert compute_health_status(_ago(150)) == "offline"
