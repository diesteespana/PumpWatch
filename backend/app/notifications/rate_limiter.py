"""
Per-user notification rate limiter backed by Redis.

Prevents a sudden burst of events from flooding a user's Telegram/email.
Uses a sliding window counter (Redis INCR + EXPIRE).

Default: 10 notifications per 5 minutes per user per channel.
Configurable per-user in Milestone 6+ (user settings endpoint).
"""
import redis.asyncio as aioredis

from app.core.logging import get_logger

logger = get_logger(__name__)

_KEY_TEMPLATE = "pumpwatch:rate_limit:notify:{user_id}:{channel}"
_DEFAULT_MAX = 10
_DEFAULT_WINDOW_SECONDS = 300  # 5 minutes


class NotificationRateLimiter:
    def __init__(
        self,
        redis_client: aioredis.Redis,
        max_per_window: int = _DEFAULT_MAX,
        window_seconds: int = _DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self._redis = redis_client
        self._max = max_per_window
        self._window = window_seconds

    async def is_allowed(self, user_id: str, channel: str) -> bool:
        """
        Return True if the user is under the rate limit for this channel.
        Increments the counter atomically; sets TTL on first call.
        """
        key = _KEY_TEMPLATE.format(user_id=user_id, channel=channel)

        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, self._window)

        if count > self._max:
            logger.warning(
                "notification_rate_limited",
                user=user_id,
                channel=channel,
                count=count,
                max=self._max,
            )
            return False
        return True

    async def get_remaining(self, user_id: str, channel: str) -> int:
        key = _KEY_TEMPLATE.format(user_id=user_id, channel=channel)
        count = await self._redis.get(key)
        current = int(count) if count else 0
        return max(0, self._max - current)
