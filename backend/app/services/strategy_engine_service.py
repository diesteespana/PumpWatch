"""
Strategy engine — evaluates all active strategies against live prediction
signals and fires paper trades when conditions are met.

One session per scheduler tick; each strategy evaluation is recorded in
strategy_runs regardless of whether a trade was executed.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import create_prediction_engine
from app.ai.interfaces import SignalDirection
from app.blockchain.price_oracle import CoinGeckoPriceOracle
from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.database.redis import get_redis_client
from app.models.strategy import Strategy
from app.repositories.paper_trading import PaperPortfolioRepository
from app.repositories.strategy import (
    RiskProfileRepository,
    StrategyRepository,
    StrategyRunRepository,
)
from app.schemas.paper_trading import TradeRequest
from app.services.paper_trading_service import PaperTradingService

logger = get_logger(__name__)

_DEFAULT_MAX_DRAWDOWN_PCT = Decimal("30")
_DEFAULT_MAX_POSITION_PCT = Decimal("25")


class StrategyEngineService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._strategy_repo = StrategyRepository(session)
        self._run_repo = StrategyRunRepository(session)
        self._portfolio_repo = PaperPortfolioRepository(session)
        self._risk_repo = RiskProfileRepository(session)
        self._paper_svc = PaperTradingService(session)
        self._oracle = CoinGeckoPriceOracle(redis_client=get_redis_client())
        self._prediction_engine = create_prediction_engine()

    async def run_all_active(self) -> int:
        """Evaluate every active strategy. Returns count of trades fired."""
        if not get_settings().trading_enabled:
            logger.info("strategy_engine_skipped", reason="TRADING_ENABLED=false")
            return 0
        strategies = await self._strategy_repo.get_all_active()
        trades_fired = 0
        for strategy in strategies:
            fired = await self._evaluate(strategy)
            if fired:
                trades_fired += 1
        return trades_fired

    async def _evaluate(self, strategy: Strategy) -> bool:
        """Evaluate one strategy. Returns True if a trade was executed."""
        try:
            signal = await self._prediction_engine.get_token_signal(
                strategy.token_contract, strategy.chain
            )
        except Exception as exc:
            logger.warning(
                "strategy_signal_fetch_failed",
                strategy_id=str(strategy.id),
                error=str(exc),
            )
            await self._run_repo.record(
                strategy_id=strategy.id,
                triggered=False,
                reason=f"Signal fetch failed: {exc}",
            )
            return False

        signal_dir = str(signal.direction)
        confidence = float(signal.confidence)

        # Check direction match
        direction_ok = (
            strategy.signal_direction == "any"
            or signal_dir == strategy.signal_direction
        )
        # For a sell strategy on bearish signal, direction should match "bearish"
        confidence_ok = confidence >= float(strategy.min_confidence)

        if not direction_ok or not confidence_ok:
            await self._run_repo.record(
                strategy_id=strategy.id,
                triggered=False,
                signal_direction=signal_dir,
                signal_confidence=Decimal(str(confidence)),
                reason=(
                    f"No match: dir={signal_dir} vs {strategy.signal_direction}, "
                    f"conf={confidence:.2f} vs {strategy.min_confidence}"
                ),
            )
            return False

        # Check portfolio drawdown guard before firing
        portfolio = await self._portfolio_repo.get_by_id(strategy.portfolio_id)
        if portfolio is None:
            return False

        risk = await self._risk_repo.get_by_portfolio(strategy.portfolio_id)
        max_dd_pct = Decimal(str(risk.max_drawdown_pct)) if risk else _DEFAULT_MAX_DRAWDOWN_PCT
        max_pos_pct = Decimal(str(risk.max_position_pct)) if risk else _DEFAULT_MAX_POSITION_PCT
        starting = Decimal(str(portfolio.starting_balance))
        equity_floor = starting * (1 - max_dd_pct / 100)
        # Approximate equity as current_cash (positions not fetched here for speed)
        approx_equity = Decimal(str(portfolio.current_cash))
        if approx_equity <= equity_floor:
            await self._run_repo.record(
                strategy_id=strategy.id,
                triggered=False,
                signal_direction=signal_dir,
                signal_confidence=Decimal(str(confidence)),
                reason="Max drawdown guard: strategy paused",
            )
            return False

        # Fetch live price for quantity calculation
        price = await self._oracle.get_price_usd(strategy.token_contract, strategy.chain)
        if price <= 0:
            await self._run_repo.record(
                strategy_id=strategy.id,
                triggered=False,
                signal_direction=signal_dir,
                signal_confidence=Decimal(str(confidence)),
                reason="Price unavailable",
            )
            return False

        # Calculate quantity from size_pct, capped by max_position_pct of equity
        size_pct = Decimal(str(strategy.size_pct)) / 100
        if strategy.action == "buy":
            cash = Decimal(str(portfolio.current_cash))
            budget = cash * size_pct
            # Hard cap: a single trade may not exceed max_position_pct % of equity
            max_budget = approx_equity * (max_pos_pct / 100)
            budget = min(budget, max_budget)
            quantity = (budget / price).quantize(Decimal("0.0000000001"))
        else:  # sell
            from app.repositories.paper_trading import PaperPositionRepository
            pos_repo = PaperPositionRepository(self._session)
            position = await pos_repo.get_position(
                strategy.portfolio_id, strategy.token_contract, strategy.chain
            )
            if position is None:
                await self._run_repo.record(
                    strategy_id=strategy.id,
                    triggered=False,
                    signal_direction=signal_dir,
                    signal_confidence=Decimal(str(confidence)),
                    reason="No position to sell",
                )
                return False
            quantity = (Decimal(str(position.quantity)) * size_pct).quantize(
                Decimal("0.0000000001")
            )

        if quantity <= 0:
            await self._run_repo.record(
                strategy_id=strategy.id,
                triggered=False,
                signal_direction=signal_dir,
                signal_confidence=Decimal(str(confidence)),
                reason="Calculated quantity is zero (insufficient cash/position)",
            )
            return False

        req = TradeRequest(
            trade_type=strategy.action,
            token_symbol=strategy.token_symbol,
            token_contract=strategy.token_contract,
            chain=strategy.chain,
            quantity=quantity,
            trigger="signal",
        )

        try:
            trade = await self._paper_svc.execute_trade_system(
                portfolio_id=strategy.portfolio_id,
                req=req,
                price=price,
            )
        except (ValidationError, Exception) as exc:
            await self._run_repo.record(
                strategy_id=strategy.id,
                triggered=False,
                signal_direction=signal_dir,
                signal_confidence=Decimal(str(confidence)),
                reason=f"Trade failed: {exc}",
            )
            logger.warning(
                "strategy_trade_failed",
                strategy_id=str(strategy.id),
                error=str(exc),
            )
            return False

        await self._run_repo.record(
            strategy_id=strategy.id,
            triggered=True,
            signal_direction=signal_dir,
            signal_confidence=Decimal(str(confidence)),
            trade_id=trade.id,
            reason=(
                f"Signal {signal_dir} @ {confidence:.0%} confidence → "
                f"{strategy.action} {quantity} {strategy.token_symbol} @ ${price:.4f}"
            ),
        )

        logger.info(
            "strategy_trade_executed",
            strategy_id=str(strategy.id),
            strategy_name=strategy.name,
            action=strategy.action,
            token=strategy.token_symbol,
            quantity=str(quantity),
            price=str(price),
        )
        return True

    async def run_strategy_manually(
        self, portfolio_id: uuid.UUID, strategy_id: uuid.UUID
    ) -> bool:
        strategy = await self._strategy_repo.get_by_portfolio_and_id(
            portfolio_id, strategy_id
        )
        if strategy is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("Strategy", str(strategy_id))
        return await self._evaluate(strategy)
