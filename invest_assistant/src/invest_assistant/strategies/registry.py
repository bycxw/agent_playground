"""Strategy type registry — maps `type_name` strings to concrete classes.

Subclasses register via `@register`. Persistence reads `type` from the
DB and looks up the class here to deserialise.
"""
from __future__ import annotations

from typing import TypeVar

from .base import Strategy

T = TypeVar("T", bound=type[Strategy])

_REGISTRY: dict[str, type[Strategy]] = {}


def register(cls: T) -> T:
    name = cls.type_name()
    if name in _REGISTRY and _REGISTRY[name] is not cls:
        raise ValueError(f"Strategy type {name!r} already registered")
    _REGISTRY[name] = cls
    return cls


def lookup(type_name: str) -> type[Strategy]:
    if type_name not in _REGISTRY:
        raise KeyError(f"Unknown strategy type: {type_name!r}")
    return _REGISTRY[type_name]


def known_types() -> list[str]:
    return sorted(_REGISTRY.keys())
