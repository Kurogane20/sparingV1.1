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
