"""Unit tests for PaperTradingService business logic."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.models.paper_trading import PaperPortfolio, PaperPosition, PaperTrade
from app.schemas.paper_trading import PortfolioCreate, TradeRequest
from app.services.paper_trading_service import PaperTradingService


def _make_portfolio(**kwargs) -> PaperPortfolio:
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Test Portfolio",
        starting_balance=Decimal("10000"),
        current_cash=Decimal("10000"),
        is_active=True,
    )
    defaults.update(kwargs)
    p = MagicMock(spec=PaperPortfolio)
    for k, v in defaults.items():
        setattr(p, k, v)
    return p


def _make_position(**kwargs) -> PaperPosition:
    defaults = dict(
        id=uuid.uuid4(),
        portfolio_id=uuid.uuid4(),
        token_symbol="WETH",
        token_contract="0x" + "a" * 40,
        chain="ethereum",
        quantity=Decimal("1"),
        avg_entry_price=Decimal("2000"),
    )
    defaults.update(kwargs)
    p = MagicMock(spec=PaperPosition)
    for k, v in defaults.items():
        setattr(p, k, v)
    return p


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def svc(mock_session):
    with (
        patch("app.services.paper_trading_service.PaperPortfolioRepository") as mock_port_repo_cls,
        patch("app.services.paper_trading_service.PaperPositionRepository") as mock_pos_repo_cls,
        patch("app.services.paper_trading_service.PaperTradeRepository") as mock_trade_repo_cls,
        patch("app.services.paper_trading_service.CoinGeckoPriceOracle") as mock_oracle_cls,
        patch("app.services.paper_trading_service.get_redis_client"),
    ):
        service = PaperTradingService(mock_session)
        service._portfolio_repo = mock_port_repo_cls.return_value
        service._position_repo = mock_pos_repo_cls.return_value
        service._trade_repo = mock_trade_repo_cls.return_value
        service._oracle = mock_oracle_cls.return_value
        yield service


class TestBuyTrade:
    @pytest.mark.asyncio
    async def test_buy_creates_new_position(self, svc, mock_session):
        portfolio = _make_portfolio()
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._oracle.get_price_usd = AsyncMock(return_value=Decimal("3000"))
        svc._position_repo.get_position = AsyncMock(return_value=None)
        svc._position_repo.upsert_position = AsyncMock()

        trade_obj = MagicMock(spec=PaperTrade)
        trade_obj.id = uuid.uuid4()
        trade_obj.portfolio_id = portfolio.id
        trade_obj.trade_type = "buy"
        trade_obj.token_symbol = "WETH"
        trade_obj.token_contract = "0x" + "a" * 40
        trade_obj.chain = "ethereum"
        trade_obj.quantity = Decimal("1")
        trade_obj.price_at_execution = Decimal("3000")
        trade_obj.total_value = Decimal("3000")
        trade_obj.realized_pnl = None
        trade_obj.trigger = "manual"
        from datetime import datetime, timezone
        trade_obj.executed_at = datetime.now(timezone.utc)
        svc._trade_repo.record_trade = AsyncMock(return_value=trade_obj)

        req = TradeRequest(
            trade_type="buy",
            token_symbol="WETH",
            token_contract="0x" + "a" * 40,
            quantity=Decimal("1"),
        )
        result = await svc.execute_trade(portfolio.user_id, portfolio.id, req)

        svc._position_repo.upsert_position.assert_called_once()
        call_kwargs = svc._position_repo.upsert_position.call_args.kwargs
        assert call_kwargs["new_quantity"] == Decimal("1")
        assert call_kwargs["new_avg_price"] == Decimal("3000")
        # cash deducted
        assert portfolio.current_cash == Decimal("7000")

    @pytest.mark.asyncio
    async def test_buy_updates_avg_cost_basis(self, svc, mock_session):
        """Buying more of a held token should compute weighted average price."""
        portfolio = _make_portfolio(current_cash=Decimal("20000"))
        existing = _make_position(quantity=Decimal("1"), avg_entry_price=Decimal("2000"))
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._oracle.get_price_usd = AsyncMock(return_value=Decimal("3000"))
        svc._position_repo.get_position = AsyncMock(return_value=existing)
        svc._position_repo.upsert_position = AsyncMock()

        trade_obj = MagicMock(spec=PaperTrade)
        for attr in ["id", "portfolio_id", "trade_type", "token_symbol", "token_contract",
                     "chain", "quantity", "price_at_execution", "total_value", "realized_pnl",
                     "trigger", "executed_at"]:
            setattr(trade_obj, attr, None)
        from datetime import datetime, timezone
        trade_obj.executed_at = datetime.now(timezone.utc)
        svc._trade_repo.record_trade = AsyncMock(return_value=trade_obj)

        req = TradeRequest(
            trade_type="buy",
            token_symbol="WETH",
            token_contract="0x" + "a" * 40,
            quantity=Decimal("1"),
        )
        await svc.execute_trade(portfolio.user_id, portfolio.id, req)

        call_kwargs = svc._position_repo.upsert_position.call_args.kwargs
        assert call_kwargs["new_quantity"] == Decimal("2")
        assert call_kwargs["new_avg_price"] == Decimal("2500")  # (2000 + 3000) / 2

    @pytest.mark.asyncio
    async def test_buy_insufficient_cash_raises(self, svc, mock_session):
        portfolio = _make_portfolio(current_cash=Decimal("100"))
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._oracle.get_price_usd = AsyncMock(return_value=Decimal("3000"))
        svc._position_repo.get_position = AsyncMock(return_value=None)

        req = TradeRequest(
            trade_type="buy",
            token_symbol="WETH",
            token_contract="0x" + "a" * 40,
            quantity=Decimal("1"),
        )
        with pytest.raises(ValidationError, match="Insufficient cash"):
            await svc.execute_trade(portfolio.user_id, portfolio.id, req)

    @pytest.mark.asyncio
    async def test_buy_unknown_price_raises(self, svc, mock_session):
        portfolio = _make_portfolio()
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._oracle.get_price_usd = AsyncMock(return_value=Decimal("0"))

        req = TradeRequest(
            trade_type="buy",
            token_symbol="UNKNOWN",
            token_contract="0x" + "b" * 40,
            quantity=Decimal("10"),
        )
        with pytest.raises(ValidationError, match="Cannot determine current price"):
            await svc.execute_trade(portfolio.user_id, portfolio.id, req)


class TestSellTrade:
    @pytest.mark.asyncio
    async def test_sell_full_position_removes_it(self, svc, mock_session):
        portfolio = _make_portfolio(current_cash=Decimal("0"))
        position = _make_position(quantity=Decimal("2"), avg_entry_price=Decimal("2000"))
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._oracle.get_price_usd = AsyncMock(return_value=Decimal("3000"))
        svc._position_repo.get_position = AsyncMock(return_value=position)
        svc._position_repo.delete_position = AsyncMock()
        svc._position_repo.upsert_position = AsyncMock()

        trade_obj = MagicMock(spec=PaperTrade)
        trade_obj.realized_pnl = Decimal("2000")
        for attr in ["id", "portfolio_id", "trade_type", "token_symbol", "token_contract",
                     "chain", "quantity", "price_at_execution", "total_value", "trigger"]:
            setattr(trade_obj, attr, None)
        from datetime import datetime, timezone
        trade_obj.executed_at = datetime.now(timezone.utc)
        svc._trade_repo.record_trade = AsyncMock(return_value=trade_obj)

        req = TradeRequest(
            trade_type="sell",
            token_symbol="WETH",
            token_contract="0x" + "a" * 40,
            quantity=Decimal("2"),
        )
        await svc.execute_trade(portfolio.user_id, portfolio.id, req)

        svc._position_repo.delete_position.assert_called_once()
        svc._position_repo.upsert_position.assert_not_called()
        assert portfolio.current_cash == Decimal("6000")  # 2 * 3000

    @pytest.mark.asyncio
    async def test_sell_partial_position_updates_quantity(self, svc, mock_session):
        portfolio = _make_portfolio(current_cash=Decimal("0"))
        position = _make_position(quantity=Decimal("3"), avg_entry_price=Decimal("2000"))
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._oracle.get_price_usd = AsyncMock(return_value=Decimal("3000"))
        svc._position_repo.get_position = AsyncMock(return_value=position)
        svc._position_repo.delete_position = AsyncMock()
        svc._position_repo.upsert_position = AsyncMock()

        trade_obj = MagicMock(spec=PaperTrade)
        trade_obj.realized_pnl = Decimal("1000")
        for attr in ["id", "portfolio_id", "trade_type", "token_symbol", "token_contract",
                     "chain", "quantity", "price_at_execution", "total_value", "trigger"]:
            setattr(trade_obj, attr, None)
        from datetime import datetime, timezone
        trade_obj.executed_at = datetime.now(timezone.utc)
        svc._trade_repo.record_trade = AsyncMock(return_value=trade_obj)

        req = TradeRequest(
            trade_type="sell",
            token_symbol="WETH",
            token_contract="0x" + "a" * 40,
            quantity=Decimal("1"),
        )
        await svc.execute_trade(portfolio.user_id, portfolio.id, req)

        call_kwargs = svc._position_repo.upsert_position.call_args.kwargs
        assert call_kwargs["new_quantity"] == Decimal("2")
        svc._position_repo.delete_position.assert_not_called()

    @pytest.mark.asyncio
    async def test_sell_realized_pnl_computed_correctly(self, svc, mock_session):
        portfolio = _make_portfolio(current_cash=Decimal("0"))
        position = _make_position(quantity=Decimal("5"), avg_entry_price=Decimal("1000"))
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._oracle.get_price_usd = AsyncMock(return_value=Decimal("1500"))
        svc._position_repo.get_position = AsyncMock(return_value=position)
        svc._position_repo.delete_position = AsyncMock()
        svc._position_repo.upsert_position = AsyncMock()

        captured_pnl: list[Decimal] = []

        async def capture_trade(**kwargs):
            captured_pnl.append(kwargs["realized_pnl"])
            t = MagicMock(spec=PaperTrade)
            t.realized_pnl = kwargs["realized_pnl"]
            for attr in ["id", "portfolio_id", "trade_type", "token_symbol", "token_contract",
                         "chain", "quantity", "price_at_execution", "total_value", "trigger"]:
                setattr(t, attr, None)
            from datetime import datetime, timezone
            t.executed_at = datetime.now(timezone.utc)
            return t

        svc._trade_repo.record_trade = AsyncMock(side_effect=capture_trade)

        req = TradeRequest(
            trade_type="sell",
            token_symbol="WETH",
            token_contract="0x" + "a" * 40,
            quantity=Decimal("5"),
        )
        await svc.execute_trade(portfolio.user_id, portfolio.id, req)

        assert captured_pnl[0] == Decimal("2500")  # (1500 - 1000) * 5

    @pytest.mark.asyncio
    async def test_sell_no_position_raises(self, svc, mock_session):
        portfolio = _make_portfolio()
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._oracle.get_price_usd = AsyncMock(return_value=Decimal("3000"))
        svc._position_repo.get_position = AsyncMock(return_value=None)

        req = TradeRequest(
            trade_type="sell",
            token_symbol="WETH",
            token_contract="0x" + "a" * 40,
            quantity=Decimal("1"),
        )
        with pytest.raises(ValidationError, match="No open position"):
            await svc.execute_trade(portfolio.user_id, portfolio.id, req)

    @pytest.mark.asyncio
    async def test_sell_more_than_held_raises(self, svc, mock_session):
        portfolio = _make_portfolio()
        position = _make_position(quantity=Decimal("1"))
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._oracle.get_price_usd = AsyncMock(return_value=Decimal("3000"))
        svc._position_repo.get_position = AsyncMock(return_value=position)

        req = TradeRequest(
            trade_type="sell",
            token_symbol="WETH",
            token_contract="0x" + "a" * 40,
            quantity=Decimal("5"),
        )
        with pytest.raises(ValidationError, match="Cannot sell"):
            await svc.execute_trade(portfolio.user_id, portfolio.id, req)


class TestPortfolioAccess:
    @pytest.mark.asyncio
    async def test_missing_portfolio_raises_not_found(self, svc, mock_session):
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=None)
        with pytest.raises(NotFoundError):
            await svc.get_portfolio_summary(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.asyncio
    async def test_execute_trade_on_missing_portfolio_raises(self, svc, mock_session):
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=None)
        req = TradeRequest(
            trade_type="buy",
            token_symbol="WETH",
            token_contract="0x" + "a" * 40,
            quantity=Decimal("1"),
        )
        with pytest.raises(NotFoundError):
            await svc.execute_trade(uuid.uuid4(), uuid.uuid4(), req)
