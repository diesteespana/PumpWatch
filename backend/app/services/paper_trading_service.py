from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain.price_oracle import CoinGeckoPriceOracle
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.database.redis import get_redis_client
from app.repositories.paper_trading import (
    PaperPortfolioRepository,
    PaperPositionRepository,
    PaperTradeRepository,
)
from app.schemas.paper_trading import (
    PortfolioCreate,
    PortfolioSummaryResponse,
    PositionResponse,
    TradeRequest,
    TradeResponse,
)

logger = get_logger(__name__)


class PaperTradingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._portfolio_repo = PaperPortfolioRepository(session)
        self._position_repo = PaperPositionRepository(session)
        self._trade_repo = PaperTradeRepository(session)
        self._oracle = CoinGeckoPriceOracle(redis_client=get_redis_client())

    async def create_portfolio(
        self, user_id: uuid.UUID, data: PortfolioCreate
    ):
        from app.models.paper_trading import PaperPortfolio

        portfolio = PaperPortfolio(
            id=uuid.uuid4(),
            user_id=user_id,
            name=data.name,
            starting_balance=data.starting_balance,
            current_cash=data.starting_balance,
            is_active=True,
        )
        self._session.add(portfolio)
        await self._session.flush()
        return portfolio

    async def list_portfolios(self, user_id: uuid.UUID):
        return await self._portfolio_repo.get_by_user(user_id)

    async def get_portfolio_summary(
        self, user_id: uuid.UUID, portfolio_id: uuid.UUID
    ) -> PortfolioSummaryResponse:
        portfolio = await self._portfolio_repo.get_by_user_and_id(user_id, portfolio_id)
        if portfolio is None:
            raise NotFoundError("Portfolio", str(portfolio_id))

        positions = await self._position_repo.get_by_portfolio(portfolio_id)

        # Batch price lookup for all open positions
        contracts = [p.token_contract for p in positions]
        prices: dict[str, Decimal] = {}
        if contracts:
            # Group by chain for separate batch calls
            chains: dict[str, list[str]] = {}
            for pos in positions:
                chains.setdefault(pos.chain, []).append(pos.token_contract)
            for chain, addrs in chains.items():
                fetched = await self._oracle.get_prices_usd(addrs, chain)
                prices.update(fetched)

        total_position_value = Decimal(0)
        position_responses: list[PositionResponse] = []
        for pos in positions:
            current_price = prices.get(pos.token_contract, Decimal(0))
            quantity = Decimal(str(pos.quantity))
            avg_price = Decimal(str(pos.avg_entry_price))
            current_value = quantity * current_price
            unrealized_pnl = current_value - (quantity * avg_price)
            cost_basis = quantity * avg_price
            unrealized_pnl_pct = (
                (unrealized_pnl / cost_basis * 100)
                if cost_basis > 0
                else Decimal(0)
            )
            total_position_value += current_value
            position_responses.append(
                PositionResponse(
                    id=pos.id,
                    portfolio_id=pos.portfolio_id,
                    token_symbol=pos.token_symbol,
                    token_contract=pos.token_contract,
                    chain=pos.chain,
                    quantity=quantity,
                    avg_entry_price=avg_price,
                    current_price=current_price if current_price > 0 else None,
                    current_value=current_value if current_price > 0 else None,
                    unrealized_pnl=unrealized_pnl if current_price > 0 else None,
                    unrealized_pnl_pct=unrealized_pnl_pct if current_price > 0 else None,
                )
            )

        # Realized P&L from all closed trades
        trades = await self._trade_repo.get_by_portfolio(portfolio_id, limit=10_000)
        realized_pnl = sum(
            Decimal(str(t.realized_pnl))
            for t in trades
            if t.realized_pnl is not None
        )

        current_cash = Decimal(str(portfolio.current_cash))
        starting = Decimal(str(portfolio.starting_balance))
        total_equity = current_cash + total_position_value
        total_return = total_equity - starting
        total_return_pct = (total_return / starting * 100) if starting > 0 else Decimal(0)

        from app.schemas.paper_trading import PortfolioResponse

        return PortfolioSummaryResponse(
            portfolio=PortfolioResponse.model_validate(portfolio),
            positions=position_responses,
            total_position_value=total_position_value,
            total_equity=total_equity,
            total_return=total_return,
            total_return_pct=total_return_pct,
            realized_pnl=realized_pnl,
        )

    async def execute_trade(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        req: TradeRequest,
    ) -> TradeResponse:
        portfolio = await self._portfolio_repo.get_by_user_and_id(user_id, portfolio_id)
        if portfolio is None:
            raise NotFoundError("Portfolio", str(portfolio_id))

        price = await self._oracle.get_price_usd(req.token_contract, req.chain)
        if price <= 0:
            raise ValidationError(
                f"Cannot determine current price for {req.token_symbol}. "
                "Ensure the contract address and chain are correct."
            )

        return await self._execute_trade_internal(portfolio, req, price)

    async def execute_trade_system(
        self,
        portfolio_id: uuid.UUID,
        req: TradeRequest,
        price: Decimal,
    ) -> TradeResponse:
        """Used by strategy engine / risk manager — bypasses user ownership check."""
        portfolio = await self._portfolio_repo.get_by_id(portfolio_id)
        if portfolio is None:
            raise NotFoundError("Portfolio", str(portfolio_id))
        return await self._execute_trade_internal(portfolio, req, price)

    async def _execute_trade_internal(self, portfolio, req: TradeRequest, price: Decimal) -> TradeResponse:
        portfolio_id = portfolio.id
        quantity = req.quantity
        total_value = quantity * price
        realized_pnl: Decimal | None = None

        if req.trade_type == "buy":
            cash = Decimal(str(portfolio.current_cash))
            if total_value > cash:
                raise ValidationError(
                    f"Insufficient cash. Need ${total_value:.2f}, have ${cash:.2f}."
                )
            portfolio.current_cash = cash - total_value

            existing = await self._position_repo.get_position(
                portfolio_id, req.token_contract, req.chain
            )
            if existing is None:
                new_qty = quantity
                new_avg = price
            else:
                old_qty = Decimal(str(existing.quantity))
                old_avg = Decimal(str(existing.avg_entry_price))
                new_qty = old_qty + quantity
                new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty

            await self._position_repo.upsert_position(
                portfolio_id=portfolio_id,
                token_symbol=req.token_symbol,
                token_contract=req.token_contract,
                chain=req.chain,
                new_quantity=new_qty,
                new_avg_price=new_avg,
            )

        else:  # sell
            position = await self._position_repo.get_position(
                portfolio_id, req.token_contract, req.chain
            )
            if position is None:
                raise ValidationError(f"No open position for {req.token_symbol}.")

            held = Decimal(str(position.quantity))
            if quantity > held:
                raise ValidationError(
                    f"Cannot sell {quantity} — only {held} held."
                )

            avg_cost = Decimal(str(position.avg_entry_price))
            realized_pnl = (price - avg_cost) * quantity

            new_qty = held - quantity
            if new_qty == 0:
                await self._position_repo.delete_position(
                    portfolio_id, req.token_contract, req.chain
                )
            else:
                await self._position_repo.upsert_position(
                    portfolio_id=portfolio_id,
                    token_symbol=req.token_symbol,
                    token_contract=req.token_contract,
                    chain=req.chain,
                    new_quantity=new_qty,
                    new_avg_price=avg_cost,
                )

            portfolio.current_cash = Decimal(str(portfolio.current_cash)) + total_value

        trade = await self._trade_repo.record_trade(
            portfolio_id=portfolio_id,
            trade_type=req.trade_type,
            token_symbol=req.token_symbol,
            token_contract=req.token_contract,
            chain=req.chain,
            quantity=quantity,
            price_at_execution=price,
            total_value=total_value,
            realized_pnl=realized_pnl,
            trigger=req.trigger,
        )
        await self._session.flush()

        logger.info(
            "paper_trade_executed",
            portfolio_id=str(portfolio_id),
            trade_type=req.trade_type,
            token=req.token_symbol,
            quantity=str(quantity),
            price=str(price),
        )

        return TradeResponse.model_validate(trade)

    async def get_trade_history(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TradeResponse]:
        portfolio = await self._portfolio_repo.get_by_user_and_id(user_id, portfolio_id)
        if portfolio is None:
            raise NotFoundError("Portfolio", str(portfolio_id))
        trades = await self._trade_repo.get_by_portfolio(portfolio_id, limit=limit, offset=offset)
        return [TradeResponse.model_validate(t) for t in trades]

    async def delete_portfolio(self, user_id: uuid.UUID, portfolio_id: uuid.UUID) -> None:
        portfolio = await self._portfolio_repo.get_by_user_and_id(user_id, portfolio_id)
        if portfolio is None:
            raise NotFoundError("Portfolio", str(portfolio_id))
        await self._session.delete(portfolio)
