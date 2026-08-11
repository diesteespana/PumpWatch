"""Unit tests for StrategyService (CRUD layer)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.models.strategy import RiskProfile, Strategy
from app.schemas.strategy import (
    RiskProfileResponse,
    RiskProfileUpsert,
    StrategyCreate,
    StrategyResponse,
    StrategyUpdate,
)


def _make_portfolio():
    p = MagicMock()
    p.id = uuid.uuid4()
    p.name = "Test"
    return p


def _make_strategy(portfolio_id=None, **kwargs):
    s = MagicMock(spec=Strategy)
    s.id = uuid.uuid4()
    s.portfolio_id = portfolio_id or uuid.uuid4()
    s.name = "My Strategy"
    s.description = None
    s.is_active = True
    s.token_contract = "0x" + "a" * 40
    s.token_symbol = "WETH"
    s.chain = "ethereum"
    s.signal_direction = "bullish"
    s.min_confidence = Decimal("0.60")
    s.action = "buy"
    s.size_pct = Decimal("10")
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def _make_risk_profile(portfolio_id=None):
    r = MagicMock(spec=RiskProfile)
    r.id = uuid.uuid4()
    r.portfolio_id = portfolio_id or uuid.uuid4()
    r.stop_loss_pct = 10.0
    r.take_profit_pct = 50.0
    r.max_position_pct = 20.0
    r.max_drawdown_pct = 30.0
    return r


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def svc(mock_session):
    with (
        patch("app.services.strategy_service.StrategyRepository") as sr,
        patch("app.services.strategy_service.StrategyRunRepository") as rr,
        patch("app.services.strategy_service.RiskProfileRepository") as risk_r,
        patch("app.services.strategy_service.PaperPortfolioRepository") as pr,
    ):
        from app.services.strategy_service import StrategyService

        instance = StrategyService(mock_session)
        instance._strategy_repo = sr.return_value
        instance._run_repo = rr.return_value
        instance._risk_repo = risk_r.return_value
        instance._portfolio_repo = pr.return_value
        yield instance


class TestStrategyServiceOwnership:
    @pytest.mark.asyncio
    async def test_assert_portfolio_owned_raises_when_not_found(self, svc):
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=None)
        with pytest.raises(NotFoundError):
            await svc._assert_portfolio_owned(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.asyncio
    async def test_assert_portfolio_owned_passes_when_found(self, svc):
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=_make_portfolio())
        await svc._assert_portfolio_owned(uuid.uuid4(), uuid.uuid4())


class TestRiskProfile:
    @pytest.mark.asyncio
    async def test_get_risk_profile_returns_none_when_missing(self, svc):
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=_make_portfolio())
        svc._risk_repo.get_by_portfolio = AsyncMock(return_value=None)
        result = await svc.get_risk_profile(uuid.uuid4(), uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_risk_profile_calls_repo(self, svc):
        portfolio = _make_portfolio()
        risk = _make_risk_profile(portfolio_id=portfolio.id)
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._risk_repo.upsert = AsyncMock(return_value=risk)

        data = RiskProfileUpsert(
            stop_loss_pct=10.0,
            take_profit_pct=50.0,
            max_position_pct=20.0,
            max_drawdown_pct=30.0,
        )
        with patch.object(RiskProfileResponse, "model_validate", return_value=MagicMock()):
            await svc.upsert_risk_profile(uuid.uuid4(), portfolio.id, data)

        svc._risk_repo.upsert.assert_called_once()


class TestStrategyServiceCRUD:
    @pytest.mark.asyncio
    async def test_list_strategies_returns_mapped(self, svc):
        portfolio = _make_portfolio()
        strategies = [_make_strategy(portfolio_id=portfolio.id)]
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._strategy_repo.get_by_portfolio = AsyncMock(return_value=strategies)

        with patch.object(StrategyResponse, "model_validate", side_effect=lambda s: s):
            result = await svc.list_strategies(uuid.uuid4(), portfolio.id)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_create_strategy_adds_to_session(self, svc, mock_session):
        portfolio = _make_portfolio()
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)

        data = StrategyCreate(
            name="Test",
            description=None,
            token_contract="0x" + "a" * 40,
            token_symbol="WETH",
            chain="ethereum",
            signal_direction="bullish",
            min_confidence=0.6,
            action="buy",
            size_pct=10.0,
        )

        strategy_obj = _make_strategy(portfolio_id=portfolio.id)
        with patch("app.services.strategy_service.Strategy", return_value=strategy_obj):
            with patch.object(StrategyResponse, "model_validate", return_value=MagicMock()):
                await svc.create_strategy(uuid.uuid4(), portfolio.id, data)

        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_strategy_raises_when_not_found(self, svc):
        portfolio = _make_portfolio()
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._strategy_repo.get_by_portfolio_and_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await svc.update_strategy(
                uuid.uuid4(), portfolio.id, uuid.uuid4(),
                StrategyUpdate(is_active=False)
            )

    @pytest.mark.asyncio
    async def test_delete_strategy_raises_when_not_found(self, svc):
        portfolio = _make_portfolio()
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._strategy_repo.get_by_portfolio_and_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await svc.delete_strategy(uuid.uuid4(), portfolio.id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_delete_strategy_calls_session_delete(self, svc, mock_session):
        portfolio = _make_portfolio()
        strategy = _make_strategy(portfolio_id=portfolio.id)
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._strategy_repo.get_by_portfolio_and_id = AsyncMock(return_value=strategy)

        await svc.delete_strategy(uuid.uuid4(), portfolio.id, strategy.id)

        mock_session.delete.assert_called_once_with(strategy)

    @pytest.mark.asyncio
    async def test_get_portfolio_runs_returns_mapped(self, svc):
        portfolio = _make_portfolio()
        run = MagicMock()
        svc._portfolio_repo.get_by_user_and_id = AsyncMock(return_value=portfolio)
        svc._run_repo.get_recent_for_portfolio = AsyncMock(return_value=[run])

        with patch("app.services.strategy_service.StrategyRunResponse.model_validate", return_value=run):
            result = await svc.get_portfolio_runs(uuid.uuid4(), portfolio.id)

        assert len(result) == 1
