"""NotificationChannel — abstraction over delivery transports.

Each Strategy declares which channels it uses (e.g. ["email", "telegram"]).
The engine, after collecting Triggered events, dispatches them through the
matching registered channels.

Adding a new channel (DingTalk, Webhook, ...) is one new module + one
register() call at startup.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..strategies.base import Triggered

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, strategy_name: str, triggered: list["Triggered"]) -> None: ...


_REGISTRY: dict[str, NotificationChannel] = {}


def register_channel(name: str, channel: NotificationChannel) -> None:
    _REGISTRY[name] = channel


def dispatch(
    strategy_name: str,
    triggered: list["Triggered"],
    channel_names: list[str],
) -> None:
    if not triggered:
        return
    for n in channel_names:
        ch = _REGISTRY.get(n)
        if ch is None:
            logger.warning("Channel %s not registered, skipping", n)
            continue
        try:
            ch.send(strategy_name, triggered)
        except Exception:
            logger.exception("Channel %s failed for strategy %s", n, strategy_name)


def known_channels() -> list[str]:
    return sorted(_REGISTRY.keys())
