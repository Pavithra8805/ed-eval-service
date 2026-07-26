"""
FastAPI application entry point.

Lifespan:
  - Opens Redis connection on startup
  - Creates all tables (for dev/test convenience; prod uses Alembic)
  - Closes Redis on shutdown
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, evaluations, sessions
from app.database import Base, engine
from app.redis_client import close_redis, get_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # startup
    await get_redis()  # warm up Redis connection
    # (In production, use Alembic migrations — do NOT create_all in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # shutdown
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="ed-eval-service",
    description=(
        "Education Evaluation Service — FastAPI backend with PostgreSQL, Redis, "
        "and role-based access control for the Bodhrik assessment."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────

PREFIX = "/api/v1"

app.include_router(auth.router, prefix=PREFIX)
app.include_router(sessions.router, prefix=PREFIX)
app.include_router(evaluations.router, prefix=PREFIX)


# ── Health check ─────────────────────────────────────────────────────────────


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "service": "ed-eval-service"}
