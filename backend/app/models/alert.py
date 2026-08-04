import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Alert(Base, TimestampMixin):
    """
    User-defined alert rule.

    Filters which events trigger a notification:
    - event_types: empty list = all types
    - wallet_addresses: empty list = all wallets
    - token_contracts: empty list = all tokens
    - min_usd_value: minimum USD threshold (overrides global setting)

    The notification engine evaluates each detected event against all
    active alerts for users who track the relevant wallet/token.
    """

    __tablename__ = "alerts"

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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Filter criteria — stored as JSONB lists for flexibility
    event_types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    wallet_addresses: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    token_contracts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    min_usd_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    user: Mapped["User"] = relationship(back_populates="alerts")  # noqa: F821

    def matches_event(
        self,
        event_type: str,
        wallet_address: str,
        token_contract: str,
        usd_value: float,
    ) -> bool:
        """
        Return True if this alert should fire for the given event parameters.

        Called by the notification engine — kept pure (no I/O) so it can be
        tested without DB access.
        """
        if not self.is_active:
            return False
        if usd_value < self.min_usd_value:
            return False
        if self.event_types and event_type not in self.event_types:
            return False
        if self.wallet_addresses and wallet_address.lower() not in [
            a.lower() for a in self.wallet_addresses
        ]:
            return False
        if self.token_contracts and token_contract.lower() not in [
            c.lower() for c in self.token_contracts
        ]:
            return False
        return True

    def __repr__(self) -> str:
        return f"<Alert id={self.id} name={self.name} active={self.is_active}>"
