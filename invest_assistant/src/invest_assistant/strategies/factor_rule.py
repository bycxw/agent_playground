"""FactorRuleStrategy — multi-condition fundamental screen.

Direct replacement for the old MonitorRule (PE<15 AND ROE>10 etc.).
Reads cached fundamentals once per market, evaluates conditions row by
row, returns Triggered for matches.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd

from data import query_all_financial_metrics

from .base import Condition, Strategy, Triggered
from .registry import register

logger = logging.getLogger(__name__)


_OPS = {
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _evaluate_condition(row: pd.Series, cond: Condition) -> bool:
    if cond.field not in row.index:
        return False
    val = row[cond.field]
    if pd.isna(val):
        return False
    op = _OPS.get(cond.op)
    if op is None:
        return False
    try:
        return op(float(val), float(cond.value))
    except (ValueError, TypeError):
        return False


@register
@dataclass
class FactorRuleStrategy(Strategy):
    """All conditions joined by `condition_logic` (AND/OR)."""

    conditions: list[Condition] = field(default_factory=list)
    condition_logic: str = "AND"

    def evaluate(self, asof: date) -> list[Triggered]:
        df = query_all_financial_metrics(market=self.market)
        if df.empty:
            logger.warning("FactorRuleStrategy %s: empty market data", self.name)
            return []

        joiner = all if self.condition_logic == "AND" else any
        triggered: list[Triggered] = []

        for _, row in df.iterrows():
            if not joiner(_evaluate_condition(row, c) for c in self.conditions):
                continue
            snapshot = {c.field: row.get(c.field) for c in self.conditions}
            triggered.append(Triggered(
                symbol=row["symbol"],
                name=row.get("name", ""),
                snapshot=snapshot,
                event_type="match",
            ))
        logger.info("Strategy %s matched %d stocks", self.name, len(triggered))
        return triggered

    @classmethod
    def type_name(cls) -> str:
        return "factor_rule"

    def to_config(self) -> dict[str, Any]:
        return {
            "conditions": [
                {"field": c.field, "op": c.op, "value": c.value}
                for c in self.conditions
            ],
            "condition_logic": self.condition_logic,
        }

    @classmethod
    def from_config(cls, config: dict[str, Any], **base_fields: Any) -> "FactorRuleStrategy":
        conditions = [Condition(**c) for c in config.get("conditions", [])]
        return cls(
            conditions=conditions,
            condition_logic=config.get("condition_logic", "AND"),
            **base_fields,
        )
