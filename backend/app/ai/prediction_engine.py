"""
Rule-based prediction engine.

Derives directional signals from recent on-chain event patterns without
calling any external AI API. The logic is deterministic and cheap — it runs
on every signal request (Redis-cached for 5 min to avoid DB hammering).

Signal logic:
  buy_pressure  = whale_buy + exchange_withdrawal + wallet_accumulation
  sell_pressure = whale_sell + exchange_deposit + wallet_distribution
  net_flow      = sum(usd_value for bullish events) - sum(usd_value for bearish events)

  BULLISH  if buy_pressure > sell_pressure AND net_flow > 0
  BEARISH  if sell_pressure > buy_pressure AND net_flow < 0
  NEUTRAL  otherwise
  confidence: |imbalance| / total_events (capped at 0.95)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interfaces import (
    MarketOverview,
    PredictionEngine,
    SignalDirection,
    TokenSignal,
)
from app.core.constants import CACHE_TTL_TOKEN_SIGNAL
from app.core.logging import get_logger
from app.database.redis import get_redis_client
from app.repositories.event import EventRepository

logger = get_logger(__name__)

_BULLISH_TYPES = {"whale_buy", "exchange_withdrawal", "wallet_accumulation", "liquidity_added"}
_BEARISH_TYPES = {"whale_sell", "exchange_deposit", "wallet_distribution", "liquidity_removed"}

_CACHE_KEY_SIGNAL = "pumpwatch:signal:token:{contract}:{chain}"
_CACHE_KEY_OVERVIEW = "pumpwatch:signal:overview:{chain}"


class RuleBasedPredictionEngine(PredictionEngine):
    def __init__(self, session: AsyncSession) -> None:
        self._event_repo = EventRepository(session)
        self._redis = get_redis_client()

    async def get_token_signal(
        self, token_contract: str, chain: str = "ethereum"
    ) -> TokenSignal:
        cache_key = _CACHE_KEY_SIGNAL.format(
            contract=token_contract.lower(), chain=chain
        )
        cached = await self._redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return TokenSignal(**data)

        since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        events = await self._event_repo.get_by_token(
            token_contract, page=1, page_size=200
        )
        # Filter to last 24h
        recent = [e for e in events if e.timestamp >= since_24h]

        buy_count = sum(1 for e in recent if e.event_type in _BULLISH_TYPES)
        sell_count = sum(1 for e in recent if e.event_type in _BEARISH_TYPES)
        buy_usd = sum(float(e.usd_value) for e in recent if e.event_type in _BULLISH_TYPES)
        sell_usd = sum(float(e.usd_value) for e in recent if e.event_type in _BEARISH_TYPES)
        net_flow = buy_usd - sell_usd
        total = buy_count + sell_count

        # Determine symbol from most recent event
        symbol = recent[0].token_symbol if recent else "UNKNOWN"

        if total == 0:
            direction = SignalDirection.NEUTRAL
            confidence = 0.0
            reasoning = "No on-chain activity detected in the last 24 hours."
        else:
            imbalance = abs(buy_count - sell_count) / total
            confidence = min(0.95, imbalance)

            if buy_count > sell_count and net_flow > 0:
                direction = SignalDirection.BULLISH
                reasoning = (
                    f"{buy_count} bullish vs {sell_count} bearish events. "
                    f"Net flow: +${net_flow:,.0f}. Accumulation pattern detected."
                )
            elif sell_count > buy_count and net_flow < 0:
                direction = SignalDirection.BEARISH
                reasoning = (
                    f"{sell_count} bearish vs {buy_count} bullish events. "
                    f"Net flow: -${abs(net_flow):,.0f}. Distribution pattern detected."
                )
            else:
                direction = SignalDirection.NEUTRAL
                confidence = 0.0
                reasoning = (
                    f"Mixed signals: {buy_count} bullish, {sell_count} bearish events. "
                    f"Net flow near zero."
                )

        signal = TokenSignal(
            token_contract=token_contract.lower(),
            token_symbol=symbol,
            direction=direction,
            confidence=confidence,
            reasoning=reasoning,
            buy_pressure=buy_count,
            sell_pressure=sell_count,
            net_flow_usd=net_flow,
        )

        payload = signal.__dict__.copy()
        payload["direction"] = str(signal.direction)
        await self._redis.setex(
            cache_key,
            CACHE_TTL_TOKEN_SIGNAL,
            json.dumps(payload),
        )
        return signal

    async def get_market_overview(self, chain: str = "ethereum") -> MarketOverview:
        cache_key = _CACHE_KEY_OVERVIEW.format(chain=chain)
        cached = await self._redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return MarketOverview(**data)

        since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        rows = await self._event_repo.get_top_wallets_by_volume(limit=5, chain=chain)
        # Approximate 24h volume from all events
        recent_events = await self._event_repo.get_recent(
            chain=chain, page=1, page_size=200
        )
        recent = [e for e in recent_events if e.timestamp >= since_24h]

        total_volume = sum(float(e.usd_value) for e in recent)
        buy_count = sum(1 for e in recent if e.event_type in _BULLISH_TYPES)
        sell_count = sum(1 for e in recent if e.event_type in _BEARISH_TYPES)

        if buy_count > sell_count:
            direction = SignalDirection.BULLISH
        elif sell_count > buy_count:
            direction = SignalDirection.BEARISH
        else:
            direction = SignalDirection.NEUTRAL

        summary = (
            f"{len(recent)} events in the last 24h on {chain}. "
            f"Total volume: ${total_volume:,.0f}. "
            f"Dominant trend: {direction.value}."
        )

        overview = MarketOverview(
            chain=chain,
            dominant_direction=direction,
            total_volume_24h=total_volume,
            top_events=[
                {"address": addr, "volume": vol, "events": cnt}
                for addr, vol, cnt in rows
            ],
            summary=summary,
        )
        payload = overview.__dict__.copy()
        payload["dominant_direction"] = str(overview.dominant_direction)
        await self._redis.setex(
            cache_key,
            CACHE_TTL_TOKEN_SIGNAL,
            json.dumps(payload),
        )
        return overview
