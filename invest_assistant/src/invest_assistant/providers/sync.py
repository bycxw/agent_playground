"""Data synchronization tasks."""
import logging
from datetime import datetime
from typing import List

from ..config import settings

logger = logging.getLogger(__name__)


def sync_stock_meta(provider: str = None) -> dict:
    """Sync stock metadata (list of stocks).

    Returns:
        dict with sync results
    """
    from zvt.recorders import EastmoneyStockMetaRecorder

    provider = provider or settings.DEFAULT_PROVIDER
    logger.info(f"Starting stock meta sync with provider: {provider}")

    try:
        recorder = EastmoneyStockMetaRecorder(provider=provider)
        recorder.run()

        logger.info("Stock meta sync completed")
        return {"status": "success", "provider": provider}
    except Exception as e:
        logger.error(f"Stock meta sync failed: {e}")
        return {"status": "error", "error": str(e)}


def sync_financial_data(
    codes: List[str] = None,
    provider: str = None,
) -> dict:
    """Sync financial data for specified stocks.

    Args:
        codes: List of stock codes like ["000001", "600000"]
               None means sync all stocks
        provider: Data provider
    """
    from zvt.recorders import EastmoneyFinanceFactorRecorder

    provider = provider or settings.DEFAULT_PROVIDER
    logger.info(f"Starting financial data sync with provider: {provider}")

    try:
        recorder = EastmoneyFinanceFactorRecorder(
            codes=codes or ["all"],
            provider=provider,
        )
        recorder.run()

        logger.info("Financial data sync completed")
        return {"status": "success", "provider": provider, "codes": codes}
    except Exception as e:
        logger.error(f"Financial data sync failed: {e}")
        return {"status": "error", "error": str(e)}


def sync_daily_kdata(
    codes: List[str] = None,
    provider: str = None,
) -> dict:
    """Sync daily kline data.

    Args:
        codes: List of stock codes
        provider: Data provider
    """
    from zvt.recorders import EastmoneyKdataRecorder

    provider = provider or settings.DEFAULT_PROVIDER
    logger.info(f"Starting daily kline sync with provider: {provider}")

    try:
        recorder = EastmoneyKdataRecorder(
            codes=codes or ["all"],
            provider=provider,
        )
        recorder.run()

        logger.info("Daily kline sync completed")
        return {"status": "success", "provider": provider, "codes": codes}
    except Exception as e:
        logger.error(f"Daily kline sync failed: {e}")
        return {"status": "error", "error": str(e)}


def sync_all(provider: str = None) -> dict:
    """Run full sync (meta -> financial -> kline).

    Returns:
        dict with sync results for each step
    """
    provider = provider or settings.DEFAULT_PROVIDER
    logger.info(f"Starting full sync with provider: {provider}")

    results = {
        "meta": sync_stock_meta(provider),
        "financial": sync_financial_data(provider=provider),
        "kline": sync_daily_kdata(provider=provider),
        "completed_at": datetime.now().isoformat(),
    }

    return results