from datetime import datetime, timedelta, timezone

import pytest

from app.models.models import SensorData, Site
from app.utils.data_recency import has_newer_data


@pytest.mark.anyio
async def test_has_newer_data(db_session):
    site = Site(uid="RECENCY", name="Test", company_name="C", is_active=True)
    db_session.add(site)
    await db_session.flush()
    now = datetime.now(timezone.utc)
    reading_ts = now - timedelta(minutes=10)
    db_session.add(SensorData(site_id=site.id, ts=reading_ts.replace(tzinfo=None), ph=7.0))
    await db_session.commit()

    assert await has_newer_data(db_session, site.id, now - timedelta(hours=1)) is True
    assert await has_newer_data(db_session, site.id, reading_ts) is False
    assert await has_newer_data(db_session, site.id, now) is False


@pytest.mark.anyio
async def test_far_future_row_does_not_make_live_data_stale(db_session):
    # One reading from a device with a wrong clock must not mark every later
    # burst as late (which would silence alerts for that site for good)
    site = Site(uid="RECENCY-FUTURE", name="Test", company_name="C", is_active=True)
    db_session.add(site)
    await db_session.flush()
    now = datetime.now(timezone.utc)
    db_session.add(SensorData(site_id=site.id, ts=(now + timedelta(days=2)).replace(tzinfo=None), ph=7.0))
    await db_session.commit()

    assert await has_newer_data(db_session, site.id, now) is False
