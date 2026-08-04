"""
Paper trading simulator models — Milestone 10.

Three tables:
  paper_portfolios   — one virtual portfolio per user (they may have many)
  paper_positions    — open positions: quantity + avg entry price
  paper_trades       — immutable trade log; source of truth for P&L history
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class PaperPortfolio(Base, TimestampMixin):
    __tablename__ = "paper_portfolios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    starting_balance: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False
    )
    current_cash: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    positions: Mapped[list["PaperPosition"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    trades: Mapped[list["PaperTrade"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan", order_by="PaperTrade.executed_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<PaperPortfolio name={self.name} cash={self.current_cash}>"


class PaperPosition(Base):
    """Open position: how much of a token the portfolio currently holds."""

    __tablename__ = "paper_positions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    token_contract: Mapped[str] = mapped_column(String(42), nullable=False)
    chain: Mapped[str] = mapped_column(String(30), nullable=False, default="ethereum")
    quantity: Mapped[float] = mapped_column(
        Numeric(precision=28, scale=10), nullable=False
    )
    avg_entry_price: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=6), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "portfolio_id", "token_contract", "chain",
            name="uq_position_portfolio_token_chain",
        ),
    )

    portfolio: Mapped["PaperPortfolio"] = relationship(back_populates="positions")

    def __repr__(self) -> str:
        return f"<PaperPosition {self.token_symbol} qty={self.quantity}>"


class PaperTrade(Base):
    """Immutable record of a simulated trade execution."""

    __tablename__ = "paper_trades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trade_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "buy" | "sell"
    token_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    token_contract: Mapped[str] = mapped_column(String(42), nullable=False)
    chain: Mapped[str] = mapped_column(String(30), nullable=False, default="ethereum")
    quantity: Mapped[float] = mapped_column(
        Numeric(precision=28, scale=10), nullable=False
    )
    price_at_execution: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=6), nullable=False
    )
    total_value: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False
    )
    realized_pnl: Mapped[float | None] = mapped_column(
        Numeric(precision=20, scale=4), nullable=True
    )
    trigger: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual"
    )  # "manual" | "signal"
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    portfolio: Mapped["PaperPortfolio"] = relationship(back_populates="trades")

    def __repr__(self) -> str:
        return (
            f"<PaperTrade {self.trade_type} {self.token_symbol} "
            f"qty={self.quantity} @{self.price_at_execution}>"
        )
