"""Per-field quality flags: a stuck/implausible sensor must only invalidate its
own parameter, never the other readings delivered in the same row."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.models import SensorData, Site
from app.utils.anomaly_engine import _mark_sensor_quality, detect_realtime
from app.utils.quality import field_is_flagged, field_quality_ok, parse_quality_fields

BASE = datetime(2026, 8, 1, tzinfo=timezone.utc)


def _use_test_session(monkeypatch, db_session):
    class ExistingSessionContext:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr("app.core.db.SessionLocal", lambda: ExistingSessionContext())


async def _site(db_session, uid):
    site = Site(uid=uid, name=uid, company_name="C", is_active=True)
    db_session.add(site)
    await db_session.flush()
    return site


def test_parse_quality_fields():
    assert parse_quality_fields(None) is None
    assert parse_quality_fields(",cod,tss,") == frozenset({"cod", "tss"})
    assert parse_quality_fields(",") == frozenset()


def test_field_is_flagged_per_field_and_legacy():
    assert field_is_flagged("sensor_error", ",cod,", "cod") is True
    assert field_is_flagged("sensor_error", ",cod,", "ph") is False
    # Legacy rows carry no field list: the whole row stays flagged.
    assert field_is_flagged("sensor_error", None, "ph") is True
    assert field_is_flagged(None, None, "ph") is False


@pytest.mark.anyio
async def test_flatline_flags_only_the_stuck_field(db_session, monkeypatch):
    _use_test_session(monkeypatch, db_session)
    site = await _site(db_session, "QF-FLATLINE")
    readings = []
    for index in range(30):
        ts = BASE + timedelta(minutes=2 * index)
        reading = {"ts": ts, "ph": 7.0 + (index % 3) * 0.1, "cod": 55.0}
        readings.append(reading)
        db_session.add(SensorData(site_id=site.id, ts=ts.replace(tzinfo=None),
                                  ph=reading["ph"], cod=55.0, created_at=ts.replace(tzinfo=None)))
    await db_session.commit()

    await detect_realtime(site.id, site.uid, None, readings)

    newest = (await db_session.execute(
        select(SensorData).where(SensorData.site_id == site.id)
        .order_by(SensorData.ts.desc()).limit(1)
    )).scalar_one()
    assert newest.quality_flag == "sensor_error"
    assert newest.quality_fields == ",cod,"


@pytest.mark.anyio
async def test_mark_quality_appends_fields_without_duplicates(db_session):
    site = await _site(db_session, "QF-APPEND")
    ts = BASE
    db_session.add(SensorData(site_id=site.id, ts=ts.replace(tzinfo=None), ph=7.0,
                              cod=1.0, tss=2.0, created_at=ts.replace(tzinfo=None)))
    await db_session.commit()

    await _mark_sensor_quality(db_session, site.id, ts, "sensor_error", "cod")
    await _mark_sensor_quality(db_session, site.id, ts, "sensor_error", "tss")
    await _mark_sensor_quality(db_session, site.id, ts, "sensor_error", "cod")
    # A lower-severity flag for another field adds the field but keeps the row severity.
    await _mark_sensor_quality(db_session, site.id, ts, "anomaly", "ph")
    await db_session.commit()

    row = (await db_session.execute(
        select(SensorData).where(SensorData.site_id == site.id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert row.quality_flag == "sensor_error"
    assert row.quality_fields == ",cod,tss,ph,"


@pytest.mark.anyio
async def test_field_quality_ok_filters_per_field(db_session):
    site = await _site(db_session, "QF-SQL")
    rows = {
        "clean": (None, None),
        "cod_only": ("sensor_error", ",cod,"),
        "ph_flagged": ("sensor_error", ",ph,"),
        "legacy": ("sensor_error", None),
    }
    for minute, (name, (flag, fields)) in enumerate(rows.items()):
        ts = (BASE + timedelta(minutes=minute)).replace(tzinfo=None)
        db_session.add(SensorData(site_id=site.id, ts=ts, ph=7.0 + minute, created_at=ts,
                                  quality_flag=flag, quality_fields=fields))
    await db_session.commit()

    kept = (await db_session.execute(
        select(SensorData.ph).where(SensorData.site_id == site.id, field_quality_ok("ph"))
        .order_by(SensorData.ts)
    )).scalars().all()
    assert kept == [7.0, 8.0]  # clean + cod_only; ph-flagged and legacy rows drop out


async def _seed_mixed_flags(db_session, uid):
    """pH 7 clean, pH 10 in a row flagged only for NH3-N, pH 11 flagged for pH."""
    site = await _site(db_session, uid)
    for minute, (ph, flag, fields) in enumerate([
        (7.0, None, None),
        (10.0, "sensor_error", ",nh3n,"),
        (11.0, "sensor_error", ",ph,"),
    ]):
        ts = (BASE + timedelta(minutes=minute)).replace(tzinfo=None)
        db_session.add(SensorData(site_id=site.id, ts=ts, ph=ph, nh3n=0.0, created_at=ts,
                                  quality_flag=flag, quality_fields=fields))
    await db_session.commit()
    return site


async def _admin_headers(client, db_session, email):
    from app.core.security import hash_password
    from app.models.models import User
    db_session.add(User(name="QF", email=email, password_hash=hash_password("Secret123"),
                        role="admin", is_active=True))
    await db_session.commit()
    login = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.anyio
async def test_compliance_counts_reading_flagged_only_for_other_field(db_session):
    from app.api.routers.stats import _compliance_window
    from app.models.models import AlertRule
    site = await _seed_mixed_flags(db_session, "QF-COMPLIANCE")
    rule = AlertRule(site_id=site.id, field="ph", danger_max=9.0, is_active=True)

    checks, violations = await _compliance_window(
        db_session, [rule], BASE.replace(tzinfo=None), (BASE + timedelta(hours=1)).replace(tzinfo=None)
    )

    assert (checks, violations) == (2, 1)


@pytest.mark.anyio
async def test_analytics_statistics_keep_reading_flagged_only_for_other_field(client, db_session):
    site = await _seed_mixed_flags(db_session, "QF-ANALYTICS")
    headers = await _admin_headers(client, db_session, "qf-analytics@example.com")

    response = await client.get("/analytics/statistics", headers=headers, params={
        "site_uid": site.uid,
        "date_from": BASE.isoformat(),
        "date_to": (BASE + timedelta(hours=1)).isoformat(),
    })

    assert response.status_code == 200
    assert response.json()["fields"]["ph"]["count"] == 2


@pytest.mark.anyio
async def test_hourly_data_keeps_reading_flagged_only_for_other_field(client, db_session):
    site = await _seed_mixed_flags(db_session, "QF-HOURLY")
    headers = await _admin_headers(client, db_session, "qf-hourly@example.com")

    response = await client.get("/data", headers=headers, params={
        "site_uid": site.uid,
        "interval": "hourly",
        "date_from": BASE.isoformat(),
        "fields": "ph",
    })

    assert response.status_code == 200
    assert response.json()["items"][0]["ph"] == 8.5  # mean of 7 and 10; flagged pH 11 excluded
