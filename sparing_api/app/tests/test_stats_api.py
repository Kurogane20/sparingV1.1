from datetime import datetime, timezone, timedelta

import pytest

from app.core.security import hash_password
from app.models.models import User, Site, SensorData, AlertRule


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
async def test_completeness_counts_window(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    now = datetime.now(timezone.utc)
    for i in range(45):  # 45 rows inside the last 24h
        db_session.add(_row(site.id, now - timedelta(minutes=5 * i), ph=7.0))
    db_session.add(_row(site.id, now - timedelta(hours=30), ph=7.0))  # outside window
    await db_session.commit()

    res = await client.get("/stats/completeness", params={"hours": 24}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["actual"] == 45
    assert body["expected"] == 1 * 30 * 24  # sites * 30/hour * hours
    assert body["pct"] == round(45 * 100.0 / 720, 1)
