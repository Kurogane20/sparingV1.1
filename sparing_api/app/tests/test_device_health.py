from datetime import datetime, timezone, timedelta
from app.utils.device_health import compute_health_status

def _ago(minutes: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)

def test_health_online():
    assert compute_health_status(_ago(5)) == "online"

def test_health_warning():
    assert compute_health_status(_ago(30)) == "warning"

def test_health_offline():
    assert compute_health_status(_ago(120)) == "offline"

def test_health_unknown():
    assert compute_health_status(None) == "unknown"

def test_health_boundary_online():
    assert compute_health_status(_ago(14)) == "online"

def test_health_boundary_warning():
    assert compute_health_status(_ago(15)) == "warning"

def test_health_boundary_offline():
    assert compute_health_status(_ago(60)) == "offline"
