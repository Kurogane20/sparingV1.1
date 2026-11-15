from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.models import (Alert, DeviceRejection, LoggerEvent, LoggerIncident,
                               LoggerStatus, SensorData, Site)
from app.utils.logger_incidents import (close_open_incident, import_down_history, load_site_inputs,
                                        open_incident, recompute_causes, sync_incidents)
from app.utils import logger_incidents
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
    hb = NOW - timedelta(minutes=120)
    for i in range(60):                                   # the whole silence caught up
        db_session.add(SensorData(site_id=site.id, ts=hb + timedelta(minutes=2 * i), ph=7.0))
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
    statuses = sorted((a.status, a.followup_note) for a in await _alerts(db_session) if a.triggered_at and as_utc(a.triggered_at) == NOW - timedelta(hours=3))
    assert statuses == [("active", None), ("resolved", "Ditutup otomatis — alarm ganda untuk gangguan yang sama")]   # the older duplicate is stale
    closed, still_open = await _incidents(db_session)
    assert as_utc(closed.started_at) == trig - timedelta(minutes=30)
    assert as_utc(closed.ended_at) == trig + timedelta(hours=2) and closed.open_key is None
    assert still_open.open_key == f"{site.id}:down" and still_open.alert_id == newest_open
    assert await import_down_history(db_session, NOW) == 0


@pytest.mark.anyio
async def test_a_persons_note_survives_close_and_recompute(db_session):
    site = await _site(db_session, "L-NOTE")
    await _status(db_session, site, minutes_ago=60)
    await sync_incidents(db_session, NOW)
    alert = (await _alerts(db_session))[0]
    alert.status, alert.followup_note = "acknowledged", "Teknisi menuju lokasi"
    await db_session.commit()
    await close_open_incident(db_session, site.id, "down", NOW)
    await recompute_causes(db_session, NOW + timedelta(hours=1))
    await db_session.refresh(alert)
    assert (alert.status, alert.followup_note) == ("resolved", "Teknisi menuju lokasi")


@pytest.mark.anyio
async def test_an_alarm_from_an_earlier_outage_is_not_adopted(db_session):
    site = await _site(db_session, "L-OLDACK")
    await _status(db_session, site, minutes_ago=60)
    old = Alert(site_id=site.id, field="logger_down", value=30.0, threshold_type="danger", status="acknowledged",
                triggered_at=NOW - timedelta(days=45), category="logger", followup_note="sudah dicek")
    db_session.add(old)
    await db_session.commit()
    await sync_incidents(db_session, NOW)
    inc = (await _incidents(db_session))[0]
    assert inc.alert_id != old.id
    assert len(await _alerts(db_session)) == 2


@pytest.mark.anyio
async def test_import_resolves_alarms_whose_logger_has_reported_since(db_session):
    site = await _site(db_session, "L-BACKNOW")
    await _status(db_session, site, minutes_ago=1)
    stale = Alert(site_id=site.id, field="logger_down", value=15.0, threshold_type="danger", status="acknowledged",
                  triggered_at=NOW - timedelta(days=20), category="logger", followup_note="Teknisi sudah cek")
    db_session.add(stale)
    await db_session.commit()
    assert await import_down_history(db_session, NOW) == 1
    await db_session.refresh(stale)
    assert (stale.status, stale.followup_note) == ("resolved", "Teknisi sudah cek")
    (inc,) = await _incidents(db_session)
    assert inc.open_key is None and as_utc(inc.ended_at) == NOW - timedelta(days=20)
    assert await import_down_history(db_session, NOW) == 0          # never twice


@pytest.mark.anyio
async def test_one_failing_site_does_not_stop_the_others(db_session, monkeypatch):
    bad = await _site(db_session, "A-BAD")
    good = await _site(db_session, "B-GOOD")
    await _status(db_session, bad, minutes_ago=60)
    await _status(db_session, good, minutes_ago=60)
    # ids captured now: a failing site's rollback expires every ORM object in the session.
    bad_id, good_id = bad.id, good.id
    real_open = logger_incidents.open_incident

    async def flaky_open(db, site_id, *args, **kwargs):
        if site_id == bad_id:
            raise RuntimeError("boom")
        return await real_open(db, site_id, *args, **kwargs)

    monkeypatch.setattr(logger_incidents, "open_incident", flaky_open)
    await sync_incidents(db_session, NOW)
    assert [(i.site_id, i.kind) for i in await _incidents(db_session)] == [(good_id, "down")]


@pytest.mark.anyio
async def test_a_reopened_silence_never_overlaps_the_closed_incidents(db_session):
    site = await _site(db_session, "L-AGAIN")
    await _status(db_session, site, minutes_ago=6 * 60)
    await sync_incidents(db_session, NOW - timedelta(hours=5))                      # down
    site.last_ingest_at = NOW - timedelta(hours=4, minutes=50)
    await db_session.commit()
    await sync_incidents(db_session, NOW - timedelta(hours=4, minutes=45))          # telemetry only
    await sync_incidents(db_session, NOW)                                           # data stopped again: down
    incidents = await _incidents(db_session)
    assert [i.kind for i in incidents] == ["down", "no_telemetry", "down"]
    for earlier, later in zip(incidents, incidents[1:]):
        assert as_utc(later.started_at) >= as_utc(earlier.ended_at)


@pytest.mark.anyio
async def test_detected_starts_are_not_taken_for_a_server_outage(db_session):
    sites = [await _site(db_session, f"L-NEW{i}") for i in range(3)]
    await sync_incidents(db_session, NOW)                    # never reported: start = when detected
    await close_open_incident(db_session, sites[0].id, "down", NOW + timedelta(minutes=30))
    inc = next(i for i in await _incidents(db_session) if i.site_id == sites[0].id)
    assert inc.evidence["start_detected"] is True
    assert inc.cause == "unknown"


@pytest.mark.anyio
async def test_a_refusal_ends_down_as_refused(db_session):
    site = await _site(db_session, "L-REFUSED")
    await _status(db_session, site, minutes_ago=180)
    await sync_incidents(db_session, NOW - timedelta(minutes=60))                  # silent: down
    db_session.add(DeviceRejection(uid="L-REFUSED", site_id=site.id, source="post-data", reason="bad_signature",
                                   first_at=NOW - timedelta(minutes=20), last_at=NOW - timedelta(minutes=5), count=2))
    await db_session.commit()
    await sync_incidents(db_session, NOW)
    down = next(i for i in await _incidents(db_session) if i.kind == "down")
    assert (down.cause, down.open_key) == ("refused", None)


@pytest.mark.anyio
async def test_a_deactivated_site_has_its_incidents_closed(db_session):
    site = await _site(db_session, "L-OFF")
    await _status(db_session, site, minutes_ago=60)
    await sync_incidents(db_session, NOW)
    site.is_active = False
    await db_session.commit()
    await sync_incidents(db_session, NOW + timedelta(minutes=2))
    inc = (await _incidents(db_session))[0]
    assert (inc.open_key, inc.cause) == (None, "site_inactive")
    assert (await _alerts(db_session))[0].status == "resolved"


@pytest.mark.anyio
async def test_evidence_keeps_the_heartbeat_snapshot_and_event_ids(db_session):
    site = await _site(db_session, "L-EVID")
    await _status(db_session, site, minutes_ago=180, internet_ok=False)
    await sync_incidents(db_session, NOW)
    hb = NOW - timedelta(minutes=180)
    await _event(db_session, site, "net_down", hb + timedelta(minutes=1))
    await _event(db_session, site, "net_up", NOW - timedelta(minutes=5))
    await close_open_incident(db_session, site.id, "down", NOW)
    inc = (await _incidents(db_session))[0]
    assert inc.evidence["heartbeat"]["internet_ok"] is False
    assert inc.evidence["heartbeat"]["last_heartbeat_at"] == hb.isoformat()
    assert inc.evidence["tech"].startswith("heartbeat terakhir")
    assert all("id" in e for e in inc.evidence["events"])


@pytest.mark.anyio
async def test_detected_starts_do_not_make_a_real_outage_look_concurrent(db_session):
    for i in range(2):
        await _site(db_session, f"L-NEW{i}")
    await sync_incidents(db_session, NOW)                         # never reported: start = NOW, only "detected"
    real = await _site(db_session, "L-REAL")
    db_session.add(LoggerStatus(site_id=real.id, state="alive", last_heartbeat_at=NOW + timedelta(minutes=2)))
    await db_session.commit()
    real_id = real.id
    await sync_incidents(db_session, NOW + timedelta(minutes=15))  # a real silence from NOW + 2 min
    await close_open_incident(db_session, real_id, "down", NOW + timedelta(minutes=30))
    inc = next(i for i in await _incidents(db_session) if i.site_id == real_id)
    assert inc.cause != "server"


@pytest.mark.anyio
async def test_a_site_without_heartbeat_records_its_data_gap_without_a_second_alarm(db_session):
    site = await _site(db_session, "L-NOHB", last_ingest_at=NOW - timedelta(minutes=30))
    site_id = site.id
    await sync_incidents(db_session, NOW)                                   # data flows, no heartbeat
    assert [i.kind for i in await _incidents(db_session)] == ["no_telemetry"]
    await sync_incidents(db_session, NOW + timedelta(hours=5))              # data stopped 5.5 h ago
    telemetry, down = await _incidents(db_session)
    assert telemetry.open_key is None and down.kind == "down" and down.open_key == f"{site_id}:down"
    assert down.alert_id is None                                            # device_offline already alarms
    assert as_utc(down.started_at) >= as_utc(telemetry.ended_at)
    assert [a.field for a in await _alerts(db_session)] == ["no_telemetry"]
