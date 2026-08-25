import asyncio
import time
from datetime import datetime, timezone

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
async def test_post_data_schedules_compliance_alert_at_newest_measurement_time(
    client, db_session, monkeypatch
):
    await _make_site(db_session, "TST-ALERT-TS")
    captured = []

    async def _capture_alert(**kwargs):
        captured.append(kwargs)

    created_tasks = []
    original_create_task = asyncio.create_task

    def _capture_task(coro):
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr("app.api.routers.getdata.trigger_alerts", _capture_alert)
    monkeypatch.setattr("app.api.routers.getdata.asyncio.create_task", _capture_task)
    epoch = 1785576600
    readings = [
        {"datetime": epoch - 120, "tss": 20},
        {"datetime": epoch, "tss": 250},
    ]

    response = await client.post(
        "/api/post-data", json={"token": _token("TST-ALERT-TS", readings)}
    )
    await asyncio.gather(*created_tasks)

    assert response.status_code == 200
    assert len(captured) == 1
    call = captured[0]
    expected_ts = datetime.fromtimestamp(epoch, tz=timezone.utc)
    assert call["site_uid"] == "TST-ALERT-TS"
    assert call["device_uid"] == "DEV-1"
    assert call["data"]["tss"] == 250.0
    assert call["data"]["ts"] == expected_ts
    assert call["measurement_ts"] == expected_ts


@pytest.mark.anyio
async def test_post_data_schedules_from_newest_accepted_row_not_input_order(
    client, db_session, monkeypatch
):
    await _make_site(db_session, "TST-UNORDERED-TS")
    captured_alerts = []
    captured_anomalies = []

    async def _capture_alert(**kwargs):
        captured_alerts.append(kwargs)

    async def _capture_anomaly(**kwargs):
        captured_anomalies.append(kwargs)

    created_tasks = []
    original_create_task = asyncio.create_task

    def _capture_task(coro):
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr("app.api.routers.getdata.trigger_alerts", _capture_alert)
    monkeypatch.setattr("app.api.routers.getdata.detect_realtime", _capture_anomaly)
    monkeypatch.setattr("app.api.routers.getdata.asyncio.create_task", _capture_task)
    epoch = 1785576600
    response = await client.post("/api/post-data", json={"token": _token(
        "TST-UNORDERED-TS",
        [
            {"datetime": epoch + 240, "tss": 250},  # newest accepted, first
            {"datetime": epoch, "tss": 20},
        ],
    )})
    await asyncio.gather(*created_tasks)

    expected_ts = datetime.fromtimestamp(epoch + 240, tz=timezone.utc)
    stored = (await db_session.execute(
        select(SensorData).where(SensorData.ts == expected_ts)
    )).scalar_one()
    assert response.status_code == 200
    assert captured_alerts[0]["data"]["tss"] == stored.tss == 250.0
    assert captured_alerts[0]["data"]["ts"] == expected_ts
    assert captured_alerts[0]["measurement_ts"] == expected_ts
    assert [row["ts"] for row in captured_anomalies[0]["readings"]] == [
        expected_ts,
        datetime.fromtimestamp(epoch, tz=timezone.utc),
    ]


@pytest.mark.anyio
async def test_post_data_does_not_schedule_from_trailing_duplicate(
    client, db_session, monkeypatch
):
    await _make_site(db_session, "TST-DUPLICATE-TS")
    site = (await db_session.execute(select(Site).where(Site.uid == "TST-DUPLICATE-TS"))).scalar_one()
    epoch = 1785576600
    duplicate_ts = datetime.fromtimestamp(epoch + 480, tz=timezone.utc)
    db_session.add(SensorData(site_id=site.id, ts=duplicate_ts, tss=999))
    await db_session.commit()
    captured_alerts = []
    captured_anomalies = []

    async def _capture_alert(**kwargs):
        captured_alerts.append(kwargs)

    async def _capture_anomaly(**kwargs):
        captured_anomalies.append(kwargs)

    created_tasks = []
    original_create_task = asyncio.create_task

    def _capture_task(coro):
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr("app.api.routers.getdata.trigger_alerts", _capture_alert)
    monkeypatch.setattr("app.api.routers.getdata.detect_realtime", _capture_anomaly)
    monkeypatch.setattr("app.api.routers.getdata.asyncio.create_task", _capture_task)
    response = await client.post("/api/post-data", json={"token": _token(
        "TST-DUPLICATE-TS",
        [
            {"datetime": epoch + 240, "tss": 250},  # accepted
            {"datetime": epoch + 480, "tss": 999},  # existing duplicate
        ],
    )})
    await asyncio.gather(*created_tasks)

    expected_ts = datetime.fromtimestamp(epoch + 240, tz=timezone.utc)
    stored = (await db_session.execute(
        select(SensorData).where(SensorData.ts == expected_ts)
    )).scalar_one()
    assert response.status_code == 200
    assert captured_alerts[0]["data"]["tss"] == stored.tss == 250.0
    assert captured_alerts[0]["data"]["ts"] == expected_ts
    assert captured_alerts[0]["measurement_ts"] == expected_ts
    assert captured_anomalies[0]["readings"] == [captured_alerts[0]["data"]]


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
async def test_post_data_drops_garbage_electrical_and_extreme_values(client, db_session):
    """#5: ingest hard-rejects clearly-corrupt values on every parameter,
    including voltage/current/temp which were previously unbounded."""
    await _make_site(db_session, "TST-SAN")
    now = int(time.time())
    readings = [{
        "datetime": now,
        "ph": 7.0,
        "voltage": 99999,   # garbage — no real mains reads 99999 V
        "current": 88888,   # garbage
        "temp": 9999,       # garbage
        "tss": 20,
    }]
    res = await client.post("/api/post-data", json={"token": _token("TST-SAN", readings)})
    assert res.status_code == 200
    body = res.json()
    assert body["dropped"] == 3   # voltage, current, temp
    row = (await db_session.execute(select(SensorData))).scalars().first()
    assert row.voltage is None and row.current is None and row.temp is None
    assert row.ph == 7.0 and row.tss == 20   # valid fields untouched


@pytest.mark.anyio
async def test_post_data_keeps_implausible_but_real_value(client, db_session):
    """#5: sanity caps are WIDER than the anomaly engine's plausible ranges.
    A high-but-real reading (e.g. TSS 1500, above the 2000 plausible ceiling's
    normal band) must still be STORED so the anomaly engine can flag it — the
    ingest guard only discards physically-impossible garbage."""
    await _make_site(db_session, "TST-IMPL")
    now = int(time.time())
    readings = [{"datetime": now, "tss": 1500, "cod": 2500}]
    res = await client.post("/api/post-data", json={"token": _token("TST-IMPL", readings)})
    assert res.status_code == 200
    assert res.json()["dropped"] == 0
    row = (await db_session.execute(select(SensorData))).scalars().first()
    assert row.tss == 1500 and row.cod == 2500


@pytest.mark.anyio
async def test_post_data_duplicate_burst_is_idempotent(client, db_session):
    """#1: re-sending the same burst must not create duplicate (site_id, ts) rows.
    The first write wins; the retry is silently dropped at the DB."""
    await _make_site(db_session, "TST-DUP")
    now = int(time.time())
    readings = [
        {"datetime": now, "ph": 7.1, "tss": 20},
        {"datetime": now + 120, "ph": 7.2, "tss": 22},
    ]
    tok = _token("TST-DUP", readings)
    first = await client.post("/api/post-data", json={"token": tok})
    second = await client.post("/api/post-data", json={"token": tok})  # exact retry
    assert first.status_code == 200 and second.status_code == 200
    count = (await db_session.execute(select(func.count(SensorData.id)))).scalar_one()
    assert count == 2   # not 4 — duplicates dropped


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


@pytest.mark.anyio
async def test_calibration_sentinel_stored_as_op_status(client, db_session):
    """All water params carrying the same negative sentinel = an operational-status
    row, not readings: params NULL, op_status recorded."""
    await _make_site(db_session, "TST-CAL")
    token = _token("TST-CAL", [{
        "datetime": 1753000000,
        "pH": -2, "tss": -2, "debit": -2, "cod": -2, "nh3n": -2,
    }])
    res = await client.post("/api/post-data", json={"token": token})
    assert res.status_code == 200
    row = (await db_session.execute(select(SensorData))).scalars().first()
    assert row.op_status == -2
    assert row.ph is None and row.tss is None and row.cod is None
    assert row.nh3n is None      # the one that used to slip through unbounded
    assert row.debit is None


@pytest.mark.anyio
async def test_partial_negative_is_not_a_sentinel_row(client, db_session):
    """Only some params negative => ordinary impossible-value handling, no op_status."""
    await _make_site(db_session, "TST-P")
    token = _token("TST-P", [{
        "datetime": 1753000100,
        "pH": 7.1, "tss": 20.0, "debit": 5.0, "cod": 30.0, "nh3n": -2,
    }])
    res = await client.post("/api/post-data", json={"token": token})
    assert res.status_code == 200
    row = (await db_session.execute(select(SensorData))).scalars().first()
    assert row.op_status is None
    assert row.ph == 7.1
    assert row.nh3n is None      # dropped as impossible, not treated as sentinel
