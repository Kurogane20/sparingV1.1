from datetime import datetime, timezone, timedelta

import pytest

from app.core.security import hash_password
from app.models.models import User, Site, SensorData


async def _auth_headers(client, db, email="an@example.com"):
    db.add(User(name="An", email=email, password_hash=hash_password("Secret123"),
                role="operator", is_active=True))
    await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _make_site(db, uid="AN-1"):
    site = Site(uid=uid, name="Test", company_name="C", is_active=True)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


def _row(site_id, ts, **vals):
    return SensorData(site_id=site_id, ts=ts, created_at=datetime.now(timezone.utc), **vals)


@pytest.mark.anyio
async def test_gaps_endpoint_detects_hole(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    base = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
    # steady 2-min readings, then a 30-min hole, then resume
    for m in (0, 2, 4, 34, 36):
        db_session.add(_row(site.id, base + timedelta(minutes=m), ph=7.0))
    # a calibration row inside the hole must NOT patch the gap
    db_session.add(_row(site.id, base + timedelta(minutes=18), ph=None, op_status=-2))
    await db_session.commit()

    res = await client.get("/analytics/gaps", params={
        "site_uid": "AN-1",
        "date_from": base.isoformat(),
        "date_to": (base + timedelta(hours=1)).isoformat(),
    }, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["gap_count"] == 1
    assert body["reading_count"] == 5          # op_status row excluded
    assert body["gaps"][0]["duration_minutes"] == 30.0


@pytest.mark.anyio
async def test_volume_endpoint_integrates_debit(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session, uid="AN-VOL")
    base = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
    # 10 L/min held across 10 minutes = 100 L = 0.1 m3
    for m in (0, 5, 10):
        db_session.add(_row(site.id, base + timedelta(minutes=m), debit=10.0))
    await db_session.commit()

    res = await client.get("/analytics/volume", params={
        "site_uid": "AN-VOL",
        "date_from": base.isoformat(),
        "date_to": (base + timedelta(hours=1)).isoformat(),
    }, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total_liters"] == 100.0
    assert body["total_m3"] == 0.1


@pytest.mark.anyio
async def test_analytics_forbidden_for_unassigned_viewer(client, db_session):
    # viewer scoped to a different site cannot read AN-1
    db_session.add(User(name="V", email="v@example.com",
                        password_hash=hash_password("Secret123"), role="viewer", is_active=True))
    site = await _make_site(db_session, uid="AN-SECRET")
    other = await _make_site(db_session, uid="AN-OTHER")
    from app.models.models import ViewerSite
    user = (await db_session.execute(
        __import__("sqlalchemy").select(User).where(User.email == "v@example.com")
    )).scalar_one()
    db_session.add(ViewerSite(user_id=user.id, site_id=other.id))
    await db_session.commit()

    res = await client.post("/auth/login", json={"email": "v@example.com", "password": "Secret123"})
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    r = await client.get("/analytics/gaps", params={"site_uid": "AN-SECRET"}, headers=headers)
    assert r.status_code == 403
