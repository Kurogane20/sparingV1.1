import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.models import OperationalRule, SiteMonitoringConfig, User, ViewerSite


async def _auth_headers(client, db, *, role: str, email: str):
    user = User(
        name=role.title(),
        email=email,
        password_hash=hash_password("Secret123"),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    response = await client.post(
        "/auth/login", json={"email": email, "password": "Secret123"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, user


async def _create_site(client, headers, uid: str):
    response = await client.post(
        "/sites",
        headers=headers,
        json={"uid": uid, "name": "Monitoring Site", "company_name": "PT Test"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def _flow_rule(**overrides):
    rule = {
        "field": "debit",
        "rule_type": "flow_state",
        "is_active": True,
        "hold_seconds": 240,
        "cooldown_seconds": 300,
        "no_flow_threshold": 0.0,
        "low_flow_threshold": 1.0,
        "recovery_threshold": 1.5,
    }
    rule.update(overrides)
    return rule


def _config_payload(**overrides):
    payload = {
        "cadence_seconds": 120,
        "stale_after_seconds": 5400,
        "max_chart_points": 720,
        "max_range_days": 31,
        "rules": [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.anyio
async def test_creating_site_provisions_monitoring_defaults_in_same_result(client, db_session):
    headers, _ = await _auth_headers(
        client, db_session, role="operator", email="create-config@example.com"
    )

    site_id = await _create_site(client, headers, "CONFIG-CREATE")
    config = (
        await db_session.execute(
            select(SiteMonitoringConfig).where(SiteMonitoringConfig.site_id == site_id)
        )
    ).scalar_one()

    assert (config.cadence_seconds, config.stale_after_seconds) == (120, 5400)
    assert (config.max_chart_points, config.max_range_days) == (720, 31)
    rules = (
        await db_session.execute(
            select(OperationalRule).where(OperationalRule.site_id == site_id)
        )
    ).scalars().all()
    assert rules == []


@pytest.mark.anyio
async def test_assigned_viewer_gets_their_sites_monitoring_config(client, db_session):
    operator_headers, _ = await _auth_headers(
        client, db_session, role="operator", email="assigned-owner@example.com"
    )
    site_id = await _create_site(client, operator_headers, "CONFIG-ASSIGNED")
    viewer_headers, viewer = await _auth_headers(
        client, db_session, role="viewer", email="assigned-viewer@example.com"
    )
    db_session.add(ViewerSite(user_id=viewer.id, site_id=site_id))
    await db_session.commit()
    # A viewer token carries its allowed UID list, so log in after assignment.
    login = await client.post(
        "/auth/login", json={"email": viewer.email, "password": "Secret123"}
    )
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.get(
        "/sites/CONFIG-ASSIGNED/monitoring-config", headers=viewer_headers
    )

    assert response.status_code == 200
    assert response.json()["cadence_seconds"] == 120
    assert response.json()["rules"] == []


@pytest.mark.anyio
async def test_unassigned_viewer_cannot_get_monitoring_config(client, db_session):
    operator_headers, _ = await _auth_headers(
        client, db_session, role="operator", email="forbidden-owner@example.com"
    )
    await _create_site(client, operator_headers, "CONFIG-FORBIDDEN")
    viewer_headers, _ = await _auth_headers(
        client, db_session, role="viewer", email="forbidden-viewer@example.com"
    )

    response = await client.get(
        "/sites/CONFIG-FORBIDDEN/monitoring-config", headers=viewer_headers
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_operator_updates_flow_rule_with_zero_no_flow_threshold(client, db_session):
    headers, operator = await _auth_headers(
        client, db_session, role="operator", email="flow-config@example.com"
    )
    site_id = await _create_site(client, headers, "FLOW-CONFIG")

    response = await client.put(
        "/sites/FLOW-CONFIG/monitoring-config",
        headers=headers,
        json=_config_payload(rules=[_flow_rule()]),
    )

    assert response.status_code == 200
    assert response.json()["rules"][0]["no_flow_threshold"] == 0.0
    config = (
        await db_session.execute(
            select(SiteMonitoringConfig).where(SiteMonitoringConfig.site_id == site_id)
        )
    ).scalar_one()
    rule = (
        await db_session.execute(
            select(OperationalRule).where(OperationalRule.site_id == site_id)
        )
    ).scalar_one()
    assert config.updated_by_user_id == operator.id
    assert rule.updated_by_user_id == operator.id
    assert rule.no_flow_threshold == 0.0


@pytest.mark.anyio
async def test_invalid_flow_threshold_order_is_rejected(client, db_session):
    headers, _ = await _auth_headers(
        client, db_session, role="operator", email="invalid-flow@example.com"
    )
    await _create_site(client, headers, "FLOW-INVALID")

    response = await client.put(
        "/sites/FLOW-INVALID/monitoring-config",
        headers=headers,
        json=_config_payload(rules=[_flow_rule(no_flow_threshold=1.1, low_flow_threshold=1.0)]),
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_duplicate_rule_type_for_one_field_is_rejected(client, db_session):
    headers, _ = await _auth_headers(
        client, db_session, role="operator", email="duplicate-flow@example.com"
    )
    await _create_site(client, headers, "FLOW-DUPLICATE")

    response = await client.put(
        "/sites/FLOW-DUPLICATE/monitoring-config",
        headers=headers,
        json=_config_payload(rules=[_flow_rule(), _flow_rule()]),
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_low_flow_tss_round_trip_references_detectors_without_dead_thresholds(
    client, db_session
):
    headers, _ = await _auth_headers(
        client, db_session, role="operator", email="compound-config@example.com"
    )
    site_id = await _create_site(client, headers, "COMPOUND-CONFIG")
    compound = {
        "field": "debit",
        "secondary_field": "tss",
        "rule_type": "low_flow_tss",
        "is_active": True,
        "hold_seconds": 0,
        "cooldown_seconds": 300,
    }

    updated = await client.put(
        "/sites/COMPOUND-CONFIG/monitoring-config",
        headers=headers,
        json=_config_payload(rules=[compound]),
    )
    fetched = await client.get(
        "/sites/COMPOUND-CONFIG/monitoring-config", headers=headers
    )

    assert updated.status_code == 200
    assert fetched.status_code == 200
    updated_rule = updated.json()["rules"][0]
    fetched_rule = fetched.json()["rules"][0]
    assert updated_rule == fetched_rule
    assert updated_rule["field"] == "debit"
    assert updated_rule["secondary_field"] == "tss"
    assert updated_rule["rule_type"] == "low_flow_tss"
    assert updated_rule["hold_seconds"] == 0
    assert updated_rule["cooldown_seconds"] == 300
    assert "low_flow_threshold" not in updated_rule
    assert "recovery_threshold" not in updated_rule
    persisted = (
        await db_session.execute(
            select(OperationalRule).where(OperationalRule.site_id == site_id)
        )
    ).scalar_one()
    assert persisted.field == "debit"
    assert persisted.secondary_field == "tss"
    assert persisted.low_flow_threshold is None
    assert persisted.recovery_threshold is None
