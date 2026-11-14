from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.models import (Alert, DeviceRejection, LoggerEvent, LoggerIncident,
                               LoggerStatus, SensorData, Site)
from app.utils.logger_incidents import (close_open_incident, import_down_history, load_site_inputs,
                                        open_incident, recompute_causes, sync_incidents)
from app.utils.time import as_utc

NOW = datetime(2026, 11, 4, 3, 0, tzinfo=timezone.utc)


async def _site(db, uid, active=True, **kw):
    s = Site(uid=uid, name=uid, company_name="C", is_active=active, **kw)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _status(db, site, minutes_ago, **kw):
    db.add(LoggerStatus(site_id=site.id, state="alive",
                        last_heartbeat_at=NOW - timedelta(minutes=minutes_ago), **kw))
    await db.commit()


async def _event(db, site, kind, ts, detail=None):
    db.add(LoggerEvent(site_id=site.id, event_uid=f"{kind}-{ts.timestamp()}", type=kind, ts=ts,
                       received_at=ts, severity="info", detail=detail))
    await db.commit()


async def _incidents(db):
    return (await db.execute(select(LoggerIncident).order_by(LoggerIncident.id))).scalars().all()


async def _alerts(db):
    return (await db.execute(select(Alert).order_by(Alert.id))).scalars().all()


@pytest.mark.anyio
async def test_inputs_cover_sites_without_heartbeat_and_skip_inactive(db_session):
    a = await _site(db_session, "A")
    b = await _site(db_session, "B")
    await _site(db_session, "C", active=False)
    await _status(db_session, a, minutes_ago=1)
    db_session.add(SensorData(site_id=b.id, ts=NOW - timedelta(minutes=30), ph=7.0))
    await db_session.commit()

    inputs = {i.uid: i for i in await load_site_inputs(db_session, NOW)}
    assert set(inputs) == {"A", "B"}
    assert inputs["B"].status is None
    assert as_utc(inputs["B"].last_data_ts) == NOW - timedelta(minutes=30)
    assert inputs["A"].status["last_heartbeat_at"] == NOW - timedelta(minutes=1)


@pytest.mark.anyio
async def test_loggers_silent_together_are_counted(db_session):
    for uid, minutes in (("A", 20), ("B", 22), ("C", 25), ("D", 180)):
        await _status(db_session, await _site(db_session, uid), minutes_ago=minutes)
    inputs = {i.uid: i.concurrent_down for i in await load_site_inputs(db_session, NOW)}
    assert inputs == {"A": 3, "B": 3, "C": 3, "D": 1}


@pytest.mark.anyio
async def test_down_opens_one_incident_and_one_alarm_even_when_run_twice(db_session):
    site = await _site(db_session, "L-DOWN")
    await _status(db_session, site, minutes_ago=3 * 1440)
    await sync_incidents(db_session, NOW)
    await sync_incidents(db_session, NOW)

    incidents = await _incidents(db_session)
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.kind == "down" and inc.open_key == f"{site.id}:down"
    assert as_utc(inc.started_at) == NOW - timedelta(days=3)        # when it fell silent
    alerts = await _alerts(db_session)
    assert len(alerts) == 1
    assert (alerts[0].field, alerts[0].threshold_type, alerts[0].category) == ("logger_down", "danger", "logger")
    assert alerts[0].detail.startswith("Tidak melapor sejak 1 Nov 10:00.")
    assert inc.alert_id == alerts[0].id


@pytest.mark.anyio
async def test_a_concurrent_open_is_refused_by_open_key(db_session):
    site = await _site(db_session, "L-RACE")
    db_session.add(LoggerIncident(site_id=site.id, kind="down", started_at=NOW, open_key=f"{site.id}:down"))
    await db_session.commit()
    finding = {"title": "Tidak melapor.", "severity": "danger"}
    assert await open_incident(db_session, site.id, "down", NOW, NOW, finding) is None
    assert await _alerts(db_session) == []


@pytest.mark.anyio
async def test_an_existing_logger_down_alarm_is_adopted(db_session):
    site = await _site(db_session, "L-OLD")
    await _status(db_session, site, minutes_ago=60)
    old = Alert(site_id=site.id, field="logger_down", value=50.0, threshold_type="danger",
                status="active", triggered_at=NOW - timedelta(minutes=50), category="logger")
    db_session.add(old)
    await db_session.commit()
    await sync_incidents(db_session, NOW)
    assert len(await _alerts(db_session)) == 1
    assert (await _incidents(db_session))[0].alert_id == old.id


@pytest.mark.anyio
async def test_recovery_closes_the_incident_with_its_cause_and_resolves_the_alarm(db_session):
    site = await _site(db_session, "L-NET")
    await _status(db_session, site, minutes_ago=180)
    await sync_incidents(db_session, NOW)
    hb = NOW - timedelta(minutes=180)
    await _event(db_session, site, "net_down", hb + timedelta(minutes=1))
    await _event(db_session, site, "net_up", NOW - timedelta(minutes=5))
    for i in range(10):
        db_session.add(SensorData(site_id=site.id, ts=hb + timedelta(minutes=2 * i + 1), ph=7.0))
    await db_session.commit()

    await close_open_incident(db_session, site.id, "down", NOW)
    inc = (await _incidents(db_session))[0]
    assert inc.ended_at is not None and inc.open_key is None
    assert inc.cause == "internet"
    assert inc.cause_detail == "Internet lokasi putus 3 jam; data menyusul 11%."
    assert (inc.data_expected, inc.data_recovered) == (90, 10)
    alert = (await _alerts(db_session))[0]
    assert alert.status == "resolved"
    assert alert.followup_note == "Pulih otomatis: Internet lokasi putus 3 jam; data menyusul 11%."


@pytest.mark.anyio
async def test_data_accepted_after_the_heartbeat_stopped_turns_down_into_telemetry_only(db_session):
    site = await _site(db_session, "L-TEL")
    await _status(db_session, site, minutes_ago=120)
    await sync_incidents(db_session, NOW - timedelta(minutes=90))          # silent, no data yet: down
    db_session.add(SensorData(site_id=site.id, ts=NOW - timedelta(minutes=30), ph=7.0))
    site.last_ingest_at = NOW - timedelta(minutes=30)   # accepted by the server after the heartbeat stopped
    await db_session.commit()
    await sync_incidents(db_session, NOW)

    down, telemetry = await _incidents(db_session)
    assert down.kind == "down" and down.cause == "telemetry_only" and down.open_key is None
    assert telemetry.kind == "no_telemetry" and telemetry.open_key == f"{site.id}:no_telemetry"
    fields = [(a.field, a.status) for a in await _alerts(db_session)]
    assert fields == [("logger_down", "resolved"), ("no_telemetry", "active")]


@pytest.mark.anyio
async def test_alive_only_incidents_are_held_while_the_logger_is_silent(db_session):
    site = await _site(db_session, "L-HOLD")
    await _status(db_session, site, minutes_ago=1, last_send_ok_klhk=False,
                  klhk_fail_since=NOW - timedelta(hours=5))
    await sync_incidents(db_session, NOW)
    assert [(i.kind, i.open_key is not None) for i in await _incidents(db_session)] == [("send_fail_klhk", True)]

    later = NOW + timedelta(minutes=30)                      # the heartbeat is now 31 minutes old
    await sync_incidents(db_session, later)
    kinds = {(i.kind, i.open_key is not None) for i in await _incidents(db_session)}
    assert kinds == {("send_fail_klhk", True), ("down", True)}
    assert all(a.status == "active" for a in await _alerts(db_session))


@pytest.mark.anyio
async def test_refused_data_then_partly_refused(db_session):
    site = await _site(db_session, "L-REJ", last_ingest_at=NOW - timedelta(hours=5))
    await _status(db_session, site, minutes_ago=1)
    db_session.add(DeviceRejection(uid="L-REJ", site_id=site.id, source="post-data", reason="bad_signature",
                                   first_at=NOW - timedelta(days=2), last_at=NOW - timedelta(minutes=30), count=40))
    await db_session.commit()
    await sync_incidents(db_session, NOW)
    first = await _incidents(db_session)
    assert [i.kind for i in first] == ["rejected"]
    assert as_utc(first[0].started_at) == NOW - timedelta(days=2)        # the start of the refusal run

    site.last_ingest_at = NOW - timedelta(minutes=10)
    await db_session.commit()
    await sync_incidents(db_session, NOW)
    kinds = [(i.kind, i.open_key is not None) for i in await _incidents(db_session)]
    assert kinds == [("rejected", False), ("rejected_partial", True)]
    assert [(a.field, a.threshold_type, a.status) for a in await _alerts(db_session)] == [
        ("rejected", "danger", "resolved"), ("rejected_partial", "warning", "active")]


@pytest.mark.anyio
async def test_a_cause_is_worked_out_again_when_events_arrive_late(db_session):
    site = await _site(db_session, "L-LATE")
    await _status(db_session, site, minutes_ago=60)
    await sync_incidents(db_session, NOW)
    await close_open_incident(db_session, site.id, "down", NOW)
    inc = (await _incidents(db_session))[0]
    assert inc.cause == "unknown"

    await _event(db_session, site, "started", NOW - timedelta(minutes=2), "previous_shutdown_clean=False")
    await recompute_causes(db_session, NOW + timedelta(hours=1))
    await db_session.refresh(inc)
    assert inc.cause == "power_or_crash"
    alert = (await _alerts(db_session))[0]
    assert alert.followup_note.startswith("Pulih otomatis: Logger mati mendadak")


@pytest.mark.anyio
async def test_history_is_imported_once_and_duplicate_open_alarms_are_skipped(db_session):
    site = await _site(db_session, "L-HIST")
    trig = NOW - timedelta(days=5)
    db_session.add_all([
        Alert(site_id=site.id, field="logger_down", value=30.0, threshold_type="danger", status="resolved",
              triggered_at=trig, resolved_at=trig + timedelta(hours=2), category="logger"),
        Alert(site_id=site.id, field="logger_down", value=12.0, threshold_type="danger", status="active",
              triggered_at=NOW - timedelta(hours=3), category="logger"),
        Alert(site_id=site.id, field="logger_down", value=12.0, threshold_type="danger", status="active",
              triggered_at=NOW - timedelta(hours=3), category="logger"),
        Alert(site_id=site.id, field="logger_down", value=5.0, threshold_type="danger", status="resolved",
              triggered_at=NOW - timedelta(days=40), resolved_at=NOW - timedelta(days=40), category="logger"),
    ])
    await db_session.commit()
    newest_open = max(a.id for a in await _alerts(db_session) if a.status == "active")

    assert await import_down_history(db_session, NOW) == 2
    closed, still_open = await _incidents(db_session)
    assert as_utc(closed.started_at) == trig - timedelta(minutes=30)
    assert as_utc(closed.ended_at) == trig + timedelta(hours=2) and closed.open_key is None
    assert still_open.open_key == f"{site.id}:down" and still_open.alert_id == newest_open
    assert await import_down_history(db_session, NOW) == 0
