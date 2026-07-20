"""Device-JWT verification shared by every device-facing endpoint.

The scheme (unchanged from /api/post-data): the request body carries
{"token": "<jwt>"}; the JWT payload holds the actual data and a `uid`; the
signature is verified with that site's device_secret (falling back to the
global getdata secret). Extracted here so heartbeat/event endpoints cannot
drift from the data endpoint's auth.
"""
import jwt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Site


def global_secret() -> str:
    return settings.getdata_secret


async def verify_device_token(token: str, db: AsyncSession) -> tuple[Site, dict]:
    """Return (site, decoded_payload) or raise HTTPException."""
    if not token:
        raise HTTPException(400, "Token is required")
    try:
        unverified = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["HS256"],
        )
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid token format")

    uid = unverified.get("uid")
    if not uid:
        raise HTTPException(400, "Invalid data format")

    site = (await db.execute(select(Site).where(Site.uid == uid))).scalar_one_or_none()
    if not site:
        raise HTTPException(401, "Invalid UID")

    signing_secret = site.device_secret or global_secret()
    try:
        decoded = jwt.decode(token, signing_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(400, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid token format")
    return site, decoded
