"""Unit tests for NotificationRateLimiter."""
import pytest
from unittest.mock import AsyncMock

from app.notifications.rate_limiter import NotificationRateLimiter


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    r.get = AsyncMock(return_value=None)
    return r


@pytest.fixture
def limiter(mock_redis):
    return NotificationRateLimiter(mock_redis, max_per_window=3, window_seconds=300)


@pytest.mark.asyncio
async def test_first_call_is_allowed(limiter, mock_redis):
    mock_redis.incr = AsyncMock(return_value=1)
    assert await limiter.is_allowed("user1", "telegram") is True


@pytest.mark.asyncio
async def test_sets_expire_on_first_call(limiter, mock_redis):
    mock_redis.incr = AsyncMock(return_value=1)
    await limiter.is_allowed("user1", "telegram")
    mock_redis.expire.assert_called_once_with(
        "pumpwatch:rate_limit:notify:user1:telegram", 300
    )


@pytest.mark.asyncio
async def test_expire_not_set_after_first(limiter, mock_redis):
    mock_redis.incr = AsyncMock(return_value=2)
    await limiter.is_allowed("user1", "telegram")
    mock_redis.expire.assert_not_called()


@pytest.mark.asyncio
async def test_at_limit_is_still_allowed(limiter, mock_redis):
    mock_redis.incr = AsyncMock(return_value=3)
    assert await limiter.is_allowed("user1", "telegram") is True


@pytest.mark.asyncio
async def test_over_limit_is_denied(limiter, mock_redis):
    mock_redis.incr = AsyncMock(return_value=4)
    assert await limiter.is_allowed("user1", "telegram") is False


@pytest.mark.asyncio
async def test_different_channels_are_independent(limiter, mock_redis):
    mock_redis.incr = AsyncMock(return_value=4)
    assert await limiter.is_allowed("user1", "email") is False
    # channel key must include the channel name
    call_key = mock_redis.incr.call_args[0][0]
    assert "email" in call_key


@pytest.mark.asyncio
async def test_remaining_count(limiter, mock_redis):
    mock_redis.get = AsyncMock(return_value="2")
    remaining = await limiter.get_remaining("user1", "telegram")
    assert remaining == 1
