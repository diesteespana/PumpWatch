from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper_trading import PaperPortfolio, PaperPosition, PaperTrade
from app.repositories.base import BaseRepository


class PaperPortfolioRepository(BaseRepository[PaperPortfolio]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PaperPortfolio)

    async def get_by_user(self, user_id: uuid.UUID) -> Sequence[PaperPortfolio]:
        result = await self._session.execute(
            select(PaperPortfolio)
            .where(PaperPortfolio.user_id == user_id)
            .order_by(PaperPortfolio.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_user_and_id(
        self, user_id: uuid.UUID, portfolio_id: uuid.UUID
    ) -> PaperPortfolio | None:
        result = await self._session.execute(
            select(PaperPortfolio).where(
                PaperPortfolio.user_id == user_id,
                PaperPortfolio.id == portfolio_id,
            )
        )
        return result.scalar_one_or_none()


class PaperPositionRepository(BaseRepository[PaperPosition]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PaperPosition)

    async def get_by_portfolio(
        self, portfolio_id: uuid.UUID
    ) -> Sequence[PaperPosition]:
        result = await self._session.execute(
            select(PaperPosition)
            .where(PaperPosition.portfolio_id == portfolio_id)
            .order_by(PaperPosition.token_symbol)
        )
        return result.scalars().all()

    async def get_position(
        self, portfolio_id: uuid.UUID, token_contract: str, chain: str
    ) -> PaperPosition | None:
        result = await self._session.execute(
            select(PaperPosition).where(
                PaperPosition.portfolio_id == portfolio_id,
                PaperPosition.token_contract == token_contract.lower(),
                PaperPosition.chain == chain,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_position(
        self,
        portfolio_id: uuid.UUID,
        token_symbol: str,
        token_contract: str,
        chain: str,
        new_quantity: Decimal,
        new_avg_price: Decimal,
    ) -> PaperPosition:
        position = await self.get_position(portfolio_id, token_contract, chain)
        if position is None:
            position = PaperPosition(
                id=uuid.uuid4(),
                portfolio_id=portfolio_id,
                token_symbol=token_symbol.upper(),
                token_contract=token_contract.lower(),
                chain=chain,
                quantity=new_quantity,
                avg_entry_price=new_avg_price,
            )
            self._session.add(position)
        else:
            position.quantity = new_quantity
            position.avg_entry_price = new_avg_price
        return position

    async def delete_position(
        self, portfolio_id: uuid.UUID, token_contract: str, chain: str
    ) -> None:
        position = await self.get_position(portfolio_id, token_contract, chain)
        if position is not None:
            await self._session.delete(position)


class PaperTradeRepository(BaseRepository[PaperTrade]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PaperTrade)

    async def get_by_portfolio(
        self,
        portfolio_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[PaperTrade]:
        result = await self._session.execute(
            select(PaperTrade)
            .where(PaperTrade.portfolio_id == portfolio_id)
            .order_by(PaperTrade.executed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def record_trade(
        self,
        portfolio_id: uuid.UUID,
        trade_type: str,
        token_symbol: str,
        token_contract: str,
        chain: str,
        quantity: Decimal,
        price_at_execution: Decimal,
        total_value: Decimal,
        realized_pnl: Decimal | None = None,
        trigger: str = "manual",
    ) -> PaperTrade:
        trade = PaperTrade(
            id=uuid.uuid4(),
            portfolio_id=portfolio_id,
            trade_type=trade_type,
            token_symbol=token_symbol.upper(),
            token_contract=token_contract.lower(),
            chain=chain,
            quantity=quantity,
            price_at_execution=price_at_execution,
            total_value=total_value,
            realized_pnl=realized_pnl,
            trigger=trigger,
            executed_at=datetime.now(timezone.utc),
        )
        self._session.add(trade)
        return trade
