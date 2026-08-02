"""Unit tests for EtherscanProvider — no real HTTP calls."""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.blockchain.providers.etherscan import EtherscanProvider
from app.core.exceptions import RateLimitedError


@pytest.fixture
def provider():
    return EtherscanProvider(api_key="test-key")


@pytest.fixture
def raw_tx():
    return {
        "hash": "0xabc",
        "blockNumber": "18000000",
        "timeStamp": "1700000000",
        "from": "0xSENDER",
        "to": "0xRECEIVER",
        "value": "1000000000000000000",
        "gasUsed": "21000",
        "gasPrice": "20000000000",
        "isError": "0",
        "input": "0x",
    }


def test_parse_transaction(provider, raw_tx):
    tx = provider._parse_transaction(raw_tx)
    assert tx.tx_hash == "0xabc"
    assert tx.value_wei == 10**18
    assert tx.from_address == "0xsender"
    assert not tx.is_error


@pytest.mark.asyncio
async def test_rate_limit_raises(provider):
    mock_response = {"message": "Max rate limit reached", "status": "0", "result": ""}
    with patch.object(provider, "_get", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(RateLimitedError):
            await provider.get_latest_block_number()


def test_requires_api_key():
    with pytest.raises(ValueError):
        EtherscanProvider(api_key="")
