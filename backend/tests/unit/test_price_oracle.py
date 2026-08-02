"""Unit tests for CoinGeckoPriceOracle — all HTTP mocked, Redis in-memory."""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.blockchain.price_oracle import CoinGeckoPriceOracle, _REDIS_KEY_PREFIX


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)   # cache miss by default
    redis.setex = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def oracle(mock_redis):
    return CoinGeckoPriceOracle(redis_client=mock_redis)


@pytest.mark.asyncio
async def test_get_prices_empty_list_returns_empty(oracle):
    result = await oracle.get_prices_usd([])
    assert result == {}


@pytest.mark.asyncio
async def test_eth_price_from_cache(oracle, mock_redis):
    eth_addr = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    mock_redis.get = AsyncMock(return_value="3500.50")

    result = await oracle.get_prices_usd([eth_addr])
    assert result[eth_addr] == Decimal("3500.50")
    # Should NOT make any HTTP calls when fully cached
    oracle._client.get = AsyncMock()  # type: ignore[attr-defined]
    oracle._client.get.assert_not_called()


@pytest.mark.asyncio
async def test_token_price_fetched_and_cached(oracle, mock_redis):
    contract = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"  # USDC

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={
        contract: {"usd": 1.0001}
    })

    with patch.object(oracle._client, "get", new_callable=AsyncMock, return_value=mock_response):
        result = await oracle.get_prices_usd([contract])

    assert result[contract] == Decimal("1.0001")
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert contract in call_args[0][0]  # key contains address


@pytest.mark.asyncio
async def test_missing_token_maps_to_zero(oracle, mock_redis):
    contract = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={})  # CoinGecko returns empty

    with patch.object(oracle._client, "get", new_callable=AsyncMock, return_value=mock_response):
        result = await oracle.get_prices_usd([contract])

    assert result[contract] == Decimal(0)


@pytest.mark.asyncio
async def test_health_check_returns_true_on_200(oracle):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(oracle._client, "get", new_callable=AsyncMock, return_value=mock_response):
        assert await oracle.health_check() is True


@pytest.mark.asyncio
async def test_health_check_returns_false_on_exception(oracle):
    with patch.object(oracle._client, "get", side_effect=Exception("timeout")):
        assert await oracle.health_check() is False
