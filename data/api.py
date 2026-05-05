"""Public, provider-agnostic data interface.

All functions take an `asof` date where applicable, and are responsible
for enforcing point-in-time correctness — never returning data the
caller could not have known at `asof`.

Implementations are provided by `data.providers.*`.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd

from common.symbols import Symbol


# ── Prices ────────────────────────────────────────────────────────────────────

def get_prices(
    symbols: Iterable[Symbol],
    start: date,
    end: date,
    adjust: str = "raw",
) -> pd.DataFrame:
    """Daily OHLCV for `symbols` between `start` and `end` (inclusive).

    Args:
        adjust: "raw" (不复权), "forward" (前复权), "backward" (后复权).

    Returns:
        Long-format DataFrame: symbol, date, open, high, low, close, volume, amount.
    """
    raise NotImplementedError("Wired in Step 3")


# ── Fundamentals ──────────────────────────────────────────────────────────────

def get_fundamentals(symbols: Iterable[Symbol], asof: date) -> pd.DataFrame:
    """Latest financial metrics knowable at `asof` (PIT-correct).

    Returns:
        DataFrame indexed by symbol, columns: pe_ttm, pb, roe, gross_margin,
        debt_to_asset_ratio, report_date, pub_date.
    """
    raise NotImplementedError("Wired in Step 3")


# ── Universe ──────────────────────────────────────────────────────────────────

def get_universe(name: str, asof: date) -> list[Symbol]:
    """PIT-correct universe membership at `asof`.

    Args:
        name: e.g. "csi300", "all_a", or a user-defined watchlist name.
    """
    raise NotImplementedError("Wired in Step 3")


# ── Stock metadata ────────────────────────────────────────────────────────────

def get_stock_list() -> pd.DataFrame:
    """Active stock universe (current). Columns: symbol, name, exchange."""
    raise NotImplementedError("Wired in Step 3")
