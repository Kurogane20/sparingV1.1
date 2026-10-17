"""Offline-device alerts: one open alert per offline site, closed automatically
when the site delivers data again."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.models import Alert, SensorData, Site
from app.utils.alert_engine import check_offline_devices


def _now():
    return datetime.now(timezone.utc)


async def _site_with_last_reading(db_session, uid, last_reading_age):
    site = Site(uid=uid, name=uid, company_name="C", is_active=True)
    db_session.add(site)
    await db_session.flush()
    ts = (_now() - last_reading_age).replace(tzinfo=None)
    db_session.add(SensorData(site_id=site.id, ts=ts, ph=7.0))
    await db_session.commit()
    return site


def _offline_alert(site_id, age, status="active"):
    return Alert(site_id=site_id, field="device_offline", value=0.0, threshold_type="danger",
                 status=status, triggered_at=_now() - age)


async def _alerts(db_session, site_id):
    return (await db_session.execute(
        select(Alert).where(Alert.site_id == site_id).order_by(Alert.triggered_at)
        .execution_options(populate_existing=True)
    )).scalars().all()


@pytest.mark.anyio
async def test_offline_site_without_alert_gets_one(db_session):
    site = await _site_with_last_reading(db_session, "OFF-NEW", timedelta(hours=6))

    await check_offline_devices(db_session)

    assert [a.status for a in await _alerts(db_session, site.id)] == ["active"]


@pytest.mark.anyio
async def test_offline_site_with_old_open_alert_gets_no_new_one(db_session):
    site = await _site_with_last_reading(db_session, "OFF-OLD", timedelta(days=3))
    db_session.add(_offline_alert(site.id, timedelta(days=2)))
    await db_session.commit()

    await check_offline_devices(db_session)

    assert len(await _alerts(db_session, site.id)) == 1


@pytest.mark.anyio
async def test_duplicate_offline_alerts_collapse_to_oldest(db_session):
    site = await _site_with_last_reading(db_session, "OFF-DUP", timedelta(days=3))
    for hours in (48, 24, 2):
        db_session.add(_offline_alert(site.id, timedelta(hours=hours)))
    await db_session.commit()

    await check_offline_devices(db_session)

    alerts = await _alerts(db_session, site.id)
    assert [a.status for a in alerts] == ["active", "resolved", "resolved"]
    assert alerts[1].resolved_at is not None


@pytest.mark.anyio
async def test_site_back_online_resolves_offline_alerts(db_session):
    site = await _site_with_last_reading(db_session, "OFF-BACK", timedelta(minutes=10))
    db_session.add(_offline_alert(site.id, timedelta(hours=5)))
    db_session.add(_offline_alert(site.id, timedelta(hours=3), status="acknowledged"))
    await db_session.commit()

    await check_offline_devices(db_session)

    alerts = await _alerts(db_session, site.id)
    assert [a.status for a in alerts] == ["resolved", "resolved"]
    assert all("kembali" in a.followup_note for a in alerts)
