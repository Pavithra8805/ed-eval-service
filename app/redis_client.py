"""
Redis integration — two responsibilities:

1. Hot-read cache  : session objects are cached under `session:<id>` with a
                     configurable TTL (default 5 min).  Cache is invalidated
                     on every write / delete.

2. Evaluation queue: evaluation-trigger requests are pushed onto the Redis
                     list `eval_queue`.  The background worker pops from the
                     same list and processes jobs.
"""

import json
import uuid
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

# ── Shared async Redis client ────────────────────────────────────────────────

_redis_client: aioredis.Redis | None = None

SESSION_CACHE_TTL = 300  # 5 minutes
EVAL_QUEUE_KEY = "eval_queue"


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


# ── Session cache helpers ────────────────────────────────────────────────────

def _session_key(session_id: uuid.UUID | str) -> str:
    return f"session:{session_id}"


async def cache_session(session_id: uuid.UUID | str, data: dict[str, Any]) -> None:
    r = await get_redis()
    await r.setex(_session_key(session_id), SESSION_CACHE_TTL, json.dumps(data, default=str))


async def get_cached_session(session_id: uuid.UUID | str) -> dict[str, Any] | None:
    r = await get_redis()
    raw = await r.get(_session_key(session_id))
    return json.loads(raw) if raw else None


async def invalidate_session_cache(session_id: uuid.UUID | str) -> None:
    r = await get_redis()
    await r.delete(_session_key(session_id))


# ── Evaluation queue helpers ─────────────────────────────────────────────────

async def enqueue_evaluation(evaluation_id: uuid.UUID | str) -> None:
    r = await get_redis()
    await r.rpush(EVAL_QUEUE_KEY, str(evaluation_id))


async def dequeue_evaluation(timeout: int = 5) -> str | None:
    """Blocking pop with timeout — returns evaluation_id string or None."""
    r = await get_redis()
    result = await r.blpop(EVAL_QUEUE_KEY, timeout=timeout)
    if result:
        _, value = result
        return value
    return None
