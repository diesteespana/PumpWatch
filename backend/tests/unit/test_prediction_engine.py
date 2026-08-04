"""Unit tests for the rule-based prediction engine signal logic."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.interfaces import SignalDirection
from app.ai.prediction_engine import (
    RuleBasedPredictionEngine,
    _BEARISH_TYPES,
    _BULLISH_TYPES,
)


def _event(event_type: str, usd: float = 100_000.0) -> MagicMock:
    e = MagicMock()
    e.event_type = event_type
    e.usd_value = usd
    e.timestamp = datetime.now(timezone.utc)
    e.token_symbol = "ETH"
    return e


def _old_event(event_type: str) -> MagicMock:
    e = _event(event_type)
    e.timestamp = datetime.now(timezone.utc) - timedelta(hours=25)
    return e


@pytest.fixture
def engine(monkeypatch):
    """Build an engine with a mocked DB session and Redis client."""
    session = MagicMock()
    eng = RuleBasedPredictionEngine.__new__(RuleBasedPredictionEngine)
    eng._event_repo = AsyncMock()
    eng._redis = AsyncMock()
    eng._redis.get = AsyncMock(return_value=None)
    eng._redis.setex = AsyncMock()
    return eng


# ── Signal direction ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bullish_signal(engine):
    engine._event_repo.get_by_token = AsyncMock(return_value=[
        _event("whale_buy", 500_000),
        _event("exchange_withdrawal", 200_000),
        _event("exchange_withdrawal", 150_000),
        _event("whale_sell", 100_000),
    ])
    signal = await engine.get_token_signal("0xabc", "ethereum")
    assert signal.direction == SignalDirection.BULLISH
    assert signal.confidence > 0


@pytest.mark.asyncio
async def test_bearish_signal(engine):
    engine._event_repo.get_by_token = AsyncMock(return_value=[
        _event("whale_sell", 800_000),
        _event("exchange_deposit", 600_000),
        _event("wallet_distribution", 300_000),
        _event("whale_buy", 100_000),
    ])
    signal = await engine.get_token_signal("0xabc", "ethereum")
    assert signal.direction == SignalDirection.BEARISH
    assert signal.net_flow_usd < 0


@pytest.mark.asyncio
async def test_neutral_signal_no_events(engine):
    engine._event_repo.get_by_token = AsyncMock(return_value=[])
    signal = await engine.get_token_signal("0xabc", "ethereum")
    assert signal.direction == SignalDirection.NEUTRAL
    assert signal.confidence == 0.0


@pytest.mark.asyncio
async def test_neutral_signal_balanced(engine):
    engine._event_repo.get_by_token = AsyncMock(return_value=[
        _event("whale_buy", 200_000),
        _event("whale_sell", 200_000),
    ])
    signal = await engine.get_token_signal("0xabc", "ethereum")
    assert signal.direction == SignalDirection.NEUTRAL


@pytest.mark.asyncio
async def test_only_24h_events_counted(engine):
    """Events older than 24h must be excluded from the signal."""
    engine._event_repo.get_by_token = AsyncMock(return_value=[
        _old_event("whale_sell"),  # outside window
        _event("whale_buy", 500_000),  # within window
    ])
    signal = await engine.get_token_signal("0xabc", "ethereum")
    # Only the recent buy counts — should be bullish
    assert signal.direction == SignalDirection.BULLISH


# ── Pressure counts ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_buy_sell_pressure_counts(engine):
    engine._event_repo.get_by_token = AsyncMock(return_value=[
        _event("whale_buy"),
        _event("exchange_withdrawal"),
        _event("whale_sell"),
    ])
    signal = await engine.get_token_signal("0xabc", "ethereum")
    assert signal.buy_pressure == 2
    assert signal.sell_pressure == 1


@pytest.mark.asyncio
async def test_confidence_capped_at_95(engine):
    """Even with extreme imbalance, confidence ≤ 0.95."""
    engine._event_repo.get_by_token = AsyncMock(return_value=[
        _event("whale_buy") for _ in range(20)
    ])
    signal = await engine.get_token_signal("0xabc", "ethereum")
    assert signal.confidence <= 0.95


# ── Redis caching ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_result_cached_in_redis(engine):
    engine._event_repo.get_by_token = AsyncMock(return_value=[_event("whale_buy")])
    await engine.get_token_signal("0xabc", "ethereum")
    engine._redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_cache_hit_skips_db(engine):
    import json
    from app.ai.interfaces import TokenSignal
    cached = TokenSignal(
        token_contract="0xabc",
        token_symbol="TKN",
        direction=SignalDirection.BULLISH,
        confidence=0.8,
        reasoning="cached",
        buy_pressure=5,
        sell_pressure=1,
        net_flow_usd=500_000,
    )
    payload = cached.__dict__.copy()
    payload["direction"] = str(cached.direction)
    engine._redis.get = AsyncMock(return_value=json.dumps(payload).encode())
    signal = await engine.get_token_signal("0xabc", "ethereum")
    assert signal.direction == SignalDirection.BULLISH
    engine._event_repo.get_by_token.assert_not_called()
