from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select

from app.models.models import Site, LoggerStatus, Alert
from app.utils.logger_monitor import scan_logger_liveness, resolve_logger_down_alert


async def _site_with_status(db, uid, minutes_ago, state="alive"):
    s = Site(uid=uid, name=uid, company_name="C", is_active=True)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    st = LoggerStatus(
        site_id=s.id, state=state,
        last_heartbeat_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        state_since=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    db.add(st)
    await db.commit()
    return s


@pytest.mark.anyio
async def test_silent_logger_marked_down_and_alerted(db_session):
    site = await _site_with_status(db_session, "L-DOWN", minutes_ago=15)
    await scan_logger_liveness(db_session)

    st = (await db_session.execute(select(LoggerStatus))).scalars().first()
    assert st.state == "down"
    alerts = (await db_session.execute(select(Alert))).scalars().all()
    assert len(alerts) == 1
    a = alerts[0]
    assert a.category == "logger" and a.field == "logger_down"
    assert a.threshold_type == "danger" and a.status == "active"
    assert a.site_id == site.id


@pytest.mark.anyio
async def test_recent_heartbeat_not_alerted(db_session):
    await _site_with_status(db_session, "L-OK", minutes_ago=3)
    await scan_logger_liveness(db_session)
    st = (await db_session.execute(select(LoggerStatus))).scalars().first()
    assert st.state == "alive"
    assert (await db_session.execute(select(Alert))).scalars().first() is None


@pytest.mark.anyio
async def test_scan_is_idempotent_across_concurrent_workers(db_session):
    """Two gunicorn workers run the scheduler; a second pass must not duplicate."""
    await _site_with_status(db_session, "L-DUP", minutes_ago=20)
    await scan_logger_liveness(db_session)
    await scan_logger_liveness(db_session)
    alerts = (await db_session.execute(select(Alert))).scalars().all()
    assert len(alerts) == 1


@pytest.mark.anyio
async def test_recovery_resolves_with_system_note(db_session):
    site = await _site_with_status(db_session, "L-BACK", minutes_ago=20)
    await scan_logger_liveness(db_session)
    now = datetime.now(timezone.utc)
    await resolve_logger_down_alert(db_session, site.id, now)

    a = (await db_session.execute(select(Alert))).scalars().first()
    assert a.status == "resolved"
    assert a.resolved_at is not None
    assert a.followup_note   # system note, so the mandatory-note rule isn't tripped


@pytest.mark.anyio
async def test_inactive_site_is_not_scanned(db_session):
    """A decommissioned site must not raise logger alarms forever."""
    s = Site(uid="L-OFF", name="off", company_name="C", is_active=False)
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    db_session.add(LoggerStatus(
        site_id=s.id, state="alive",
        last_heartbeat_at=datetime.now(timezone.utc) - timedelta(hours=5),
    ))
    await db_session.commit()

    await scan_logger_liveness(db_session)
    assert (await db_session.execute(select(Alert))).scalars().first() is None


@pytest.mark.anyio
async def test_never_seen_logger_is_marked_down(db_session):
    """A site whose logger has never checked in at all counts as down."""
    s = Site(uid="L-NEVER", name="never", company_name="C", is_active=True)
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    db_session.add(LoggerStatus(site_id=s.id, state="alive", last_heartbeat_at=None))
    await db_session.commit()

    await scan_logger_liveness(db_session)
    st = (await db_session.execute(select(LoggerStatus))).scalars().first()
    assert st.state == "down"
    assert (await db_session.execute(select(Alert))).scalars().first() is not None


@pytest.mark.anyio
async def test_persistent_sensor_failure_raises_warning(db_session):
    site = await _site_with_status(db_session, "L-SENS", minutes_ago=1)
    st = (await db_session.execute(select(LoggerStatus))).scalars().first()
    st.tss_ok = False
    st.sensor_fail_since = datetime.now(timezone.utc) - timedelta(minutes=20)
    await db_session.commit()

    await scan_logger_liveness(db_session)
    alerts = (await db_session.execute(select(Alert))).scalars().all()
    sensor_alerts = [a for a in alerts if a.field == "sensor_tss"]
    assert len(sensor_alerts) == 1
    assert sensor_alerts[0].threshold_type == "warning"
    assert sensor_alerts[0].category == "logger"


@pytest.mark.anyio
async def test_brief_sensor_failure_not_alerted(db_session):
    await _site_with_status(db_session, "L-BRIEF", minutes_ago=1)
    st = (await db_session.execute(select(LoggerStatus))).scalars().first()
    st.tss_ok = False
    st.sensor_fail_since = datetime.now(timezone.utc) - timedelta(minutes=3)
    await db_session.commit()

    await scan_logger_liveness(db_session)
    alerts = (await db_session.execute(select(Alert))).scalars().all()
    assert not [a for a in alerts if a.field.startswith("sensor_")]


@pytest.mark.anyio
async def test_sensor_alert_auto_resolves_on_recovery(db_session):
    """A recovered sensor must not leave a warning hanging forever."""
    from app.utils.logger_monitor import resolve_sensor_alerts

    site = await _site_with_status(db_session, "L-REC", minutes_ago=1)
    st = (await db_session.execute(select(LoggerStatus))).scalars().first()
    st.tss_ok = False
    st.sensor_fail_since = datetime.now(timezone.utc) - timedelta(minutes=20)
    await db_session.commit()
    await scan_logger_liveness(db_session)
    assert (await db_session.execute(select(Alert))).scalars().first().status == "active"

    await resolve_sensor_alerts(db_session, site.id, datetime.now(timezone.utc))
    a = (await db_session.execute(select(Alert))).scalars().first()
    assert a.status == "resolved"
    assert a.resolved_at is not None
    assert a.followup_note   # system note keeps the mandatory-note rule satisfied


@pytest.mark.anyio
async def test_heartbeat_recovery_resolves_sensor_alert_end_to_end(client, db_session):
    """Full path: sensor fails, warning fires, a healthy heartbeat clears it."""
    import jwt
    from app.models.models import Site

    s = Site(uid="L-E2E", name="e2e", company_name="C", is_active=True, device_secret="sec")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)

    bad = {"tss_ok": False, "ph_ok": True}
    tok = lambda st: jwt.encode({"uid": "L-E2E", "status": st}, "sec", algorithm="HS256")
    await client.post("/logger/heartbeat", json={"token": tok(bad)})

    # backdate the failure so the scan considers it persistent, then raise the alarm
    row = (await db_session.execute(select(LoggerStatus))).scalars().first()
    row.sensor_fail_since = datetime.now(timezone.utc) - timedelta(minutes=20)
    await db_session.commit()
    await scan_logger_liveness(db_session)
    assert (await db_session.execute(select(Alert))).scalars().first().status == "active"

    # sensor reads fine again → heartbeat must auto-resolve the warning
    await client.post("/logger/heartbeat", json={"token": tok({"tss_ok": True, "ph_ok": True})})
    a = (await db_session.execute(select(Alert))).scalars().first()
    assert a.status == "resolved"
