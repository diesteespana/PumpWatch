"""Unit tests for EthereumChainService."""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.blockchain.address_registry import AddressRegistry
from app.blockchain.block_tracker import BlockTracker
from app.blockchain.chain_service import EthereumChainService
from app.blockchain.interfaces import RawTransaction, TokenTransfer


def make_raw_tx(**kwargs) -> RawTransaction:
    defaults = dict(
        tx_hash="0xabc",
        block_number=18_000_010,
        timestamp=datetime.now(tz=timezone.utc),
        from_address="0xsender",
        to_address="0xreceiver",
        value_wei=5 * 10**18,  # 5 ETH
        gas_used=21_000,
        gas_price_wei=20_000_000_000,
        is_error=False,
        input_data="0x",
    )
    return RawTransaction(**{**defaults, **kwargs})


@pytest.fixture
def provider():
    p = AsyncMock()
    p.get_latest_block_number = AsyncMock(return_value=18_000_020)
    p.get_transactions = AsyncMock(return_value=[make_raw_tx()])
    p.get_token_transfers = AsyncMock(return_value=[])
    return p


@pytest.fixture
def price_oracle():
    oracle = AsyncMock()
    eth_pseudo = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    oracle.get_prices_usd = AsyncMock(return_value={eth_pseudo: Decimal("3000")})
    return oracle


@pytest.fixture
def block_tracker():
    tracker = AsyncMock(spec=BlockTracker)
    tracker.get_last_processed_block = AsyncMock(return_value=18_000_000)
    tracker.set_last_processed_block = AsyncMock()
    return tracker


@pytest.fixture
def service(provider, price_oracle, block_tracker):
    return EthereumChainService(
        provider=provider,
        price_oracle=price_oracle,
        block_tracker=block_tracker,
        address_registry=AddressRegistry(),
    )


@pytest.mark.asyncio
async def test_poll_cycle_enriches_eth_transfer(service):
    transfers = await service.poll_cycle(["0xsomewallet"])
    assert len(transfers) == 1
    t = transfers[0]
    assert t.token_symbol == "ETH"
    assert t.usd_value == Decimal("15000")  # 5 ETH * $3000


@pytest.mark.asyncio
async def test_poll_cycle_empty_on_no_new_blocks(provider, price_oracle, block_tracker):
    block_tracker.get_last_processed_block = AsyncMock(return_value=18_000_020)
    service = EthereumChainService(
        provider=provider,
        price_oracle=price_oracle,
        block_tracker=block_tracker,
        address_registry=AddressRegistry(),
    )
    result = await service.poll_cycle(["0xwallet"])
    assert result == []


@pytest.mark.asyncio
async def test_poll_cycle_empty_watched_addresses(service):
    result = await service.poll_cycle([])
    assert result == []


@pytest.mark.asyncio
async def test_poll_cycle_returns_empty_on_provider_error(service, provider):
    provider.get_latest_block_number = AsyncMock(side_effect=Exception("API error"))
    result = await service.poll_cycle(["0xwallet"])
    assert result == []


@pytest.mark.asyncio
async def test_block_tracker_advanced_after_cycle(service, block_tracker):
    await service.poll_cycle(["0xwallet"])
    block_tracker.set_last_processed_block.assert_called_once()


@pytest.mark.asyncio
async def test_exchange_label_attached(service, provider):
    binance = "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"
    provider.get_transactions = AsyncMock(
        return_value=[make_raw_tx(to_address=binance)]
    )
    transfers = await service.poll_cycle(["0xwallet"])
    assert transfers[0].to_label is not None
    assert "Binance" in transfers[0].to_label.name
