"""
conftest.py
===========
Shared pytest fixtures for the ed-eval-service test suite.

Strategy
--------
* SQLite (in-process, async via aiosqlite) is used instead of PostgreSQL so
  tests can run without a live DB. We swap the engine/session via
  FastAPI's dependency_overrides mechanism.
* Redis is replaced with FakeAsyncRedis (fakeredis) so no real
  Redis server is needed in CI.

pytest-asyncio >=0.21 requires asyncio_mode = "auto", configured in pyproject.toml.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

# ── SQLite async engine (in-memory) ──────────────────────────────────────────

SQLITE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    SQLITE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


# ── Fake Redis (shared singleton) ─────────────────────────────────────────────

_fake_redis: FakeAsyncRedis | None = None


async def _get_fake_redis() -> FakeAsyncRedis:
    global _fake_redis
    if _fake_redis is None:
        _fake_redis = FakeAsyncRedis(decode_responses=True)
    return _fake_redis


# ── Session-scoped event loop ─────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ── Function-scoped HTTP client fixture ───────────────────────────────────────


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Returns an HTTPX AsyncClient wired to the FastAPI app with:
    - SQLite in-memory DB override
    - FakeRedis override (no real Redis server needed)
    """
    # Override DB dependency
    app.dependency_overrides[get_db] = override_get_db

    # Monkey-patch the Redis factory in the redis_client module
    import app.redis_client as rc_module

    _original_get_redis = rc_module.get_redis
    rc_module.get_redis = _get_fake_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    # Restore overrides
    app.dependency_overrides.clear()
    rc_module.get_redis = _original_get_redis


# ── Convenience helpers (not fixtures) ───────────────────────────────────────


async def _register_and_login(
    client: AsyncClient, email: str, password: str, full_name: str, role: str
) -> dict:
    """Register a user and return the JWT token dict."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role,
        },
    )
    assert reg.status_code == 201, reg.text

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login.json()


def auth_headers(token_data: dict) -> dict:
    return {"Authorization": f"Bearer {token_data['access_token']}"}
