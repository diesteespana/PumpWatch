"""Unit tests for DefaultDetectionEngine."""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.blockchain.chain_service import EnrichedTransfer
from app.events.classifiers.whale import WhaleBuyClassifier
from app.events.engine import DefaultDetectionEngine
from app.events.threshold import ThresholdConfig
from app.events.types import BaseEvent, EventType

_CONFIG = ThresholdConfig(whale_threshold_usd=100_000)
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def make_transfer(usd_value: float = 500_000) -> EnrichedTransfer:
    return EnrichedTransfer(
        tx_hash="0xabc123",
        block_number=18_000_000,
        timestamp=datetime.now(tz=timezone.utc),
        chain="ethereum",
        from_address="0xsender",
        to_address="0xreceiver",
        from_label=None,
        to_label=None,
        token_symbol="USDC",
        token_contract=USDC,
        token_decimals=6,
        raw_value=int(usd_value) * 10**6,
        token_amount=Decimal(str(usd_value)),
        usd_value=Decimal(str(usd_value)),
        is_contract_creation=False,
        input_data="0x",
    )


@pytest.fixture
def mock_event_repo():
    repo = AsyncMock()
    repo.tx_hash_exists = AsyncMock(return_value=False)
    repo.create = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_engine_processes_transfers(mock_event_repo):
    engine = DefaultDetectionEngine(
        event_repo=mock_event_repo,
        config=_CONFIG,
        classifiers=[WhaleBuyClassifier(_CONFIG)],
    )
    events = await engine.process_transfers([make_transfer(500_000)])
    assert len(events) == 1
    assert events[0].event_type == EventType.WHALE_BUY


@pytest.mark.asyncio
async def test_engine_deduplicates(mock_event_repo):
    mock_event_repo.tx_hash_exists = AsyncMock(return_value=True)
    engine = DefaultDetectionEngine(
        event_repo=mock_event_repo,
        config=_CONFIG,
        classifiers=[WhaleBuyClassifier(_CONFIG)],
    )
    events = await engine.process_transfers([make_transfer(500_000)])
    assert len(events) == 0
    mock_event_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_engine_skips_low_confidence(mock_event_repo):
    # Threshold above 1.0 means nothing passes
    config = ThresholdConfig(whale_threshold_usd=100_000, min_confidence_to_persist=1.1)
    engine = DefaultDetectionEngine(
        event_repo=mock_event_repo,
        config=config,
        classifiers=[WhaleBuyClassifier(config)],
    )
    events = await engine.process_transfers([make_transfer(500_000)])
    assert len(events) == 0


@pytest.mark.asyncio
async def test_engine_returns_empty_on_no_transfers(mock_event_repo):
    engine = DefaultDetectionEngine(event_repo=mock_event_repo, config=_CONFIG)
    assert await engine.process_transfers([]) == []


@pytest.mark.asyncio
async def test_engine_handles_classifier_exception(mock_event_repo):
    """A crashing classifier must not crash the whole cycle."""
    bad_classifier = MagicMock()
    bad_classifier.classify = MagicMock(side_effect=RuntimeError("oops"))
    bad_classifier.event_type = "whale_buy"

    engine = DefaultDetectionEngine(
        event_repo=mock_event_repo,
        config=_CONFIG,
        classifiers=[bad_classifier],
    )
    # Should not raise
    events = await engine.process_transfers([make_transfer(500_000)])
    assert events == []


@pytest.mark.asyncio
async def test_engine_persist_error_is_skipped(mock_event_repo):
    """A DB write failure must not crash other events in the same batch."""
    mock_event_repo.create = AsyncMock(side_effect=Exception("DB error"))
    engine = DefaultDetectionEngine(
        event_repo=mock_event_repo,
        config=_CONFIG,
        classifiers=[WhaleBuyClassifier(_CONFIG)],
    )
    events = await engine.process_transfers([make_transfer(500_000)])
    assert events == []  # failed to persist, so returned list is empty
