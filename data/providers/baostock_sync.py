"""Sync layer — pulls from baostock API into the local SQLite cache."""
import logging
import sqlite3
import time
from datetime import date, datetime, timedelta
from typing import Iterable, Optional

from common.symbols import Symbol

from ..config import DB_PATH
from .baostock import init_db

logger = logging.getLogger(__name__)


_SLEEP = 0.05  # ~20 req/s, well within baostock limits


def _open() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _to_float(val) -> Optional[float]:
    try:
        return float(val) if val not in (None, "", "None") else None
    except (ValueError, TypeError):
        return None


def _latest_quarter() -> tuple[int, int]:
    """Most recently completed (year, quarter)."""
    today = date.today()
    q = (today.month - 1) // 3   # 0 in Jan-Mar (Q1 not done yet)
    if q == 0:
        return today.year - 1, 4
    return today.year, q


# ── Stock metadata sync ──────────────────────────────────────────────────────

def sync_stock_meta() -> dict:
    """Download active A/B-share list from baostock.

    Returns:
        {'status': 'success', 'count': N} or {'status': 'error', 'error': ...}
    """
    import baostock as bs

    init_db()
    logger.info("Syncing stock metadata...")

    rs = bs.login()
    if rs.error_code != "0":
        return {"status": "error", "error": f"login failed: {rs.error_msg}"}

    try:
        rs2 = bs.query_stock_basic()
        rows = []
        while rs2.error_code == "0" and rs2.next():
            row = rs2.get_row_data()
            # fields: code, code_name, ipoDate, outDate, type, status
            # type='1' = 股票, status='1' = 上市中
            if row[4] == "1" and row[5] == "1":
                rows.append(row)
    finally:
        bs.logout()

    if not rows:
        return {"status": "error", "error": "empty response from baostock"}

    now = datetime.now().isoformat()
    records = []
    for row in rows:
        sym = Symbol.parse(row[0])           # baostock format "sh.600000"
        records.append((sym.canonical(), sym.code, sym.exchange, row[1], now))

    conn = _open()
    with conn:
        conn.execute("DELETE FROM stocks")
        conn.executemany(
            "INSERT INTO stocks (symbol, code, exchange, name, updated_at) VALUES (?,?,?,?,?)",
            records,
        )
    conn.close()

    logger.info("Stock meta synced: %d stocks", len(records))
    return {"status": "success", "count": len(records)}


# ── Financial data sync ──────────────────────────────────────────────────────

def _fetch_quarterly(bs, sym: Symbol, year: int, quarter: int) -> dict:
    """roe, gross_margin, debt_to_asset_ratio for one stock-quarter.

    baostock returns ratios as decimals (0.106 = 10.6%); we store as
    percentages so screener thresholds like roe_min=10 work directly.
    """
    result: dict = {}
    bs_code = sym.baostock()

    rs = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
    rows = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    if rows:
        d = dict(zip(rs.fields, rows[0]))
        result["report_date"] = d.get("statDate", "")
        v = _to_float(d.get("roeAvg"));    result["roe"]          = v * 100 if v is not None else None
        v = _to_float(d.get("gpMargin"));  result["gross_margin"] = v * 100 if v is not None else None
    time.sleep(_SLEEP)

    rs = bs.query_balance_data(code=bs_code, year=year, quarter=quarter)
    rows = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    if rows:
        d = dict(zip(rs.fields, rows[0]))
        v = _to_float(d.get("liabilityToAsset"))
        result["debt_to_asset_ratio"] = v * 100 if v is not None else None
    time.sleep(_SLEEP)

    return result


def _fetch_valuation(bs, sym: Symbol) -> dict:
    """Latest pe_ttm and pb from recent daily kdata."""
    end_date = date.today().strftime("%Y-%m-%d")
    start_date = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")

    rs = bs.query_history_k_data_plus(
        sym.baostock(),
        "date,peTTM,pbMRQ",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3",  # 不复权: PE/PB are valuation ratios, price adjustment irrelevant
    )
    rows = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    time.sleep(_SLEEP)

    for raw in reversed(rows):
        pe = _to_float(raw[1])
        pb = _to_float(raw[2])
        if pe is not None or pb is not None:
            return {"pe_ttm": pe, "pb": pb}

    return {}


def sync_financial_data(symbols: Optional[Iterable[str | Symbol]] = None) -> dict:
    """Sync financial metrics for every cached A-share (or the given subset).

    Time estimate: ~20 min for all ~5000 A-share stocks.

    Args:
        symbols: e.g. ["SH600000", "SZ000001"]; None = all A-shares in cache.
    """
    import baostock as bs

    init_db()
    conn = _open()
    if symbols:
        canon_list = [Symbol.parse(s).canonical() if not isinstance(s, Symbol) else s.canonical()
                      for s in symbols]
        ph = ",".join("?" * len(canon_list))
        rows = conn.execute(
            f"SELECT symbol, code, exchange FROM stocks "
            f"WHERE symbol IN ({ph}) AND exchange IN ('SH','SZ')",
            canon_list,
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT symbol, code, exchange FROM stocks WHERE exchange IN ('SH','SZ')"
        ).fetchall()
    conn.close()

    if not rows:
        return {"status": "error", "error": "no stocks in cache — run sync_stock_meta first"}

    year, q = _latest_quarter()
    prev_year, prev_q = (year, q - 1) if q > 1 else (year - 1, 4)
    logger.info("Syncing financial data: %d stocks, target %dQ%d", len(rows), year, q)

    rs = bs.login()
    if rs.error_code != "0":
        return {"status": "error", "error": f"login failed: {rs.error_msg}"}

    try:
        now = datetime.now().isoformat()
        db = _open()
        ok = err = 0

        for i, (canon, code, exchange) in enumerate(rows):
            sym = Symbol(exchange=exchange, code=code)
            if i % 100 == 0:
                logger.info("  [%d/%d] %s", i, len(rows), canon)

            try:
                data = _fetch_quarterly(bs, sym, year, q)
                # Fall back to previous quarter if current one has no data yet.
                if not data.get("report_date"):
                    data = _fetch_quarterly(bs, sym, prev_year, prev_q)

                data.update(_fetch_valuation(bs, sym))
                data["symbol"] = canon
                data["updated_at"] = now

                with db:
                    db.execute(
                        """INSERT OR REPLACE INTO financial_metrics
                           (symbol, report_date, pe_ttm, pb, roe,
                            gross_margin, debt_to_asset_ratio, updated_at)
                           VALUES (:symbol, :report_date, :pe_ttm, :pb, :roe,
                                   :gross_margin, :debt_to_asset_ratio, :updated_at)""",
                        {
                            "symbol":              canon,
                            "report_date":         data.get("report_date"),
                            "pe_ttm":              data.get("pe_ttm"),
                            "pb":                  data.get("pb"),
                            "roe":                 data.get("roe"),
                            "gross_margin":        data.get("gross_margin"),
                            "debt_to_asset_ratio": data.get("debt_to_asset_ratio"),
                            "updated_at":          now,
                        },
                    )
                ok += 1
            except Exception as exc:
                logger.warning("  %s failed: %s", canon, exc)
                err += 1

        db.close()
    finally:
        bs.logout()

    logger.info("Financial sync done — ok=%d, errors=%d", ok, err)
    return {"status": "success", "success": ok, "errors": err}


# ── Daily kdata sync ─────────────────────────────────────────────────────────

def sync_daily_kdata(symbols: Optional[Iterable[str | Symbol]] = None, **_) -> dict:
    """Cache daily kdata for explicit symbols.

    `symbols=None` is a no-op — for ad-hoc lookups, callers should use
    `query_daily_kdata()` which fetches live without caching.
    """
    if not symbols:
        return {
            "status": "skipped",
            "reason": "no symbols specified; kdata fetched on-demand per stock",
        }

    import baostock as bs

    init_db()
    end_date = date.today().strftime("%Y-%m-%d")
    start_date = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")

    rs = bs.login()
    if rs.error_code != "0":
        return {"status": "error", "error": f"login failed: {rs.error_msg}"}

    try:
        conn = _open()
        ok = 0

        for s in symbols:
            sym = Symbol.parse(s) if not isinstance(s, Symbol) else s
            canon = sym.canonical()

            rs2 = bs.query_history_k_data_plus(
                sym.baostock(),
                "date,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3",
            )
            rows = []
            while rs2.error_code == "0" and rs2.next():
                rows.append(rs2.get_row_data())

            with conn:
                for r in rows:
                    conn.execute(
                        """INSERT OR REPLACE INTO daily_kdata
                           (symbol, trade_date, open, high, low, close, volume, amount)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (
                            canon, r[0],
                            _to_float(r[1]), _to_float(r[2]),
                            _to_float(r[3]), _to_float(r[4]),
                            _to_float(r[5]), _to_float(r[6]),
                        ),
                    )
            ok += 1
            time.sleep(_SLEEP)

        conn.close()
    finally:
        bs.logout()

    return {"status": "success", "count": ok}


def sync_all() -> dict:
    """Stock metadata → financial metrics. Daily kdata stays on-demand."""
    logger.info("Starting full sync...")
    return {
        "meta":         sync_stock_meta(),
        "financial":    sync_financial_data(),
        "kline":        sync_daily_kdata(),
        "completed_at": datetime.now().isoformat(),
    }
