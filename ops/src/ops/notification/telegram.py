"""Telegram channel."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..config import settings
from .channel import NotificationChannel
from .formatter import format_message

if TYPE_CHECKING:
    from ..strategies.base import Triggered

logger = logging.getLogger(__name__)


class TelegramChannel(NotificationChannel):
    def send(self, strategy_name: str, triggered: list["Triggered"]) -> None:
        if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID):
            logger.warning("Telegram not configured, skipping")
            return

        import httpx

        body = format_message(strategy_name, triggered)
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        response = httpx.post(
            url,
            data={"chat_id": settings.TELEGRAM_CHAT_ID, "text": body},
            timeout=10,
        )
        response.raise_for_status()
        logger.info("Telegram message sent")
