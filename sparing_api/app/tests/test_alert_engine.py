from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from unittest.mock import MagicMock
from app.models.models import Alert, AlertRule, Site
from app.utils.alert_engine import _is_violated, _determine_threshold_type, trigger_alerts
from app.utils.time import as_utc

def test_is_violated_upper_limit():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _is_violated(120.0, rule, "warning") is False
    assert _is_violated(160.0, rule, "warning") is True
    assert _is_violated(210.0, rule, "danger") is True

def test_is_violated_range():
    rule = MagicMock(warning_min=6.5, warning_max=8.5, danger_min=6.0, danger_max=9.0)
    assert _is_violated(7.2, rule, "warning") is False   # within range
    assert _is_violated(6.2, rule, "warning") is True    # below min
    assert _is_violated(9.1, rule, "danger") is True     # above max
    assert _is_violated(6.05, rule, "danger") is False   # within danger range

def test_determine_threshold_type_danger():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _determine_threshold_type(210.0, rule) == "danger"

def test_determine_threshold_type_warning():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _determine_threshold_type(160.0, rule) == "warning"

def test_determine_threshold_type_normal():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _determine_threshold_type(100.0, rule) is None

def test_is_violated_none_thresholds():
    rule = MagicMock(warning_min=None, warning_max=None, danger_min=None, danger_max=None)
    assert _is_violated(999.0, rule, "warning") is False
    assert _is_violated(0.0, rule, "danger") is False

def test_is_violated_lower_limit_only():
    rule = MagicMock(warning_min=6.5, warning_max=None, danger_min=6.0, danger_max=None)
    assert _is_violated(7.0, rule, "warning") is False   # above min: OK
    assert _is_violated(6.2, rule, "warning") is True    # below min: violated
    assert _is_violated(5.9, rule, "danger") is True     # below danger min: violated


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("measurement_ts", "expected"),
    [
        (
            datetime(2026, 8, 1, 9, 30),
            datetime(2026, 8, 1, 9, 30, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 8, 1, 16, 30, tzinfo=timezone(timedelta(hours=7))),
            datetime(2026, 8, 1, 9, 30, tzinfo=timezone.utc),
        ),
    ],
)
async def test_compliance_alert_uses_normalized_measurement_timestamp(
    db_session, monkeypatch, measurement_ts, expected
):
    """A new alert is charted at the sample instant, never task wall-clock time."""
    site = Site(uid="ALERT-TS", name="Test", company_name="C", is_active=True)
    db_session.add(site)
    await db_session.flush()
    db_session.add(AlertRule(
        site_id=site.id, field="tss", warning_max=150, danger_max=200, is_active=True,
    ))
    await db_session.commit()

    @asynccontextmanager
    async def _test_session():
        yield db_session

    monkeypatch.setattr("app.core.db.SessionLocal", _test_session)

    await trigger_alerts(
        site_id=site.id,
        site_uid=site.uid,
        device_uid="DEV-1",
        data={"tss": 250},
        measurement_ts=measurement_ts,
    )

    alert = (await db_session.execute(select(Alert))).scalar_one()
    assert as_utc(alert.triggered_at) == expected


@pytest.mark.anyio
async def test_compliance_severity_transition_uses_measurement_timestamp(
    db_session, monkeypatch
):
    site = Site(uid="ALERT-TRANSITION", name="Test", company_name="C", is_active=True)
    db_session.add(site)
    await db_session.flush()
    db_session.add_all([
        AlertRule(site_id=site.id, field="tss", warning_max=150, danger_max=200, is_active=True),
        Alert(
            site_id=site.id, field="tss", value=160, threshold_type="warning",
            status="active", category="compliance",
            triggered_at=datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc),
        ),
    ])
    await db_session.commit()

    @asynccontextmanager
    async def _test_session():
        yield db_session

    monkeypatch.setattr("app.core.db.SessionLocal", _test_session)
    measurement_ts = datetime(2026, 8, 1, 16, 30, tzinfo=timezone(timedelta(hours=7)))

    await trigger_alerts(
        site_id=site.id,
        site_uid=site.uid,
        device_uid="DEV-1",
        data={"tss": 250},
        measurement_ts=measurement_ts,
    )

    alert = (await db_session.execute(select(Alert))).scalar_one()
    assert alert.threshold_type == "danger"
    assert as_utc(alert.triggered_at) == datetime(2026, 8, 1, 9, 30, tzinfo=timezone.utc)


# ── Backfilled (late) readings ─────────────────────────────────────────
# Alert state follows the site's newest data. A logger resending its backlog
# must not auto-resolve a current alert with an old in-range value, nor open
# an alert (and e-mail) for an old breach — FSK-LOG lost alerts open since
# June this way on 2026-10-18.

async def _site_with_rule_and_newer_data(db_session, uid):
    from app.models.models import SensorData
    site = Site(uid=uid, name="Test", company_name="C", is_active=True)
    db_session.add(site)
    await db_session.flush()
    db_session.add_all([
        AlertRule(site_id=site.id, field="tss", warning_max=150, danger_max=200, is_active=True),
        SensorData(site_id=site.id, ts=datetime(2026, 10, 18, 4, 0), tss=250),
    ])
    await db_session.commit()
    return site


def _patch_session(monkeypatch, db_session):
    @asynccontextmanager
    async def _test_session():
        yield db_session

    monkeypatch.setattr("app.core.db.SessionLocal", _test_session)


@pytest.mark.anyio
async def test_backfilled_reading_does_not_resolve_current_alert(db_session, monkeypatch):
    site = await _site_with_rule_and_newer_data(db_session, "ALERT-BACKFILL-RESOLVE")
    db_session.add(Alert(
        site_id=site.id, field="tss", value=250, threshold_type="danger",
        status="active", category="compliance",
        triggered_at=datetime(2026, 6, 22, 11, 30, tzinfo=timezone.utc),
    ))
    await db_session.commit()
    _patch_session(monkeypatch, db_session)

    await trigger_alerts(
        site_id=site.id, site_uid=site.uid, device_uid="DEV-1",
        data={"tss": 20}, measurement_ts=datetime(2026, 9, 13, 3, 0, tzinfo=timezone.utc),
    )

    alert = (await db_session.execute(
        select(Alert).execution_options(populate_existing=True)
    )).scalar_one()
    assert alert.status == "active"


@pytest.mark.anyio
async def test_backfilled_breach_does_not_open_alert(db_session, monkeypatch):
    site = await _site_with_rule_and_newer_data(db_session, "ALERT-BACKFILL-OPEN")
    _patch_session(monkeypatch, db_session)

    await trigger_alerts(
        site_id=site.id, site_uid=site.uid, device_uid="DEV-1",
        data={"tss": 250}, measurement_ts=datetime(2026, 9, 13, 3, 0, tzinfo=timezone.utc),
    )

    assert (await db_session.execute(select(Alert))).scalars().all() == []
