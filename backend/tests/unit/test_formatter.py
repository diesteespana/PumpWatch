"""Unit tests for EventFormatter — no HTTP, no DB."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.events.types import BaseEvent, EventType
from app.notifications.formatter import EventFormatter


def make_event(event_type: str = EventType.WHALE_BUY, usd_value: float = 500_000) -> BaseEvent:
    return BaseEvent(
        event_type=EventType(event_type),
        blockchain="ethereum",
        tx_hash="0x" + "a" * 64,
        block_number=18_000_000,
        timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        wallet_address="0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
        token_symbol="USDC",
        token_contract="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        usd_value=Decimal(str(usd_value)),
        confidence_score=0.90,
        explanation="Test explanation.",
    )


@pytest.fixture
def formatter():
    return EventFormatter()


def test_format_produces_all_fields(formatter):
    msg = formatter.format(make_event())
    assert msg.title
    assert msg.body_text
    assert msg.body_html
    assert msg.discord_embed


def test_title_contains_token(formatter):
    msg = formatter.format(make_event())
    assert "USDC" in msg.title


def test_title_contains_emoji(formatter):
    msg = formatter.format(make_event(EventType.WHALE_BUY))
    assert "🐋" in msg.title


def test_body_contains_usd_value(formatter):
    msg = formatter.format(make_event(usd_value=1_250_000))
    assert "1,250,000" in msg.body_text


def test_body_contains_wallet_prefix(formatter):
    msg = formatter.format(make_event())
    assert "0x3f5c" in msg.body_text


def test_html_contains_pumpwatch_branding(formatter):
    msg = formatter.format(make_event())
    assert "pumpwat.ch" in msg.body_html


def test_discord_embed_has_required_keys(formatter):
    msg = formatter.format(make_event())
    embed = msg.discord_embed
    assert "title" in embed
    assert "color" in embed
    assert "fields" in embed
    assert "footer" in embed
    assert "timestamp" in embed


def test_discord_embed_footer_has_brand(formatter):
    msg = formatter.format(make_event())
    assert "pumpwat.ch" in msg.discord_embed["footer"]["text"]


@pytest.mark.parametrize("event_type", list(EventType))
def test_all_event_types_format_without_error(formatter, event_type):
    event = make_event(event_type=event_type)
    msg = formatter.format(event)
    assert msg.title
