"""Unit tests for channel implementations — all HTTP mocked."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.events.types import BaseEvent, EventType
from app.notifications.channels.discord import DiscordChannel
from app.notifications.channels.telegram import TelegramChannel
from app.notifications.interfaces import ChannelType, NotificationPayload
from app.core.exceptions import NotificationDeliveryError


def make_event() -> BaseEvent:
    return BaseEvent(
        event_type=EventType.WHALE_BUY,
        blockchain="ethereum",
        tx_hash="0x" + "c" * 64,
        block_number=18_000_000,
        timestamp=datetime.now(tz=timezone.utc),
        wallet_address="0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
        token_symbol="USDC",
        token_contract="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        usd_value=Decimal("500000"),
        confidence_score=0.9,
        explanation="Whale alert.",
    )


def make_payload(channel: ChannelType, config: dict) -> NotificationPayload:
    return NotificationPayload(
        event=make_event(),
        recipient_id=str(uuid.uuid4()),
        channel=channel,
        channel_config=config,
    )


# ── Telegram ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_telegram_send_success():
    channel = TelegramChannel()
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch.object(channel._client, "post", new_callable=AsyncMock, return_value=mock_resp):
        result = await channel.send(
            make_payload(ChannelType.TELEGRAM, {"chat_id": "123", "bot_token": "tok"})
        )
    assert result is True


@pytest.mark.asyncio
async def test_telegram_missing_config_returns_false():
    channel = TelegramChannel()
    result = await channel.send(
        make_payload(ChannelType.TELEGRAM, {})  # no chat_id or token
    )
    assert result is False


@pytest.mark.asyncio
async def test_telegram_rate_limit_raises():
    channel = TelegramChannel()
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json = MagicMock(return_value={"error_code": 429, "description": "Too Many Requests"})

    with patch.object(channel._client, "post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(NotificationDeliveryError):
            await channel.send(
                make_payload(ChannelType.TELEGRAM, {"chat_id": "123", "bot_token": "tok"})
            )


# ── Discord ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_discord_send_success_204():
    channel = DiscordChannel()
    mock_resp = MagicMock()
    mock_resp.status_code = 204

    with patch.object(channel._client, "post", new_callable=AsyncMock, return_value=mock_resp):
        result = await channel.send(
            make_payload(ChannelType.DISCORD, {"webhook_url": "https://discord.com/api/webhooks/test"})
        )
    assert result is True


@pytest.mark.asyncio
async def test_discord_missing_webhook_returns_false():
    channel = DiscordChannel()
    with patch("app.notifications.channels.discord.get_settings") as mock_settings:
        mock_settings.return_value.discord_webhook_url = ""
        result = await channel.send(make_payload(ChannelType.DISCORD, {}))
    assert result is False


@pytest.mark.asyncio
async def test_discord_rate_limit_raises():
    channel = DiscordChannel()
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json = MagicMock(return_value={"retry_after": 5.0})

    with patch.object(channel._client, "post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(NotificationDeliveryError):
            await channel.send(
                make_payload(ChannelType.DISCORD, {"webhook_url": "https://discord.com/..."})
            )
