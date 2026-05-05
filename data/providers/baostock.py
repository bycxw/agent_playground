"""baostock-backed query layer over local SQLite cache.

Symbol identification: every row keys on `symbol` in canonical form
("SH600000"). The Symbol class (`common.symbols`) is used at every
boundary that accepts user input — internally we store and pass the
canonical string for DataFrame/SQL friendliness.
"""
import logging
import sqlite3
from typing import Optional

import pandas as pd

from common.symbols import Symbol

from ..config import DB_PATH

logger = logging.getLogger(__name__)


_KDATA_FIELDS = "date,open,high,low,close,volume,amount"

_DDL = """
CREATE TABLE IF NOT EXISTS stocks (
    symbol     TEXT PRIMARY KEY,        -- canonical, e.g. "SH600000"
    code       TEXT NOT NULL,           -- "600000"
    exchange   TEXT NOT NULL,           -- "SH" / "SZ" / "HK"
    name       TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS financial_metrics (
    symbol              TEXT PRIMARY KEY,
    report_date         TEXT,
    pe_ttm              REAL,
    pb                  REAL,
    roe                 REAL,
    gross_margin        REAL,
    debt_to_asset_ratio REAL,
    updated_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_kdata (
    symbol     TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open       REAL,
    high       REAL,
    low        REAL,
    close      REAL,
    volume     REAL,
    amount     REAL,
    PRIMARY KEY (symbol, trade_date)
);
"""


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_DDL)
    conn.commit()
    conn.close()


def _open() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _canonical(symbol: str | Symbol) -> str:
    """Coerce any input to canonical 'SH600000' form."""
    return symbol.canonical() if isinstance(symbol, Symbol) else Symbol.parse(symbol).canonical()


# ── Public query API ──────────────────────────────────────────────────────────

def query_stock_list() -> pd.DataFrame:
    """All cached stocks. Columns: symbol, code, exchange, name."""
    conn = _open()
    df = pd.read_sql(
        "SELECT symbol, code, exchange, name FROM stocks ORDER BY symbol",
        conn,
    )
    conn.close()
    return df


def query_daily_kdata(
    symbol: str | Symbol,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """Daily OHLCV for one stock, fetched live from baostock (no caching here).

    Args:
        symbol: any format accepted by Symbol.parse (e.g. "600000.SH",
                "SH600000", or a Symbol instance).
        start_date: 'YYYY-MM-DD'; defaults to 1 year ago.
        end_date:   'YYYY-MM-DD'; defaults to today.
    """
    import baostock as bs
    from datetime import date, timedelta

    sym = Symbol.parse(symbol) if not isinstance(symbol, Symbol) else symbol

    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")

    rs = bs.login()
    if rs.error_code != "0":
        logger.error("baostock login failed: %s", rs.error_msg)
        return pd.DataFrame()

    try:
        rs2 = bs.query_history_k_data_plus(
            sym.baostock(),
            _KDATA_FIELDS,
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3",  # 不复权: raw prices, correct for live display
        )
        rows = []
        while rs2.error_code == "0" and rs2.next():
            rows.append(rs2.get_row_data())
    finally:
        bs.logout()

    if not rows:
        return pd.DataFrame(columns=rs2.fields)

    df = pd.DataFrame(rows, columns=rs2.fields)
    for col in df.columns:
        if col != "date":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def query_financial_metrics(symbol: str | Symbol) -> pd.DataFrame:
    """Cached financial metrics for one stock (empty if not yet synced)."""
    canon = _canonical(symbol)
    conn = _open()
    df = pd.read_sql(
        "SELECT * FROM financial_metrics WHERE symbol = ?",
        conn,
        params=(canon,),
    )
    conn.close()
    return df


def query_all_financial_metrics(market: str = "A股") -> pd.DataFrame:
    """All cached financial metrics joined with stock metadata.

    Returns:
        Columns: symbol, code, exchange, name, report_date, pe_ttm, pb, roe,
                 gross_margin, debt_to_asset_ratio, revenue_yoy, net_income_yoy.
    """
    exchange_map = {"A股": ("SH", "SZ"), "港股": ("HK",), "ALL": None}
    exchanges = exchange_map.get(market, ("SH", "SZ"))

    conn = _open()
    if exchanges:
        ph = ",".join("?" * len(exchanges))
        df = pd.read_sql(
            f"""
            SELECT s.symbol, s.code, s.exchange, s.name,
                   f.report_date, f.pe_ttm, f.pb, f.roe,
                   f.gross_margin, f.debt_to_asset_ratio
            FROM financial_metrics f
            JOIN stocks s ON f.symbol = s.symbol
            WHERE s.exchange IN ({ph})
            """,
            conn,
            params=list(exchanges),
        )
    else:
        df = pd.read_sql(
            """
            SELECT s.symbol, s.code, s.exchange, s.name,
                   f.report_date, f.pe_ttm, f.pb, f.roe,
                   f.gross_margin, f.debt_to_asset_ratio
            FROM financial_metrics f
            JOIN stocks s ON f.symbol = s.symbol
            """,
            conn,
        )
    conn.close()

    # Phase 1: revenue_yoy / net_income_yoy not yet derived from baostock.
    df["revenue_yoy"] = float("nan")
    df["net_income_yoy"] = float("nan")

    return df


def get_stock_info(symbol: str | Symbol) -> dict:
    """Basic info for one stock. Empty dict if not cached."""
    canon = _canonical(symbol)
    conn = _open()
    row = conn.execute(
        "SELECT symbol, code, exchange, name FROM stocks WHERE symbol = ?",
        (canon,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {}
