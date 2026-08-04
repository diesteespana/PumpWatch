"""
Claude-powered market insight engine.

Implements MarketInsightEngine (events/interfaces.py).

explain_event  — enriches a detected BaseEvent with narrative context.
get_token_sentiment — analyses recent token events and returns a sentiment summary.

Both are Redis-cached. With no API key, graceful fallback to the
event's existing explanation / neutral sentiment string.
"""
from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import CACHE_TTL_AI_TOKEN_SENTIMENT
from app.core.logging import get_logger
from app.database.redis import get_redis_client
from app.events.interfaces import MarketInsightEngine
from app.events.types import BaseEvent
from app.repositories.event import EventRepository

logger = get_logger(__name__)

_CACHE_KEY_EVENT = "pumpwatch:ai:event_explain:{tx_hash}:{event_type}"
_CACHE_KEY_SENTIMENT = "pumpwatch:ai:token_sentiment:{contract}"

_SENTIMENT_SYSTEM = """\
You are a concise on-chain market analyst. Given recent blockchain events for a \
token, produce a one-paragraph (3–4 sentence) sentiment summary.
Be direct and data-driven. Avoid speculation. Focus on observable on-chain behaviour.
Respond with only the paragraph — no headings, no bullet points.
"""

_EXPLAIN_SYSTEM = """\
You are an expert blockchain analyst. Given a detected on-chain event, provide a \
2–3 sentence explanation that adds context beyond the raw data.
Consider: who might be behind this, what it could signal, why it matters.
Be concise and data-driven. Respond with only the explanation paragraph.
"""


class AIMarketInsightEngine(MarketInsightEngine):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()
        self._redis = get_redis_client()
        self._event_repo = EventRepository(session)

    def _is_enabled(self) -> bool:
        return bool(self._settings.anthropic_api_key)

    async def explain_event(self, event: BaseEvent) -> str:
        cache_key = _CACHE_KEY_EVENT.format(
            tx_hash=event.tx_hash, event_type=event.event_type
        )
        cached = await self._redis.get(cache_key)
        if cached:
            return cached.decode()

        if not self._is_enabled():
            return event.explanation

        try:
            explanation = await self._call_claude_explain(event)
        except Exception as exc:
            logger.warning("ai_event_explain_failed", tx_hash=event.tx_hash, error=str(exc))
            return event.explanation

        # Cache for the lifetime of the AI wallet insights (events are immutable)
        await self._redis.setex(cache_key, CACHE_TTL_AI_TOKEN_SENTIMENT, explanation)
        return explanation

    async def get_token_sentiment(self, token_contract: str) -> str:
        cache_key = _CACHE_KEY_SENTIMENT.format(contract=token_contract.lower())
        cached = await self._redis.get(cache_key)
        if cached:
            return cached.decode()

        recent = await self._event_repo.get_by_token(
            token_contract, page=1, page_size=50
        )
        if not recent:
            return "No recent on-chain activity detected for this token."

        if not self._is_enabled():
            buys = sum(1 for e in recent if e.event_type in {"whale_buy", "exchange_withdrawal"})
            sells = sum(1 for e in recent if e.event_type in {"whale_sell", "exchange_deposit"})
            if buys > sells:
                sentiment = f"Bullish: {buys} buy-side events vs {sells} sell-side in recent activity."
            elif sells > buys:
                sentiment = f"Bearish: {sells} sell-side events vs {buys} buy-side in recent activity."
            else:
                sentiment = f"Neutral: {len(recent)} events with balanced buy/sell pressure."
            await self._redis.setex(cache_key, CACHE_TTL_AI_TOKEN_SENTIMENT, sentiment)
            return sentiment

        try:
            sentiment = await self._call_claude_sentiment(token_contract, recent)
        except Exception as exc:
            logger.warning("ai_token_sentiment_failed", contract=token_contract, error=str(exc))
            sentiment = f"{len(recent)} recent events recorded for this token."

        await self._redis.setex(cache_key, CACHE_TTL_AI_TOKEN_SENTIMENT, sentiment)
        return sentiment

    async def _call_claude_explain(self, event: BaseEvent) -> str:
        import anthropic

        context = {
            "event_type": str(event.event_type),
            "blockchain": event.blockchain,
            "tx_hash": event.tx_hash,
            "wallet_address": event.wallet_address,
            "token_symbol": event.token_symbol,
            "usd_value": float(event.usd_value),
            "confidence_score": event.confidence_score,
            "original_explanation": event.explanation,
        }
        client = anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        msg = await client.messages.create(
            model=self._settings.ai_model,
            max_tokens=256,
            system=_EXPLAIN_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": f"Explain this event:\n{json.dumps(context, indent=2)}",
                }
            ],
        )
        return msg.content[0].text.strip()

    async def _call_claude_sentiment(self, contract: str, events: list) -> str:
        import anthropic

        summary = {
            "token_contract": contract,
            "total_events": len(events),
            "event_type_counts": {},
            "total_volume_usd": 0.0,
        }
        for e in events:
            summary["event_type_counts"][e.event_type] = (
                summary["event_type_counts"].get(e.event_type, 0) + 1
            )
            summary["total_volume_usd"] += float(e.usd_value)

        client = anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        msg = await client.messages.create(
            model=self._settings.ai_model,
            max_tokens=256,
            system=_SENTIMENT_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Recent activity for token {contract}:\n"
                        f"{json.dumps(summary, indent=2)}"
                    ),
                }
            ],
        )
        return msg.content[0].text.strip()
