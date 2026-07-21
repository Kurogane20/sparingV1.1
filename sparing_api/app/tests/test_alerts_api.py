from datetime import datetime, timezone

import pytest

from app.core.security import hash_password
from app.models.models import User, Site, Alert


async def _auth_headers(client, db, email="op@example.com"):
    db.add(User(name="Operator Satu", email=email,
                password_hash=hash_password("Secret123"), role="operator", is_active=True))
    await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _viewer_headers(client, db, email="viewer@example.com"):
    db.add(User(name="Pengawas", email=email,
                password_hash=hash_password("Secret123"), role="viewer", is_active=True))
    await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _make_alert(db, site_uid="TST-1", **overrides):
    site = Site(uid=site_uid, name="Test", company_name="C", is_active=True)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    fields = dict(site_id=site.id, field="tss", value=250.0, threshold_type="danger",
                  status="active", triggered_at=datetime.now(timezone.utc),
                  category="compliance")
    fields.update(overrides)
    alert = Alert(**fields)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@pytest.mark.anyio
async def test_resolve_without_note_400(client, db_session):
    headers = await _auth_headers(client, db_session)
    alert = await _make_alert(db_session)
    res = await client.patch(f"/alerts/{alert.id}/resolve", json={}, headers=headers)
    assert res.status_code == 400
    res2 = await client.patch(f"/alerts/{alert.id}/resolve", json={"note": "   "}, headers=headers)
    assert res2.status_code == 400


@pytest.mark.anyio
async def test_resolve_with_note_stores_fields(client, db_session):
    headers = await _auth_headers(client, db_session)
    alert = await _make_alert(db_session)
    res = await client.patch(f"/alerts/{alert.id}/resolve",
                             json={"note": "Sensor dibersihkan, nilai normal"}, headers=headers)
    assert res.status_code == 200
    await db_session.refresh(alert)
    assert alert.status == "resolved"
    assert alert.followup_note == "Sensor dibersihkan, nilai normal"
    assert alert.resolved_at is not None
    assert alert.followup_by_user_id is not None


@pytest.mark.anyio
async def test_followup_sets_acknowledged_note_optional(client, db_session):
    headers = await _auth_headers(client, db_session)
    alert = await _make_alert(db_session)
    res = await client.patch(f"/alerts/{alert.id}/followup", json={}, headers=headers)
    assert res.status_code == 200
    await db_session.refresh(alert)
    assert alert.status == "acknowledged"
    assert alert.followup_at is not None
    assert alert.followup_by_user_id is not None
    # then resolving still demands a note
    res2 = await client.patch(f"/alerts/{alert.id}/resolve", json={}, headers=headers)
    assert res2.status_code == 400


@pytest.mark.anyio
async def test_alert_out_includes_followup_fields(client, db_session):
    headers = await _auth_headers(client, db_session)
    alert = await _make_alert(db_session)
    await client.patch(f"/alerts/{alert.id}/followup",
                       json={"note": "Cek panel listrik"}, headers=headers)
    res = await client.get("/alerts", params={"status": "acknowledged"}, headers=headers)
    assert res.status_code == 200
    item = res.json()[0]
    assert item["followup_note"] == "Cek panel listrik"
    assert item["followup_by_name"] == "Operator Satu"
    assert item["followup_at"] is not None


@pytest.mark.anyio
async def test_alerts_bare_list_without_page_param(client, db_session):
    headers = await _auth_headers(client, db_session)
    await _make_alert(db_session)
    res = await client.get("/alerts", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)  # AlertDropdown compatibility


@pytest.mark.anyio
async def test_alerts_paginated_wrapper_with_page_param(client, db_session):
    headers = await _auth_headers(client, db_session)
    for i in range(3):
        await _make_alert(db_session, site_uid=f"TST-{i}")
    res = await client.get("/alerts", params={"page": 1, "per_page": 2}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert len(body["items"]) == 2


@pytest.mark.anyio
async def test_alerts_filters(client, db_session):
    headers = await _auth_headers(client, db_session)
    await _make_alert(db_session, site_uid="TST-A")  # compliance/danger
    await _make_alert(db_session, site_uid="TST-B",
                      category="data_quality", anomaly_type="flatline",
                      threshold_type="warning")
    r1 = await client.get("/alerts", params={"category": "data_quality"}, headers=headers)
    assert len(r1.json()) == 1 and r1.json()[0]["category"] == "data_quality"
    r2 = await client.get("/alerts", params={"threshold_type": "danger"}, headers=headers)
    assert len(r2.json()) == 1 and r2.json()[0]["threshold_type"] == "danger"
    r3 = await client.get("/alerts", params={"status": "all"}, headers=headers)
    assert len(r3.json()) == 2


@pytest.mark.anyio
async def test_viewer_cannot_resolve_alert_403(client, db_session):
    # Viewers are read-only per the access matrix: they must not close/mutate alerts.
    alert = await _make_alert(db_session)
    headers = await _viewer_headers(client, db_session)
    res = await client.patch(f"/alerts/{alert.id}/resolve",
                             json={"note": "coba tutup"}, headers=headers)
    assert res.status_code == 403
    await db_session.refresh(alert)
    assert alert.status == "active"  # unchanged


@pytest.mark.anyio
async def test_viewer_cannot_followup_or_acknowledge_403(client, db_session):
    alert = await _make_alert(db_session)
    headers = await _viewer_headers(client, db_session)
    r1 = await client.patch(f"/alerts/{alert.id}/followup", json={}, headers=headers)
    r2 = await client.patch(f"/alerts/{alert.id}/acknowledge", headers=headers)
    assert r1.status_code == 403
    assert r2.status_code == 403


@pytest.mark.anyio
async def test_alert_count_scoped_by_site_uid(client, db_session):
    headers = await _auth_headers(client, db_session)
    await _make_alert(db_session, site_uid="AC-A")
    b = await _make_alert(db_session, site_uid="AC-B")
    # a second active alert on the SAME site B (unique site uid, two alerts)
    db_session.add(Alert(site_id=b.site_id, field="ph", value=5.0, threshold_type="danger",
                         status="active", triggered_at=datetime.now(timezone.utc),
                         category="compliance"))
    await db_session.commit()
    total = await client.get("/alerts/count", params={"status": "active"}, headers=headers)
    assert total.json()["count"] == 3
    scoped = await client.get("/alerts/count", params={"status": "active", "site_uid": "AC-B"}, headers=headers)
    assert scoped.json()["count"] == 2
