"""Strategy ABC — polymorphic replacement for the old MonitorRule.

A Strategy is the unit of evaluation: it holds its own config, owns its
universe selection, and produces a list of Triggered events when called
at a given asof. The engine just iterates active strategies and calls
`evaluate(asof)`; it does not know how each type works internally.

Concrete subclasses (factor_rule, signal_topk, llm_score, agent, ...)
register themselves via `@register` so they can be deserialised from
DB rows.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Triggered:
    """One stock matched a strategy at `asof`.

    `event_type` distinguishes strategy semantics:
      - "match"      : factor-rule condition met
      - "enter_topk" : entered the Top-K of a signal-based strategy
      - "exit_topk"  : exited the Top-K
    """
    symbol: str                  # canonical "SH600000"
    name: str
    snapshot: dict[str, Any]
    event_type: str = "match"


@dataclass(slots=True)
class Condition:
    """Single field/op/value comparison used by FactorRuleStrategy."""
    field: str
    op: str        # < <= > >= == !=
    value: float


@dataclass
class Strategy(ABC):
    """Abstract strategy. Subclasses implement evaluate() + (de)serialise."""

    name: str
    market: str = "A股"
    channels: list[str] = field(default_factory=list)
    strategy_id: str = field(default_factory=lambda: str(uuid4()))
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @abstractmethod
    def evaluate(self, asof: date) -> list[Triggered]:
        """Return all stocks matching this strategy at `asof`."""

    @classmethod
    @abstractmethod
    def type_name(cls) -> str:
        """Stable string identifier used in the DB `type` column."""

    @abstractmethod
    def to_config(self) -> dict[str, Any]:
        """Serialise strategy-specific params (everything not on Strategy itself)."""

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict[str, Any], **base_fields: Any) -> Strategy:
        """Inverse of to_config; **base_fields contains shared Strategy fields."""
