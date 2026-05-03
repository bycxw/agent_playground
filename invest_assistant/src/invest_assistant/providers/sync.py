"""Data synchronisation — downloads from baostock into local SQLite cache."""
import logging
import time
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional, List

from ..config import settings
from .baostock import init_db, DB_PATH

logger = logging.getLogger(__name__)

_SLEEP = 0.05  # seconds between API calls (~20 req/s, well within baostock limits)


def _open() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _to_float(val) -> Optional[float]:
    try:
        return float(val) if val not in (None, "", "None") else None
    except (ValueError, TypeError):
        return None


def _latest_quarter() -> tuple:
    """Return the most recently completed (year, quarter)."""
    today = date.today()
    q = (today.month - 1) // 3   # 0 when in Jan-Mar (Q1 not yet done)
    if q == 0:
        return today.year - 1, 4
    return today.year, q


def sync_stock_meta() -> dict:
    """Download active A-share & B-share stock list from baostock into local SQLite.

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
            # type='1' = 股票; status='1' = 上市中
            if row[4] == "1" and row[5] == "1":
                rows.append(row)
    finally:
        bs.logout()

    if not rows:
        return {"status": "error", "error": "empty response from baostock"}

    now = datetime.now().isoformat()
    records = []
    for row in rows:
        bs_code = row[0]   # "sh.600000"
        name = row[1]
        ex, code = bs_code.split(".", 1)
        records.append((
            f"stock_{ex}_{code}",  # entity_id
            code,                  # symbol
            name,
            ex.upper(),            # SH / SZ
            now,
        ))

    conn = _open()
    with conn:
        conn.execute("DELETE FROM stocks")
        conn.executemany(
            "INSERT INTO stocks (entity_id, symbol, name, exchange, updated_at) VALUES (?,?,?,?,?)",
            records,
        )
    conn.close()

    logger.info("Stock meta synced: %d stocks", len(records))
    return {"status": "success", "count": len(records)}


def _fetch_quarterly(bs, bs_code: str, year: int, quarter: int) -> dict:
    """Fetch roe, gross_margin, debt_to_asset_ratio for one stock and quarter.

    baostock returns ratios as decimals (e.g. 0.106 = 10.6%); we store as
    percentages so the screener thresholds like roe_min=10 work directly.
    """
    result: dict = {}

    rs = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
    rows = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    if rows:
        d = dict(zip(rs.fields, rows[0]))
        result["report_date"] = d.get("statDate", "")
        v = _to_float(d.get("roeAvg"))
        result["roe"] = v * 100 if v is not None else None
        v = _to_float(d.get("gpMargin"))
        result["gross_margin"] = v * 100 if v is not None else None
    time.sleep(_SLEEP)

    # balance fields: currentRatio, quickRatio, cashRatio, YOYLiability,
    #                 liabilityToAsset, assetToEquity
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


def _fetch_valuation(bs, bs_code: str) -> dict:
    """Fetch latest pe_ttm and pb from recent daily kdata."""
    end_date = date.today().strftime("%Y-%m-%d")
    start_date = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")

    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,peTTM,pbMRQ",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3",
    )
    rows = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    time.sleep(_SLEEP)

    # Take the latest row with at least one non-None value
    for raw in reversed(rows):
        pe = _to_float(raw[1])
        pb = _to_float(raw[2])
        if pe is not None or pb is not None:
            return {"pe_ttm": pe, "pb": pb}

    return {}


def sync_financial_data(codes: Optional[List[str]] = None) -> dict:
    """Sync financial metrics (pe_ttm, pb, roe, gross_margin, debt_to_asset_ratio).

    Downloads quarterly fundamentals + latest valuation for every A-share stock
    (or the specified list) and stores results in local SQLite.

    Time estimate: ~20 min for all ~5000 A-share stocks.

    Args:
        codes: stock symbols like ['600000', '000001']; None = all stocks in DB
    """
    import baostock as bs

    init_db()
    conn = _open()
    if codes:
        ph = ",".join("?" * len(codes))
        stock_rows = conn.execute(
            f"SELECT entity_id FROM stocks WHERE symbol IN ({ph}) AND exchange IN ('SH','SZ')",
            codes,
        ).fetchall()
    else:
        stock_rows = conn.execute(
            "SELECT entity_id FROM stocks WHERE exchange IN ('SH','SZ')"
        ).fetchall()
    conn.close()

    if not stock_rows:
        return {"status": "error", "error": "no stocks in DB — run sync_stock_meta first"}

    year, q = _latest_quarter()
    prev_year, prev_q = (year, q - 1) if q > 1 else (year - 1, 4)
    logger.info("Syncing financial data: %d stocks, target %dQ%d", len(stock_rows), year, q)

    rs = bs.login()
    if rs.error_code != "0":
        return {"status": "error", "error": f"login failed: {rs.error_msg}"}

    try:
        now = datetime.now().isoformat()
        db = _open()
        ok = err = 0

        for i, (entity_id,) in enumerate(stock_rows):
            parts = entity_id.split("_")
            bs_code = f"{parts[1]}.{parts[2]}"

            if i % 100 == 0:
                logger.info("  [%d/%d] %s", i, len(stock_rows), bs_code)

            try:
                data = _fetch_quarterly(bs, bs_code, year, q)
                # Fall back to previous quarter if current has no data yet
                if not data.get("report_date"):
                    data = _fetch_quarterly(bs, bs_code, prev_year, prev_q)

                data.update(_fetch_valuation(bs, bs_code))
                data["entity_id"] = entity_id
                data["updated_at"] = now

                with db:
                    db.execute(
                        """INSERT OR REPLACE INTO financial_metrics
                           (entity_id, report_date, pe_ttm, pb, roe,
                            gross_margin, debt_to_asset_ratio, updated_at)
                           VALUES (:entity_id, :report_date, :pe_ttm, :pb, :roe,
                                   :gross_margin, :debt_to_asset_ratio, :updated_at)""",
                        {
                            "entity_id": entity_id,
                            "report_date": data.get("report_date"),
                            "pe_ttm": data.get("pe_ttm"),
                            "pb": data.get("pb"),
                            "roe": data.get("roe"),
                            "gross_margin": data.get("gross_margin"),
                            "debt_to_asset_ratio": data.get("debt_to_asset_ratio"),
                            "updated_at": now,
                        },
                    )
                ok += 1
            except Exception as exc:
                logger.warning("  %s failed: %s", bs_code, exc)
                err += 1

        db.close()
    finally:
        bs.logout()

    logger.info("Financial sync done — ok=%d, errors=%d", ok, err)
    return {"status": "success", "success": ok, "errors": err}


def sync_daily_kdata(codes: Optional[List[str]] = None, **_) -> dict:
    """Cache daily kdata for specific stocks into local SQLite.

    When codes=None, this is a no-op — the monitoring engine calls
    query_daily_kdata() on-demand per stock which is fast enough for
    single-stock lookups.

    Args:
        codes: stock symbols like ['600000.SH', '000001.SZ']
    """
    if not codes:
        return {
            "status": "skipped",
            "reason": "no codes specified; kdata fetched on-demand per stock",
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

        for symbol in codes:
            if "." in symbol:
                code, ex = symbol.rsplit(".", 1)
                bs_code = f"{ex.lower()}.{code}"
            else:
                bs_code = f"sh.{symbol}"

            ex_part, code_part = bs_code.split(".", 1)
            entity_id = f"stock_{ex_part}_{code_part}"

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

            with conn:
                for r in rows:
                    conn.execute(
                        """INSERT OR REPLACE INTO daily_kdata
                           (entity_id, trade_date, open, high, low, close, volume, amount)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (
                            entity_id, r[0],
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
    """Full sync: stock metadata → financial metrics.

    Daily kdata is fetched on-demand and not bulk-cached here.
    """
    logger.info("Starting full sync...")
    return {
        "meta": sync_stock_meta(),
        "financial": sync_financial_data(),
        "kline": {"status": "skipped", "reason": "fetched on-demand"},
        "completed_at": datetime.now().isoformat(),
    }
