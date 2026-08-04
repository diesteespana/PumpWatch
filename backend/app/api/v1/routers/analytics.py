from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import (
    create_market_insight_engine,
    create_prediction_engine,
    create_wallet_scorer,
)
from app.auth.dependencies import get_current_active_user
from app.core.config import get_settings
from app.database.session import get_db_session
from app.models.user import User
from app.schemas.analytics import (
    AIInsightsResponse,
    MarketOverviewResponse,
    RankingsResponse,
    ScoreBreakdown,
    TokenSentimentResponse,
    TokenSignalResponse,
    TopToken,
    VolumeDataPoint,
    WalletAnalyticsResponse,
    WalletRankingItemResponse,
)
from app.services.analytics_service import WalletAnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/wallets/{address}", response_model=WalletAnalyticsResponse)
async def get_wallet_analytics(
    address: str,
    chain: str = Query(default="ethereum"),
    history_days: int = Query(default=30, ge=7, le=365),
    _current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = WalletAnalyticsService(session)
    summary = await svc.get_wallet_summary(address, chain, history_days=history_days)
    return WalletAnalyticsResponse(
        address=summary.address,
        chain=summary.chain,
        total_events=summary.total_events,
        total_volume_usd=summary.total_volume_usd,
        event_type_breakdown=summary.event_type_breakdown,
        top_tokens=[TopToken(**t) for t in summary.top_tokens],
        first_seen=summary.first_seen,
        last_seen=summary.last_seen,
        volume_over_time=[VolumeDataPoint(**p) for p in summary.volume_over_time],
        score=summary.score,
        score_breakdown=(
            ScoreBreakdown(**summary.score_breakdown)
            if summary.score_breakdown
            else None
        ),
        insights=summary.insights,
    )


@router.get("/wallets/{address}/ai-insights", response_model=AIInsightsResponse)
async def get_wallet_ai_insights(
    address: str,
    _current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Return AI-generated wallet insights (Claude-powered when API key present,
    heuristic fallback otherwise). Results are cached for 1 hour.
    """
    scorer = create_wallet_scorer(session)
    score = await scorer.score_wallet(address)
    insights = await scorer.get_wallet_insights(address)
    ai_powered = bool(get_settings().anthropic_api_key)
    return AIInsightsResponse(
        address=address.lower(),
        score=score,
        insights=insights,
        ai_powered=ai_powered,
    )


@router.get("/tokens/{contract}/signal", response_model=TokenSignalResponse)
async def get_token_signal(
    contract: str,
    chain: str = Query(default="ethereum"),
    _current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    engine = create_prediction_engine(session)
    signal = await engine.get_token_signal(contract, chain)
    return TokenSignalResponse(
        token_contract=signal.token_contract,
        token_symbol=signal.token_symbol,
        direction=signal.direction,
        confidence=signal.confidence,
        reasoning=signal.reasoning,
        buy_pressure=signal.buy_pressure,
        sell_pressure=signal.sell_pressure,
        net_flow_usd=signal.net_flow_usd,
    )


@router.get("/tokens/{contract}/sentiment", response_model=TokenSentimentResponse)
async def get_token_sentiment(
    contract: str,
    _current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    engine = create_market_insight_engine(session)
    sentiment = await engine.get_token_sentiment(contract)
    return TokenSentimentResponse(token_contract=contract.lower(), sentiment=sentiment)


@router.get("/market/overview", response_model=MarketOverviewResponse)
async def get_market_overview(
    chain: str = Query(default="ethereum"),
    _current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    engine = create_prediction_engine(session)
    overview = await engine.get_market_overview(chain)
    return MarketOverviewResponse(
        chain=overview.chain,
        dominant_direction=overview.dominant_direction,
        total_volume_24h=overview.total_volume_24h,
        top_events=overview.top_events,
        summary=overview.summary,
    )


@router.get("/rankings", response_model=RankingsResponse)
async def get_rankings(
    chain: str = Query(default="ethereum"),
    limit: int = Query(default=50, ge=1, le=200),
    _current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = WalletAnalyticsService(session)
    items = await svc.get_rankings(limit=limit, chain=chain)
    return RankingsResponse(
        items=[
            WalletRankingItemResponse(
                rank=item.rank,
                address=item.address,
                label=item.label,
                score=item.score,
                trade_count=item.trade_count,
                total_volume_usd=item.total_volume_usd,
                last_seen=item.last_seen,
            )
            for item in items
        ],
        total=len(items),
    )
