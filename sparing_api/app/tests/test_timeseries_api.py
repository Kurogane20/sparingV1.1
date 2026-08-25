from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import hash_password
from app.models.models import (
    AlertRule,
    LoggerEvent,
    OperationalRule,
    SensorData,
    SensorHealth,
    Site,
    SiteMonitoringConfig,
    User,
    ViewerSite,
)


async def _site(db, uid: str = "TS-1", *, timezone_name: str = "Asia/Jakarta") -> Site:
    site = Site(
        uid=uid,
        name="Timeseries Test",
        company_name="Test Company",
        timezone=timezone_name,
        is_active=True,
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


async def _headers(client, db, *, role: str = "operator", email: str = "ts@example.com"):
    user = User(
        name="Timeseries User",
        email=email,
        password_hash=hash_password("Secret123"),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    login = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user


@pytest.mark.anyio
async def test_timeseries_requires_authentication(client):
    response = await client.get("/analytics/timeseries", params={"site_uid": "TS-1"})
    assert response.status_code == 401


@pytest.mark.anyio
async def test_timeseries_returns_default_fields_for_operator(client, db_session):
    await _site(db_session)
    headers, _ = await _headers(client, db_session)

    response = await client.get("/analytics/timeseries", params={"site_uid": "TS-1"}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body["series"]) == {"ph", "tss", "debit"}
    assert body["meta"]["timezone"] == "Asia/Jakarta"


@pytest.mark.anyio
async def test_timeseries_default_today_ends_at_request_time(client, db_session):
    await _site(db_session, "TS-TODAY")
    headers, _ = await _headers(client, db_session, email="today@example.com")
    before = datetime.now(timezone.utc)

    response = await client.get(
        "/analytics/timeseries", params={"site_uid": "TS-TODAY"}, headers=headers
    )
    after = datetime.now(timezone.utc)

    assert response.status_code == 200
    requested_end = datetime.fromisoformat(
        response.json()["meta"]["date_to"].replace("Z", "+00:00")
    )
    assert before <= requested_end <= after


@pytest.mark.anyio
async def test_timeseries_allows_assigned_viewer_and_forbids_unassigned_viewer(client, db_session):
    assigned = await _site(db_session, "TS-ASSIGNED")
    await _site(db_session, "TS-SECRET")
    headers, viewer = await _headers(client, db_session, role="viewer", email="viewer-ts@example.com")
    db_session.add(ViewerSite(user_id=viewer.id, site_id=assigned.id))
    await db_session.commit()

    # Viewer site UIDs are encoded at login, so log in again after assignment.
    login = await client.post(
        "/auth/login", json={"email": "viewer-ts@example.com", "password": "Secret123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    allowed = await client.get(
        "/analytics/timeseries", params={"site_uid": "TS-ASSIGNED"}, headers=headers
    )
    forbidden = await client.get(
        "/analytics/timeseries", params={"site_uid": "TS-SECRET"}, headers=headers
    )

    assert allowed.status_code == 200
    assert forbidden.status_code == 403


@pytest.mark.anyio
async def test_timeseries_unassigned_viewer_cannot_read_any_site(client, db_session):
    await _site(db_session, "TS-NONE")
    headers, _ = await _headers(client, db_session, role="viewer", email="viewer-none@example.com")

    response = await client.get(
        "/analytics/timeseries", params={"site_uid": "TS-NONE"}, headers=headers
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_timeseries_unknown_site_is_not_found(client, db_session):
    headers, _ = await _headers(client, db_session)
    response = await client.get(
        "/analytics/timeseries", params={"site_uid": "TS-MISSING"}, headers=headers
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_timeseries_rejects_arbitrary_fields(client, db_session):
    await _site(db_session)
    headers, _ = await _headers(client, db_session)
    response = await client.get(
        "/analytics/timeseries",
        params={"site_uid": "TS-1", "fields": "ph,password_hash"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_fields"


@pytest.mark.anyio
async def test_timeseries_rejects_mixed_preset_and_custom_range(client, db_session):
    await _site(db_session)
    headers, _ = await _headers(client, db_session)
    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": "TS-1",
            "preset": "1h",
            "date_from": "2026-08-01T00:00:00Z",
            "date_to": "2026-08-01T01:00:00Z",
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "mixed_range_parameters"


@pytest.mark.anyio
async def test_timeseries_rejects_preset_outside_public_contract(client, db_session):
    await _site(db_session)
    headers, _ = await _headers(client, db_session, email="preset-invalid@example.com")
    response = await client.get(
        "/analytics/timeseries",
        params={"site_uid": "TS-1", "preset": "30d"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_preset"


@pytest.mark.anyio
async def test_timeseries_maps_malformed_datetime_to_syntax_error(client, db_session):
    await _site(db_session)
    headers, _ = await _headers(client, db_session, email="datetime-invalid@example.com")
    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": "TS-1",
            "date_from": "not-a-date",
            "date_to": "2026-08-01T01:00:00Z",
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_datetime"


@pytest.mark.anyio
async def test_timeseries_rejects_range_over_site_cap(client, db_session):
    site = await _site(db_session)
    db_session.add(
        SiteMonitoringConfig(
            site_id=site.id,
            cadence_seconds=120,
            stale_after_seconds=5400,
            max_chart_points=720,
            max_range_days=1,
        )
    )
    await db_session.commit()
    headers, _ = await _headers(client, db_session)
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": "TS-1",
            "date_from": start.isoformat(),
            "date_to": (start + timedelta(days=2)).isoformat(),
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "range_too_large:max_range_days=1"


@pytest.mark.anyio
@pytest.mark.parametrize("preset", ["6h", "12h"])
async def test_timeseries_supports_all_approved_rolling_presets(
    client, db_session, preset
):
    await _site(db_session)
    headers, _ = await _headers(client, db_session, email=f"{preset}@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={"site_uid": "TS-1", "preset": preset},
        headers=headers,
    )

    assert response.status_code == 200


@pytest.mark.anyio
async def test_24h_resolution_matches_cadence_without_aggregation(client, db_session):
    site = await _site(db_session, "TS-24H", timezone_name="UTC")
    db_session.add(
        SiteMonitoringConfig(
            site_id=site.id,
            cadence_seconds=120,
            stale_after_seconds=5400,
            max_chart_points=720,
            max_range_days=31,
        )
    )
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="24h@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={"site_uid": site.uid, "preset": "24h", "max_points": 720},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["meta"]["resolution_seconds"] == 120
    assert response.json()["meta"]["is_aggregated"] is False


@pytest.mark.anyio
async def test_timeseries_snapshot_uses_raw_range_before_display_aggregation(
    client, db_session
):
    site = await _site(db_session, "TS-SNAPSHOT", timezone_name="UTC")
    db_session.add(
        SiteMonitoringConfig(
            site_id=site.id,
            cadence_seconds=120,
            stale_after_seconds=5400,
            max_chart_points=3,
            max_range_days=31,
        )
    )
    db_session.add_all(
        [
            AlertRule(
                site_id=site.id,
                field="ph",
                warning_min=6.5,
                warning_max=8.5,
                danger_min=6.0,
                danger_max=10.0,
                reference_label="Permit pH limits",
                regulation="Permit 42",
                is_active=True,
            ),
            AlertRule(
                site_id=site.id,
                field="tss",
                warning_max=50.0,
                danger_max=100.0,
                reference_label="Permit TSS limits",
                regulation=None,
                is_active=True,
            ),
            OperationalRule(
                site_id=site.id,
                field="ph",
                rule_type="rapid_change",
                is_active=True,
                window_seconds=600,
                min_points=2,
                abs_delta=3.0,
                trigger_mode="any",
            ),
        ]
    )
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    readings = [
        (0, 7.0, 10.0, None),
        (2, 8.0, 11.0, None),
        (4, 12.0, 12.0, None),
        (10, 6.0, 13.0, None),
        (12, 7.0, 14.0, None),
        (14, 11.0, 15.0, "spike"),
    ]
    for minute, ph, tss, quality in readings:
        db_session.add(
            SensorData(
                site_id=site.id,
                ts=base + timedelta(minutes=minute),
                ph=ph,
                tss=tss,
                debit=0.0,
                quality_flag=quality,
            )
        )
    # Operational markers are not measurements even when they carry values.
    db_session.add(
        SensorData(
            site_id=site.id,
            ts=base + timedelta(minutes=6),
            ph=13.0,
            tss=999.0,
            debit=99.0,
            op_status=-2,
        )
    )
    # A field-specific explicit sensor error excludes only this pH measurement.
    db_session.add(
        SensorHealth(
            site_id=site.id,
            field="ph",
            status="bad",
            anomaly_type="implausible",
            updated_at=base,
        )
    )
    db_session.add(
        LoggerEvent(
            site_id=site.id,
            event_uid="logger-snapshot",
            type="sensor_fail",
            ts=base + timedelta(minutes=8),
            received_at=base + timedelta(minutes=9),
            severity="warning",
        )
    )
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="snapshot@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": site.uid,
            "date_from": base.isoformat(),
            "date_to": (base + timedelta(minutes=15)).isoformat(),
            "max_points": 20,
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {
        "site_uid": "TS-SNAPSHOT",
        "timezone": "UTC",
        "date_from": "2026-08-01T00:00:00Z",
        "date_to": "2026-08-01T00:15:00Z",
        "generated_at": body["meta"]["generated_at"],
        "rules_evaluated_at": body["meta"]["rules_evaluated_at"],
        "cadence_seconds": 120,
        "resolution_seconds": 300,
        "is_aggregated": True,
        "max_points": 3,
        "availability_pct": 62.5,
        "is_partial": True,
        "partial_reasons": ["missing_intervals"],
        "normalization_warnings": [],
    }
    assert datetime.fromisoformat(body["meta"]["generated_at"].replace("Z", "+00:00")).utcoffset() == timedelta(0)
    assert datetime.fromisoformat(body["meta"]["rules_evaluated_at"].replace("Z", "+00:00")).utcoffset() == timedelta(0)

    ph_points = body["series"]["ph"]["points"]
    assert len(ph_points) == 3
    assert ph_points[1] == {
        "ts": "2026-08-01T00:05:00Z",
        "value": None,
        "min": None,
        "max": None,
        "count": 0,
    }
    assert body["statistics"]["ph"] == {
        "current": 11.0,
        "current_ts": "2026-08-01T00:14:00Z",
        "current_quality": "check_required",
        "avg": 8.8,
        "min": 6.0,
        "max": 12.0,
        "count": 5,
        "availability_pct": 62.5,
        "status": "critical",
    }
    assert max(point["value"] for point in ph_points if point["value"] is not None) == 10.0

    debit = body["statistics"]["debit"]
    assert debit["current"] == 0.0
    assert debit["count"] == 6
    assert any(point["value"] == 0.0 for point in body["series"]["debit"]["points"])
    assert body["thresholds"]["ph"] == {
        "warning_min": 6.5,
        "warning_max": 8.5,
        "danger_min": 6.0,
        "danger_max": 10.0,
        "unit": "",
        "label": "Permit pH limits",
        "regulation": "Permit 42",
        "source": "site_alert_rule",
    }


@pytest.mark.anyio
async def test_timeseries_empty_range_is_not_partial_and_threshold_is_unconfigured(
    client, db_session
):
    site = await _site(db_session, "TS-EMPTY", timezone_name="UTC")
    headers, _ = await _headers(client, db_session, email="empty@example.com")
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": site.uid,
            "date_from": start.isoformat(),
            "date_to": (start + timedelta(hours=1)).isoformat(),
            "fields": "ph",
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["series"]["ph"]["points"] == []
    assert body["statistics"]["ph"]["status"] == "no_data"
    assert body["statistics"]["ph"]["count"] == 0
    assert body["meta"]["availability_pct"] == 0.0
    assert body["meta"]["is_partial"] is False
    assert body["meta"]["partial_reasons"] == []
    assert body["thresholds"]["ph"] == {
        "warning_min": None,
        "warning_max": None,
        "danger_min": None,
        "danger_max": None,
        "unit": "",
        "label": "pH",
        "regulation": None,
        "source": "unconfigured",
    }


@pytest.mark.anyio
async def test_timeseries_keeps_requested_future_end_but_excludes_future_availability_slots(
    client, db_session
):
    site = await _site(db_session, "TS-FUTURE", timezone_name="UTC")
    db_session.add(
        SiteMonitoringConfig(
            site_id=site.id,
            cadence_seconds=120,
            stale_after_seconds=5400,
            max_chart_points=720,
            max_range_days=31,
        )
    )
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start = now - timedelta(minutes=4)
    requested_end = now + timedelta(hours=1)
    db_session.add(SensorData(site_id=site.id, ts=start, ph=7.0))
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="future@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": site.uid,
            "date_from": start.isoformat(),
            "date_to": requested_end.isoformat(),
            "fields": "ph",
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert datetime.fromisoformat(body["meta"]["date_to"].replace("Z", "+00:00")) == requested_end
    assert body["meta"]["availability_pct"] >= 30.0


@pytest.mark.anyio
async def test_timeseries_range_is_exclusive_at_date_to(client, db_session):
    site = await _site(db_session, "TS-BOUNDARY", timezone_name="UTC")
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)
    end = start + timedelta(minutes=10)
    db_session.add_all(
        [
            SensorData(site_id=site.id, ts=start, ph=1.0),
            SensorData(site_id=site.id, ts=end - timedelta(seconds=1), ph=2.0),
            SensorData(site_id=site.id, ts=end, ph=99.0),
        ]
    )
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="boundary@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": site.uid,
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "fields": "ph",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["statistics"]["ph"]["count"] == 2
    assert response.json()["statistics"]["ph"]["max"] == 2.0


@pytest.mark.anyio
async def test_overall_availability_and_freshness_use_only_accepted_measurement_rows(
    client, db_session
):
    site = await _site(db_session, "TS-ACCEPTED", timezone_name="UTC")
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    db_session.add(
        SiteMonitoringConfig(
            site_id=site.id,
            cadence_seconds=120,
            stale_after_seconds=300,
            max_chart_points=720,
            max_range_days=31,
        )
    )
    db_session.add_all(
        [
            # Delivered zero is a real measurement row.
            SensorData(site_id=site.id, ts=base, debit=0.0),
            # Every requested field is missing or hard-invalid.
            SensorData(site_id=site.id, ts=base + timedelta(minutes=17), ph=99.0),
            SensorData(site_id=site.id, ts=base + timedelta(minutes=18), tss=float("inf")),
            # Explicit sensor error has a finite payload but is not delivered data.
            SensorData(site_id=site.id, ts=base + timedelta(minutes=19), ph=7.0),
            SensorHealth(
                site_id=site.id,
                field="ph",
                status="bad",
                anomaly_type="implausible",
                updated_at=base + timedelta(minutes=19),
            ),
        ]
    )
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="accepted@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": site.uid,
            "date_from": base.isoformat(),
            "date_to": (base + timedelta(minutes=20)).isoformat(),
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["availability_pct"] == 10.0
    assert "stale_tail" in body["meta"]["partial_reasons"]
    assert body["statistics"]["debit"]["current"] == 0.0
    assert body["statistics"]["debit"]["count"] == 1
    assert body["statistics"]["ph"]["status"] == "sensor_error"


@pytest.mark.anyio
async def test_status_priority_handles_check_required_no_flow_and_normal(
    client, db_session
):
    site = await _site(db_session, "TS-STATUS", timezone_name="UTC")
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    db_session.add_all(
        [
            AlertRule(
                site_id=site.id,
                field="ph",
                warning_min=6.0,
                warning_max=9.0,
                danger_min=5.0,
                danger_max=10.0,
                is_active=True,
            ),
            OperationalRule(
                site_id=site.id,
                field="debit",
                rule_type="flow_state",
                is_active=True,
                no_flow_threshold=0.0,
                low_flow_threshold=1.0,
                recovery_threshold=2.0,
            ),
            SensorData(
                site_id=site.id,
                ts=base,
                ph=7.0,
                tss=10.0,
                debit=0.0,
                quality_flag="spike",
            ),
            SensorData(
                site_id=site.id,
                ts=base + timedelta(minutes=1),
                tss=10.0,
            ),
        ]
    )
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="status@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": site.uid,
            "date_from": base.isoformat(),
            "date_to": (base + timedelta(minutes=2)).isoformat(),
        },
        headers=headers,
    )

    assert response.status_code == 200
    stats = response.json()["statistics"]
    assert stats["ph"]["current_quality"] == "check_required"
    assert stats["ph"]["status"] == "warning"
    assert stats["debit"]["status"] == "no_flow"
    assert stats["tss"]["status"] == "normal"
