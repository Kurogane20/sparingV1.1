from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.models import AlertRule, OperationalRule, Site, SiteMonitoringConfig, User
from app.schemas.alert import AlertRuleCreate, AlertRuleOut, AlertRuleUpdate


@pytest.mark.anyio
async def test_monitoring_models_round_trip_and_enforce_site_scoped_keys(db_session):
    """Persist monitoring settings without converting meaningful zeros to nulls."""
    user = User(
        name="Operator",
        email="monitor@example.com",
        password_hash="hash",
        role="operator",
        is_active=True,
    )
    site = Site(uid="MON-1", name="Monitor", company_name="PT Test")
    db_session.add_all([user, site])
    await db_session.flush()
    site_id = site.id
    user_id = user.id

    db_session.add(
        SiteMonitoringConfig(
            site_id=site_id,
            cadence_seconds=120,
            stale_after_seconds=5400,
            max_chart_points=720,
            max_range_days=31,
            updated_by_user_id=user_id,
        )
    )
    db_session.add(
        OperationalRule(
            site_id=site_id,
            field="ph",
            rule_type="rapid_change",
            is_active=True,
            window_seconds=600,
            min_points=4,
            hold_seconds=0,
            cooldown_seconds=0,
            abs_delta=0.0,
            percent_delta=0.0,
            minimum_baseline=0.0,
            trigger_mode="any",
            no_flow_threshold=0.0,
            low_flow_threshold=0.0,
            recovery_threshold=0.0,
            updated_by_user_id=user_id,
        )
    )
    db_session.add(
        AlertRule(
            site_id=site_id,
            field="tss",
            warning_max=150.0,
            danger_max=200.0,
            reference_label="Baku Mutu",
            regulation=None,
            is_active=True,
            updated_by_user_id=user_id,
        )
    )
    await db_session.commit()

    config = (await db_session.execute(select(SiteMonitoringConfig))).scalar_one()
    rule = (await db_session.execute(select(OperationalRule))).scalar_one()
    alert_rule = (await db_session.execute(select(AlertRule))).scalar_one()

    assert config.cadence_seconds == 120
    assert config.updated_by_user_id == user_id
    assert rule.hold_seconds == 0
    assert rule.cooldown_seconds == 0
    assert rule.abs_delta == 0.0
    assert rule.percent_delta == 0.0
    assert rule.minimum_baseline == 0.0
    assert rule.no_flow_threshold == 0.0
    assert rule.low_flow_threshold == 0.0
    assert rule.recovery_threshold == 0.0
    assert alert_rule.reference_label == "Baku Mutu"
    assert alert_rule.regulation is None
    assert alert_rule.updated_by_user_id == user_id

    db_session.add(
        SiteMonitoringConfig(
            site_id=site_id,
            cadence_seconds=60,
            stale_after_seconds=300,
            max_chart_points=100,
            max_range_days=1,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    db_session.add(
        OperationalRule(site_id=site_id, field="ph", rule_type="rapid_change")
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


def test_alert_rule_schemas_include_optional_reference_and_audit_fields():
    created = AlertRuleCreate(
        field="tss", reference_label="Baku Mutu", regulation="PP 22/2021"
    )
    updated = AlertRuleUpdate(reference_label=None, regulation="Revised regulation")
    changed_at = datetime(2026, 8, 25, tzinfo=timezone.utc)
    output = AlertRuleOut(
        id=1,
        site_id=2,
        field="tss",
        warning_min=None,
        warning_max=150.0,
        danger_min=None,
        danger_max=200.0,
        is_active=True,
        reference_label="Baku Mutu",
        regulation="PP 22/2021",
        updated_at=changed_at,
        updated_by_user_id=3,
    )

    assert created.reference_label == "Baku Mutu"
    assert updated.regulation == "Revised regulation"
    assert output.updated_at == changed_at
    assert output.updated_by_user_id == 3


@pytest.mark.anyio
async def test_alert_rule_endpoint_persists_reference_and_audit_fields(client, db_session):
    operator = User(
        name="Operator",
        email="rule-operator@example.com",
        password_hash=hash_password("Secret123"),
        role="operator",
        is_active=True,
    )
    site = Site(uid="MON-API", name="Monitor API", company_name="PT Test")
    db_session.add_all([operator, site])
    await db_session.commit()

    login = await client.post(
        "/auth/login", json={"email": operator.email, "password": "Secret123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = await client.post(
        "/alert-rules",
        params={"site_uid": site.uid},
        json={
            "field": "tss",
            "warning_max": 150.0,
            "danger_max": 200.0,
            "reference_label": "Baku Mutu",
            "regulation": "PP 22/2021",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["reference_label"] == "Baku Mutu"
    assert response.json()["regulation"] == "PP 22/2021"
    assert response.json()["updated_by_user_id"] == operator.id
