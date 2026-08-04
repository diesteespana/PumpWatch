import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class WalletScore(Base, TimestampMixin):
    """
    AI-generated wallet reputation score (Milestone 9 implementation).

    The table is created now so Milestones 3-8 can reference it and
    the schema doesn't require a disruptive migration later.

    score: 0.0 (poor) → 1.0 (exceptional)
    win_rate: fraction of profitable trades in historical window
    insights: list of human-readable observations (AI-generated)
    """

    __tablename__ = "wallet_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    insights: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    wallet: Mapped["Wallet"] = relationship(back_populates="score")  # noqa: F821

    def __repr__(self) -> str:
        return f"<WalletScore wallet_id={self.wallet_id} score={self.score:.2f}>"
