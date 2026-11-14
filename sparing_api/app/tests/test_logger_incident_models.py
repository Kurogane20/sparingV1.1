from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.models import DeviceRejection, LoggerIncident, LoggerStatus, Site


async def _site(db, uid="S-1"):
    s = Site(uid=uid, name=uid, company_name="C", is_active=True)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest.mark.anyio
async def test_open_key_allows_one_open_incident_per_site_and_kind(db_session):
    site = await _site(db_session)
    now = datetime.now(timezone.utc)
    db_session.add(LoggerIncident(site_id=site.id, kind="down", started_at=now, open_key=f"{site.id}:down"))
    await db_session.commit()
    db_session.add(LoggerIncident(site_id=site.id, kind="down", started_at=now, open_key=f"{site.id}:down"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.anyio
async def test_closed_incidents_never_collide(db_session):
    site = await _site(db_session)
    now = datetime.now(timezone.utc)
    for _ in range(2):
        db_session.add(LoggerIncident(site_id=site.id, kind="down", started_at=now, ended_at=now, open_key=None))
    await db_session.commit()
    assert len((await db_session.execute(select(LoggerIncident))).scalars().all()) == 2


@pytest.mark.anyio
async def test_rejection_is_unique_per_uid_source_reason(db_session):
    now = datetime.now(timezone.utc)
    for _ in range(2):
        db_session.add(DeviceRejection(uid="X-LOG", source="post-data", reason="bad_signature",
                                       first_at=now, last_at=now, count=1))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.anyio
async def test_logger_status_keeps_send_failure_clocks(db_session):
    site = await _site(db_session)
    now = datetime.now(timezone.utc)
    db_session.add(LoggerStatus(site_id=site.id, state="alive", mm_fail_since=now, klhk_fail_since=None))
    await db_session.commit()
    st = (await db_session.execute(select(LoggerStatus))).scalars().one()
    assert st.mm_fail_since is not None and st.klhk_fail_since is None
