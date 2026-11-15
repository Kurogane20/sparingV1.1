from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.models.models import DeviceRejection, Site
from app.utils import rejection_log
from app.utils.rejection_log import flush_pending, record_rejection
from app.utils.time import as_utc


async def _site(db, uid="LOG-R", secret="sec"):
    s = Site(uid=uid, name=uid, company_name="C", is_active=True, device_secret=secret)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest.mark.anyio
async def test_record_counts_a_run_and_starts_a_new_one_after_24h(db_session):
    site = await _site(db_session)
    t0 = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    await record_rejection(db_session, "LOG-R", "post-data", "bad_signature", "n=30", t0)
    await record_rejection(db_session, "LOG-R", "post-data", "bad_signature", "n=30 later", t0 + timedelta(hours=1))
    row = (await db_session.execute(select(DeviceRejection))).scalars().one()
    assert row.count == 2
    assert row.site_id == site.id
    assert row.last_detail == "n=30 later"
    assert as_utc(row.first_at) == t0

    await record_rejection(db_session, "LOG-R", "post-data", "bad_signature", None, t0 + timedelta(hours=30))
    await db_session.refresh(row)
    assert row.count == 1                                  # a new run, not 3
    assert as_utc(row.first_at) == t0 + timedelta(hours=30)


@pytest.mark.anyio
async def test_unknown_uid_and_unreadable_token_are_recorded_without_a_site(db_session):
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    await record_rejection(db_session, "admin-LOG", "get-key", "unknown_uid", None, now)
    await record_rejection(db_session, "", "post-data", "malformed", None, now)
    rows = (await db_session.execute(select(DeviceRejection))).scalars().all()
    assert {(r.uid, r.site_id) for r in rows} == {("admin-LOG", None), ("", None)}


@pytest.mark.anyio
async def test_a_refused_heartbeat_is_recorded_in_the_background(client, db_session):
    await _site(db_session)
    bad = jwt.encode({"uid": "LOG-R", "status": {}}, "WRONG", algorithm="HS256")
    res = await client.post("/logger/heartbeat", json={"token": bad})
    assert res.status_code == 400
    await flush_pending()
    row = (await db_session.execute(select(DeviceRejection))).scalars().one()
    assert (row.uid, row.source, row.reason) == ("LOG-R", "heartbeat", "bad_signature")


@pytest.mark.anyio
async def test_get_key_for_an_unknown_uid_is_recorded(client, db_session):
    res = await client.get("/api/get-key", params={"uid": "admin-LOG"})
    assert res.status_code == 404
    await flush_pending()
    row = (await db_session.execute(select(DeviceRejection))).scalars().one()
    assert (row.uid, row.source, row.reason, row.site_id) == ("admin-LOG", "get-key", "unknown_uid", None)


@pytest.mark.anyio
async def test_a_failing_record_never_changes_the_response(client, db_session, monkeypatch, caplog):
    await _site(db_session)

    async def boom(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(rejection_log, "record_rejection", boom)
    bad = jwt.encode({"uid": "LOG-R", "status": {}}, "WRONG", algorithm="HS256")
    res = await client.post("/logger/heartbeat", json={"token": bad})
    assert res.status_code == 400
    await flush_pending()                                  # the failure is logged and swallowed
    assert "could not record device rejection" in caplog.text
    assert (await db_session.execute(select(DeviceRejection))).scalars().first() is None


@pytest.mark.anyio
async def test_new_unknown_uids_stop_at_the_cap(db_session, monkeypatch):
    monkeypatch.setattr(rejection_log, "MAX_UNKNOWN", 3)
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    for i in range(5):
        await record_rejection(db_session, f"rnd-{i}", "get-key", "unknown_uid", None, now)
    await record_rejection(db_session, "rnd-0", "get-key", "unknown_uid", None, now)   # an existing one still counts
    rows = (await db_session.execute(select(DeviceRejection))).scalars().all()
    assert sorted(r.uid for r in rows) == ["rnd-0", "rnd-1", "rnd-2"]
    assert next(r for r in rows if r.uid == "rnd-0").count == 2


@pytest.mark.anyio
async def test_known_sites_are_never_capped(db_session, monkeypatch):
    monkeypatch.setattr(rejection_log, "MAX_UNKNOWN", 1)
    await _site(db_session)
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    await record_rejection(db_session, "rnd-0", "get-key", "unknown_uid", None, now)
    await record_rejection(db_session, "LOG-R", "post-data", "bad_signature", None, now)
    assert {r.uid for r in (await db_session.execute(select(DeviceRejection))).scalars().all()} == {"rnd-0", "LOG-R"}


@pytest.mark.anyio
async def test_a_long_or_odd_uid_is_cut_to_the_column(db_session):
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    for _ in range(2):
        await record_rejection(db_session, "x" * 500, "post-data", "unknown_uid", None, now)
    await record_rejection(db_session, 12345, "post-data", "unknown_uid", None, now)
    rows = (await db_session.execute(select(DeviceRejection).order_by(DeviceRejection.id))).scalars().all()
    assert [(len(r.uid), r.count) for r in rows] == [(64, 2), (5, 1)]


@pytest.mark.anyio
async def test_a_non_string_uid_is_refused_as_no_uid(client, db_session):
    # One refusal at a time: test sessions share one SQLite connection, so
    # overlapping background writes would interfere in a way production
    # (one connection per session) does not.
    for uid in (12345, {"$ne": ""}, ["LOG-R"]):
        token = jwt.encode({"uid": uid, "status": {}}, "x", algorithm="HS256")
        res = await client.post("/logger/heartbeat", json={"token": token})
        assert res.status_code == 400
        await flush_pending()
    row = (await db_session.execute(select(DeviceRejection))).scalars().one()
    assert (row.uid, row.reason, row.count) == ("", "no_uid", 3)
