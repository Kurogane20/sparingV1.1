from datetime import datetime, timezone, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.models import User, Site, LoggerStatus


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
