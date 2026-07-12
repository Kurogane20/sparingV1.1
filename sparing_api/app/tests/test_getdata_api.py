import time

import jwt
import pytest
from sqlalchemy import select, func

from app.models.models import Site, SensorData

SECRET = "test-device-secret"


@pytest.fixture(autouse=True)
def _silence_background_tasks(monkeypatch):
    """post_data fires trigger_alerts/detect_realtime via asyncio.create_task;
    they open their own (MySQL) session. Stub them so tests exercise only the
    parse-and-store path."""
    async def _noop(*args, **kwargs):
        return None
    monkeypatch.setattr("app.api.routers.getdata.trigger_alerts", _noop)
    monkeypatch.setattr("app.api.routers.getdata.detect_realtime", _noop)


def _token(uid, readings, secret=SECRET, device_id="DEV-1"):
    return jwt.encode({"uid": uid, "device_id": device_id, "data": readings},
                      secret, algorithm="HS256")


async def _make_site(db, uid):
    db.add(Site(uid=uid, name="Test", company_name="C", device_secret=SECRET, is_active=True))
    await db.commit()


@pytest.mark.anyio
async def test_post_data_stores_valid_batch(client, db_session):
    await _make_site(db_session, "TST-1")
    now = int(time.time())
    readings = [
        {"datetime": now, "ph": 7.1, "tss": 20, "cod": 100},
        {"datetime": now + 120, "ph": 7.2, "tss": 22, "cod": 105},
    ]
    res = await client.post("/api/post-data", json={"token": _token("TST-1", readings)})
    assert res.status_code == 200
    body = res.json()
    assert body["rows"] == 2 and body["dropped"] == 0
    count = (await db_session.execute(select(func.count(SensorData.id)))).scalar_one()
    assert count == 2


@pytest.mark.anyio
async def test_post_data_drops_impossible_value_keeps_batch(client, db_session):
    # #6 regression: one impossible reading must not discard the valid ones
    await _make_site(db_session, "TST-2")
    now = int(time.time())
    readings = [
        {"datetime": now, "ph": 15.0, "tss": 20},        # pH 15 is impossible
        {"datetime": now + 120, "ph": 7.2, "tss": 22},
    ]
    res = await client.post("/api/post-data", json={"token": _token("TST-2", readings)})
    assert res.status_code == 200
    body = res.json()
    assert body["rows"] == 2      # both readings stored
    assert body["dropped"] == 1   # the impossible pH dropped
    rows = (await db_session.execute(
        select(SensorData.ph, SensorData.tss).order_by(SensorData.ts)
    )).all()
    assert rows[0].ph is None and rows[0].tss == 20   # bad field NULLed, rest kept
    assert rows[1].ph == 7.2


@pytest.mark.anyio
async def test_post_data_invalid_signature_rejected(client, db_session):
    await _make_site(db_session, "TST-3")
    now = int(time.time())
    bad = _token("TST-3", [{"datetime": now, "ph": 7.0}], secret="wrong-secret")
    res = await client.post("/api/post-data", json={"token": bad})
    assert res.status_code == 400
    count = (await db_session.execute(select(func.count(SensorData.id)))).scalar_one()
    assert count == 0


@pytest.mark.anyio
async def test_post_data_unknown_site_rejected(client, db_session):
    now = int(time.time())
    tok = _token("NO-SUCH-SITE", [{"datetime": now, "ph": 7.0}])
    res = await client.post("/api/post-data", json={"token": tok})
    assert res.status_code == 401
