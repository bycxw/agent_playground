"""Shared message formatting for notification channels."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..strategies.base import Triggered


_EVENT_PREFIX = {
    "match":      "📊",
    "enter_topk": "📈",
    "exit_topk":  "📉",
}


def format_message(strategy_name: str, triggered: list["Triggered"]) -> str:
    """Plain-text message body shared across email/telegram channels."""
    if not triggered:
        return ""

    # Group by event_type to keep the message readable when both
    # entries and exits fire on the same check.
    by_type: dict[str, list["Triggered"]] = {}
    for t in triggered:
        by_type.setdefault(t.event_type, []).append(t)

    lines: list[str] = [f"📊 {strategy_name}", f"触发 {len(triggered)} 项", ""]
    for event_type, items in by_type.items():
        prefix = _EVENT_PREFIX.get(event_type, "•")
        lines.append(f"{prefix} {event_type} ({len(items)})")
        for t in items[:10]:
            snap = " | ".join(f"{k}: {v}" for k, v in t.snapshot.items() if v is not None)
            lines.append(f"  {t.name} ({t.symbol}): {snap}")
        if len(items) > 10:
            lines.append(f"  ... 还有 {len(items) - 10} 项")
        lines.append("")
    return "\n".join(lines).rstrip()
