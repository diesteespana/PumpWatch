"""
Discord notification channel.

Delivers via Discord webhooks — no bot token required.
Users paste their webhook URL into NotificationSetting.config:
  {"webhook_url": "https://discord.com/api/webhooks/..."}

Discord embeds allow rich formatting with color-coded sidebars, fields,
and footers — far better than plain text for whale alerts.
"""
import httpx

from app.core.config import get_settings
from app.core.exceptions import NotificationDeliveryError
from app.core.logging import get_logger
from app.notifications.formatter import EventFormatter
from app.notifications.interfaces import ChannelType, NotificationChannel, NotificationPayload

logger = get_logger(__name__)


class DiscordChannel(NotificationChannel):
    def __init__(self, formatter: EventFormatter | None = None) -> None:
        self._formatter = formatter or EventFormatter()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.DISCORD

    async def send(self, payload: NotificationPayload) -> bool:
        webhook_url = payload.channel_config.get("webhook_url") or get_settings().discord_webhook_url

        if not webhook_url:
            logger.warning("discord_missing_webhook", user=payload.recipient_id)
            return False

        msg = self._formatter.format(payload.event)

        try:
            resp = await self._client.post(
                webhook_url,
                json={"embeds": [msg.discord_embed]},
            )

            # Discord returns 204 No Content on success
            if resp.status_code in (200, 204):
                logger.info("discord_sent", user=payload.recipient_id)
                return True

            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", "?")
                raise NotificationDeliveryError(
                    f"Discord rate limited, retry after {retry_after}s"
                )

            logger.warning(
                "discord_send_failed",
                status=resp.status_code,
                body=resp.text[:200],
                user=payload.recipient_id,
            )
            return False

        except NotificationDeliveryError:
            raise
        except Exception as exc:
            logger.error("discord_send_error", error=str(exc), exc_info=True)
            raise NotificationDeliveryError(str(exc)) from exc

    async def health_check(self) -> bool:
        webhook_url = get_settings().discord_webhook_url
        if not webhook_url:
            return False
        try:
            # GET on a webhook URL returns its metadata (200) without sending anything
            resp = await self._client.get(webhook_url)
            return resp.status_code == 200
        except Exception:
            return False
