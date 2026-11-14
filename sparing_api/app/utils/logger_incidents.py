"""Logger incidents: gather the diagnosis inputs, open and close incidents, and
keep their alarms in step (logger-diagnosis spec, Bagian 1 and 3).

Called by the liveness scan every 2 minutes and by the heartbeat recovery path.
An incident is opened by INSERTing its open_key ("<site_id>:<kind>"). The UNIQUE
index makes a second, concurrent open fail, and only the process whose INSERT
won raises the alarm, so an incident and its alarm exist at most once.
"""
import math
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger as applog
from app.models.models import (Alert, DeviceRejection, LoggerEvent, LoggerIncident,
                               LoggerStatus, SensorData, Site)
from app.utils.logger_diagnosis import (ALIVE_ONLY_KINDS, CONCURRENT_WINDOW, DOWN_AFTER, EVIDENCE_SLACK,
                                        RECENT, SiteInputs, diagnose, heartbeat_alive, infer_cause, utc)

LOGGER_CATEGORY = "logger"
DOWN_FIELD = "logger_down"
OPEN_ALERT = ("active", "acknowledged")
RECOMPUTE_WINDOW = timedelta(hours=24)
HISTORY_DAYS = 30
AUTO_NOTE_PREFIX = "Pulih otomatis: "
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
    out = {}
    for column in STATUS_COLUMNS:
        value = getattr(st, column)
        out[column] = utc(value) if isinstance(value, datetime) else value
    return out


async def _events(db: AsyncSession, site_id: int, start: datetime, end: datetime | None = None) -> list:
    q = select(LoggerEvent).where(LoggerEvent.site_id == site_id, LoggerEvent.ts >= start)
    if end is not None:
        q = q.where(LoggerEvent.ts <= end)
    rows = (await db.execute(q.order_by(LoggerEvent.ts))).scalars().all()
    return [{"type": e.type, "ts": utc(e.ts), "detail": e.detail, "received_at": utc(e.received_at)}
            for e in rows]


async def load_site_inputs(db: AsyncSession, now: datetime) -> list[SiteInputs]:
    """One SiteInputs per active site, including sites that never sent a heartbeat."""
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
        # Events from 24 h before the logger fell silent (or before now) feed the hints.
        events = await _events(db, s.id, min(now, hb or now) - timedelta(hours=24))
        out.append(SiteInputs(
            site_id=s.id, uid=s.uid, name=s.name, timezone=s.timezone or "Asia/Jakarta",
            status=None if st is None else _status_dict(st),
            last_data_ts=last_data.get(s.id), last_ingest_at=utc(s.last_ingest_at),
            events=events, rejections=rejections.get(s.id, []),
            open_kinds=open_kinds.get(s.id, set()), concurrent_down=concurrent(s.id),
        ))
    return out


async def open_incident(db: AsyncSession, site_id: int, kind: str, started_at: datetime,
                        now: datetime, finding: dict) -> LoggerIncident | None:
    """Open an incident and its alarm; None when another process opened it first."""
    await db.commit()   # nothing else may be lost to the rollback below
    inc = LoggerIncident(site_id=site_id, kind=kind, started_at=started_at,
                         open_key=f"{site_id}:{kind}", evidence={"title": finding["title"]})
    db.add(inc)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return None
    alert = None
    if kind == "down":
        # An alarm raised before incidents existed is adopted, not duplicated.
        alert = (await db.execute(select(Alert).where(
            Alert.site_id == site_id, Alert.category == LOGGER_CATEGORY, Alert.field == DOWN_FIELD,
            Alert.status.in_(OPEN_ALERT)).order_by(Alert.id.desc()).limit(1))).scalars().first()
    if alert is None:
        minutes = round((utc(now) - utc(started_at)).total_seconds() / 60, 1) if kind == "down" else 0.0
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
        concurrent = (await db.execute(select(func.count(func.distinct(LoggerIncident.site_id))).where(
            LoggerIncident.kind == "down",
            LoggerIncident.started_at >= start - CONCURRENT_WINDOW,
            LoggerIncident.started_at <= start + CONCURRENT_WINDOW))).scalar_one()
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
    """End an incident, settle its cause, and resolve its alarm with that cause."""
    inc.ended_at = now
    inc.open_key = None
    await _settle_cause(db, inc, ended_by)
    if inc.alert_id:
        alert = await db.get(Alert, inc.alert_id)
        if alert is not None and alert.status in OPEN_ALERT:
            alert.status, alert.resolved_at = "resolved", now
            alert.followup_note = AUTO_NOTE_PREFIX + inc.cause_detail
    await db.commit()


async def close_open_incident(db: AsyncSession, site_id: int, kind: str, now: datetime) -> None:
    inc = (await db.execute(select(LoggerIncident).where(
        LoggerIncident.open_key == f"{site_id}:{kind}"))).scalars().first()
    if inc is not None:
        await close_incident(db, inc, now)


def _since(finding: dict, now: datetime) -> datetime:
    return datetime.fromisoformat(finding["since"]) if finding.get("since") else now


async def sync_incidents(db: AsyncSession, now: datetime) -> None:
    """Diagnose every active site; open incidents for new findings and close the
    ones whose finding has gone."""
    for inp in await load_site_inputs(db, now):
        try:
            row = diagnose(inp, now)
        except Exception:
            applog.exception("logger diagnosis failed for %s", inp.uid)
            continue
        wanted = {f["kind"]: f for f in row["findings"] if f["kind"]}
        alive = heartbeat_alive(inp, now)
        open_rows = (await db.execute(select(LoggerIncident).where(
            LoggerIncident.site_id == inp.site_id, LoggerIncident.open_key.is_not(None)))).scalars().all()
        for inc in open_rows:
            if inc.kind in wanted:
                continue
            if inc.kind in ALIVE_ONLY_KINDS and not alive:
                # Judged from the heartbeat: neither confirmed nor cleared while it is silent,
                # so an outage does not close (and later reopen) a KLHK or disk alarm.
                continue
            ended_by = "no_telemetry" if inc.kind == "down" and "no_telemetry" in wanted else None
            await close_incident(db, inc, now, ended_by)
        already = {inc.kind for inc in open_rows}
        for kind, finding in wanted.items():
            if kind not in already:
                await open_incident(db, inp.site_id, kind, _since(finding, now), now, finding)


async def recompute_causes(db: AsyncSession, now: datetime) -> None:
    """Events reach the server after the logger reconnects, so the causes of
    incidents that ended in the last 24 h (and any not yet settled) are redone."""
    rows = (await db.execute(select(LoggerIncident).where(
        LoggerIncident.ended_at.is_not(None),
        or_(LoggerIncident.ended_at >= now - RECOMPUTE_WINDOW, LoggerIncident.cause.is_(None)),
    ))).scalars().all()
    for inc in rows:
        await _settle_cause(db, inc)
        if inc.alert_id:
            alert = await db.get(Alert, inc.alert_id)
            if alert is not None and (alert.followup_note or "").startswith(AUTO_NOTE_PREFIX):
                alert.followup_note = AUTO_NOTE_PREFIX + inc.cause_detail
    await db.commit()


async def import_down_history(db: AsyncSession, now: datetime) -> int:
    """First run only: the last 30 days of logger_down alarms become incidents.

    Of the alarms still open, only the newest per site becomes the open
    incident; older duplicates (raised twice before incidents existed) are
    skipped. Causes are left empty for recompute_causes to settle."""
    if (await db.execute(select(LoggerIncident.id).limit(1))).first() is not None:
        return 0
    alerts = (await db.execute(select(Alert).where(
        Alert.category == LOGGER_CATEGORY, Alert.field == DOWN_FIELD,
        Alert.triggered_at >= now - timedelta(days=HISTORY_DAYS)).order_by(Alert.id))).scalars().all()
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
        elif newest_open.get(a.site_id) == a.id:
            db.add(LoggerIncident(site_id=a.site_id, kind="down", started_at=start,
                                  open_key=f"{a.site_id}:down", alert_id=a.id))
        else:
            continue
        imported += 1
    await db.commit()
    return imported
