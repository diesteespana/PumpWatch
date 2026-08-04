"""
Telegram notification channel.

Uses the Bot API sendMessage endpoint directly via httpx (no heavy SDK needed).
Parse mode is MarkdownV2 — all user-generated content is escaped before sending.

Bot token comes from the user's NotificationSetting.config:
  {"chat_id": "123456789", "bot_token": "1234:abc..."}

If no per-user bot_token is set, falls back to the global TELEGRAM_BOT_TOKEN
from settings (useful for a shared "PumpWatch Alerts" bot).
"""
import httpx

from app.core.config import get_settings
from app.core.exceptions import NotificationDeliveryError
from app.core.logging import get_logger
from app.notifications.formatter import EventFormatter, FormattedMessage
from app.notifications.interfaces import ChannelType, NotificationChannel, NotificationPayload

logger = get_logger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramChannel(NotificationChannel):
    def __init__(self, formatter: EventFormatter | None = None) -> None:
        self._formatter = formatter or EventFormatter()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.TELEGRAM

    async def send(self, payload: NotificationPayload) -> bool:
        config = payload.channel_config
        chat_id = config.get("chat_id", "")
        bot_token = config.get("bot_token") or get_settings().telegram_bot_token

        if not chat_id or not bot_token:
            logger.warning("telegram_missing_config", user=payload.recipient_id)
            return False

        msg: FormattedMessage = self._formatter.format(payload.event)

        try:
            resp = await self._client.post(
                _TELEGRAM_API.format(token=bot_token),
                json={
                    "chat_id": chat_id,
                    "text": msg.body_text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False,
                },
            )
            if resp.status_code == 200:
                logger.info("telegram_sent", user=payload.recipient_id, chat=chat_id)
                return True

            data = resp.json()
            error_code = data.get("error_code")
            description = data.get("description", "")

            if error_code == 429:
                raise NotificationDeliveryError(f"Telegram rate limited: {description}")

            logger.warning(
                "telegram_send_failed",
                status=resp.status_code,
                error=description,
                user=payload.recipient_id,
            )
            return False

        except NotificationDeliveryError:
            raise
        except Exception as exc:
            logger.error("telegram_send_error", error=str(exc), exc_info=True)
            raise NotificationDeliveryError(str(exc)) from exc

    async def health_check(self) -> bool:
        token = get_settings().telegram_bot_token
        if not token:
            return False
        try:
            resp = await self._client.get(
                f"https://api.telegram.org/bot{token}/getMe"
            )
            return resp.status_code == 200
        except Exception:
            return False
