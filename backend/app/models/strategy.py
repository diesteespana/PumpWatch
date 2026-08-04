"""
M11 — strategy + risk management models.

  risk_profiles     — per-portfolio stop-loss / take-profit / position-size limits
  strategies        — named auto-trade rules driven by prediction-engine signals
  strategy_runs     — immutable audit log of every strategy evaluation
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class RiskProfile(Base, TimestampMixin):
    """One risk profile per paper portfolio (optional; defaults are permissive)."""

    __tablename__ = "risk_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_portfolios.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Percentage of avg entry price — triggers auto-sell
    stop_loss_pct: Mapped[float] = mapped_column(
        Numeric(6, 2), nullable=False, default=10.0
    )
    # Percentage of avg entry price — triggers auto-sell (profit lock)
    take_profit_pct: Mapped[float] = mapped_column(
        Numeric(6, 2), nullable=False, default=50.0
    )
    # Max single position as % of total equity
    max_position_pct: Mapped[float] = mapped_column(
        Numeric(6, 2), nullable=False, default=25.0
    )
    # Auto-pause all strategies if portfolio drops this % below starting balance
    max_drawdown_pct: Mapped[float] = mapped_column(
        Numeric(6, 2), nullable=False, default=30.0
    )

    def __repr__(self) -> str:
        return (
            f"<RiskProfile sl={self.stop_loss_pct}% tp={self.take_profit_pct}%>"
        )


class Strategy(Base, TimestampMixin):
    """
    A named rule that fires paper trades when the prediction engine
    reports a signal matching the configured direction + confidence floor.
    """

    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Which token contract + chain to watch
    token_contract: Mapped[str] = mapped_column(String(42), nullable=False)
    token_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    chain: Mapped[str] = mapped_column(String(30), nullable=False, default="ethereum")

    # Signal filter
    signal_direction: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "bullish" | "bearish" | "any"
    min_confidence: Mapped[float] = mapped_column(
        Numeric(4, 2), nullable=False, default=0.60
    )

    # What to do when triggered
    action: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "buy" | "sell"
    # Percentage of available cash (buy) or position (sell) to trade
    size_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=10.0
    )

    runs: Mapped[list["StrategyRun"]] = relationship(
        back_populates="strategy", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Strategy {self.name} {self.action} {self.token_symbol}>"


class StrategyRun(Base):
    """Immutable audit log — one row per strategy evaluation cycle."""

    __tablename__ = "strategy_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Did the signal meet the strategy's conditions?
    triggered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Signal values at evaluation time
    signal_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    signal_confidence: Mapped[float | None] = mapped_column(
        Numeric(4, 2), nullable=True
    )
    # If triggered, the resulting PaperTrade id
    trade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_trades.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    strategy: Mapped["Strategy"] = relationship(back_populates="runs")

    def __repr__(self) -> str:
        return (
            f"<StrategyRun strategy={self.strategy_id} triggered={self.triggered}>"
        )
