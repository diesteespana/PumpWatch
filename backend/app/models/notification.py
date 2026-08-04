import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class NotificationSetting(Base, TimestampMixin):
    """
    Per-user, per-channel notification configuration.

    `config` is channel-specific:
    - telegram: {"chat_id": "...", "bot_token": "..."}
    - discord:  {"webhook_url": "..."}
    - email:    {"to": "user@example.com"}

    Sensitive values in `config` are encrypted at rest (Milestone 6).
    """

    __tablename__ = "notification_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    user: Mapped["User"] = relationship(back_populates="notification_settings")  # noqa: F821

    def __repr__(self) -> str:
        return f"<NotificationSetting channel={self.channel} user_id={self.user_id}>"
