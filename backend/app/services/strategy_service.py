"""CRUD service for strategies and risk profiles — used by the REST router."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.strategy import Strategy
from app.repositories.paper_trading import PaperPortfolioRepository
from app.repositories.strategy import (
    RiskProfileRepository,
    StrategyRepository,
    StrategyRunRepository,
)
from app.schemas.strategy import (
    RiskProfileResponse,
    RiskProfileUpsert,
    StrategyCreate,
    StrategyResponse,
    StrategyRunResponse,
    StrategyUpdate,
)


class StrategyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._strategy_repo = StrategyRepository(session)
        self._run_repo = StrategyRunRepository(session)
        self._risk_repo = RiskProfileRepository(session)
        self._portfolio_repo = PaperPortfolioRepository(session)

    async def _assert_portfolio_owned(
        self, user_id: uuid.UUID, portfolio_id: uuid.UUID
    ) -> None:
        p = await self._portfolio_repo.get_by_user_and_id(user_id, portfolio_id)
        if p is None:
            raise NotFoundError("Portfolio", str(portfolio_id))

    # ── Risk Profile ──────────────────────────────────────────────────────────

    async def get_risk_profile(
        self, user_id: uuid.UUID, portfolio_id: uuid.UUID
    ) -> RiskProfileResponse | None:
        await self._assert_portfolio_owned(user_id, portfolio_id)
        profile = await self._risk_repo.get_by_portfolio(portfolio_id)
        if profile is None:
            return None
        return RiskProfileResponse.model_validate(profile)

    async def upsert_risk_profile(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        data: RiskProfileUpsert,
    ) -> RiskProfileResponse:
        await self._assert_portfolio_owned(user_id, portfolio_id)
        profile = await self._risk_repo.upsert(
            portfolio_id=portfolio_id,
            stop_loss_pct=data.stop_loss_pct,
            take_profit_pct=data.take_profit_pct,
            max_position_pct=data.max_position_pct,
            max_drawdown_pct=data.max_drawdown_pct,
        )
        await self._session.flush()
        return RiskProfileResponse.model_validate(profile)

    # ── Strategies ────────────────────────────────────────────────────────────

    async def list_strategies(
        self, user_id: uuid.UUID, portfolio_id: uuid.UUID
    ) -> list[StrategyResponse]:
        await self._assert_portfolio_owned(user_id, portfolio_id)
        strategies = await self._strategy_repo.get_by_portfolio(portfolio_id)
        return [StrategyResponse.model_validate(s) for s in strategies]

    async def create_strategy(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        data: StrategyCreate,
    ) -> StrategyResponse:
        await self._assert_portfolio_owned(user_id, portfolio_id)
        strategy = Strategy(
            id=uuid.uuid4(),
            portfolio_id=portfolio_id,
            name=data.name,
            description=data.description,
            is_active=True,
            token_contract=data.token_contract,
            token_symbol=data.token_symbol,
            chain=data.chain,
            signal_direction=data.signal_direction,
            min_confidence=data.min_confidence,
            action=data.action,
            size_pct=data.size_pct,
        )
        self._session.add(strategy)
        await self._session.flush()
        return StrategyResponse.model_validate(strategy)

    async def update_strategy(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        strategy_id: uuid.UUID,
        data: StrategyUpdate,
    ) -> StrategyResponse:
        await self._assert_portfolio_owned(user_id, portfolio_id)
        strategy = await self._strategy_repo.get_by_portfolio_and_id(
            portfolio_id, strategy_id
        )
        if strategy is None:
            raise NotFoundError("Strategy", str(strategy_id))

        if data.name is not None:
            strategy.name = data.name
        if data.description is not None:
            strategy.description = data.description
        if data.is_active is not None:
            strategy.is_active = data.is_active
        if data.signal_direction is not None:
            strategy.signal_direction = data.signal_direction
        if data.min_confidence is not None:
            strategy.min_confidence = data.min_confidence
        if data.action is not None:
            strategy.action = data.action
        if data.size_pct is not None:
            strategy.size_pct = data.size_pct

        await self._session.flush()
        return StrategyResponse.model_validate(strategy)

    async def delete_strategy(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        strategy_id: uuid.UUID,
    ) -> None:
        await self._assert_portfolio_owned(user_id, portfolio_id)
        strategy = await self._strategy_repo.get_by_portfolio_and_id(
            portfolio_id, strategy_id
        )
        if strategy is None:
            raise NotFoundError("Strategy", str(strategy_id))
        await self._session.delete(strategy)

    async def get_strategy_runs(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        strategy_id: uuid.UUID,
    ) -> list[StrategyRunResponse]:
        await self._assert_portfolio_owned(user_id, portfolio_id)
        runs = await self._run_repo.get_by_strategy(strategy_id, limit=100)
        return [StrategyRunResponse.model_validate(r) for r in runs]

    async def get_portfolio_runs(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
    ) -> list[StrategyRunResponse]:
        await self._assert_portfolio_owned(user_id, portfolio_id)
        runs = await self._run_repo.get_recent_for_portfolio(portfolio_id, limit=100)
        return [StrategyRunResponse.model_validate(r) for r in runs]
