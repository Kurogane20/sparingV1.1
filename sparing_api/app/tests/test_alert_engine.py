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
