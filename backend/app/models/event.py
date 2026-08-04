import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class OnChainEvent(Base, TimestampMixin):
    """
    Persisted record of a detected blockchain event.

    Immutable after creation — events are facts, not state.
    tx_hash is NOT unique because one transaction can generate multiple events
    (e.g. a swap that also constitutes a whale buy).

    JSONB `raw_metadata` stores provider-specific or classifier-specific
    supplementary data without requiring schema migrations.
    """

    __tablename__ = "on_chain_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    blockchain: Mapped[str] = mapped_column(String(30), nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False, index=True)
    block_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    wallet_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    token_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    token_contract: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    usd_value: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    raw_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        # Query pattern: "show me recent whale events on ethereum for this token"
        Index(
            "ix_events_chain_type_timestamp",
            "blockchain", "event_type", "timestamp",
        ),
        # Query pattern: "all events for this wallet in the last 30 days"
        Index(
            "ix_events_wallet_timestamp",
            "wallet_address", "timestamp",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<OnChainEvent type={self.event_type} "
            f"usd={self.usd_value} tx={self.tx_hash[:10]}>"
        )
