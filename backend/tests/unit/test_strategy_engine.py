"""Unit tests for StrategyEngineService and RiskManagementService."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.interfaces import SignalDirection, TokenSignal
from app.core.exceptions import ValidationError
from app.models.strategy import Strategy


def _make_strategy(**kwargs) -> Strategy:
    defaults = dict(
        id=uuid.uuid4(),
        portfolio_id=uuid.uuid4(),
        name="Test",
        description=None,
        is_active=True,
        token_contract="0x" + "a" * 40,
        token_symbol="WETH",
        chain="ethereum",
        signal_direction="bullish",
        min_confidence=Decimal("0.60"),
        action="buy",
        size_pct=Decimal("10"),
    )
    defaults.update(kwargs)
    s = MagicMock(spec=Strategy)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _make_signal(direction="bullish", confidence=0.80) -> TokenSignal:
    return TokenSignal(
        token_contract="0x" + "a" * 40,
        token_symbol="WETH",
        direction=SignalDirection(direction),
        confidence=confidence,
        reasoning="test",
        buy_pressure=10,
        sell_pressure=2,
        net_flow_usd=5000.0,
    )


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def engine(mock_session):
    with (
        patch("app.services.strategy_engine_service.StrategyRepository") as sr,
        patch("app.services.strategy_engine_service.StrategyRunRepository") as rr,
        patch("app.services.strategy_engine_service.PaperPortfolioRepository") as pr,
        patch("app.services.strategy_engine_service.RiskProfileRepository") as risk_r,
        patch("app.services.strategy_engine_service.PaperTradingService") as pts,
        patch("app.services.strategy_engine_service.CoinGeckoPriceOracle") as oracle,
        patch("app.services.strategy_engine_service.create_prediction_engine") as cpe,
        patch("app.services.strategy_engine_service.get_redis_client"),
    ):
        from app.services.strategy_engine_service import StrategyEngineService

        svc = StrategyEngineService(mock_session)
        svc._strategy_repo = sr.return_value
        svc._run_repo = rr.return_value
        svc._portfolio_repo = pr.return_value
        svc._risk_repo = risk_r.return_value
        svc._paper_svc = pts.return_value
        svc._oracle = oracle.return_value
        svc._prediction_engine = cpe.return_value
        yield svc


def _make_portfolio(cash="10000", starting="10000"):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.current_cash = Decimal(cash)
    p.starting_balance = Decimal(starting)
    return p


class TestStrategyEngine:
    @pytest.mark.asyncio
    async def test_bullish_signal_triggers_buy(self, engine):
        strategy = _make_strategy(signal_direction="bullish", action="buy", size_pct=Decimal("10"))
        portfolio = _make_portfolio(cash="10000")

        engine._prediction_engine.get_token_signal = AsyncMock(return_value=_make_signal("bullish", 0.80))
        engine._portfolio_repo.get_by_id = AsyncMock(return_value=portfolio)
        engine._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
        engine._oracle.get_price_usd = AsyncMock(return_value=Decimal("3000"))
        engine._run_repo.record = AsyncMock()

        trade = MagicMock()
        trade.id = uuid.uuid4()
        engine._paper_svc.execute_trade_system = AsyncMock(return_value=trade)

        fired = await engine._evaluate(strategy)

        assert fired is True
        engine._paper_svc.execute_trade_system.assert_called_once()
        call_kwargs = engine._paper_svc.execute_trade_system.call_args.kwargs
        assert call_kwargs["req"].trade_type == "buy"
        assert call_kwargs["req"].trigger == "signal"

    @pytest.mark.asyncio
    async def test_confidence_below_threshold_skips(self, engine):
        strategy = _make_strategy(min_confidence=Decimal("0.80"))
        engine._prediction_engine.get_token_signal = AsyncMock(return_value=_make_signal("bullish", 0.50))
        engine._run_repo.record = AsyncMock()

        fired = await engine._evaluate(strategy)

        assert fired is False
        engine._paper_svc.execute_trade_system.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrong_direction_skips(self, engine):
        strategy = _make_strategy(signal_direction="bearish", action="sell")
        engine._prediction_engine.get_token_signal = AsyncMock(return_value=_make_signal("bullish", 0.90))
        engine._run_repo.record = AsyncMock()

        fired = await engine._evaluate(strategy)

        assert fired is False

    @pytest.mark.asyncio
    async def test_any_direction_always_matches(self, engine):
        strategy = _make_strategy(signal_direction="any", action="buy", size_pct=Decimal("5"))
        portfolio = _make_portfolio()
        engine._prediction_engine.get_token_signal = AsyncMock(return_value=_make_signal("bearish", 0.75))
        engine._portfolio_repo.get_by_id = AsyncMock(return_value=portfolio)
        engine._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
        engine._oracle.get_price_usd = AsyncMock(return_value=Decimal("100"))
        engine._run_repo.record = AsyncMock()
        trade = MagicMock()
        trade.id = uuid.uuid4()
        engine._paper_svc.execute_trade_system = AsyncMock(return_value=trade)

        fired = await engine._evaluate(strategy)

        assert fired is True

    @pytest.mark.asyncio
    async def test_buy_quantity_computed_from_size_pct(self, engine):
        strategy = _make_strategy(signal_direction="bullish", action="buy", size_pct=Decimal("10"))
        portfolio = _make_portfolio(cash="5000")
        engine._prediction_engine.get_token_signal = AsyncMock(return_value=_make_signal("bullish", 0.90))
        engine._portfolio_repo.get_by_id = AsyncMock(return_value=portfolio)
        engine._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
        engine._oracle.get_price_usd = AsyncMock(return_value=Decimal("500"))
        engine._run_repo.record = AsyncMock()
        trade = MagicMock()
        trade.id = uuid.uuid4()
        engine._paper_svc.execute_trade_system = AsyncMock(return_value=trade)

        await engine._evaluate(strategy)

        call_kwargs = engine._paper_svc.execute_trade_system.call_args.kwargs
        # 10% of 5000 cash = 500 budget; 500 / 500 per token = 1.0 qty
        assert call_kwargs["req"].quantity == Decimal("1.0000000000")

    @pytest.mark.asyncio
    async def test_max_drawdown_guard_skips(self, engine):
        strategy = _make_strategy()
        portfolio = _make_portfolio(cash="5000", starting="10000")
        # Drawdown = (10000 - 5000) / 10000 = 50%, default max is 30%
        engine._prediction_engine.get_token_signal = AsyncMock(return_value=_make_signal("bullish", 0.90))
        engine._portfolio_repo.get_by_id = AsyncMock(return_value=portfolio)
        engine._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
        engine._run_repo.record = AsyncMock()

        fired = await engine._evaluate(strategy)

        assert fired is False
        run_call = engine._run_repo.record.call_args.kwargs
        assert "drawdown" in run_call["reason"].lower()

    @pytest.mark.asyncio
    async def test_unavailable_price_skips(self, engine):
        strategy = _make_strategy()
        portfolio = _make_portfolio()
        engine._prediction_engine.get_token_signal = AsyncMock(return_value=_make_signal("bullish", 0.90))
        engine._portfolio_repo.get_by_id = AsyncMock(return_value=portfolio)
        engine._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
        engine._oracle.get_price_usd = AsyncMock(return_value=Decimal("0"))
        engine._run_repo.record = AsyncMock()

        fired = await engine._evaluate(strategy)

        assert fired is False

    @pytest.mark.asyncio
    async def test_signal_fetch_error_is_handled(self, engine):
        strategy = _make_strategy()
        engine._prediction_engine.get_token_signal = AsyncMock(
            side_effect=RuntimeError("timeout")
        )
        engine._run_repo.record = AsyncMock()

        fired = await engine._evaluate(strategy)

        assert fired is False
        run_call = engine._run_repo.record.call_args.kwargs
        assert "Signal fetch failed" in run_call["reason"]

    @pytest.mark.asyncio
    async def test_run_all_active_counts_trades(self, engine):
        strategies = [_make_strategy(), _make_strategy()]
        engine._strategy_repo.get_all_active = AsyncMock(return_value=strategies)

        fired_flags = [True, False]
        call_count = 0

        async def fake_evaluate(s):
            nonlocal call_count
            result = fired_flags[call_count]
            call_count += 1
            return result

        engine._evaluate = fake_evaluate

        count = await engine.run_all_active()
        assert count == 1
