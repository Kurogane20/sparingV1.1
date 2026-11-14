"""Persist refused device requests so the web can say why a logger's data is
not arriving (logger-diagnosis spec, Bagian 1).

device_auth.rejected() is synchronous and sits on the request path. It hands
the record to schedule_rejection, which writes it in a background task with its
own session. A failure is logged and swallowed: recording a refusal must never
change or delay the response the logger gets.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.models import DeviceRejection, Site
from app.utils.time import as_utc

NEW_RUN_AFTER = timedelta(hours=24)   # a refusal this long after the last one starts a new run

_pending: set = set()                 # strong refs: an unreferenced task may be garbage-collected
_session_factory = None               # tests point this at their own engine


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
    task = loop.create_task(_record_safely(uid or "", source or "-", reason, detail))
    _pending.add(task)
    task.add_done_callback(_pending.discard)


async def flush_pending() -> None:
    """Wait for every scheduled record (tests)."""
    while _pending:
        await asyncio.gather(*list(_pending), return_exceptions=True)


async def _record_safely(uid: str, source: str, reason: str, detail: str | None) -> None:
    try:
        async with _factory()() as db:
            await record_rejection(db, uid, source, reason, detail, datetime.now(timezone.utc))
    except Exception:
        logger.exception("could not record device rejection (uid=%s reason=%s)", uid, reason)


async def record_rejection(db: AsyncSession, uid: str, source: str, reason: str,
                           detail: str | None, now: datetime) -> None:
    site_id = None
    if uid:
        site_id = (await db.execute(select(Site.id).where(Site.uid == uid))).scalar_one_or_none()
    detail = detail[:255] if detail else None
    for _attempt in range(2):
        row = (await db.execute(select(DeviceRejection).where(
            DeviceRejection.uid == uid,
            DeviceRejection.source == source,
            DeviceRejection.reason == reason,
        ))).scalars().first()
        if row is None:
            db.add(DeviceRejection(uid=uid, site_id=site_id, source=source, reason=reason,
                                   first_at=now, last_at=now, count=1, last_detail=detail))
        else:
            if as_utc(row.last_at) < now - NEW_RUN_AFTER:
                row.first_at, row.count = now, 1
            else:
                row.count += 1
            row.last_at, row.last_detail, row.site_id = now, detail, site_id
        try:
            await db.commit()
            return
        except IntegrityError:
            # A concurrent request inserted the first row of this run; count on it.
            await db.rollback()
    logger.warning("device rejection not recorded after retry (uid=%s reason=%s)", uid, reason)
