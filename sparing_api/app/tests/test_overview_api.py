from datetime import datetime, timezone, timedelta

import pytest

from app.core.security import hash_password
from app.models.models import User, Site, SensorData, AlertRule, Alert, LoggerStatus


async def _login(client, db, role, email):
    db.add(User(name=role, email=email, password_hash=hash_password("Secret123"),
                role=role, is_active=True))
    await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _make_site(db, uid, name):
    site = Site(uid=uid, name=name, company_name="C", is_active=True)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


def _row(site_id, ts, **vals):
    return SensorData(site_id=site_id, ts=ts, created_at=datetime.now(timezone.utc), **vals)


@pytest.mark.anyio
async def test_overview_admin_aggregates_all_sites(client, db_session):
    headers = await _login(client, db_session, "admin", "a@example.com")
    now = datetime.now(timezone.utc)
    a = await _make_site(db_session, "OV-A", "Alpha")
    b = await _make_site(db_session, "OV-B", "Bravo")
    # A: fresh reading (online) + a compliant tss rule
    db_session.add(_row(a.id, now - timedelta(minutes=5), tss=50.0, ph=7.0))
    db_session.add(AlertRule(site_id=a.id, field="tss", danger_min=None, danger_max=200.0,
                             is_active=True, created_at=now, updated_at=now))
    # B: stale reading (offline) + an active danger alarm
    db_session.add(_row(b.id, now - timedelta(days=3), tss=250.0))
    db_session.add(Alert(site_id=b.id, field="tss", value=250.0, threshold_type="danger",
                         status="active", triggered_at=now, category="compliance"))
    db_session.add(LoggerStatus(site_id=b.id, state="down", last_heartbeat_at=now - timedelta(hours=2)))
    await db_session.commit()

    res = await client.get("/overview", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["totals"]["site_count"] == 2
    assert body["totals"]["online_count"] == 1          # only A
    assert body["totals"]["total_active_alarms"] == 1
    assert body["totals"]["sites_with_danger"] == 1

    by_uid = {s["uid"]: s for s in body["sites"]}
    assert by_uid["OV-A"]["status"] == "online"
    assert by_uid["OV-A"]["last_values"]["tss"] == 50.0
    assert by_uid["OV-A"]["compliance_pct"] == 100.0
    assert by_uid["OV-B"]["status"] == "offline"
    assert by_uid["OV-B"]["active_alarms"] == 1
    assert by_uid["OV-B"]["danger_alarms"] == 1
    assert by_uid["OV-B"]["logger_state"] == "down"


@pytest.mark.anyio
async def test_overview_forbidden_for_operator(client, db_session):
    headers = await _login(client, db_session, "operator", "op@example.com")
    res = await client.get("/overview", headers=headers)
    assert res.status_code == 403


@pytest.mark.anyio
async def test_overview_forbidden_for_viewer(client, db_session):
    headers = await _login(client, db_session, "viewer", "v@example.com")
    res = await client.get("/overview", headers=headers)
    assert res.status_code == 403
