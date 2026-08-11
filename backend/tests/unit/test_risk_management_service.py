"""Unit tests for RiskManagementService."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.paper_trading import PaperPosition


def _make_portfolio(cash="10000", starting="10000"):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.current_cash = Decimal(cash)
    p.starting_balance = Decimal(starting)
    return p


def _make_position(contract="0x" + "a" * 40, symbol="WETH", chain="ethereum",
                   qty="1", avg_cost="3000") -> PaperPosition:
    pos = MagicMock(spec=PaperPosition)
    pos.token_contract = contract
    pos.token_symbol = symbol
    pos.chain = chain
    pos.quantity = Decimal(qty)
    pos.avg_entry_price = Decimal(avg_cost)
    return pos


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def svc(mock_session):
    with (
        patch("app.services.risk_management_service.PaperPortfolioRepository") as ppr,
        patch("app.services.risk_management_service.PaperPositionRepository") as ppos,
        patch("app.services.risk_management_service.RiskProfileRepository") as rpr,
        patch("app.services.risk_management_service.CoinGeckoPriceOracle") as oracle,
        patch("app.services.risk_management_service.PaperTradingService") as pts,
        patch("app.services.risk_management_service.get_redis_client"),
    ):
        from app.services.risk_management_service import RiskManagementService

        instance = RiskManagementService(mock_session)
        instance._portfolio_repo = ppr.return_value
        instance._position_repo = ppos.return_value
        instance._risk_repo = rpr.return_value
        instance._oracle = oracle.return_value
        instance._paper_svc = pts.return_value
        yield instance


class TestRiskManagementService:
    @pytest.mark.asyncio
    async def test_trading_disabled_returns_empty(self, svc):
        with patch("app.services.risk_management_service.get_settings") as gs:
            gs.return_value.trading_enabled = False
            result = await svc.run_checks_for_portfolio(uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_portfolio_not_found_returns_empty(self, svc):
        with patch("app.services.risk_management_service.get_settings") as gs:
            gs.return_value.trading_enabled = True
            svc._portfolio_repo.get_by_id = AsyncMock(return_value=None)
            result = await svc.run_checks_for_portfolio(uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_positions_returns_empty(self, svc):
        portfolio = _make_portfolio()
        with patch("app.services.risk_management_service.get_settings") as gs:
            gs.return_value.trading_enabled = True
            svc._portfolio_repo.get_by_id = AsyncMock(return_value=portfolio)
            svc._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
            svc._position_repo.get_by_portfolio = AsyncMock(return_value=[])
            result = await svc.run_checks_for_portfolio(portfolio.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_stop_loss_triggers_sell(self, svc):
        portfolio = _make_portfolio(cash="9000", starting="10000")
        pos = _make_position(avg_cost="3000")
        # Current price is 2600 → drop of 13.3%, above default 10% stop-loss
        with patch("app.services.risk_management_service.get_settings") as gs:
            gs.return_value.trading_enabled = True
            svc._portfolio_repo.get_by_id = AsyncMock(return_value=portfolio)
            svc._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
            svc._position_repo.get_by_portfolio = AsyncMock(return_value=[pos])
            svc._oracle.get_prices_usd = AsyncMock(
                return_value={pos.token_contract: Decimal("2600")}
            )
            trade = MagicMock()
            trade.id = uuid.uuid4()
            svc._paper_svc.execute_trade_system = AsyncMock(return_value=trade)

            actions = await svc.run_checks_for_portfolio(portfolio.id)

        assert len(actions) == 1
        assert "stop-loss" in actions[0].lower()
        svc._paper_svc.execute_trade_system.assert_called_once()
        call_req = svc._paper_svc.execute_trade_system.call_args.kwargs["req"]
        assert call_req.trade_type == "sell"

    @pytest.mark.asyncio
    async def test_take_profit_triggers_sell(self, svc):
        portfolio = _make_portfolio(cash="10000", starting="10000")
        pos = _make_position(avg_cost="2000")
        # Current price is 3200 → gain of 60%, above default 50% take-profit
        with patch("app.services.risk_management_service.get_settings") as gs:
            gs.return_value.trading_enabled = True
            svc._portfolio_repo.get_by_id = AsyncMock(return_value=portfolio)
            svc._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
            svc._position_repo.get_by_portfolio = AsyncMock(return_value=[pos])
            svc._oracle.get_prices_usd = AsyncMock(
                return_value={pos.token_contract: Decimal("3200")}
            )
            trade = MagicMock()
            trade.id = uuid.uuid4()
            svc._paper_svc.execute_trade_system = AsyncMock(return_value=trade)

            actions = await svc.run_checks_for_portfolio(portfolio.id)

        assert len(actions) == 1
        assert "take-profit" in actions[0].lower()

    @pytest.mark.asyncio
    async def test_no_breach_returns_no_actions(self, svc):
        portfolio = _make_portfolio()
        pos = _make_position(avg_cost="3000")
        with patch("app.services.risk_management_service.get_settings") as gs:
            gs.return_value.trading_enabled = True
            svc._portfolio_repo.get_by_id = AsyncMock(return_value=portfolio)
            svc._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
            svc._position_repo.get_by_portfolio = AsyncMock(return_value=[pos])
            svc._oracle.get_prices_usd = AsyncMock(
                return_value={pos.token_contract: Decimal("3050")}
            )

            actions = await svc.run_checks_for_portfolio(portfolio.id)

        assert actions == []
        svc._paper_svc.execute_trade_system.assert_not_called()

    @pytest.mark.asyncio
    async def test_max_drawdown_guard_halts_checks(self, svc):
        # Equity = 5000 cash + 1 token × 0 price = 5000; starting = 10000
        # Drawdown 50% > default 30%, so we should bail before checking positions
        portfolio = _make_portfolio(cash="5000", starting="10000")
        pos = _make_position(avg_cost="3000")
        with patch("app.services.risk_management_service.get_settings") as gs:
            gs.return_value.trading_enabled = True
            svc._portfolio_repo.get_by_id = AsyncMock(return_value=portfolio)
            svc._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
            svc._position_repo.get_by_portfolio = AsyncMock(return_value=[pos])
            svc._oracle.get_prices_usd = AsyncMock(
                return_value={pos.token_contract: Decimal("0")}
            )

            actions = await svc.run_checks_for_portfolio(portfolio.id)

        assert len(actions) == 1
        assert "drawdown" in actions[0].lower()
        svc._paper_svc.execute_trade_system.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_price_position_skipped(self, svc):
        portfolio = _make_portfolio(cash="10000", starting="10000")
        pos = _make_position(avg_cost="3000")
        with patch("app.services.risk_management_service.get_settings") as gs:
            gs.return_value.trading_enabled = True
            svc._portfolio_repo.get_by_id = AsyncMock(return_value=portfolio)
            svc._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
            svc._position_repo.get_by_portfolio = AsyncMock(return_value=[pos])
            # Price missing from oracle response
            svc._oracle.get_prices_usd = AsyncMock(return_value={})

            actions = await svc.run_checks_for_portfolio(portfolio.id)

        assert actions == []
