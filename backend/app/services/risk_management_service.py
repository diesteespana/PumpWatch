"""
Risk management service — evaluates open positions against a portfolio's
RiskProfile and fires automatic stop-loss / take-profit paper trades.

Called from the strategy engine scheduler job so everything runs in one
DB session per cycle.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain.price_oracle import CoinGeckoPriceOracle
from app.core.logging import get_logger
from app.database.redis import get_redis_client
from app.repositories.paper_trading import (
    PaperPortfolioRepository,
    PaperPositionRepository,
)
from app.repositories.strategy import RiskProfileRepository
from app.schemas.paper_trading import TradeRequest
from app.services.paper_trading_service import PaperTradingService

logger = get_logger(__name__)

_DEFAULT_STOP_LOSS_PCT = Decimal("10")
_DEFAULT_TAKE_PROFIT_PCT = Decimal("50")
_DEFAULT_MAX_DRAWDOWN_PCT = Decimal("30")


class RiskManagementService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._portfolio_repo = PaperPortfolioRepository(session)
        self._position_repo = PaperPositionRepository(session)
        self._risk_repo = RiskProfileRepository(session)
        self._oracle = CoinGeckoPriceOracle(redis_client=get_redis_client())
        self._paper_svc = PaperTradingService(session)

    async def run_checks_for_portfolio(self, portfolio_id: uuid.UUID) -> list[str]:
        """
        Evaluate every open position. Returns list of action descriptions taken.
        """
        portfolio = await self._portfolio_repo.get_by_id(portfolio_id)
        if portfolio is None:
            return []

        # Max-drawdown guard — skip if already breached (strategy engine handles pause)
        risk = await self._risk_repo.get_by_portfolio(portfolio_id)
        sl_pct = Decimal(str(risk.stop_loss_pct)) if risk else _DEFAULT_STOP_LOSS_PCT
        tp_pct = Decimal(str(risk.take_profit_pct)) if risk else _DEFAULT_TAKE_PROFIT_PCT
        max_dd_pct = Decimal(str(risk.max_drawdown_pct)) if risk else _DEFAULT_MAX_DRAWDOWN_PCT

        # Check drawdown: if equity < starting * (1 - max_dd_pct/100), skip risk checks
        starting = Decimal(str(portfolio.starting_balance))
        positions = await self._position_repo.get_by_portfolio(portfolio_id)
        if not positions:
            return []

        # Batch price fetch
        chains: dict[str, list[str]] = {}
        for pos in positions:
            chains.setdefault(pos.chain, []).append(pos.token_contract)
        prices: dict[str, Decimal] = {}
        for chain, addrs in chains.items():
            fetched = await self._oracle.get_prices_usd(addrs, chain)
            prices.update(fetched)

        # Estimate equity for drawdown check
        position_value = sum(
            Decimal(str(pos.quantity)) * prices.get(pos.token_contract, Decimal(0))
            for pos in positions
        )
        total_equity = Decimal(str(portfolio.current_cash)) + position_value
        drawdown_floor = starting * (1 - max_dd_pct / 100)

        actions: list[str] = []

        if total_equity <= drawdown_floor:
            logger.warning(
                "max_drawdown_reached",
                portfolio_id=str(portfolio_id),
                equity=str(total_equity),
                floor=str(drawdown_floor),
            )
            return [f"Max drawdown reached (equity={total_equity:.2f}). Skipping further risk checks."]

        for pos in positions:
            current_price = prices.get(pos.token_contract, Decimal(0))
            if current_price <= 0:
                continue

            avg_cost = Decimal(str(pos.avg_entry_price))
            change_pct = (current_price - avg_cost) / avg_cost * 100

            triggered_reason: str | None = None
            if change_pct <= -sl_pct:
                triggered_reason = f"stop-loss ({change_pct:.1f}% < -{sl_pct}%)"
            elif change_pct >= tp_pct:
                triggered_reason = f"take-profit ({change_pct:.1f}% > +{tp_pct}%)"

            if triggered_reason:
                try:
                    req = TradeRequest(
                        trade_type="sell",
                        token_symbol=pos.token_symbol,
                        token_contract=pos.token_contract,
                        chain=pos.chain,
                        quantity=Decimal(str(pos.quantity)),
                        trigger="signal",
                    )
                    await self._paper_svc.execute_trade_system(
                        portfolio_id=portfolio.id,
                        req=req,
                        price=current_price,
                    )
                    msg = (
                        f"Auto-sold {pos.token_symbol} @ ${current_price:.4f} "
                        f"({triggered_reason})"
                    )
                    actions.append(msg)
                    logger.info(
                        "risk_trigger_sell",
                        portfolio_id=str(portfolio_id),
                        token=pos.token_symbol,
                        reason=triggered_reason,
                    )
                except Exception as exc:
                    logger.error(
                        "risk_trigger_sell_failed",
                        portfolio_id=str(portfolio_id),
                        token=pos.token_symbol,
                        error=str(exc),
                    )

        return actions
