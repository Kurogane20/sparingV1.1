from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import hash_password
from app.models.models import (
    Alert,
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
        "status_label": "Kritis",
        "status_reason": "danger_threshold_violated",
        "status_severity": "critical",
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
    assert body["statistics"]["ph"]["status_label"] == "Tidak Ada Data"
    assert body["statistics"]["ph"]["status_reason"] == "no_finite_measurement"
    assert body["statistics"]["ph"]["status_severity"] == "warning"
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
    assert body["statistics"]["ph"]["status_label"] == "Kesalahan Sensor"
    assert body["statistics"]["ph"]["status_reason"] == "explicit_sensor_error"
    assert body["statistics"]["ph"]["status_severity"] == "critical"


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
    assert stats["ph"]["status_label"] == "Peringatan"
    assert stats["ph"]["status_reason"] == "quality_check_required"
    assert stats["ph"]["status_severity"] == "warning"
    assert stats["debit"]["status"] == "no_flow"
    assert stats["debit"]["status_label"] == "Aliran Terhenti"
    assert stats["debit"]["status_reason"] == "no_flow_threshold_violated"
    assert stats["debit"]["status_severity"] == "warning"
    assert stats["tss"]["status"] == "normal"
    assert stats["tss"]["status_label"] == "Normal"
    assert stats["tss"]["status_reason"] == "within_configured_limits"
    assert stats["tss"]["status_severity"] == "info"


@pytest.mark.anyio
async def test_timeseries_places_exact_threshold_quality_op_and_logger_events(
    client, db_session
):
    site = await _site(db_session, "TS-EVENTS", timezone_name="UTC")
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    db_session.add_all(
        [
            SiteMonitoringConfig(
                site_id=site.id,
                cadence_seconds=60,
                stale_after_seconds=5400,
                max_chart_points=720,
                max_range_days=31,
            ),
            AlertRule(
                site_id=site.id,
                field="ph",
                warning_max=8.0,
                danger_max=10.0,
                is_active=True,
            ),
            SensorData(site_id=site.id, ts=base, ph=7.0),
            SensorData(site_id=site.id, ts=base + timedelta(minutes=1), ph=9.0),
            SensorData(
                site_id=site.id,
                ts=base + timedelta(minutes=2),
                ph=11.0,
                quality_flag="anomaly",
            ),
            SensorData(
                site_id=site.id,
                ts=base + timedelta(minutes=3),
                ph=7.0,
                op_status=-2,
            ),
            LoggerEvent(
                site_id=site.id,
                event_uid="logger-device-clock",
                type="sensor_fail",
                ts=base + timedelta(minutes=4),
                received_at=base + timedelta(minutes=9),
                severity="warning",
                detail="Probe disconnected",
            ),
            # This legacy wall-clock row has no exact SensorData match and must
            # remain available only through the alerts API.
            Alert(
                site_id=site.id,
                field="ph",
                value=9.0,
                threshold_type="warning",
                status="active",
                triggered_at=base + timedelta(minutes=7),
            ),
        ]
    )
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="events@example.com")
    params = {
        "site_uid": site.uid,
        "date_from": base.isoformat(),
        "date_to": (base + timedelta(minutes=10)).isoformat(),
        "fields": "ph",
    }

    first = await client.get("/analytics/timeseries", params=params, headers=headers)
    second = await client.get("/analytics/timeseries", params=params, headers=headers)

    assert first.status_code == 200
    events = first.json()["events"]
    assert [(event["type"], event["ts"]) for event in events] == [
        ("threshold_warning", "2026-08-01T00:01:00Z"),
        ("threshold_danger", "2026-08-01T00:02:00Z"),
        ("sensor_anomaly", "2026-08-01T00:02:00Z"),
        ("op_status", "2026-08-01T00:03:00Z"),
        ("sensor_fail", "2026-08-01T00:04:00Z"),
    ]
    assert [event["id"] for event in events] == [
        event["id"] for event in second.json()["events"]
    ]
    assert not any(event["ts"] == "2026-08-01T00:07:00Z" for event in events)
    anomaly = next(event for event in events if event["type"] == "sensor_anomaly")
    assert anomaly["label"] == "Anomali Sensor"
    logger = next(event for event in events if event["type"] == "sensor_fail")
    assert logger["label"] == "Kegagalan Sensor"
    assert logger["context"]["interval_seconds"] == 300
    assert first.json()["statistics"]["ph"]["count"] == 3
    assert first.json()["statistics"]["ph"]["current_quality"] == "check_required"


@pytest.mark.anyio
async def test_timeseries_invokes_rapid_detector_on_raw_measurement_timestamps(
    client, db_session
):
    site = await _site(db_session, "TS-RAPID", timezone_name="UTC")
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    db_session.add(
        OperationalRule(
            site_id=site.id,
            field="ph",
            rule_type="rapid_change",
            is_active=True,
            window_seconds=600,
            min_points=2,
            abs_delta=3.0,
            minimum_baseline=1.0,
            trigger_mode="any",
            cooldown_seconds=0,
        )
    )
    db_session.add_all(
        [
            SensorData(site_id=site.id, ts=base, ph=7.0),
            SensorData(site_id=site.id, ts=base + timedelta(minutes=1), ph=7.0),
            SensorData(site_id=site.id, ts=base + timedelta(minutes=2), ph=11.0),
        ]
    )
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="rapid@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": site.uid,
            "date_from": base.isoformat(),
            "date_to": (base + timedelta(minutes=5)).isoformat(),
            "fields": "ph",
        },
        headers=headers,
    )

    assert response.status_code == 200
    rapid = next(event for event in response.json()["events"] if event["type"] == "rapid_change")
    assert rapid["ts"] == "2026-08-01T00:02:00Z"
    assert rapid["label"] == "Perubahan Cepat"
    assert rapid["direction"] == "up"
    assert rapid["context"]["baseline"] == 7.0
    assert rapid["context"]["current"] == 11.0
    assert rapid["context"]["delta"] == 4.0
    assert rapid["context"]["points"] == 3
    assert response.json()["statistics"]["ph"]["status"] == "warning"
    assert response.json()["statistics"]["ph"]["status_reason"] == "rapid_change_detected"


@pytest.mark.anyio
async def test_timeseries_derives_flow_restore_and_only_significant_low_flow_tss(
    client, db_session
):
    site = await _site(db_session, "TS-FLOW", timezone_name="UTC")
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    db_session.add_all(
        [
            AlertRule(
                site_id=site.id,
                field="tss",
                warning_max=50.0,
                danger_max=100.0,
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
                hold_seconds=0,
                cooldown_seconds=0,
            ),
            OperationalRule(
                site_id=site.id,
                field="tss",
                rule_type="rapid_change",
                is_active=True,
                window_seconds=600,
                min_points=2,
                abs_delta=20.0,
                minimum_baseline=1.0,
                trigger_mode="any",
                cooldown_seconds=0,
            ),
            OperationalRule(
                site_id=site.id,
                field="debit",
                secondary_field="tss",
                rule_type="low_flow_tss",
                is_active=True,
                cooldown_seconds=0,
            ),
        ]
    )
    for minute, debit, tss in [
        (0, 3.0, 10.0),
        (1, 0.5, 10.0),
        (2, 0.5, 120.0),
        (3, 3.0, 120.0),
    ]:
        db_session.add(
            SensorData(
                site_id=site.id,
                ts=base + timedelta(minutes=minute),
                debit=debit,
                tss=tss,
            )
        )
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="flow@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": site.uid,
            "date_from": base.isoformat(),
            "date_to": (base + timedelta(minutes=5)).isoformat(),
            "fields": "debit,tss",
        },
        headers=headers,
    )

    assert response.status_code == 200
    events = response.json()["events"]
    assert [(event["type"], event["ts"]) for event in events] == [
        ("flow_drop", "2026-08-01T00:01:00Z"),
        ("low_flow_tss_check", "2026-08-01T00:02:00Z"),
        ("threshold_danger", "2026-08-01T00:02:00Z"),
        ("rapid_change", "2026-08-01T00:02:00Z"),
        ("flow_restored", "2026-08-01T00:03:00Z"),
    ]
    compound = next(event for event in events if event["type"] == "low_flow_tss_check")
    assert compound["severity"] == "critical"
    assert compound["label"] == "Perlu Pemeriksaan TSS saat Aliran Rendah"


@pytest.mark.anyio
async def test_timeseries_does_not_flag_low_flow_tss_from_tss_presence_alone(
    client, db_session
):
    site = await _site(db_session, "TS-FLOW-CONSTANT", timezone_name="UTC")
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    db_session.add_all(
        [
            OperationalRule(
                site_id=site.id,
                field="debit",
                rule_type="flow_state",
                is_active=True,
                no_flow_threshold=0.0,
                low_flow_threshold=1.0,
                recovery_threshold=2.0,
                hold_seconds=0,
            ),
            OperationalRule(
                site_id=site.id,
                field="tss",
                rule_type="rapid_change",
                is_active=True,
                window_seconds=600,
                min_points=2,
                abs_delta=20.0,
                trigger_mode="any",
            ),
            OperationalRule(
                site_id=site.id,
                field="debit",
                secondary_field="tss",
                rule_type="low_flow_tss",
                is_active=True,
            ),
            SensorData(site_id=site.id, ts=base, debit=3.0, tss=10.0),
            SensorData(site_id=site.id, ts=base + timedelta(minutes=1), debit=0.5, tss=10.0),
            SensorData(site_id=site.id, ts=base + timedelta(minutes=2), debit=0.5, tss=10.0),
        ]
    )
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="flow-constant@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": site.uid,
            "date_from": base.isoformat(),
            "date_to": (base + timedelta(minutes=3)).isoformat(),
            "fields": "debit,tss",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert "low_flow_tss_check" not in {
        event["type"] for event in response.json()["events"]
    }


@pytest.mark.anyio
async def test_timeseries_derives_major_gap_from_raw_cadence(client, db_session):
    site = await _site(db_session, "TS-GAP", timezone_name="UTC")
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    db_session.add(
        SiteMonitoringConfig(
            site_id=site.id,
            cadence_seconds=60,
            stale_after_seconds=5400,
            max_chart_points=720,
            max_range_days=31,
        )
    )
    db_session.add_all(
        [
            SensorData(site_id=site.id, ts=base, ph=7.0),
            SensorData(site_id=site.id, ts=base + timedelta(minutes=10), ph=7.0),
        ]
    )
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="gap@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": site.uid,
            "date_from": base.isoformat(),
            "date_to": (base + timedelta(minutes=11)).isoformat(),
            "fields": "ph",
        },
        headers=headers,
    )

    assert response.status_code == 200
    gap = next(event for event in response.json()["events"] if event["type"] == "data_gap")
    assert gap["ts"] == "2026-08-01T00:01:00Z"
    assert gap["end_ts"] == "2026-08-01T00:09:00Z"
    assert gap["context"]["interval_seconds"] == 540
    assert gap["label"] == "Kesenjangan Data Utama"


@pytest.mark.anyio
async def test_timeseries_caps_event_details_without_changing_availability(
    client, db_session
):
    site = await _site(db_session, "TS-EVENT-CAP", timezone_name="UTC")
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    db_session.add(
        SiteMonitoringConfig(
            site_id=site.id,
            cadence_seconds=60,
            stale_after_seconds=5400,
            max_chart_points=720,
            max_range_days=31,
        )
    )
    for minute in range(101):
        db_session.add(
            SensorData(
                site_id=site.id,
                ts=base + timedelta(minutes=minute),
                ph=7.0,
                quality_flag="anomaly",
            )
        )
    db_session.add(
        LoggerEvent(
            site_id=site.id,
            event_uid="critical-oldest",
            type="sensor_fail",
            ts=base,
            received_at=base,
            severity="critical",
        )
    )
    await db_session.commit()
    headers, _ = await _headers(client, db_session, email="event-cap@example.com")

    response = await client.get(
        "/analytics/timeseries",
        params={
            "site_uid": site.uid,
            "date_from": base.isoformat(),
            "date_to": (base + timedelta(minutes=101)).isoformat(),
            "fields": "ph",
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["event_total"] == 102
    assert len(body["events"]) == 100
    assert body["events"][0]["type"] == "sensor_fail"
    assert body["events"][1]["ts"] == "2026-08-01T00:02:00Z"
    assert body["events"][-1]["ts"] == "2026-08-01T01:40:00Z"
    assert body["meta"]["availability_pct"] == 100.0
    assert body["meta"]["is_partial"] is True
    assert body["meta"]["partial_reasons"] == ["events_truncated"]
