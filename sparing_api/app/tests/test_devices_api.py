from datetime import datetime, timezone, timedelta

import pytest

from app.core.security import hash_password
from app.models.models import User, Site, SensorDevice, SensorData


async def _auth_headers(client, db, email="admin@example.com", role="admin"):
    db.add(User(name="Admin", email=email, password_hash=hash_password("Secret123"),
                role=role, is_active=True))
    await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _site_with_device(db, uid, dev_name="DEVICE-001"):
    site = Site(uid=uid, name=uid, company_name="C", is_active=True)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    dev = SensorDevice(site_id=site.id, name=dev_name, serial_no=dev_name,
                       modbus_addr=1, is_active=True)
    db.add(dev)
    await db.commit()
    await db.refresh(dev)
    return site, dev


def _row(site_id, device_id, device_uid, ts):
    return SensorData(site_id=site_id, device_id=device_id, device_uid=device_uid,
                      ts=ts, created_at=datetime.now(timezone.utc), ph=7.0)


@pytest.mark.anyio
async def test_device_status_does_not_bleed_across_sites_with_shared_name(client, db_session):
    """Two sites each have a device literally named DEVICE-001. Only site A has
    fresh data. Site B's device must read as offline — it must NOT inherit site
    A's last_seen via the shared device_uid/serial_no."""
    now = datetime.now(timezone.utc)
    site_a, dev_a = await _site_with_device(db_session, "SITE-A")
    site_b, dev_b = await _site_with_device(db_session, "SITE-B")
    # fresh data for A only
    db_session.add(_row(site_a.id, dev_a.id, "DEVICE-001", now - timedelta(minutes=5)))
    # B's only data is ancient
    db_session.add(_row(site_b.id, dev_b.id, "DEVICE-001", now - timedelta(days=10)))
    await db_session.commit()
    headers = await _auth_headers(client, db_session)

    res = await client.get("/devices", params={"site_uid": "SITE-B"}, headers=headers)
    assert res.status_code == 200
    dev = res.json()[0]
    assert dev["status"] == "offline"   # not "online" borrowed from SITE-A


@pytest.mark.anyio
async def test_device_health_does_not_bleed_across_sites(client, db_session):
    now = datetime.now(timezone.utc)
    site_a, dev_a = await _site_with_device(db_session, "SITE-C")
    site_b, dev_b = await _site_with_device(db_session, "SITE-D")
    db_session.add(_row(site_a.id, dev_a.id, "DEVICE-001", now - timedelta(minutes=5)))
    await db_session.commit()
    headers = await _auth_headers(client, db_session)

    res = await client.get(f"/devices/{dev_b.id}/health", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["last_seen"] is None       # B has no data of its own
    assert body["status"] in ("offline", "unknown")


@pytest.mark.anyio
async def test_device_status_uses_own_recent_data(client, db_session):
    """Sanity: a device with its own fresh data reads online."""
    now = datetime.now(timezone.utc)
    site, dev = await _site_with_device(db_session, "SITE-E")
    db_session.add(_row(site.id, dev.id, "DEVICE-001", now - timedelta(minutes=5)))
    await db_session.commit()
    headers = await _auth_headers(client, db_session)

    res = await client.get("/devices", params={"site_uid": "SITE-E"}, headers=headers)
    dev_out = res.json()[0]
    assert dev_out["status"] == "online"


@pytest.mark.anyio
async def test_device_health_flags_overdue_maintenance(client, db_session):
    """#14: a past next_due_at with no later maintenance reads as overdue."""
    from app.models.models import MaintenanceLog
    now = datetime.now(timezone.utc)
    site, dev = await _site_with_device(db_session, "SITE-MNT")
    db_session.add(MaintenanceLog(
        device_id=dev.id, type="calibration", notes="cal",
        performed_at=now - timedelta(days=40),
        next_due_at=now - timedelta(days=10),   # due 10 days ago → overdue
    ))
    await db_session.commit()
    headers = await _auth_headers(client, db_session)

    res = await client.get(f"/devices/{dev.id}/health", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["maintenance_overdue"] is True
    assert body["calibration_overdue"] is True
    assert body["days_until_due"] < 0


@pytest.mark.anyio
async def test_device_health_upcoming_maintenance_not_overdue(client, db_session):
    from app.models.models import MaintenanceLog
    now = datetime.now(timezone.utc)
    site, dev = await _site_with_device(db_session, "SITE-MNT2")
    db_session.add(MaintenanceLog(
        device_id=dev.id, type="calibration", notes="cal",
        performed_at=now - timedelta(days=5),
        next_due_at=now + timedelta(days=25),   # due in future → ok
    ))
    await db_session.commit()
    headers = await _auth_headers(client, db_session)

    res = await client.get(f"/devices/{dev.id}/health", headers=headers)
    body = res.json()
    assert body["maintenance_overdue"] is False
    assert body["days_until_due"] >= 24


@pytest.mark.anyio
async def test_maintenance_calibration_fields_roundtrip(client, db_session):
    """#15: calibration before/after persist and offset is derived when omitted."""
    now = datetime.now(timezone.utc)
    site, dev = await _site_with_device(db_session, "SITE-CAL")
    headers = await _auth_headers(client, db_session)

    res = await client.post(f"/devices/{dev.id}/maintenance", headers=headers, json={
        "type": "calibration", "notes": "kalibrasi pH",
        "performed_at": now.isoformat(),
        "next_due_at": (now + timedelta(days=30)).isoformat(),
        "field": "ph", "before_value": 7.4, "after_value": 7.0,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["field"] == "ph"
    assert body["before_value"] == 7.4 and body["after_value"] == 7.0
    assert round(body["offset"], 3) == -0.4   # derived after - before

    lst = await client.get(f"/devices/{dev.id}/maintenance", headers=headers)
    assert lst.json()[0]["before_value"] == 7.4
