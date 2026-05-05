"""Top-level sync orchestration.

Currently delegates to the single baostock provider. When more providers
are added (Tushare for fundamentals, AKShare for HK), this is where the
multi-source sync logic lives.
"""
from .providers.baostock_sync import sync_stock_meta, sync_financial_data, sync_daily_kdata, sync_all

__all__ = ["sync_stock_meta", "sync_financial_data", "sync_daily_kdata", "sync_all"]
