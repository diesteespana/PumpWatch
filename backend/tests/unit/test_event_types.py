"""Unit tests for the event type system."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.events.types import BaseEvent, EventType


def make_event(**overrides) -> BaseEvent:
    defaults = dict(
        event_type=EventType.WHALE_BUY,
        blockchain="ethereum",
        tx_hash="0xabc",
        block_number=18_000_000,
        timestamp=datetime.now(tz=timezone.utc),
        wallet_address="0xwallet",
        token_symbol="USDC",
        token_contract="0xcontract",
        usd_value=Decimal("500000"),
        confidence_score=0.9,
        explanation="Large USDC purchase detected.",
    )
    return BaseEvent(**{**defaults, **overrides})


def test_valid_event_creates_ok():
    event = make_event()
    assert event.event_type == EventType.WHALE_BUY
    assert event.confidence_score == 0.9


def test_confidence_score_out_of_range_raises():
    with pytest.raises(ValueError):
        make_event(confidence_score=1.5)

    with pytest.raises(ValueError):
        make_event(confidence_score=-0.1)


def test_event_is_immutable():
    event = make_event()
    with pytest.raises(Exception):
        event.confidence_score = 0.5  # type: ignore[misc]
