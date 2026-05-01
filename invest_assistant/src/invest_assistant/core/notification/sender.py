"""Notification sender - handles sending alerts."""
import logging
from typing import List, Dict, Any

from ...config import settings

logger = logging.getLogger(__name__)


class NotificationSender:
    """Send notifications via various channels."""

    def __init__(self):
        self.email_enabled = settings.NOTIFICATION_EMAIL_ENABLED
        self.telegram_enabled = settings.NOTIFICATION_TELEGRAM_ENABLED

    def send(
        self,
        rule_name: str,
        stocks: List[Dict[str, Any]],
        conditions: List[dict],
    ) -> None:
        """Send notification for triggered rule.

        Args:
            rule_name: Name of the triggered rule
            stocks: List of stocks that triggered
            conditions: Rule conditions that were met
        """
        if not stocks:
            return

        message = self._format_message(rule_name, stocks, conditions)

        # Send to all enabled channels
        if self.email_enabled:
            self._send_email(message)

        if self.telegram_enabled:
            self._send_telegram(message)

    def _format_message(
        self,
        rule_name: str,
        stocks: List[Dict],
        conditions: List[dict],
    ) -> str:
        """Format notification message."""
        lines = [
            f"📊 监控告警: {rule_name}",
            f"触发股票数: {len(stocks)}",
            "",
            "条件:",
        ]

        for cond in conditions:
            lines.append(f"  - {cond['field']} {cond['op']} {cond['value']}")

        lines.append("")
        lines.append("触发股票:")

        for stock in stocks[:10]:  # Limit to 10 in message
            name = stock.get("name", "")
            symbol = stock.get("symbol", "")
            snapshot = stock.get("snapshot", {})

            values = " | ".join(
                f"{k}: {v}" for k, v in snapshot.items() if v is not None
            )
            lines.append(f"  {name} ({symbol}): {values}")

        if len(stocks) > 10:
            lines.append(f"  ... 还有 {len(stocks) - 10} 只")

        return "\n".join(lines)

    def _send_email(self, message: str) -> None:
        """Send email notification."""
        if not settings.SMTP_USER or not settings.NOTIFICATION_EMAIL_TO:
            logger.warning("Email not configured, skipping")
            return

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.header import Header

            msg = MIMEText(message, "plain", "utf-8")
            msg["Subject"] = Header("【监控告警】投资助手", "utf-8")
            msg["From"] = settings.SMTP_USER
            msg["To"] = settings.NOTIFICATION_EMAIL_TO

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email sent to {settings.NOTIFICATION_EMAIL_TO}")

        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    def _send_telegram(self, message: str) -> None:
        """Send Telegram notification."""
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            logger.warning("Telegram not configured, skipping")
            return

        try:
            import httpx

            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
            }

            response = httpx.post(url, data=data, timeout=10)
            response.raise_for_status()

            logger.info("Telegram message sent")

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")