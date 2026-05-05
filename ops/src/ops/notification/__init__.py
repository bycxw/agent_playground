"""Notification dispatch — channel-based.

Importing this package wires the built-in channels (email, telegram)
into the registry, gated by config flags. The engine calls
`dispatch(strategy_name, triggered, channel_names)`; dispatch routes to
each registered channel.
"""
from ..config import settings
from .channel import NotificationChannel, dispatch, known_channels, register_channel
from .email import EmailChannel
from .telegram import TelegramChannel


def _register_default_channels() -> None:
    if settings.NOTIFICATION_EMAIL_ENABLED:
        register_channel("email", EmailChannel())
    if settings.NOTIFICATION_TELEGRAM_ENABLED:
        register_channel("telegram", TelegramChannel())


_register_default_channels()


__all__ = [
    "NotificationChannel",
    "EmailChannel",
    "TelegramChannel",
    "register_channel",
    "dispatch",
    "known_channels",
]
