"""
DefaultNotificationService — routes detected events to user channels.

Pipeline for each detected event:
  1. Find all active alerts that match the event (AlertRepository)
  2. For each matching alert: look up that user's notification settings
  3. Rate-limit check (Redis sliding window)
  4. Dispatch to each enabled channel
  5. Log delivery result (structured logging; AuditLog in Milestone 6)

Design decisions:
- Channel dispatch is fire-and-forget per channel — one failing channel
  (e.g. bad Telegram token) never blocks delivery to others
- Rate limiter operates per (user, channel) — a flood of events won't
  spam a user's inbox even if many alerts match simultaneously
- NotificationService holds a registry of channels; adding Slack/SMS
  in future = implement + register. Zero changes to this file.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.events.types import BaseEvent
from app.notifications.interfaces import (
    ChannelType,
    NotificationChannel,
    NotificationPayload,
    NotificationService,
)
from app.notifications.rate_limiter import NotificationRateLimiter
from app.repositories.alert import AlertRepository
from app.repositories.notification import NotificationSettingRepository

logger = get_logger(__name__)


class DefaultNotificationService(NotificationService):
    def __init__(
        self,
        session: AsyncSession,
        rate_limiter: NotificationRateLimiter,
    ) -> None:
        self._session = session
        self._rate_limiter = rate_limiter
        self._channels: dict[ChannelType, NotificationChannel] = {}

    def register_channel(self, channel: NotificationChannel) -> None:
        self._channels[channel.channel_type] = channel
        logger.info("notification_channel_registered", channel=channel.channel_type)

    async def notify(self, event: BaseEvent, user_id: str) -> None:
        uid = uuid.UUID(user_id)
        setting_repo = NotificationSettingRepository(self._session)
        settings = await setting_repo.get_user_settings(uid)

        if not settings:
            return

        for setting in settings:
            channel_type = ChannelType(setting.channel)
            channel = self._channels.get(channel_type)
            if channel is None:
                logger.warning(
                    "notification_channel_not_registered",
                    channel=setting.channel,
                    user=user_id,
                )
                continue

            allowed = await self._rate_limiter.is_allowed(user_id, setting.channel)
            if not allowed:
                continue

            payload = NotificationPayload(
                event=event,
                recipient_id=user_id,
                channel=channel_type,
                channel_config=setting.config,
            )

            try:
                delivered = await channel.send(payload)
                logger.info(
                    "notification_dispatched",
                    user=user_id,
                    channel=setting.channel,
                    event_type=event.event_type,
                    delivered=delivered,
                )
            except Exception as exc:
                logger.error(
                    "notification_dispatch_error",
                    user=user_id,
                    channel=setting.channel,
                    error=str(exc),
                    exc_info=True,
                )

    async def notify_all_matching(self, event: BaseEvent) -> None:
        """
        Fan out a single event to all users whose active alerts match it.

        Called by DetectionService after each detection cycle.
        Collects matching user IDs from AlertRepository and dispatches.
        """
        alert_repo = AlertRepository(self._session)
        alerts = await alert_repo.get_active_alerts_for_event(
            event_type=event.event_type,
            wallet_address=event.wallet_address,
            token_contract=event.token_contract,
            usd_value=float(event.usd_value),
        )

        if not alerts:
            return

        # Deduplicate: one user may have multiple matching alerts but
        # should only receive one notification per event
        user_ids = list({str(alert.user_id) for alert in alerts})

        for user_id in user_ids:
            await self.notify(event, user_id)

        logger.info(
            "event_notifications_complete",
            event_type=event.event_type,
            tx=event.tx_hash[:12],
            recipients=len(user_ids),
        )
