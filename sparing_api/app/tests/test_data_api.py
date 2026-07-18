from datetime import datetime, timezone, timedelta

import pytest

from app.core.security import hash_password
from app.models.models import User, Site, SensorData


async def _auth_headers(client, db, email="op@example.com"):
    db.add(User(name="Op", email=email, password_hash=hash_password("Secret123"),
                role="operator", is_active=True))
    await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _make_site(db, uid="TST-1"):
    site = Site(uid=uid, name="Test", company_name="C", is_active=True)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


def _row(site_id, ts, **vals):
    return SensorData(site_id=site_id, ts=ts,
                      created_at=datetime.now(timezone.utc), **vals)


@pytest.mark.anyio
async def test_data_returns_quality_flag(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    t0 = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    db_session.add(_row(site.id, t0, ph=7.0))
    db_session.add(_row(site.id, t0 + timedelta(minutes=2), ph=13.5, quality_flag="anomaly"))
    await db_session.commit()

    res = await client.get("/data", params={"site_uid": "TST-1", "order": "asc"},
                           headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 2
    assert items[0]["quality_flag"] is None
    assert items[1]["quality_flag"] == "anomaly"
