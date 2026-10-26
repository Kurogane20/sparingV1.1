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


# The API used to reject device posts silently: PKN2-LOG got ~32 400s/hour and
# the reason could only be guessed from the response size in nginx's log.

def _rejection_log(caplog):
    lines = [r.getMessage() for r in caplog.records if "device request rejected" in r.getMessage()]
    assert len(lines) == 1, lines
    return lines[0]


@pytest.mark.anyio
async def test_bad_signature_is_logged_with_safe_context(db_session, caplog):
    await _site(db_session)
    readings = [{"datetime": 1792454400, "ph": 7}, {"datetime": 1792457880, "ph": 7}]
    token = jwt.encode({"uid": "DEV-1", "data": readings}, "OLD-KEY", algorithm="HS256")

    with pytest.raises(HTTPException):
        await verify_device_token(token, db_session, source="post-data")

    line = _rejection_log(caplog)
    assert "source=post-data" in line
    assert "reason=bad_signature" in line
    assert "uid=DEV-1" in line
    assert "n=2" in line
    assert "data=2026-10-20T00:00Z..2026-10-20T00:58Z" in line
    assert "global_secret_ok=no" in line
    for secret in ("s3cret", "OLD-KEY", token):
        assert secret not in line


@pytest.mark.anyio
async def test_token_signed_with_global_secret_is_flagged(db_session, caplog, monkeypatch):
    monkeypatch.setattr("app.utils.device_auth.settings.getdata_secret", "global-key")
    await _site(db_session)
    token = jwt.encode({"uid": "DEV-1"}, "global-key", algorithm="HS256")

    with pytest.raises(HTTPException):
        await verify_device_token(token, db_session)

    assert "global_secret_ok=yes" in _rejection_log(caplog)


@pytest.mark.anyio
async def test_malformed_and_unknown_uid_are_logged(db_session, caplog):
    with pytest.raises(HTTPException):
        await verify_device_token("not-a-jwt", db_session)
    assert "reason=malformed" in _rejection_log(caplog)

    caplog.clear()
    with pytest.raises(HTTPException):
        await verify_device_token(jwt.encode({"uid": "NOPE"}, "x", algorithm="HS256"), db_session)
    line = _rejection_log(caplog)
    assert "reason=unknown_uid" in line and "uid=NOPE" in line


@pytest.mark.anyio
async def test_expired_token_is_logged(db_session, caplog):
    await _site(db_session)
    token = jwt.encode({"uid": "DEV-1", "exp": 1700000000}, "s3cret", algorithm="HS256")

    with pytest.raises(HTTPException) as exc:
        await verify_device_token(token, db_session)

    assert exc.value.detail == "Token expired"
    assert "reason=expired" in _rejection_log(caplog)
