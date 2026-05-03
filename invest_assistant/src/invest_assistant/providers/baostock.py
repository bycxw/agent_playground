"""Data layer backed by local SQLite cache populated via baostock syncs."""
import sqlite3
import logging
import pandas as pd
from typing import Optional
from pathlib import Path

from ..config import settings

logger = logging.getLogger(__name__)

DB_PATH: Path = settings.BAOSTOCK_DATA_DIR / "cache.db"

_DDL = """
CREATE TABLE IF NOT EXISTS stocks (
    entity_id  TEXT PRIMARY KEY,
    symbol     TEXT NOT NULL,
    name       TEXT NOT NULL,
    exchange   TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS financial_metrics (
    entity_id           TEXT PRIMARY KEY,
    report_date         TEXT,
    pe_ttm              REAL,
    pb                  REAL,
    roe                 REAL,
    gross_margin        REAL,
    debt_to_asset_ratio REAL,
    updated_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_kdata (
    entity_id  TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open       REAL,
    high       REAL,
    low        REAL,
    close      REAL,
    volume     REAL,
    amount     REAL,
    PRIMARY KEY (entity_id, trade_date)
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


# ── Symbol / entity_id helpers ────────────────────────────────────────────────

def get_entity_id(symbol: str, exchange: str = "SH") -> str:
    """('600000', 'SH') → 'stock_sh_600000'."""
    return f"stock_{exchange.lower()}_{symbol}"


def parse_entity_id(entity_id: str) -> tuple:
    """'stock_sh_600000' → ('600000', 'SH')."""
    parts = entity_id.split("_")
    if len(parts) >= 3:
        ex_map = {"sh": "SH", "sz": "SZ", "hk": "HK"}
        return parts[2], ex_map.get(parts[1], "SH")
    return entity_id, "SH"


def _parse_symbol(symbol: str) -> tuple:
    """'600000.SH' → ('600000', 'SH');  '000001.SZ' → ('000001', 'SZ')."""
    if "." in symbol:
        code, ex = symbol.rsplit(".", 1)
        return code, ex.upper()
    return symbol, "SH"


# ── Public query API ──────────────────────────────────────────────────────────

def query_stock_list() -> pd.DataFrame:
    """Read stock list from local cache.

    Returns:
        DataFrame with columns: entity_id, code, name, exchange
    """
    conn = _open()
    df = pd.read_sql(
        "SELECT entity_id, symbol AS code, name, exchange FROM stocks ORDER BY entity_id",
        conn,
    )
    conn.close()
    return df


def query_daily_kdata(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    **_,
) -> pd.DataFrame:
    """Query daily OHLCV data for one stock directly from baostock (no local cache).

    Args:
        symbol: '600000.SH' or '000001.SZ'
        start_date: 'YYYY-MM-DD'
        end_date:   'YYYY-MM-DD'

    Returns:
        DataFrame with columns: date, open, high, low, close, volume, amount
    """
    import baostock as bs
    from datetime import date, timedelta

    code, ex = _parse_symbol(symbol)
    bs_code = f"{ex.lower()}.{code}"

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
            bs_code,
            "date,open,high,low,close,volume,amount",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3",
        )
        rows = []
        while rs2.error_code == "0" and rs2.next():
            rows.append(rs2.get_row_data())
    finally:
        bs.logout()

    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "amount"])

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "amount"])
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def query_financial_metrics(symbol: str, **_) -> pd.DataFrame:
    """Query financial metrics for a single stock from local cache.

    Returns:
        DataFrame with financial metric columns; empty if not cached yet.
    """
    code, ex = _parse_symbol(symbol)
    entity_id = get_entity_id(code, ex)
    conn = _open()
    df = pd.read_sql(
        "SELECT * FROM financial_metrics WHERE entity_id = ?",
        conn,
        params=(entity_id,),
    )
    conn.close()
    return df


def query_all_financial_metrics(market: str = "A股") -> pd.DataFrame:
    """Read all financial metrics + stock metadata from local cache.

    Returns:
        DataFrame with columns:
            entity_id, report_date, pe_ttm, pb, roe, gross_margin,
            debt_to_asset_ratio, revenue_yoy, net_income_yoy, symbol, name
    """
    exchange_map = {"A股": ("SH", "SZ"), "港股": ("HK",), "ALL": None}
    exchanges = exchange_map.get(market, ("SH", "SZ"))

    conn = _open()
    if exchanges:
        ph = ",".join("?" * len(exchanges))
        df = pd.read_sql(
            f"""
            SELECT f.entity_id, f.report_date, f.pe_ttm, f.pb, f.roe,
                   f.gross_margin, f.debt_to_asset_ratio,
                   s.symbol, s.name
            FROM financial_metrics f
            JOIN stocks s ON f.entity_id = s.entity_id
            WHERE s.exchange IN ({ph})
            """,
            conn,
            params=list(exchanges),
        )
    else:
        df = pd.read_sql(
            """
            SELECT f.entity_id, f.report_date, f.pe_ttm, f.pb, f.roe,
                   f.gross_margin, f.debt_to_asset_ratio,
                   s.symbol, s.name
            FROM financial_metrics f
            JOIN stocks s ON f.entity_id = s.entity_id
            """,
            conn,
        )
    conn.close()

    # Phase 1: revenue_yoy / net_income_yoy not yet calculated from baostock
    df["revenue_yoy"] = float("nan")
    df["net_income_yoy"] = float("nan")

    return df


def get_stock_info(symbol: str, **_) -> dict:
    """Get basic info for a stock from local cache.

    Returns:
        dict with keys: entity_id, symbol, name, exchange; empty if not cached.
    """
    code, ex = _parse_symbol(symbol)
    entity_id = get_entity_id(code, ex)
    conn = _open()
    row = conn.execute(
        "SELECT entity_id, symbol, name, exchange FROM stocks WHERE entity_id = ?",
        (entity_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {}
