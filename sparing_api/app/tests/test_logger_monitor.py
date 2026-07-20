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
