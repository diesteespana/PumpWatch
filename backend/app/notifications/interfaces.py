"""
Notification channel abstraction.

All notification delivery goes through NotificationChannel.
Adding Slack, SMS, or webhooks = implement + register. Zero changes elsewhere.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from app.events.types import BaseEvent


class ChannelType(StrEnum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"
    PUSH = "push"


@dataclass(frozen=True)
class NotificationPayload:
    event: BaseEvent
    recipient_id: str
    channel: ChannelType
    channel_config: dict


class NotificationChannel(ABC):
    """Delivers a notification payload over one specific channel."""

    @property
    @abstractmethod
    def channel_type(self) -> ChannelType:
        pass

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        """
        Deliver the notification.
        Returns True on success, False on soft failure.
        Raises NotificationDeliveryError on hard failure.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the channel is reachable."""


class NotificationService(ABC):
    """
    Orchestrates routing and delivery across channels.

    Holds the registered channels and dispatches based on user preferences.
    """

    @abstractmethod
    def register_channel(self, channel: NotificationChannel) -> None:
        """Register a delivery channel."""

    @abstractmethod
    async def notify(self, event: BaseEvent, user_id: str) -> None:
        """
        Look up user's notification preferences and dispatch
        the event to all configured channels.
        """
