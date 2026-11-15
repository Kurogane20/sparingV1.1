"""Logger incidents: gather the diagnosis inputs, open and close incidents, and
keep their alarms in step (logger-diagnosis spec, Bagian 1 and 3).

Called by the liveness scan every 2 minutes and by the heartbeat recovery path.
An incident is opened by INSERTing its open_key ("<site_id>:<kind>"). The UNIQUE
index makes a second, concurrent open fail, and only the process whose INSERT
won raises the alarm, so an incident and its alarm exist at most once.

One site's failure never stops the others: each site, and each recomputed
incident, runs in its own try/rollback. A note a person wrote on an alarm is
never overwritten.
"""
import math
from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger as applog
from app.models.models import (Alert, DeviceRejection, LoggerEvent, LoggerIncident,
                               LoggerStatus, SensorData, Site)
from app.utils.logger_diagnosis import (ALIVE_ONLY_KINDS, CONCURRENT_WINDOW, DOWN_AFTER, EVIDENCE_SLACK,
                                        RECENT, SiteInputs, diagnose, heartbeat_alive, infer_cause, iso, utc)

LOGGER_CATEGORY = "logger"
DOWN_FIELD = "logger_down"
OPEN_ALERT_STATUSES = ("active", "acknowledged")
RECOMPUTE_WINDOW = timedelta(hours=24)
CATCH_UP_WINDOW = timedelta(days=7)    # a Pi's backup queue can lag days: keep counting data that catches up
HISTORY_DAYS = 30
AUTO_NOTE_PREFIX = "Pulih otomatis: "
STALE_ALARM_NOTE = "Pulih otomatis — logger kembali mengirim heartbeat"   # logger_monitor's words
DUPLICATE_ALARM_NOTE = "Ditutup otomatis — alarm ganda untuk gangguan yang sama"
SILENCE_KINDS = ("down", "no_telemetry")   # successive states of one silence: they never overlap
STATUS_COLUMNS = (
    "last_heartbeat_at", "logger_version", "uptime_s", "op_status", "ph_ok", "tss_ok", "debit_ok",
    "cod_ok", "nh3n_ok", "consec_fail", "sensor_fail_since", "internet_ok", "last_send_ok_mm",
    "last_send_ok_klhk", "mm_fail_since", "klhk_fail_since", "buffer_depth", "daily_sent",
    "cpu_temp", "cpu_pct", "mem_pct", "disk_pct",
)


def alert_field(kind: str) -> str:
    """`down` keeps the alarm field the Alarm page and earlier alarms use."""
    return DOWN_FIELD if kind == "down" else kind


def expected_readings(start: datetime, end: datetime) -> int:
    """One reading every 2 minutes."""
    return max(0, math.ceil((utc(end) - utc(start)).total_seconds() / 120))


def _status_dict(st: LoggerStatus) -> dict:
    """logger_status as plain values, datetimes made aware."""
    out = {}
    for column in STATUS_COLUMNS:
        value = getattr(st, column)
        out[column] = utc(value) if isinstance(value, datetime) else value
    return out


def _write_auto_note(alert: Alert, detail: str) -> None:
    """The cause becomes the alarm's note, unless a person already wrote one."""
    if not alert.followup_note or alert.followup_note.startswith(AUTO_NOTE_PREFIX):
        alert.followup_note = AUTO_NOTE_PREFIX + detail


async def _events(db: AsyncSession, site_id: int, start: datetime, end: datetime) -> list:
    """Logger events of one site in [start, end], oldest first."""
    rows = (await db.execute(select(LoggerEvent).where(
        LoggerEvent.site_id == site_id, LoggerEvent.ts >= start, LoggerEvent.ts <= end,
    ).order_by(LoggerEvent.ts))).scalars().all()
    return [{"id": e.id, "type": e.type, "ts": utc(e.ts), "detail": e.detail,
             "received_at": utc(e.received_at)} for e in rows]


async def load_site_inputs(db: AsyncSession, now: datetime) -> list[SiteInputs]:
    """One SiteInputs per active site, including sites that never sent a heartbeat."""
    now = utc(now)
    sites = (await db.execute(select(Site).where(Site.is_active == True).order_by(Site.id))).scalars().all()
    if not sites:
        return []
    ids = [s.id for s in sites]
    statuses = {st.site_id: st for st in (await db.execute(
        select(LoggerStatus).where(LoggerStatus.site_id.in_(ids)))).scalars().all()}
    last_data = {sid: utc(ts) for sid, ts in (await db.execute(
        select(SensorData.site_id, func.max(SensorData.ts))
        .where(SensorData.site_id.in_(ids)).group_by(SensorData.site_id))).all()}
    rejections: dict = {}
    for r in (await db.execute(select(DeviceRejection).where(
            DeviceRejection.site_id.in_(ids), DeviceRejection.last_at >= now - RECENT))).scalars().all():
        rejections.setdefault(r.site_id, []).append({
            "source": r.source, "reason": r.reason, "first_at": utc(r.first_at),
            "last_at": utc(r.last_at), "count": r.count, "last_detail": r.last_detail})
    open_kinds: dict = {}
    for inc in (await db.execute(select(LoggerIncident).where(
            LoggerIncident.site_id.in_(ids), LoggerIncident.open_key.is_not(None)))).scalars().all():
        open_kinds.setdefault(inc.site_id, set()).add(inc.kind)

    heartbeats = {sid: utc(st.last_heartbeat_at) for sid, st in statuses.items()}
    # When each heartbeat-capable logger fell silent; several at once points at the server.
    silent = {sid: hb for sid, hb in heartbeats.items() if hb is not None and now - hb > DOWN_AFTER}

    def concurrent(sid: int) -> int:
        start = silent.get(sid)
        if start is None:
            return 1
        return sum(1 for other in silent.values() if abs(other - start) <= CONCURRENT_WINDOW)

    out = []
    for s in sites:
        st, hb = statuses.get(s.id), heartbeats.get(s.id)
        # The rules look at the 24 h before the logger fell silent, or before now.
        if s.id in silent:
            events = await _events(db, s.id, hb - timedelta(hours=24), hb + EVIDENCE_SLACK)
        else:
            events = await _events(db, s.id, now - timedelta(hours=24), now)
        out.append(SiteInputs(
            site_id=s.id, uid=s.uid, name=s.name, timezone=s.timezone or "Asia/Jakarta",
            status=None if st is None else _status_dict(st),
            last_data_ts=last_data.get(s.id), last_ingest_at=utc(s.last_ingest_at),
            events=events, rejections=rejections.get(s.id, []),
            open_kinds=open_kinds.get(s.id, set()), concurrent_down=concurrent(s.id),
        ))
    return out


async def open_incident(db: AsyncSession, site_id: int, kind: str, started_at: datetime,
                        now: datetime, finding: dict, inp: SiteInputs | None = None) -> LoggerIncident | None:
    """Open an incident and its alarm; None when another process opened it first.

    Commits first, so the rollback of a refused INSERT can discard nothing else."""
    now, started_at = utc(now), utc(started_at)
    await db.commit()
    # A re-opened disruption starts where the previous one of its silence ended,
    # so the same hours are never counted twice.
    related = SILENCE_KINDS if kind in SILENCE_KINDS else (kind,)
    last_end = (await db.execute(select(func.max(LoggerIncident.ended_at)).where(
        LoggerIncident.site_id == site_id, LoggerIncident.kind.in_(related)))).scalar()
    clamped = last_end is not None and utc(last_end) > started_at
    if clamped:
        started_at = utc(last_end)
    evidence = {"title": finding["title"], "tech": finding.get("tech"),
                "start_detected": finding.get("since") is None or clamped}
    if inp is not None and inp.status is not None:
        evidence["heartbeat"] = {k: iso(v) if isinstance(v, datetime) else v for k, v in inp.status.items()}
    inc = LoggerIncident(site_id=site_id, kind=kind, started_at=started_at,
                         open_key=f"{site_id}:{kind}", evidence=evidence)
    db.add(inc)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return None
    if kind == "down" and inp is not None and inp.status is None:
        # Never sent a heartbeat: this is a data gap, and device_offline already alarms on it.
        await db.commit()
        return inc
    alert = None
    if kind == "down":
        # Adopt the alarm the old scan raised for THIS silence; one from an earlier outage is not this one.
        alert = (await db.execute(select(Alert).where(
            Alert.site_id == site_id, Alert.category == LOGGER_CATEGORY, Alert.field == DOWN_FIELD,
            Alert.status.in_(OPEN_ALERT_STATUSES), Alert.triggered_at >= started_at,
        ).order_by(Alert.id.desc()).limit(1))).scalars().first()
    if alert is None:
        minutes = round((now - started_at).total_seconds() / 60, 1) if kind == "down" else 0.0
        alert = Alert(site_id=site_id, device_uid=None, field=alert_field(kind), value=minutes,
                      threshold_type=finding["severity"], status="active", triggered_at=now,
                      category=LOGGER_CATEGORY, detail=finding["title"][:255])
        db.add(alert)
        await db.flush()
    inc.alert_id = alert.id
    await db.commit()
    return inc


async def _settle_cause(db: AsyncSession, inc: LoggerIncident, ended_by: str | None = None) -> None:
    """Work out (again) why an ended incident happened; events may arrive late."""
    start, end = utc(inc.started_at), utc(inc.ended_at)
    evidence = dict(inc.evidence or {})
    ended_by = ended_by or evidence.get("ended_by")
    site = await db.get(Site, inc.site_id)
    tz = (site.timezone if site else None) or "Asia/Jakarta"
    events, concurrent = [], 1
    if inc.kind == "down":
        inc.data_expected = expected_readings(start, end)
        inc.data_recovered = (await db.execute(select(func.count(SensorData.id)).where(
            SensorData.site_id == inc.site_id, SensorData.ts >= start, SensorData.ts < end))).scalar_one()
        events = await _events(db, inc.site_id, start - EVIDENCE_SLACK, end + EVIDENCE_SLACK)
        if not evidence.get("start_detected"):
            # Only real silence times can coincide; "when detected" is the scan's own clock.
            rows = (await db.execute(select(LoggerIncident.site_id, LoggerIncident.evidence).where(
                LoggerIncident.kind == "down",
                LoggerIncident.started_at >= start - CONCURRENT_WINDOW,
                LoggerIncident.started_at <= start + CONCURRENT_WINDOW))).all()
            concurrent = len({sid for sid, ev in rows if not (ev or {}).get("start_detected")})
    cause, detail, used = infer_cause(
        inc.kind, start, end, events, tz=tz, data_expected=inc.data_expected,
        data_recovered=inc.data_recovered, concurrent=concurrent, ended_by=ended_by,
        title=evidence.get("title"))
    inc.cause, inc.cause_detail = cause, detail[:255]
    evidence["events"] = used
    if ended_by:
        evidence["ended_by"] = ended_by
    inc.evidence = evidence   # reassigned so the JSON change is persisted


async def close_incident(db: AsyncSession, inc: LoggerIncident, now: datetime,
                         ended_by: str | None = None) -> None:
    """End an incident, settle its cause, and resolve its alarm with that cause
    (a person's note on the alarm stays)."""
    now = utc(now)
    inc.ended_at = now
    inc.open_key = None
    await _settle_cause(db, inc, ended_by)
    if inc.alert_id:
        alert = await db.get(Alert, inc.alert_id)
        if alert is not None and alert.status in OPEN_ALERT_STATUSES:
            # The incident may end earlier (at the last accepted data); the alarm resolves no earlier than it was raised.
            alert.status, alert.resolved_at = "resolved", max(now, utc(alert.triggered_at))
            _write_auto_note(alert, inc.cause_detail)
    await db.commit()


async def close_open_incident(db: AsyncSession, site_id: int, kind: str, now: datetime) -> None:
    """Close the site's open incident of this kind, if there is one."""
    inc = (await db.execute(select(LoggerIncident).where(
        LoggerIncident.open_key == f"{site_id}:{kind}"))).scalars().first()
    if inc is not None:
        await close_incident(db, inc, now)


def _since(finding: dict, now: datetime) -> datetime:
    """When the finding's disruption began, or now when it does not say."""
    return datetime.fromisoformat(finding["since"]) if finding.get("since") else now


def _ended_by(kind: str, wanted: dict, alive: bool, has_heartbeat: bool) -> str | None:
    """What ended a `down` while the heartbeat is still silent: data still arriving,
    or sends being refused, prove the logger runs. A returned heartbeat, or a
    logger that never had one, leaves the cause to the events."""
    if kind != "down" or alive or not has_heartbeat:
        return None
    if "no_telemetry" in wanted:
        return "no_telemetry"
    if "rejected" in wanted or "rejected_partial" in wanted:
        return "rejected"
    return None


async def _sync_site(db: AsyncSession, inp: SiteInputs, now: datetime) -> None:
    row = diagnose(inp, now)
    wanted = {f["kind"]: f for f in row["findings"] if f["kind"]}
    alive = heartbeat_alive(inp, now)
    open_rows = (await db.execute(select(LoggerIncident).where(
        LoggerIncident.site_id == inp.site_id, LoggerIncident.open_key.is_not(None)))).scalars().all()
    already = {inc.kind for inc in open_rows}
    for inc in open_rows:
        if inc.kind in wanted:
            continue
        if inc.kind in ALIVE_ONLY_KINDS and not alive:
            # Judged from the heartbeat: neither confirmed nor cleared while it is silent,
            # so an outage does not close (and later reopen) a KLHK or disk alarm.
            continue
        end = now
        if inc.kind == "no_telemetry" and "down" in wanted and inp.last_ingest_at is not None:
            # Data stopped at the last acceptance, not when the scan noticed.
            end = max(utc(inc.started_at), min(now, utc(inp.last_ingest_at)))
        await close_incident(db, inc, end, _ended_by(inc.kind, wanted, alive, inp.status is not None))
    for kind, finding in wanted.items():
        if kind not in already:
            await open_incident(db, inp.site_id, kind, _since(finding, now), now, finding, inp)


async def sync_incidents(db: AsyncSession, now: datetime) -> None:
    """Diagnose every active site; open incidents for new findings, close the
    ones whose finding has gone, and end those of sites switched off."""
    now = utc(now)
    inputs = await load_site_inputs(db, now)
    for inp in inputs:
        try:
            await _sync_site(db, inp, now)
        except Exception:
            # Drops this site's half-done work; SiteInputs are plain data and
            # _sync_site re-reads its rows, so the next site is unaffected.
            await db.rollback()
            applog.exception("logger incidents failed for %s", inp.uid)
    active = [inp.site_id for inp in inputs]
    stale = (await db.execute(select(LoggerIncident.id).where(
        LoggerIncident.open_key.is_not(None), LoggerIncident.site_id.not_in(active)))).scalars().all()
    for incident_id in stale:
        try:
            inc = await db.get(LoggerIncident, incident_id)
            await close_incident(db, inc, now, "site_inactive")
        except Exception:
            await db.rollback()
            applog.exception("closing logger incident %s of an inactive site failed", incident_id)


async def recompute_causes(db: AsyncSession, now: datetime) -> None:
    """Events and backlogged data reach the server after the logger reconnects,
    so the causes of recently ended `down` incidents are worked out again: for
    24 h, for as long as no cause is set, and for 7 days while data is still
    catching up."""
    now = utc(now)
    ids = (await db.execute(select(LoggerIncident.id).where(
        LoggerIncident.kind == "down",
        LoggerIncident.ended_at.is_not(None),
        or_(LoggerIncident.ended_at >= now - RECOMPUTE_WINDOW,
            LoggerIncident.cause.is_(None),
            and_(LoggerIncident.ended_at >= now - CATCH_UP_WINDOW,
                 # below 98%: boundary rounding alone misses a reading
                 LoggerIncident.data_recovered * 100 < LoggerIncident.data_expected * 98)),
    ))).scalars().all()
    for incident_id in ids:
        try:
            inc = await db.get(LoggerIncident, incident_id)
            await _settle_cause(db, inc)
            if inc.alert_id:
                alert = await db.get(Alert, inc.alert_id)
                if alert is not None and alert.status == "resolved":
                    _write_auto_note(alert, inc.cause_detail)
            await db.commit()
        except Exception:
            await db.rollback()
            applog.exception("working out the cause of logger incident %s failed", incident_id)


def _still_silent(hb: datetime | None, triggered: datetime) -> bool:
    """The logger has not reported since the alarm was raised."""
    return hb is None or hb <= triggered


async def import_down_history(db: AsyncSession, now: datetime) -> int:
    """First run only: the last 30 days of logger_down alarms become incidents.

    Resolved alarms become ended incidents. Of the unresolved ones, only the
    newest per site whose logger is still silent becomes the open incident;
    the rest are stale and get resolved, keeping any note a person wrote; the
    newest stale one per site is kept as an outage ending when its alarm was
    raised. Causes are left empty for recompute_causes to settle."""
    now = utc(now)
    if (await db.execute(select(LoggerIncident.id).limit(1))).first() is not None:
        return 0
    alerts = (await db.execute(select(Alert).where(
        Alert.category == LOGGER_CATEGORY, Alert.field == DOWN_FIELD,
        Alert.triggered_at >= now - timedelta(days=HISTORY_DAYS)).order_by(Alert.id))).scalars().all()
    heartbeats = {st.site_id: utc(st.last_heartbeat_at)
                  for st in (await db.execute(select(LoggerStatus))).scalars().all()}
    newest_open = {}
    for a in alerts:
        if a.status != "resolved":
            newest_open[a.site_id] = a.id   # ascending ids: the last one wins
    imported = 0
    for a in alerts:
        triggered = utc(a.triggered_at)
        start = triggered - timedelta(minutes=min(max(a.value or 0.0, 0.0), 1440.0))
        if a.status == "resolved":
            db.add(LoggerIncident(site_id=a.site_id, kind="down", started_at=start,
                                  ended_at=utc(a.resolved_at) or triggered, alert_id=a.id))
        elif newest_open.get(a.site_id) == a.id and _still_silent(heartbeats.get(a.site_id), triggered):
            db.add(LoggerIncident(site_id=a.site_id, kind="down", started_at=start,
                                  open_key=f"{a.site_id}:down", alert_id=a.id))
        else:
            # Stale: the logger has reported since, or this is an older duplicate of the same outage.
            a.status, a.resolved_at = "resolved", now
            newest = newest_open.get(a.site_id) == a.id
            if not a.followup_note:
                a.followup_note = (DUPLICATE_ALARM_NOTE if not newest and _still_silent(heartbeats.get(a.site_id), triggered)
                                   else STALE_ALARM_NOTE)
            if not newest:
                continue
            # It ended at an unknown time after the alarm: keep the outage up to the alarm (a lower
            # bound). That also leaves the table non-empty, so the import never runs twice.
            db.add(LoggerIncident(site_id=a.site_id, kind="down", started_at=start,
                                  ended_at=triggered, alert_id=a.id))
        imported += 1
    await db.commit()
    return imported
