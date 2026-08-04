from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.database.session import get_db_session
from app.models.user import User
from app.schemas.strategy import (
    RiskProfileResponse,
    RiskProfileUpsert,
    StrategyCreate,
    StrategyResponse,
    StrategyRunResponse,
    StrategyUpdate,
)
from app.services.strategy_engine_service import StrategyEngineService
from app.services.strategy_service import StrategyService

router = APIRouter(prefix="/paper-trading/portfolios/{portfolio_id}", tags=["strategy"])


# ── Risk Profile ──────────────────────────────────────────────────────────────

@router.get("/risk-profile", response_model=RiskProfileResponse | None)
async def get_risk_profile(
    portfolio_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = StrategyService(session)
    return await svc.get_risk_profile(current_user.id, portfolio_id)


@router.put(
    "/risk-profile",
    response_model=RiskProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def upsert_risk_profile(
    portfolio_id: uuid.UUID,
    data: RiskProfileUpsert,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = StrategyService(session)
    result = await svc.upsert_risk_profile(current_user.id, portfolio_id, data)
    await session.commit()
    return result


# ── Strategies ────────────────────────────────────────────────────────────────

@router.get("/strategies", response_model=list[StrategyResponse])
async def list_strategies(
    portfolio_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = StrategyService(session)
    return await svc.list_strategies(current_user.id, portfolio_id)


@router.post(
    "/strategies",
    response_model=StrategyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_strategy(
    portfolio_id: uuid.UUID,
    data: StrategyCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = StrategyService(session)
    result = await svc.create_strategy(current_user.id, portfolio_id, data)
    await session.commit()
    return result


@router.patch("/strategies/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    portfolio_id: uuid.UUID,
    strategy_id: uuid.UUID,
    data: StrategyUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = StrategyService(session)
    result = await svc.update_strategy(current_user.id, portfolio_id, strategy_id, data)
    await session.commit()
    return result


@router.delete(
    "/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_strategy(
    portfolio_id: uuid.UUID,
    strategy_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = StrategyService(session)
    await svc.delete_strategy(current_user.id, portfolio_id, strategy_id)
    await session.commit()


@router.post(
    "/strategies/{strategy_id}/run",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def run_strategy_manually(
    portfolio_id: uuid.UUID,
    strategy_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Manually trigger a single strategy evaluation right now."""
    engine = StrategyEngineService(session)
    fired = await engine.run_strategy_manually(portfolio_id, strategy_id)
    await session.commit()
    return {"triggered": fired}


@router.get(
    "/strategies/{strategy_id}/runs", response_model=list[StrategyRunResponse]
)
async def get_strategy_runs(
    portfolio_id: uuid.UUID,
    strategy_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = StrategyService(session)
    return await svc.get_strategy_runs(current_user.id, portfolio_id, strategy_id)


@router.get("/strategy-runs", response_model=list[StrategyRunResponse])
async def get_portfolio_runs(
    portfolio_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """All execution log entries across all strategies for this portfolio."""
    svc = StrategyService(session)
    return await svc.get_portfolio_runs(current_user.id, portfolio_id)
