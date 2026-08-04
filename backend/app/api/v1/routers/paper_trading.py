from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.database.session import get_db_session
from app.models.user import User
from app.schemas.paper_trading import (
    PortfolioCreate,
    PortfolioResponse,
    PortfolioSummaryResponse,
    TradeRequest,
    TradeResponse,
)
from app.services.paper_trading_service import PaperTradingService

router = APIRouter(prefix="/paper-trading", tags=["paper-trading"])


@router.post("/portfolios", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    data: PortfolioCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = PaperTradingService(session)
    portfolio = await svc.create_portfolio(current_user.id, data)
    await session.commit()
    return PortfolioResponse.model_validate(portfolio)


@router.get("/portfolios", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = PaperTradingService(session)
    portfolios = await svc.list_portfolios(current_user.id)
    return [PortfolioResponse.model_validate(p) for p in portfolios]


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(
    portfolio_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = PaperTradingService(session)
    return await svc.get_portfolio_summary(current_user.id, portfolio_id)


@router.delete("/portfolios/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = PaperTradingService(session)
    await svc.delete_portfolio(current_user.id, portfolio_id)
    await session.commit()


@router.post(
    "/portfolios/{portfolio_id}/trades",
    response_model=TradeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def execute_trade(
    portfolio_id: uuid.UUID,
    req: TradeRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = PaperTradingService(session)
    trade = await svc.execute_trade(current_user.id, portfolio_id, req)
    await session.commit()
    return trade


@router.get("/portfolios/{portfolio_id}/trades", response_model=list[TradeResponse])
async def get_trade_history(
    portfolio_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    svc = PaperTradingService(session)
    return await svc.get_trade_history(current_user.id, portfolio_id, limit=limit, offset=offset)
