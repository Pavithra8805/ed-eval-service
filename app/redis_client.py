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
import logging
import uuid
from typing import Any

import redis.asyncio as aioredis
from fakeredis import FakeAsyncRedis

from app.config import settings

logger = logging.getLogger("app.redis")

_redis_client: aioredis.Redis | FakeAsyncRedis | None = None

SESSION_CACHE_TTL = 300  # 5 minutes
EVAL_QUEUE_KEY = "eval_queue"


async def get_redis() -> aioredis.Redis | FakeAsyncRedis:
    global _redis_client
    if _redis_client is None:
        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=1.0,
            )
            await client.ping()
            _redis_client = client
        except Exception:
            logger.warning("Real Redis not available, using in-memory FakeRedis fallback")
            _redis_client = FakeAsyncRedis(decode_responses=True)
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None


# ── Session cache helpers ────────────────────────────────────────────────────


def _session_key(session_id: uuid.UUID | str) -> str:
    return f"session:{session_id}"


async def cache_session(session_id: uuid.UUID | str, data: dict[str, Any]) -> None:
    try:
        r = await get_redis()
        await r.setex(_session_key(session_id), SESSION_CACHE_TTL, json.dumps(data, default=str))
    except Exception as e:
        logger.warning(f"Redis cache write failed: {e}")


async def get_cached_session(session_id: uuid.UUID | str) -> dict[str, Any] | None:
    try:
        r = await get_redis()
        raw = await r.get(_session_key(session_id))
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.warning(f"Redis cache read failed: {e}")
        return None


async def invalidate_session_cache(session_id: uuid.UUID | str) -> None:
    try:
        r = await get_redis()
        await r.delete(_session_key(session_id))
    except Exception as e:
        logger.warning(f"Redis cache delete failed: {e}")


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
