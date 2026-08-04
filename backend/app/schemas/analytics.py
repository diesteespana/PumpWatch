from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.ai.interfaces import SignalDirection


class VolumeDataPoint(BaseModel):
    date: str    # "YYYY-MM-DD"
    volume: float


class TopToken(BaseModel):
    symbol: str
    contract: str
    volume: float
    count: int


class ScoreBreakdown(BaseModel):
    volume: float
    activity: float
    diversity: float
    recency: float


class WalletAnalyticsResponse(BaseModel):
    address: str
    chain: str
    total_events: int
    total_volume_usd: float
    event_type_breakdown: dict[str, int]
    top_tokens: list[TopToken]
    first_seen: datetime | None
    last_seen: datetime | None
    volume_over_time: list[VolumeDataPoint]
    score: float | None
    score_breakdown: ScoreBreakdown | None
    insights: list[str]


class WalletRankingItemResponse(BaseModel):
    rank: int
    address: str
    label: str
    score: float
    trade_count: int
    total_volume_usd: float
    last_seen: datetime | None


class RankingsResponse(BaseModel):
    items: list[WalletRankingItemResponse]
    total: int


class AIInsightsResponse(BaseModel):
    address: str
    score: float
    insights: list[str]
    ai_powered: bool   # False when API key absent (heuristic fallback)


class TokenSignalResponse(BaseModel):
    token_contract: str
    token_symbol: str
    direction: SignalDirection
    confidence: float
    reasoning: str
    buy_pressure: int
    sell_pressure: int
    net_flow_usd: float


class TokenSentimentResponse(BaseModel):
    token_contract: str
    sentiment: str


class MarketOverviewResponse(BaseModel):
    chain: str
    dominant_direction: SignalDirection
    total_volume_24h: float
    top_events: list[dict]
    summary: str
