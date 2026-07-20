"""Logger telemetry ingest.

Liveness is always judged on the SERVER clock (last_heartbeat_at), never on the
logger-reported timestamp — a Pi with a skewed clock must not look alive or dead
incorrectly.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_viewer_site_uids
from app.core.db import get_db
from app.models.models import LoggerStatus, Site, User
from app.schemas.logger import LoggerEventOut, LoggerStatusOut
from app.utils.device_auth import verify_device_token

router = APIRouter()

_STATUS_FIELDS = (
    "logger_version", "uptime_s", "op_status", "ph_ok", "tss_ok", "debit_ok",
    "cod_ok", "nh3n_ok", "consec_fail", "internet_ok", "last_send_ok_mm",
    "last_send_ok_klhk", "buffer_depth", "daily_sent", "cpu_temp", "cpu_pct",
    "mem_pct", "disk_pct",
)
_SENSOR_OK_FIELDS = ("ph_ok", "tss_ok", "debit_ok", "cod_ok", "nh3n_ok")


@router.post("/heartbeat")
async def heartbeat(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    site, payload = await verify_device_token(body.get("token") or "", db)
    status = payload.get("status") or {}
    if not isinstance(status, dict):
        raise HTTPException(400, "Invalid data format")

    now = datetime.now(timezone.utc)
    st = (await db.execute(
        select(LoggerStatus).where(LoggerStatus.site_id == site.id).limit(1)
    )).scalars().first()
    if st is None:
        st = LoggerStatus(site_id=site.id, state="alive", state_since=now)
        db.add(st)
    was_down = st.state == "down"

    for f in _STATUS_FIELDS:
        if f in status:
            setattr(st, f, status[f])
    st.last_heartbeat_at = now

    # Remember when a sensor FIRST started failing; the alarm logic measures
    # duration from here, so a continuing failure must not reset it.
    any_failed = any(getattr(st, f) is False for f in _SENSOR_OK_FIELDS)
    sensors_recovered = bool(st.sensor_fail_since) and not any_failed
    if any_failed:
        if st.sensor_fail_since is None:
            st.sensor_fail_since = now
    else:
        st.sensor_fail_since = None

    if was_down:
        st.state = "alive"
        st.state_since = now
    await db.commit()

    if was_down:
        from app.utils.logger_monitor import resolve_logger_down_alert
        await resolve_logger_down_alert(db, site.id, now)
    if sensors_recovered:
        from app.utils.logger_monitor import resolve_sensor_alerts
        await resolve_sensor_alerts(db, site.id, now)
    return {"ok": True, "state": st.state}


MAX_EVENT_BATCH = 200
_KNOWN_EVENT_TYPES = {
    "started", "stopping", "stopped", "sensor_fail", "sensor_recover",
    "net_down", "net_up", "send_fail", "opstatus_change", "buffer_high",
}


@router.post("/events")
async def ingest_events(request: Request, db: AsyncSession = Depends(get_db)):
    """Batch-insert logger events.

    (site_id, event_uid) is the idempotency key so a logger that re-uploads after
    a reconnect cannot create duplicates — and, crucially, so a uid emitted by a
    cloned logger at another site can never suppress this site's event. Do not
    "optimise" the lookup to event_uid alone.
    """
    from app.models.models import LoggerEvent

    body = await request.json()
    site, payload = await verify_device_token(body.get("token") or "", db)
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        raise HTTPException(400, "Invalid data format")
    if len(events) > MAX_EVENT_BATCH:
        raise HTTPException(400, f"Batch too large (max {MAX_EVENT_BATCH})")

    now = datetime.now(timezone.utc)
    uids = [e.get("event_uid") for e in events if e.get("event_uid")]
    seen = set()
    if uids:
        seen = set((await db.execute(
            select(LoggerEvent.event_uid).where(
                LoggerEvent.site_id == site.id,        # per-site scope — do not remove
                LoggerEvent.event_uid.in_(uids),
            )
        )).scalars().all())

    accepted = 0
    duplicates = 0
    for e in events:
        uid = e.get("event_uid")
        etype = e.get("type")
        if not uid or not etype:
            continue
        if uid in seen:
            duplicates += 1
            continue
        try:
            ts = datetime.fromtimestamp(int(e.get("ts") or 0), tz=timezone.utc)
        except (TypeError, ValueError, OSError, OverflowError):
            ts = now
        db.add(LoggerEvent(
            site_id=site.id, event_uid=uid,
            # Unknown types are stored, never dropped: losing an audit record is
            # worse than storing one we don't yet have a label for.
            type=etype if etype in _KNOWN_EVENT_TYPES else "unknown",
            ts=ts, received_at=now,
            severity=e.get("severity") or "info",
            detail=e.get("detail"),
        ))
        seen.add(uid)   # also guards duplicates inside the same batch
        accepted += 1
    await db.commit()
    return {"ok": True, "accepted": accepted, "duplicates": duplicates}


# ── Web-facing read endpoints (viewer-scoped) ──────────────────────────


async def _scoped_site_ids(db: AsyncSession, viewer_uids: list[str]) -> "list[int] | None":
    """None = no restriction (admin/operator); a list = the viewer's sites only."""
    if not viewer_uids:
        return None
    return list((await db.execute(
        select(Site.id).where(Site.uid.in_(viewer_uids))
    )).scalars().all())


@router.get("/status", response_model=list[LoggerStatusOut])
async def list_logger_status(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    scoped = await _scoped_site_ids(db, viewer_uids)
    if scoped is not None and not scoped:
        return []
    q = select(LoggerStatus, Site).join(Site, Site.id == LoggerStatus.site_id)
    if scoped is not None:
        q = q.where(LoggerStatus.site_id.in_(scoped))

    now = datetime.now(timezone.utc)
    out = []
    for st, site in (await db.execute(q)).all():
        last = st.last_heartbeat_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)   # MySQL returns naive UTC
        mins = None if last is None else round((now - last).total_seconds() / 60, 2)
        out.append(LoggerStatusOut(
            site_id=site.id, site_uid=site.uid, site_name=site.name,
            state=st.state, state_since=st.state_since,
            last_heartbeat_at=st.last_heartbeat_at, minutes_since_heartbeat=mins,
            **{f: getattr(st, f) for f in _STATUS_FIELDS},
        ))
    return out


@router.get("/events")
async def list_logger_events(
    site_uid: str | None = Query(default=None),
    type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    page: int | None = Query(default=None, ge=1),
    per_page: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    """Bare list when `page` is absent; {items,total,page,per_page} when given."""
    from app.models.models import LoggerEvent

    scoped = await _scoped_site_ids(db, viewer_uids)
    empty = {"items": [], "total": 0, "page": page, "per_page": per_page} if page else []
    if scoped is not None and not scoped:
        return empty

    conds = []
    if scoped is not None:
        conds.append(LoggerEvent.site_id.in_(scoped))
    if site_uid:
        s = (await db.execute(select(Site).where(Site.uid == site_uid))).scalars().first()
        if not s:
            return empty
        conds.append(LoggerEvent.site_id == s.id)
    if type:
        conds.append(LoggerEvent.type == type)
    if severity:
        conds.append(LoggerEvent.severity == severity)
    if date_from:
        conds.append(LoggerEvent.ts >= date_from)
    if date_to:
        conds.append(LoggerEvent.ts < date_to)

    base = (select(LoggerEvent, Site).join(Site, Site.id == LoggerEvent.site_id)
            .where(*conds).order_by(LoggerEvent.ts.desc()))

    def _out(ev, site):
        return LoggerEventOut(
            id=ev.id, site_id=site.id, site_uid=site.uid, site_name=site.name,
            event_uid=ev.event_uid, type=ev.type, ts=ev.ts, received_at=ev.received_at,
            severity=ev.severity, detail=ev.detail,
        )

    if page is None:
        rows = (await db.execute(base.limit(limit))).all()
        return [_out(ev, site) for ev, site in rows]

    total = (await db.execute(select(func.count(LoggerEvent.id)).where(*conds))).scalar_one()
    rows = (await db.execute(base.offset((page - 1) * per_page).limit(per_page))).all()
    return {"items": [_out(ev, site) for ev, site in rows],
            "total": total, "page": page, "per_page": per_page}
