from functools import lru_cache

import redis.asyncio as aioredis

from app.core.config import get_settings


@lru_cache
def get_redis_client() -> aioredis.Redis:
    """
    Singleton async Redis client.

    lru_cache ensures one connection pool per process.
    Call redis_client.aclose() on shutdown to drain gracefully.
    """
    settings = get_settings()
    return aioredis.from_url(
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )
