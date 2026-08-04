"""
Email notification channel via aiosmtplib (async SMTP).

Uses HTML email with a plain-text fallback for maximum compatibility.
SMTP credentials come from settings (never from user config — we control
the sending domain for deliverability and security).

The recipient address comes from the user's NotificationSetting.config:
  {"to": "user@example.com"}

TLS: STARTTLS on port 587 by default. Override with SMTP_PORT=465 for
implicit TLS (aiosmtplib handles both).
"""
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings
from app.core.exceptions import NotificationDeliveryError
from app.core.logging import get_logger
from app.notifications.formatter import EventFormatter
from app.notifications.interfaces import ChannelType, NotificationChannel, NotificationPayload

logger = get_logger(__name__)


class EmailChannel(NotificationChannel):
    def __init__(self, formatter: EventFormatter | None = None) -> None:
        self._formatter = formatter or EventFormatter()

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.EMAIL

    async def send(self, payload: NotificationPayload) -> bool:
        settings = get_settings()
        to_address = payload.channel_config.get("to", "")

        if not to_address:
            logger.warning("email_missing_recipient", user=payload.recipient_id)
            return False
        if not settings.smtp_host:
            logger.warning("email_smtp_not_configured")
            return False

        msg = self._formatter.format(payload.event)
        mime = self._build_mime(
            to_address=to_address,
            from_address=settings.smtp_from,
            subject=msg.title,
            html=msg.body_html,
            plain=msg.body_text,
        )

        try:
            await aiosmtplib.send(
                mime,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user or None,
                password=settings.smtp_password or None,
                start_tls=settings.smtp_port == 587,
                use_tls=settings.smtp_port == 465,
            )
            logger.info("email_sent", to=to_address, user=payload.recipient_id)
            return True

        except aiosmtplib.SMTPException as exc:
            logger.error("email_smtp_error", error=str(exc), user=payload.recipient_id)
            raise NotificationDeliveryError(str(exc)) from exc
        except Exception as exc:
            logger.error("email_send_error", error=str(exc), exc_info=True)
            raise NotificationDeliveryError(str(exc)) from exc

    async def health_check(self) -> bool:
        settings = get_settings()
        if not settings.smtp_host:
            return False
        try:
            async with aiosmtplib.SMTP(
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                timeout=5,
            ) as smtp:
                await smtp.noop()
            return True
        except Exception:
            return False

    @staticmethod
    def _build_mime(
        to_address: str,
        from_address: str,
        subject: str,
        html: str,
        plain: str,
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"PumpWatch <{from_address}>"
        msg["To"] = to_address
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))
        return msg
