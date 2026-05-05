"""Market data layer.

Provider-agnostic public interface lives in `data.api` (PIT-aware
signatures, work in progress). Until that's fully wired, the legacy
baostock query/sync functions are re-exported here for transitional
convenience.

Both `ops/` (live monitoring) and `research/` (offline backtesting)
consume from this package.
"""
from .providers.baostock import (
    query_stock_list,
    query_daily_kdata,
    query_financial_metrics,
    query_all_financial_metrics,
    get_stock_info,
    init_db,
)
from .providers.baostock_sync import (
    sync_stock_meta,
    sync_financial_data,
    sync_daily_kdata,
    sync_all,
)
from .config import DB_PATH

__all__ = [
    "query_stock_list",
    "query_daily_kdata",
    "query_financial_metrics",
    "query_all_financial_metrics",
    "get_stock_info",
    "init_db",
    "sync_stock_meta",
    "sync_financial_data",
    "sync_daily_kdata",
    "sync_all",
    "DB_PATH",
]
