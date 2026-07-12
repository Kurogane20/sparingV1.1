import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.anyio
async def test_healthz_ok(monkeypatch):
    # /healthz pings the DB via init_models(); stub it so the liveness check
    # doesn't require a reachable MySQL server in the test environment.
    async def _ok():
        return None
    monkeypatch.setattr("app.main.init_models", _ok)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/healthz")
    assert res.status_code == 200
    assert res.json()["ok"] is True


@pytest.mark.anyio
async def test_healthz_reports_unhealthy_on_db_failure(monkeypatch):
    async def _boom():
        raise RuntimeError("db down")
    monkeypatch.setattr("app.main.init_models", _boom)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/healthz")
    assert res.status_code == 503
    assert res.json()["ok"] is False
