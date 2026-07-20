from datetime import datetime, timezone, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.models import User, Site, LoggerStatus, LoggerEvent


async def _site(db, uid="LOG-1", secret="s3cret"):
    s = Site(uid=uid, name="Test Site", company_name="C", is_active=True, device_secret=secret)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


def _hb_token(uid, status, secret="s3cret"):
    return jwt.encode({"uid": uid, "status": status}, secret, algorithm="HS256")


STATUS = {
    "uptime_s": 3600, "logger_version": "1.4.0", "op_status": 0,
    "ph_ok": True, "tss_ok": False, "debit_ok": True, "cod_ok": None, "nh3n_ok": None,
    "consec_fail": 0, "internet_ok": True,
    "last_send_ok_mm": True, "last_send_ok_klhk": False,
    "buffer_depth": 12, "daily_sent": 640,
    "cpu_temp": 52.3, "cpu_pct": 18.0, "mem_pct": 41.2, "disk_pct": 63.5,
}


@pytest.mark.anyio
async def test_heartbeat_creates_then_updates_single_row(client, db_session):
    site = await _site(db_session)
    r1 = await client.post("/logger/heartbeat", json={"token": _hb_token("LOG-1", STATUS)})
    assert r1.status_code == 200
    r2 = await client.post("/logger/heartbeat", json={"token": _hb_token("LOG-1", {**STATUS, "buffer_depth": 3})})
    assert r2.status_code == 200

    rows = (await db_session.execute(select(LoggerStatus))).scalars().all()
    assert len(rows) == 1                     # upsert, not insert-per-beat
    st = rows[0]
    assert st.site_id == site.id
    assert st.state == "alive"
    assert st.buffer_depth == 3               # latest wins
    assert st.tss_ok is False
    assert st.logger_version == "1.4.0"
    assert st.last_heartbeat_at is not None


@pytest.mark.anyio
async def test_heartbeat_rejects_bad_signature(client, db_session):
    await _site(db_session)
    bad = _hb_token("LOG-1", STATUS, secret="WRONG")
    res = await client.post("/logger/heartbeat", json={"token": bad})
    assert res.status_code == 400


@pytest.mark.anyio
async def test_heartbeat_unknown_site_401(client, db_session):
    res = await client.post("/logger/heartbeat", json={"token": _hb_token("NOPE", STATUS)})
    assert res.status_code == 401


@pytest.mark.anyio
async def test_heartbeat_tracks_sensor_failure_start(client, db_session):
    """sensor_fail_since is stamped when a sensor first reports false and cleared
    when all sensors read OK again — it is what the alarm logic later measures."""
    await _site(db_session)
    await client.post("/logger/heartbeat", json={"token": _hb_token("LOG-1", STATUS)})  # tss_ok False
    st = (await db_session.execute(select(LoggerStatus))).scalars().first()
    first_since = st.sensor_fail_since
    assert first_since is not None

    # still failing on the next beat → the original start time must NOT be reset
    await client.post("/logger/heartbeat", json={"token": _hb_token("LOG-1", STATUS)})
    await db_session.refresh(st)
    assert st.sensor_fail_since == first_since

    # all sensors OK again → cleared
    healthy = {**STATUS, "tss_ok": True}
    await client.post("/logger/heartbeat", json={"token": _hb_token("LOG-1", healthy)})
    await db_session.refresh(st)
    assert st.sensor_fail_since is None


def _ev_token(uid, events, secret="s3cret"):
    return jwt.encode({"uid": uid, "events": events}, secret, algorithm="HS256")


@pytest.mark.anyio
async def test_events_batch_insert_and_idempotent_replay(client, db_session):
    await _site(db_session)
    events = [
        {"event_uid": "e-1", "type": "started", "ts": 1753000000,
         "severity": "info", "detail": "previous_shutdown_clean=false"},
        {"event_uid": "e-2", "type": "net_down", "ts": 1753000100, "severity": "warning"},
    ]
    r1 = await client.post("/logger/events", json={"token": _ev_token("LOG-1", events)})
    assert r1.status_code == 200
    assert r1.json()["accepted"] == 2

    # The logger re-uploads the same batch after a flaky connection: no duplicates.
    r2 = await client.post("/logger/events", json={"token": _ev_token("LOG-1", events)})
    assert r2.status_code == 200
    assert r2.json()["duplicates"] == 2

    rows = (await db_session.execute(select(LoggerEvent))).scalars().all()
    assert len(rows) == 2
    started = [r for r in rows if r.type == "started"][0]
    assert started.severity == "info"
    assert started.received_at is not None


@pytest.mark.anyio
async def test_same_event_uid_from_different_sites_both_stored(client, db_session):
    """Cloned loggers can emit identical uids. One site's event must NEVER
    suppress another site's — dedup is scoped per site."""
    await _site(db_session, uid="LOG-A", secret="secA")
    await _site(db_session, uid="LOG-B", secret="secB")
    ev = [{"event_uid": "shared-uid-1", "type": "started", "ts": 1753000000}]

    ra = await client.post("/logger/events", json={"token": _ev_token("LOG-A", ev, "secA")})
    rb = await client.post("/logger/events", json={"token": _ev_token("LOG-B", ev, "secB")})
    assert ra.json()["accepted"] == 1
    assert rb.json()["accepted"] == 1          # NOT counted as a duplicate

    rows = (await db_session.execute(select(LoggerEvent))).scalars().all()
    assert len(rows) == 2                      # both survived
    assert len({r.site_id for r in rows}) == 2


@pytest.mark.anyio
async def test_duplicate_uids_within_one_batch_inserted_once(client, db_session):
    await _site(db_session)
    ev = [
        {"event_uid": "dup", "type": "net_down", "ts": 1753000000},
        {"event_uid": "dup", "type": "net_down", "ts": 1753000000},
    ]
    res = await client.post("/logger/events", json={"token": _ev_token("LOG-1", ev)})
    assert res.status_code == 200
    rows = (await db_session.execute(select(LoggerEvent))).scalars().all()
    assert len(rows) == 1


@pytest.mark.anyio
async def test_unknown_event_type_stored_not_dropped(client, db_session):
    """Never silently discard an audit record — unknown types are kept."""
    await _site(db_session)
    ev = [{"event_uid": "u-1", "type": "some_future_type", "ts": 1753000000}]
    res = await client.post("/logger/events", json={"token": _ev_token("LOG-1", ev)})
    assert res.json()["accepted"] == 1
    row = (await db_session.execute(select(LoggerEvent))).scalars().first()
    assert row.type == "unknown"


@pytest.mark.anyio
async def test_events_rejects_oversized_batch(client, db_session):
    await _site(db_session)
    events = [{"event_uid": f"x-{i}", "type": "net_up", "ts": 1753000000} for i in range(201)]
    res = await client.post("/logger/events", json={"token": _ev_token("LOG-1", events)})
    assert res.status_code == 400


@pytest.mark.anyio
async def test_events_rejects_empty_batch(client, db_session):
    await _site(db_session)
    res = await client.post("/logger/events", json={"token": _ev_token("LOG-1", [])})
    assert res.status_code == 400
