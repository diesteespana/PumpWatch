"""Factory functions for AI services."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interfaces import PredictionEngine
from app.ai.market_insight import AIMarketInsightEngine
from app.ai.prediction_engine import RuleBasedPredictionEngine
from app.ai.wallet_scorer import AIWalletScorer
from app.events.interfaces import MarketInsightEngine, WalletScorer


def create_wallet_scorer(session: AsyncSession) -> WalletScorer:
    return AIWalletScorer(session)


def create_market_insight_engine(session: AsyncSession) -> MarketInsightEngine:
    return AIMarketInsightEngine(session)


def create_prediction_engine(session: AsyncSession) -> PredictionEngine:
    return RuleBasedPredictionEngine(session)
