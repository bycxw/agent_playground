"""Strategy abstractions.

Importing this package registers all built-in strategy types (factor_rule,
signal_topk, ...) via the `@register` decorator side-effect.
"""
from .base import Condition, Strategy, Triggered
from .factor_rule import FactorRuleStrategy
from .registry import known_types, lookup, register

__all__ = [
    "Strategy",
    "Triggered",
    "Condition",
    "FactorRuleStrategy",
    "register",
    "lookup",
    "known_types",
]
