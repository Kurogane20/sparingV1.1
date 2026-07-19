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


@pytest.mark.anyio
async def test_hourly_aggregation_excludes_anomaly(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session, uid="TST-AGG")
    base = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    db_session.add(_row(site.id, base, tss=10.0))
    db_session.add(_row(site.id, base + timedelta(minutes=10), tss=20.0))
    db_session.add(_row(site.id, base + timedelta(minutes=20), tss=900.0, quality_flag="anomaly"))
    db_session.add(_row(site.id, base + timedelta(hours=1, minutes=5), tss=30.0))
    await db_session.commit()

    res = await client.get("/data", params={
        "site_uid": "TST-AGG", "interval": "hourly", "order": "asc",
        "date_from": "2026-07-01T00:00:00Z", "fields": "tss",
    }, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2                       # two hourly buckets
    assert body["items"][0]["tss"] == 15.0          # (10+20)/2, anomaly excluded
    assert body["items"][0]["count"] == 2
    assert body["items"][1]["tss"] == 30.0


@pytest.mark.anyio
async def test_daily_aggregation_single_bucket(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session, uid="TST-DAY")
    base = datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc)
    for i, v in enumerate((6.0, 7.0, 8.0)):
        db_session.add(_row(site.id, base + timedelta(hours=i), ph=v))
    await db_session.commit()

    res = await client.get("/data", params={
        "site_uid": "TST-DAY", "interval": "daily", "order": "asc",
        "date_from": "2026-07-01T00:00:00Z", "fields": "ph",
    }, headers=headers)
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["ph"] == 7.0
    assert body["items"][0]["count"] == 3


@pytest.mark.anyio
async def test_aggregation_requires_date_from(client, db_session):
    headers = await _auth_headers(client, db_session)
    await _make_site(db_session, uid="TST-G")
    res = await client.get("/data", params={"site_uid": "TST-G", "interval": "hourly"},
                           headers=headers)
    assert res.status_code == 400


@pytest.mark.anyio
async def test_viewer_without_site_uid_is_confined_to_assigned_sites(client, db_session):
    from app.models.models import User, ViewerSite
    # Two sites with data; viewer assigned only to the first.
    site_a = await _make_site(db_session, uid="VS-A")
    site_b = await _make_site(db_session, uid="VS-B")
    t0 = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    db_session.add(_row(site_a.id, t0, ph=7.0))
    db_session.add(_row(site_b.id, t0, ph=8.0))
    viewer = User(name="Pengawas", email="v@example.com",
                  password_hash=hash_password("Secret123"), role="viewer", is_active=True)
    db_session.add(viewer)
    await db_session.commit()
    await db_session.refresh(viewer)
    db_session.add(ViewerSite(user_id=viewer.id, site_id=site_a.id))
    await db_session.commit()
    login = await client.post("/auth/login", json={"email": "v@example.com", "password": "Secret123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # No site_uid given → must NOT leak site B's data.
    res = await client.get("/data", headers=headers)
    assert res.status_code == 200
    site_ids = {item["site_id"] for item in res.json()["items"]}
    assert site_ids == {site_a.id}
