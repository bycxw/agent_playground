"""Symbol — canonical stock identifier across all systems.

Eliminates the format chaos that earlier code carried around:
  - "600000.SH"        display / external API output
  - "sh.600000"        baostock raw API
  - "SH600000"         canonical (also qlib_research parquet output)
  - "sh600000"         qlib internal
  - "stock_sh_600000"  zvt legacy entity_id

`Symbol.parse()` accepts all five. The canonical form is `SH600000`,
used as DB primary key and for logging.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


_EXCHANGES = ("SH", "SZ", "HK")

# Recognise each input format. All tolerate case in the exchange part.
_RE_DISPLAY   = re.compile(r"^(?P<code>\d{4,6})\.(?P<ex>SH|SZ|HK)$", re.IGNORECASE)
_RE_BAOSTOCK  = re.compile(r"^(?P<ex>SH|SZ|HK)\.(?P<code>\d{4,6})$", re.IGNORECASE)
_RE_CANONICAL = re.compile(r"^(?P<ex>SH|SZ|HK)(?P<code>\d{4,6})$", re.IGNORECASE)
_RE_ZVT       = re.compile(r"^stock_(?P<ex>sh|sz|hk)_(?P<code>\d{4,6})$", re.IGNORECASE)

_PATTERNS = (_RE_DISPLAY, _RE_BAOSTOCK, _RE_CANONICAL, _RE_ZVT)


@dataclass(frozen=True, slots=True)
class Symbol:
    """Canonical stock identifier.

    Build via `Symbol.parse(s)` from any known format, or directly via
    `Symbol(exchange="SH", code="600000")`. Render via the format methods.
    """
    exchange: str   # "SH" / "SZ" / "HK"
    code: str       # "600000" (A-share, 6 digits) or "00700" (HK, 4-5 digits)

    def __post_init__(self) -> None:
        if self.exchange not in _EXCHANGES:
            raise ValueError(f"Invalid exchange: {self.exchange!r}")
        if not self.code.isdigit():
            raise ValueError(f"Code must be all digits: {self.code!r}")
        if self.exchange in ("SH", "SZ") and len(self.code) != 6:
            raise ValueError(f"A-share code must be 6 digits: {self.code!r}")
        if self.exchange == "HK" and not (4 <= len(self.code) <= 5):
            raise ValueError(f"HK code must be 4-5 digits: {self.code!r}")

    @classmethod
    def parse(cls, s: str) -> Symbol:
        s = s.strip()
        for pat in _PATTERNS:
            m = pat.match(s)
            if m:
                return cls(exchange=m.group("ex").upper(), code=m.group("code"))
        raise ValueError(f"Unrecognised symbol format: {s!r}")

    # ── Renderers ─────────────────────────────────────────────────────────────

    def canonical(self) -> str:
        """SH600000 — DB primary key, parquet, internal use."""
        return f"{self.exchange}{self.code}"

    def baostock(self) -> str:
        """sh.600000 — baostock API."""
        return f"{self.exchange.lower()}.{self.code}"

    def qlib(self) -> str:
        """sh600000 — qlib internal."""
        return f"{self.exchange.lower()}{self.code}"

    def display(self) -> str:
        """600000.SH — human-readable / external API output."""
        return f"{self.code}.{self.exchange}"

    def __str__(self) -> str:
        return self.canonical()
