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
