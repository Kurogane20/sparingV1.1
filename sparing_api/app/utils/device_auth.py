"""Device-JWT verification shared by every device-facing endpoint.

The scheme (unchanged from /api/post-data): the request body carries
{"token": "<jwt>"}; the JWT payload holds the actual data and a `uid`; the
signature is verified with that site's device_secret (falling back to the
global getdata secret). Extracted here so heartbeat/event endpoints cannot
drift from the data endpoint's auth.

Every rejection is logged with a reason code: the logger only sees the HTTP
status, and without this a site losing most of its data (PKN2-LOG, 2026-10)
could only be diagnosed from response sizes in nginx's log.
"""
from datetime import datetime, timezone

import jwt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.models import Site


def global_secret() -> str:
    return settings.getdata_secret


def _utc(epoch) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _claims_context(claims: dict | None) -> list[str]:
    """What the rejected token carried — never the token or a secret."""
    if not isinstance(claims, dict):
        return []
    parts = []
    data = claims.get("data")
    if isinstance(data, list):
        parts.append(f"n={len(data)}")
        epochs = []
        for d in data:
            try:
                epoch = int(d.get("datetime", 0)) if isinstance(d, dict) else 0
            except (TypeError, ValueError):
                epoch = 0
            if epoch > 0:
                epochs.append(epoch)
        if epochs:
            parts.append(f"data={_utc(min(epochs))}..{_utc(max(epochs))}")
    for key in ("iat", "exp"):
        if isinstance(claims.get(key), (int, float)):
            parts.append(f"{key}={_utc(claims[key])}")
    return parts


def rejected(status_code: int, detail: str, reason: str, source: str | None,
             uid: str | None = None, claims: dict | None = None, **extra) -> HTTPException:
    """Log a refused device request and return the exception to raise."""
    parts = [f"source={source or '-'}", f"reason={reason}", f"uid={uid or '-'}"]
    parts += _claims_context(claims)
    parts += [f"{k}={v}" for k, v in extra.items()]
    logger.warning("device request rejected: " + " ".join(parts))
    return HTTPException(status_code, detail)


def _signs_with(token: str, secret: str) -> bool:
    try:
        jwt.decode(token, secret, algorithms=["HS256"], options={"verify_exp": False})
        return True
    except jwt.InvalidTokenError:
        return False


async def verify_device_token(token: str, db: AsyncSession,
                              source: str | None = None) -> tuple[Site, dict]:
    """Return (site, decoded_payload) or raise HTTPException."""
    if not token:
        raise rejected(400, "Token is required", "missing_token", source)
    try:
        unverified = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["HS256"],
        )
    except jwt.InvalidTokenError:
        raise rejected(400, "Invalid token format", "malformed", source)

    uid = unverified.get("uid")
    if not uid:
        raise rejected(400, "Invalid data format", "no_uid", source, claims=unverified)

    site = (await db.execute(select(Site).where(Site.uid == uid))).scalar_one_or_none()
    if not site:
        raise rejected(401, "Invalid UID", "unknown_uid", source, uid, unverified)

    signing_secret = site.device_secret or global_secret()
    try:
        decoded = jwt.decode(token, signing_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise rejected(400, "Token expired", "expired", source, uid, unverified)
    except jwt.InvalidTokenError:
        # Tells "signed with the old shared default" apart from "signed with a
        # key the server no longer has" (e.g. queued before a secret rotation).
        extra = {}
        if site.device_secret:
            extra["global_secret_ok"] = "yes" if _signs_with(token, global_secret()) else "no"
        raise rejected(400, "Invalid token format", "bad_signature", source, uid, unverified, **extra)
    return site, decoded
