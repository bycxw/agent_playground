"""Email channel."""
from __future__ import annotations

import logging
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

from ..config import settings
from .channel import NotificationChannel
from .formatter import format_message

if TYPE_CHECKING:
    from ..strategies.base import Triggered

logger = logging.getLogger(__name__)


class EmailChannel(NotificationChannel):
    def send(self, strategy_name: str, triggered: list["Triggered"]) -> None:
        if not (settings.SMTP_USER and settings.NOTIFICATION_EMAIL_TO):
            logger.warning("Email not configured, skipping")
            return

        body = format_message(strategy_name, triggered)
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = Header(f"【监控告警】{strategy_name}", "utf-8")
        msg["From"]    = settings.SMTP_USER
        msg["To"]      = settings.NOTIFICATION_EMAIL_TO

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Email sent to %s", settings.NOTIFICATION_EMAIL_TO)
