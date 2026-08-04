"""
Wallet analytics and heuristic scoring service (Milestone 8).

Scoring is purely rule-based here; Milestone 9 replaces with AI-powered insights
while keeping the same WalletScore table and WalletScorer interface.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.event import EventRepository
from app.repositories.wallet import WalletRepository
from app.repositories.wallet_score import WalletScoreRepository

logger = get_logger(__name__)

# ── Score weights (sum = 100) ─────────────────────────────────────────────────
_VOLUME_MAX_SCORE = 40.0   # $10M+ total volume
_ACTIVITY_MAX_SCORE = 30.0  # 200+ events
_DIVERSITY_MAX_SCORE = 20.0  # 13/13 event types
_RECENCY_MAX_SCORE = 10.0   # active within last day

_VOLUME_REFERENCE_USD = 10_000_000.0  # $10M
_ACTIVITY_REFERENCE = 200             # events
_TOTAL_EVENT_TYPES = 13


@dataclass
class WalletSummary:
    address: str
    chain: str
    total_events: int
    total_volume_usd: float
    event_type_breakdown: dict[str, int]
    top_tokens: list[dict]
    first_seen: datetime | None
    last_seen: datetime | None
    volume_over_time: list[dict]  # [{date, volume}]
    score: float | None = None    # 0.0–1.0, None if unscored
    score_breakdown: dict[str, float] = field(default_factory=dict)
    insights: list[str] = field(default_factory=list)


@dataclass
class WalletRankingItem:
    rank: int
    address: str
    label: str
    score: float
    trade_count: int
    total_volume_usd: float
    last_seen: datetime | None


def _compute_score(
    total_volume: float,
    event_count: int,
    unique_types: int,
    last_seen: datetime | None,
) -> tuple[float, dict[str, float], list[str]]:
    """
    Heuristic wallet score in [0.0, 1.0].

    Returns (score, breakdown_dict, insight_strings).
    M9 will call WalletScorer AI interface for richer insights.
    """
    volume_score = min(
        _VOLUME_MAX_SCORE,
        (math.log1p(total_volume) / math.log1p(_VOLUME_REFERENCE_USD)) * _VOLUME_MAX_SCORE,
    )

    activity_score = min(
        _ACTIVITY_MAX_SCORE,
        (math.log1p(event_count) / math.log1p(_ACTIVITY_REFERENCE)) * _ACTIVITY_MAX_SCORE,
    )

    diversity_score = (unique_types / _TOTAL_EVENT_TYPES) * _DIVERSITY_MAX_SCORE

    if last_seen is None:
        recency_score = 0.0
    else:
        days_since = (datetime.now(timezone.utc) - last_seen).total_seconds() / 86_400
        recency_score = max(0.0, _RECENCY_MAX_SCORE * (1 - days_since / 30))

    raw = volume_score + activity_score + diversity_score + recency_score
    score = raw / 100.0

    breakdown = {
        "volume": round(volume_score, 2),
        "activity": round(activity_score, 2),
        "diversity": round(diversity_score, 2),
        "recency": round(recency_score, 2),
    }

    insights: list[str] = []
    if total_volume >= 1_000_000:
        insights.append(f"Moved ${total_volume / 1_000_000:.1f}M+ on-chain — high-volume actor.")
    if event_count >= 50:
        insights.append(f"Recorded {event_count} events — consistently active wallet.")
    if unique_types >= 8:
        insights.append("Diverse activity across multiple event types — sophisticated participant.")
    if last_seen and (datetime.now(timezone.utc) - last_seen).days <= 1:
        insights.append("Active within the last 24 hours.")
    if not insights:
        insights.append("Limited on-chain history in the current dataset.")

    return round(score, 4), breakdown, insights


class WalletAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._event_repo = EventRepository(session)
        self._wallet_repo = WalletRepository(session)
        self._score_repo = WalletScoreRepository(session)

    async def get_wallet_summary(
        self, address: str, chain: str = "ethereum", *, history_days: int = 30
    ) -> WalletSummary:
        addr = address.lower()

        event_counts, total_volume, (first_seen, last_seen), top_tokens, volume_over_time = (
            await self._event_repo.get_wallet_event_counts(addr),
            await self._event_repo.get_wallet_total_volume(addr),
            await self._event_repo.get_wallet_first_last_seen(addr),
            await self._event_repo.get_wallet_top_tokens(addr),
            await self._event_repo.get_volume_over_time(addr, days=history_days),
        )

        total_events = sum(event_counts.values())
        unique_types = len(event_counts)

        score, breakdown, insights = _compute_score(
            total_volume, total_events, unique_types, last_seen
        )

        # Persist score to wallet_scores table if wallet is registered
        wallet = await self._wallet_repo.get_by_address(addr, chain)
        if wallet:
            await self._score_repo.upsert(
                wallet_id=wallet.id,
                score=score,
                trade_count=total_events,
                insights=insights,
            )

        return WalletSummary(
            address=addr,
            chain=chain,
            total_events=total_events,
            total_volume_usd=total_volume,
            event_type_breakdown=event_counts,
            top_tokens=top_tokens,
            first_seen=first_seen,
            last_seen=last_seen,
            volume_over_time=volume_over_time,
            score=score,
            score_breakdown=breakdown,
            insights=insights,
        )

    async def get_rankings(self, *, limit: int = 50, chain: str = "ethereum") -> list[WalletRankingItem]:
        """Return top wallets ordered by heuristic score.

        Pulls aggregate data from the analytics query (one DB round-trip per
        wallet for last_seen). For M8 scale (hundreds of wallets) this is fine;
        M9 can materialise scores into wallet_scores and do a single join.
        """
        rows = await self._event_repo.get_top_wallets_by_volume(limit=limit * 2, chain=chain)
        # Fetch all wallet records in bulk via a single pass
        wallet_map: dict[str, "Wallet"] = {}  # type: ignore[name-defined]
        for wallet_address, _, _ in rows:
            w = await self._wallet_repo.get_by_address(wallet_address, chain)
            if w:
                wallet_map[wallet_address] = w

        items: list[WalletRankingItem] = []
        for wallet_address, total_volume, event_count in rows:
            _, last_seen = await self._event_repo.get_wallet_first_last_seen(wallet_address)
            # Use event_count from aggregate; skip per-wallet type breakdown for speed
            # (diversity component defaults to a mid-range estimate here)
            score, _, _ = _compute_score(
                total_volume, event_count, min(event_count, _TOTAL_EVENT_TYPES), last_seen
            )

            w = wallet_map.get(wallet_address)
            label = (w.label or w.exchange_name or "") if w else ""

            items.append(
                WalletRankingItem(
                    rank=0,
                    address=wallet_address,
                    label=label,
                    score=score,
                    trade_count=event_count,
                    total_volume_usd=total_volume,
                    last_seen=last_seen,
                )
            )

        items.sort(key=lambda x: x.score, reverse=True)
        for i, item in enumerate(items[:limit], start=1):
            item.rank = i
        return items[:limit]

    async def score_all_tracked_wallets(self, chain: str = "ethereum") -> int:
        """Batch-score every tracked wallet — called by the hourly scheduler job."""
        addresses = await self._wallet_repo.get_all_tracked_addresses(chain)
        scored = 0
        for addr in addresses:
            try:
                await self.get_wallet_summary(addr, chain)
                scored += 1
            except Exception:
                logger.warning("wallet_score_failed", address=addr)
        return scored
