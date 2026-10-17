import pytest

from app.models.models import User
from app.core.security import hash_password


async def _make_user(db, email="op@example.com", password="Secret123", role="operator"):
    db.add(User(name="Op", email=email, password_hash=hash_password(password),
                role=role, is_active=True))
    await db.commit()


@pytest.mark.anyio
async def test_login_success_returns_tokens(client, db_session):
    await _make_user(db_session)
    res = await client.post("/auth/login",
                            json={"email": "op@example.com", "password": "Secret123"})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_wrong_password_401(client, db_session):
    await _make_user(db_session)
    res = await client.post("/auth/login",
                            json={"email": "op@example.com", "password": "nope"})
    assert res.status_code == 401


@pytest.mark.anyio
async def test_login_unknown_email_401(client):
    res = await client.post("/auth/login",
                            json={"email": "ghost@example.com", "password": "whatever"})
    assert res.status_code == 401


@pytest.mark.anyio
async def test_me_requires_auth(client):
    res = await client.get("/auth/me")
    assert res.status_code == 401


@pytest.mark.anyio
async def test_me_returns_user_with_token(client, db_session):
    await _make_user(db_session, email="admin@example.com", role="admin")
    login = await client.post("/auth/login",
                              json={"email": "admin@example.com", "password": "Secret123"})
    token = login.json()["access_token"]
    res = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "admin@example.com"
    assert body["role"] == "admin"


async def _login_tokens(client, db_session, email):
    await _make_user(db_session, email=email)
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return res.json()


@pytest.mark.anyio
async def test_refresh_accepts_token_in_json_body(client, db_session):
    tokens = await _login_tokens(client, db_session, "body-refresh@example.com")

    res = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert res.status_code == 200
    assert res.json()["access_token"]


@pytest.mark.anyio
async def test_refresh_query_token_still_supported(client, db_session):
    tokens = await _login_tokens(client, db_session, "query-refresh@example.com")

    res = await client.post("/auth/refresh", params={"token": tokens["refresh_token"]})

    assert res.status_code == 200


@pytest.mark.anyio
async def test_refresh_reused_token_is_401(client, db_session):
    tokens = await _login_tokens(client, db_session, "reuse-refresh@example.com")
    first = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200

    second = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert second.status_code == 401


@pytest.mark.anyio
async def test_refresh_concurrent_rotation_is_401_not_500(client, db_session, monkeypatch):
    from sqlalchemy.exc import IntegrityError
    tokens = await _login_tokens(client, db_session, "race-refresh@example.com")

    async def duplicate_jti_commit():
        raise IntegrityError("INSERT INTO auth_token_blacklist", {}, Exception("Duplicate entry"))

    monkeypatch.setattr(db_session, "commit", duplicate_jti_commit)

    res = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert res.status_code == 401
