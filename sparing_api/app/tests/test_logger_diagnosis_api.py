from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.models import DeviceRejection, LoggerIncident, LoggerStatus, Site, User, ViewerSite


async def _site(db, uid, active=True):
    s = Site(uid=uid, name=uid, company_name="C", is_active=active)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _status(db, site, minutes_ago):
    db.add(LoggerStatus(site_id=site.id, state="alive", last_send_ok_mm=True, last_send_ok_klhk=True,
                        last_heartbeat_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)))
    await db.commit()


async def _login(client, db, role, email, site=None):
    db.add(User(name=role, email=email, password_hash=hash_password("Secret123"), role=role, is_active=True))
    await db.commit()
    if site is not None:
        user = (await db.execute(select(User).where(User.email == email))).scalars().first()
        db.add(ViewerSite(user_id=user.id, site_id=site.id))
        await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.anyio
async def test_diagnosis_lists_every_active_site_worst_first(client, db_session):
    ok = await _site(db_session, "A-OK")
    await _site(db_session, "B-NEVER")
    await _site(db_session, "C-OFF", active=False)
    await _status(db_session, ok, minutes_ago=1)
    headers = await _login(client, db_session, "admin", "a@example.com")

    rows = (await client.get("/logger/diagnosis", headers=headers)).json()
    assert [r["site_uid"] for r in rows] == ["B-NEVER", "A-OK"]
    assert rows[0]["state"] == "down"
    assert rows[0]["headline"] == "Belum pernah mengirim heartbeat; data terakhir tidak ada."
    assert rows[1]["state"] == "normal"


@pytest.mark.anyio
async def test_diagnosis_is_cut_per_role(client, db_session):
    site = await _site(db_session, "L-1")
    await _status(db_session, site, minutes_ago=180)
    admin = (await client.get("/logger/diagnosis", headers=await _login(client, db_session, "admin", "a@x.io"))).json()[0]
    assert admin["tech"]["uid"] == "L-1" and admin["device"] and admin["findings"][0]["action"]
    operator = (await client.get("/logger/diagnosis", headers=await _login(client, db_session, "operator", "o@x.io"))).json()[0]
    assert "tech" not in operator and operator["device"] and "tech" not in operator["findings"][0]
    viewer = (await client.get("/logger/diagnosis", headers=await _login(client, db_session, "viewer", "v@x.io", site))).json()[0]
    assert "tech" not in viewer and "device" not in viewer and "action" not in viewer["findings"][0]


@pytest.mark.anyio
async def test_a_viewer_without_sites_sees_nothing(client, db_session):
    await _site(db_session, "L-1")
    headers = await _login(client, db_session, "viewer", "v@x.io")
    assert (await client.get("/logger/diagnosis", headers=headers)).json() == []
    assert (await client.get("/logger/incidents", headers=headers)).json() == []


@pytest.mark.anyio
async def test_one_failing_site_does_not_break_the_list(client, db_session, monkeypatch):
    from app.utils import logger_diagnosis
    await _status(db_session, await _site(db_session, "GOOD"), minutes_ago=1)
    await _site(db_session, "BAD")
    real = logger_diagnosis.diagnose

    def flaky(inp, now):
        if inp.uid == "BAD":
            raise RuntimeError("boom")
        return real(inp, now)

    monkeypatch.setattr(logger_diagnosis, "diagnose", flaky)
    rows = (await client.get("/logger/diagnosis", headers=await _login(client, db_session, "admin", "a@x.io"))).json()
    by_uid = {r["site_uid"]: r for r in rows}
    assert by_uid["BAD"]["state"] == "unknown" and by_uid["BAD"]["headline"] == "Diagnosis gagal dimuat."
    assert by_uid["GOOD"]["state"] == "normal"


@pytest.mark.anyio
async def test_incidents_cover_the_window_and_hide_evidence_from_non_admins(client, db_session):
    site = await _site(db_session, "L-1")
    now = datetime.now(timezone.utc)
    db_session.add_all([
        LoggerIncident(site_id=site.id, kind="down", started_at=now - timedelta(days=40),
                       open_key=f"{site.id}:down", evidence={"title": "x"}),
        LoggerIncident(site_id=site.id, kind="down", started_at=now - timedelta(days=36),
                       ended_at=now - timedelta(days=35)),
        LoggerIncident(site_id=site.id, kind="down", started_at=now - timedelta(days=2, minutes=161),
                       ended_at=now - timedelta(days=2), cause="internet",
                       cause_detail="Internet lokasi putus 2 jam 41 menit; data menyusul 98%.",
                       data_expected=81, data_recovered=79, evidence={"events": []}),
    ])
    await db_session.commit()

    admin = (await client.get("/logger/incidents", headers=await _login(client, db_session, "admin", "a@x.io"))).json()
    assert len(admin) == 2                                     # the one ended 35 days ago is outside
    closed = next(i for i in admin if i["ended_at"])
    assert closed["duration_min"] == 161 and closed["cause"] == "internet" and "evidence" in closed
    assert next(i for i in admin if not i["ended_at"])["site_uid"] == "L-1"

    headers = await _login(client, db_session, "operator", "o@x.io")
    assert all("evidence" not in i for i in (await client.get("/logger/incidents", headers=headers)).json())
    assert (await client.get("/logger/incidents?days=0", headers=headers)).status_code == 422
    assert (await client.get("/logger/incidents?days=91", headers=headers)).status_code == 422


@pytest.mark.anyio
async def test_rejections_are_for_admins_and_include_unknown_uids(client, db_session):
    now = datetime.now(timezone.utc)
    db_session.add_all([
        DeviceRejection(uid="admin-LOG", source="get-key", reason="unknown_uid",
                        first_at=now - timedelta(hours=2), last_at=now, count=3),
        DeviceRejection(uid="OLD-LOG", source="post-data", reason="bad_signature",
                        first_at=now - timedelta(days=9), last_at=now - timedelta(days=8), count=1),
    ])
    await db_session.commit()
    rows = (await client.get("/logger/rejections", headers=await _login(client, db_session, "admin", "a@x.io"))).json()
    assert [(r["uid"], r["site_uid"], r["count"]) for r in rows] == [("admin-LOG", None, 3)]
    res = await client.get("/logger/rejections", headers=await _login(client, db_session, "operator", "o@x.io"))
    assert res.status_code == 403
