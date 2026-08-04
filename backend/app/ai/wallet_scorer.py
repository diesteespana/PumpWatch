"""
Claude-powered wallet scorer.

Implements WalletScorer (events/interfaces.py). Uses the M8 heuristic summary
as structured context and asks Claude for a richer score and narrative insights.

Caches results in Redis for CACHE_TTL_AI_WALLET_INSIGHTS seconds (1 hour) to
avoid repeated API calls for the same wallet.

Graceful degradation: if anthropic_api_key is missing or the API call fails,
returns the heuristic score from WalletAnalyticsService without raising.
"""
from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import CACHE_TTL_AI_WALLET_INSIGHTS
from app.core.logging import get_logger
from app.database.redis import get_redis_client
from app.events.interfaces import WalletScorer
from app.services.analytics_service import WalletAnalyticsService

logger = get_logger(__name__)

_CACHE_KEY = "pumpwatch:ai:wallet_insights:{address}"

_SYSTEM_PROMPT = """\
You are an expert on-chain analyst. You receive structured data about a \
blockchain wallet's activity and produce:
1. A reputation score from 0.0 to 1.0 (two decimal places)
2. Three to five concise insight bullets (1–2 sentences each)

Scoring guide:
- 0.8–1.0: Sophisticated, high-volume, consistently active — likely institutional or smart money
- 0.6–0.8: Active, diversified participant with notable volume
- 0.4–0.6: Regular user with moderate activity
- 0.2–0.4: Occasional user, limited history
- 0.0–0.2: New or dormant wallet

Respond ONLY with a JSON object, no prose outside the object:
{"score": <float>, "insights": ["...", "...", "..."]}
"""


class AIWalletScorer(WalletScorer):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()
        self._redis = get_redis_client()

    def _is_enabled(self) -> bool:
        return bool(self._settings.anthropic_api_key)

    async def score_wallet(self, wallet_address: str) -> float:
        result = await self._get_ai_result(wallet_address)
        return result["score"]

    async def get_wallet_insights(self, wallet_address: str) -> list[str]:
        result = await self._get_ai_result(wallet_address)
        return result["insights"]

    async def _get_ai_result(self, wallet_address: str) -> dict:
        cache_key = _CACHE_KEY.format(address=wallet_address.lower())
        cached = await self._redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Always compute heuristic summary first — used as AI context and fallback
        svc = WalletAnalyticsService(self._session)
        summary = await svc.get_wallet_summary(wallet_address)

        if not self._is_enabled():
            return {"score": summary.score or 0.0, "insights": summary.insights}

        try:
            result = await self._call_claude(summary)
        except Exception as exc:
            logger.warning("ai_wallet_scorer_failed", address=wallet_address, error=str(exc))
            result = {"score": summary.score or 0.0, "insights": summary.insights}

        await self._redis.setex(
            cache_key, CACHE_TTL_AI_WALLET_INSIGHTS, json.dumps(result)
        )
        return result

    async def _call_claude(self, summary: "WalletSummary") -> dict:  # type: ignore[name-defined]
        import anthropic

        context = {
            "address": summary.address,
            "chain": summary.chain,
            "total_events": summary.total_events,
            "total_volume_usd": round(summary.total_volume_usd, 2),
            "event_type_breakdown": summary.event_type_breakdown,
            "top_tokens": [
                {"symbol": t["symbol"], "volume_usd": round(t["volume"], 2)}
                for t in summary.top_tokens[:5]
            ],
            "days_since_first_seen": (
                None
                if not summary.first_seen
                else (
                    __import__("datetime").datetime.now(
                        __import__("datetime").timezone.utc
                    )
                    - summary.first_seen
                ).days
            ),
            "days_since_last_seen": (
                None
                if not summary.last_seen
                else (
                    __import__("datetime").datetime.now(
                        __import__("datetime").timezone.utc
                    )
                    - summary.last_seen
                ).days
            ),
            "heuristic_score": summary.score,
        }

        client = anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        message = await client.messages.create(
            model=self._settings.ai_model,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Analyse this wallet:\n{json.dumps(context, indent=2)}",
                }
            ],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        score = float(parsed["score"])
        insights = [str(i) for i in parsed["insights"]]
        return {"score": max(0.0, min(1.0, score)), "insights": insights}
