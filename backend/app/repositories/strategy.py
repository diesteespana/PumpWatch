from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategy import RiskProfile, Strategy, StrategyRun
from app.repositories.base import BaseRepository


class RiskProfileRepository(BaseRepository[RiskProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RiskProfile)

    async def get_by_portfolio(self, portfolio_id: uuid.UUID) -> RiskProfile | None:
        result = await self._session.execute(
            select(RiskProfile).where(RiskProfile.portfolio_id == portfolio_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        portfolio_id: uuid.UUID,
        stop_loss_pct: Decimal,
        take_profit_pct: Decimal,
        max_position_pct: Decimal,
        max_drawdown_pct: Decimal,
    ) -> RiskProfile:
        profile = await self.get_by_portfolio(portfolio_id)
        if profile is None:
            profile = RiskProfile(
                id=uuid.uuid4(),
                portfolio_id=portfolio_id,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                max_position_pct=max_position_pct,
                max_drawdown_pct=max_drawdown_pct,
            )
            self._session.add(profile)
        else:
            profile.stop_loss_pct = stop_loss_pct
            profile.take_profit_pct = take_profit_pct
            profile.max_position_pct = max_position_pct
            profile.max_drawdown_pct = max_drawdown_pct
        return profile


class StrategyRepository(BaseRepository[Strategy]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Strategy)

    async def get_by_portfolio(self, portfolio_id: uuid.UUID) -> Sequence[Strategy]:
        result = await self._session.execute(
            select(Strategy)
            .where(Strategy.portfolio_id == portfolio_id)
            .order_by(Strategy.created_at.desc())
        )
        return result.scalars().all()

    async def get_all_active(self) -> Sequence[Strategy]:
        result = await self._session.execute(
            select(Strategy).where(Strategy.is_active.is_(True))
        )
        return result.scalars().all()

    async def get_by_portfolio_and_id(
        self, portfolio_id: uuid.UUID, strategy_id: uuid.UUID
    ) -> Strategy | None:
        result = await self._session.execute(
            select(Strategy).where(
                Strategy.portfolio_id == portfolio_id,
                Strategy.id == strategy_id,
            )
        )
        return result.scalar_one_or_none()


class StrategyRunRepository(BaseRepository[StrategyRun]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StrategyRun)

    async def get_by_strategy(
        self,
        strategy_id: uuid.UUID,
        limit: int = 50,
    ) -> Sequence[StrategyRun]:
        result = await self._session.execute(
            select(StrategyRun)
            .where(StrategyRun.strategy_id == strategy_id)
            .order_by(StrategyRun.evaluated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_for_portfolio(
        self,
        portfolio_id: uuid.UUID,
        limit: int = 50,
    ) -> Sequence[StrategyRun]:
        """Fetch runs across all strategies belonging to a portfolio."""
        result = await self._session.execute(
            select(StrategyRun)
            .join(Strategy, StrategyRun.strategy_id == Strategy.id)
            .where(Strategy.portfolio_id == portfolio_id)
            .order_by(StrategyRun.evaluated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def record(
        self,
        strategy_id: uuid.UUID,
        triggered: bool,
        signal_direction: str | None = None,
        signal_confidence: float | None = None,
        trade_id: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> StrategyRun:
        run = StrategyRun(
            id=uuid.uuid4(),
            strategy_id=strategy_id,
            triggered=triggered,
            signal_direction=signal_direction,
            signal_confidence=signal_confidence,
            trade_id=trade_id,
            reason=reason,
            evaluated_at=datetime.now(timezone.utc),
        )
        self._session.add(run)
        return run
