"""
AI layer interfaces for Milestone 9.

WalletScorer and MarketInsightEngine ABCs are defined in events/interfaces.py
(they were stubbed there to avoid circular imports and allow M4-M8 to reference
them). This module adds the Prediction layer ABCs and shared value types.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class SignalDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class TokenSignal:
    token_contract: str
    token_symbol: str
    direction: SignalDirection
    confidence: float          # 0.0 – 1.0
    reasoning: str
    buy_pressure: int          # raw event counts
    sell_pressure: int
    net_flow_usd: float        # positive = more buying


@dataclass
class MarketOverview:
    chain: str
    dominant_direction: SignalDirection
    total_volume_24h: float
    top_events: list[dict]
    summary: str


class PredictionEngine(ABC):
    """Rule-based or AI-powered directional signal for tokens and markets."""

    @abstractmethod
    async def get_token_signal(
        self, token_contract: str, chain: str = "ethereum"
    ) -> TokenSignal:
        """Return a directional signal based on recent on-chain activity."""

    @abstractmethod
    async def get_market_overview(self, chain: str = "ethereum") -> MarketOverview:
        """High-level summary of market activity over the last 24 hours."""
