"""Unit tests for BlockTracker."""
import pytest
from unittest.mock import AsyncMock

from app.blockchain.block_tracker import BlockTracker, _LOOKBACK_BLOCKS


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def tracker(mock_redis):
    return BlockTracker(redis_client=mock_redis, chain="ethereum")


@pytest.mark.asyncio
async def test_cold_start_returns_lookback(tracker, mock_redis):
    mock_redis.get = AsyncMock(return_value=None)
    current = 18_000_000
    result = await tracker.get_last_processed_block(current)
    assert result == current - _LOOKBACK_BLOCKS


@pytest.mark.asyncio
async def test_returns_stored_block(tracker, mock_redis):
    mock_redis.get = AsyncMock(return_value="17_999_950")
    result = await tracker.get_last_processed_block(18_000_000)
    assert result == 17_999_950


@pytest.mark.asyncio
async def test_set_last_processed_block(tracker, mock_redis):
    mock_redis.set = AsyncMock()
    await tracker.set_last_processed_block(18_000_100)
    mock_redis.set.assert_called_once_with("pumpwatch:block_tracker:ethereum", "18000100")


@pytest.mark.asyncio
async def test_reset_deletes_key(tracker, mock_redis):
    mock_redis.delete = AsyncMock()
    await tracker.reset()
    mock_redis.delete.assert_called_once_with("pumpwatch:block_tracker:ethereum")
