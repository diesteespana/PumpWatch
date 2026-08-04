import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Wallet(Base, TimestampMixin):
    """
    A blockchain wallet address — shared across users.

    One wallet can be tracked by many users simultaneously.
    Exchange classification comes from AddressRegistry on creation.
    """

    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    chain: Mapped[str] = mapped_column(String(30), nullable=False, default="ethereum")
    label: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    is_exchange: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exchange_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("address", "chain", name="uq_wallet_address_chain"),
    )

    tracked_by: Mapped[list["UserTrackedWallet"]] = relationship(  # noqa: F821
        back_populates="wallet", cascade="all, delete-orphan"
    )
    score: Mapped["WalletScore | None"] = relationship(  # noqa: F821
        back_populates="wallet", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Wallet address={self.address} chain={self.chain}>"


class UserTrackedWallet(Base):
    """
    Association between a User and a Wallet they are tracking.

    Per-user configuration (custom label, threshold override) lives here
    rather than on Wallet so multiple users can track the same address
    with different settings.
    """

    __tablename__ = "user_tracked_wallets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), primary_key=True
    )
    custom_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    threshold_usd: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Override the global whale threshold for this wallet/user pair"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="tracked_wallets")  # noqa: F821
    wallet: Mapped["Wallet"] = relationship(back_populates="tracked_by")
