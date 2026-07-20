import jwt
import pytest
from fastapi import HTTPException

from app.models.models import Site
from app.utils.device_auth import verify_device_token


async def _site(db, uid="DEV-1", secret="s3cret"):
    s = Site(uid=uid, name="T", company_name="C", is_active=True, device_secret=secret)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest.mark.anyio
async def test_valid_token_returns_site_and_payload(db_session):
    await _site(db_session)
    token = jwt.encode({"uid": "DEV-1", "hello": "world"}, "s3cret", algorithm="HS256")
    site, payload = await verify_device_token(token, db_session)
    assert site.uid == "DEV-1"
    assert payload["hello"] == "world"


@pytest.mark.anyio
async def test_wrong_secret_rejected(db_session):
    await _site(db_session)
    token = jwt.encode({"uid": "DEV-1"}, "WRONG", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        await verify_device_token(token, db_session)
    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_unknown_uid_401(db_session):
    token = jwt.encode({"uid": "NOPE"}, "s3cret", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        await verify_device_token(token, db_session)
    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_missing_token_400(db_session):
    with pytest.raises(HTTPException) as exc:
        await verify_device_token("", db_session)
    assert exc.value.status_code == 400
