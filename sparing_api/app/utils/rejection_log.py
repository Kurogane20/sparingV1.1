"""Persist refused device requests so the web can say why a logger's data is
not arriving (logger-diagnosis spec, Bagian 1).

device_auth.rejected() is synchronous and sits on the request path. It hands
the record to schedule_rejection, which writes it in a background task with its
own session. A failure is logged and swallowed: recording a refusal must never
change or delay the response the logger gets.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.models import DeviceRejection, Site
from app.utils.time import as_utc

NEW_RUN_AFTER = timedelta(hours=24)   # a refusal this long after the last one starts a new run
UID_LEN = 64            # DeviceRejection.uid and Site.uid are String(64)
MAX_UNKNOWN = 50        # new site-less rows (unknown uids) per NEW_RUN_AFTER window
MAX_PENDING = 32        # queued background writes; beyond this a flood is dropped

_pending: set[asyncio.Task] = set()                 # strong refs: an unreferenced task may be garbage-collected
_session_factory = None               # tests point this at their own engine
_unknown_cap_logged_at = None   # when the "cap reached" line was last logged
_pending_drop_logged_at = None


def set_session_factory(factory) -> None:
    """Tests only: write refusals through the test database (None = production)."""
    global _session_factory
    _session_factory = factory


def _factory():
    if _session_factory is not None:
        return _session_factory
    from app.core.db import SessionLocal
    return SessionLocal


def schedule_rejection(uid: str | None, source: str | None, reason: str, detail: str | None) -> None:
    """Record a refusal in the background. Never raises."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:              # called outside an event loop: nothing to record into
        return
    if len(_pending) >= MAX_PENDING:   # a flood must not queue unbounded work on the pool
        _log_drop_once()
        return
    task = loop.create_task(_record_safely(uid or "", source or "-", reason, detail))
    _pending.add(task)
    task.add_done_callback(_pending.discard)


async def flush_pending() -> None:
    """Wait for every scheduled record (tests, and the shutdown hook)."""
    while _pending:
        await asyncio.gather(*list(_pending), return_exceptions=True)


async def _record_safely(uid: str, source: str, reason: str, detail: str | None) -> None:
    try:
        async with _factory()() as db:
            await record_rejection(db, uid, source, reason, detail, datetime.now(timezone.utc))
    except Exception:
        logger.exception("could not record device rejection (uid=%.64s reason=%s)", uid, reason)


async def record_rejection(db: AsyncSession, uid: str, source: str, reason: str,
                           detail: str | None, now: datetime) -> None:
    """Count one refusal. The count is incremented in SQL, so concurrent refusals of the same key are counted; only two refusals deciding "new run" at the same instant can lose one."""
    uid = uid if isinstance(uid, str) else str(uid or "")
    site_id = None
    if uid and len(uid) <= UID_LEN:
        site_id = (await db.execute(select(Site.id).where(Site.uid == uid))).scalar_one_or_none()
    uid = uid[:UID_LEN]
    detail = detail[:255] if detail else None
    for _attempt in range(2):
        row = (await db.execute(select(DeviceRejection).where(
            DeviceRejection.uid == uid,
            DeviceRejection.source == source,
            DeviceRejection.reason == reason,
        ).execution_options(populate_existing=True))).scalars().first()
        if row is None:
            if site_id is None and await _unknown_cap_reached(db, now):
                _log_cap_once(uid, now)
                return
            db.add(DeviceRejection(uid=uid, site_id=site_id, source=source, reason=reason,
                                   first_at=now, last_at=now, count=1, last_detail=detail))
        else:
            # The increment happens in SQL so concurrent refusals of one key are all
            # counted; only the "new run" decision reads the row first.
            values = {"last_at": now, "last_detail": detail, "site_id": site_id,
                      "count": DeviceRejection.count + 1}
            if as_utc(row.last_at) < now - NEW_RUN_AFTER:
                values.update(first_at=now, count=1)
            await db.execute(update(DeviceRejection)
                             .where(DeviceRejection.id == row.id).values(**values))
        try:
            await db.commit()
            return
        except IntegrityError:
            # A concurrent request inserted the first row of this run; count on it.
            await db.rollback()
    logger.warning("device rejection not recorded after retry (uid=%s reason=%s)", uid, reason)


async def _unknown_cap_reached(db: AsyncSession, now: datetime) -> bool:
    """Unknown uids are attacker-choosable on public endpoints: cap how many
    new rows without a site one window may create. Known ones keep counting."""
    recent = (await db.execute(select(func.count()).select_from(DeviceRejection).where(
        DeviceRejection.site_id.is_(None),
        DeviceRejection.last_at >= now - NEW_RUN_AFTER,
    ))).scalar_one()
    return recent >= MAX_UNKNOWN


def _log_cap_once(uid: str, now: datetime) -> None:
    global _unknown_cap_logged_at
    if _unknown_cap_logged_at is None or now - _unknown_cap_logged_at >= NEW_RUN_AFTER:
        _unknown_cap_logged_at = now
        logger.warning("device rejections: %d uids without a site in 24 h; not recording new ones (e.g. uid=%s)",
                       MAX_UNKNOWN, uid)


def _log_drop_once() -> None:
    global _pending_drop_logged_at
    now = datetime.now(timezone.utc)
    if _pending_drop_logged_at is None or now - _pending_drop_logged_at >= NEW_RUN_AFTER:
        _pending_drop_logged_at = now
        logger.warning("device rejections: %d writes already queued; dropping new ones", MAX_PENDING)
