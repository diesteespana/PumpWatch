import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Token(Base, TimestampMixin):
    """ERC-20 token registry — shared across users, one row per contract."""

    __tablename__ = "tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    chain: Mapped[str] = mapped_column(String(30), nullable=False, default="ethereum")
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    decimals: Mapped[int] = mapped_column(Integer, nullable=False, default=18)
    coingecko_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("contract_address", "chain", name="uq_token_contract_chain"),
    )

    tracked_by: Mapped[list["UserTrackedToken"]] = relationship(  # noqa: F821
        back_populates="token", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Token symbol={self.symbol} address={self.contract_address}>"


class UserTrackedToken(Base):
    """Per-user token tracking with configurable threshold."""

    __tablename__ = "user_tracked_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    token_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tokens.id", ondelete="CASCADE"), primary_key=True
    )
    threshold_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(back_populates="tracked_tokens")  # noqa: F821
    token: Mapped["Token"] = relationship(back_populates="tracked_by")
