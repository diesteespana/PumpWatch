"""Unit tests for DefaultNotificationService."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.events.types import BaseEvent, EventType
from app.notifications.interfaces import ChannelType, NotificationChannel
from app.notifications.rate_limiter import NotificationRateLimiter
from app.notifications.service import DefaultNotificationService


def make_event() -> BaseEvent:
    return BaseEvent(
        event_type=EventType.WHALE_BUY,
        blockchain="ethereum",
        tx_hash="0x" + "b" * 64,
        block_number=18_000_000,
        timestamp=datetime.now(tz=timezone.utc),
        wallet_address="0xwallet",
        token_symbol="ETH",
        token_contract="0xeeee",
        usd_value=Decimal("500000"),
        confidence_score=0.9,
        explanation="Test.",
    )


def make_setting(channel: str, config: dict, is_enabled: bool = True):
    s = MagicMock()
    s.channel = channel
    s.config = config
    s.is_enabled = is_enabled
    return s


@pytest.fixture
def mock_rate_limiter():
    rl = AsyncMock(spec=NotificationRateLimiter)
    rl.is_allowed = AsyncMock(return_value=True)
    return rl


@pytest.fixture
def mock_session():
    return AsyncMock()


def build_service(session, rate_limiter) -> DefaultNotificationService:
    return DefaultNotificationService(session=session, rate_limiter=rate_limiter)


@pytest.mark.asyncio
async def test_registered_channel_receives_dispatch(mock_session, mock_rate_limiter):
    service = build_service(mock_session, mock_rate_limiter)

    channel = AsyncMock(spec=NotificationChannel)
    channel.channel_type = ChannelType.TELEGRAM
    channel.send = AsyncMock(return_value=True)
    service.register_channel(channel)

    user_id = str(uuid.uuid4())
    setting = make_setting("telegram", {"chat_id": "123"})

    with pytest.MonkeyPatch().context() as mp:
        from app.repositories import notification as notif_repo_module
        mock_repo = AsyncMock()
        mock_repo.get_user_settings = AsyncMock(return_value=[setting])
        mp.setattr(notif_repo_module, "NotificationSettingRepository", lambda *a, **kw: mock_repo)
        await service.notify(make_event(), user_id)

    channel.send.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limited_user_skips_dispatch(mock_session, mock_rate_limiter):
    mock_rate_limiter.is_allowed = AsyncMock(return_value=False)
    service = build_service(mock_session, mock_rate_limiter)

    channel = AsyncMock(spec=NotificationChannel)
    channel.channel_type = ChannelType.TELEGRAM
    channel.send = AsyncMock(return_value=True)
    service.register_channel(channel)

    user_id = str(uuid.uuid4())
    setting = make_setting("telegram", {"chat_id": "123"})

    with pytest.MonkeyPatch().context() as mp:
        from app.repositories import notification as notif_repo_module
        mock_repo = AsyncMock()
        mock_repo.get_user_settings = AsyncMock(return_value=[setting])
        mp.setattr(notif_repo_module, "NotificationSettingRepository", lambda *a, **kw: mock_repo)
        await service.notify(make_event(), user_id)

    channel.send.assert_not_called()


@pytest.mark.asyncio
async def test_channel_exception_does_not_propagate(mock_session, mock_rate_limiter):
    service = build_service(mock_session, mock_rate_limiter)

    channel = AsyncMock(spec=NotificationChannel)
    channel.channel_type = ChannelType.DISCORD
    channel.send = AsyncMock(side_effect=Exception("webhook down"))
    service.register_channel(channel)

    user_id = str(uuid.uuid4())
    setting = make_setting("discord", {"webhook_url": "https://discord.com/..."})

    with pytest.MonkeyPatch().context() as mp:
        from app.repositories import notification as notif_repo_module
        mock_repo = AsyncMock()
        mock_repo.get_user_settings = AsyncMock(return_value=[setting])
        mp.setattr(notif_repo_module, "NotificationSettingRepository", lambda *a, **kw: mock_repo)
        # Must not raise
        await service.notify(make_event(), user_id)


@pytest.mark.asyncio
async def test_no_settings_returns_early(mock_session, mock_rate_limiter):
    service = build_service(mock_session, mock_rate_limiter)
    channel = AsyncMock(spec=NotificationChannel)
    channel.channel_type = ChannelType.EMAIL
    channel.send = AsyncMock()
    service.register_channel(channel)

    with pytest.MonkeyPatch().context() as mp:
        from app.repositories import notification as notif_repo_module
        mock_repo = AsyncMock()
        mock_repo.get_user_settings = AsyncMock(return_value=[])
        mp.setattr(notif_repo_module, "NotificationSettingRepository", lambda *a, **kw: mock_repo)
        await service.notify(make_event(), str(uuid.uuid4()))

    channel.send.assert_not_called()
