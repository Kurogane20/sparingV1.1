"""Async test harness: an in-memory SQLite DB and an httpx client wired to the
FastAPI app with the get_db dependency overridden.

Uses SQLite (not MySQL) so the suite runs anywhere with no external services.
Tables are created from the models directly (Base.metadata.create_all) rather
than via Alembic.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
# Importing app.main pulls in every router, which imports the models — so
# Base.metadata is fully populated (all tables) by the time create_all runs.
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared connection keeps the in-memory DB alive
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestSession = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with TestSession() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    # Unique client IP per test: the login RateLimitMiddleware keys its
    # process-global bucket by client host, so a shared IP makes the whole
    # suite's logins share one 10/min budget and later tests 429.
    import uuid
    transport = ASGITransport(app=app, client=(f"test-{uuid.uuid4().hex[:8]}", 123))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
