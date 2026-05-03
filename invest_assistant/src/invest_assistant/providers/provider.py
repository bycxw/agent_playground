"""Data layer - wraps zvt for data access."""
import pandas as pd
from typing import Optional, List
from datetime import datetime, date

from ..config import settings


def get_entity_id(symbol: str, exchange: str = "SH") -> str:
    """Convert symbol to zvt entity_id.

    Args:
        symbol: Stock code like "000001"
        exchange: Exchange like "SH" or "SZ"
    """
    exchange_map = {"SH": "sh", "SZ": "sz", "HK": "hk"}
    ex = exchange_map.get(exchange.upper(), "sh")
    return f"stock_{ex}_{symbol}"


def parse_entity_id(entity_id: str) -> tuple:
    """Parse entity_id to (symbol, exchange)."""
    # e.g., "stock_sh_000001" -> ("000001", "SH")
    parts = entity_id.split("_")
    if len(parts) >= 3:
        symbol = parts[2]
        exchange_map = {"sh": "SH", "sz": "SZ", "hk": "HK"}
        exchange = exchange_map.get(parts[1], "SH")
        return symbol, exchange
    return entity_id, "SH"


def query_stock_list(provider: str = None) -> pd.DataFrame:
    """Query all available stocks.

    Returns:
        DataFrame with columns: entity_id, code, name, exchange
    """
    from zvt.api import get_stocks

    provider = provider or settings.DEFAULT_PROVIDER
    return get_stocks(provider=provider)


def query_daily_kdata(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    provider: str = None,
) -> pd.DataFrame:
    """Query daily kline data.

    Args:
        symbol: Stock code like "000001.SZ"
        start_date: Start date like "2024-01-01"
        end_date: End date
        provider: Data provider

    Returns:
        DataFrame with OHLCV data
    """
    from zvt.api import query_kdata

    provider = provider or settings.DEFAULT_PROVIDER

    # Convert symbol format
    if "." in symbol:
        parts = symbol.split(".")
        symbol_code = parts[0]
        exchange = parts[1]
    else:
        symbol_code = symbol
        exchange = "SH"

    entity_id = get_entity_id(symbol_code, exchange)

    df = query_kdata(
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
    )

    return df


def query_financial_metrics(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    provider: str = None,
) -> pd.DataFrame:
    """Query financial metrics for a single stock.

    Args:
        symbol: Stock code like "000001.SZ"
        start_date: Start date like "2024-01-01"
        end_date: End date
        provider: Data provider

    Returns:
        DataFrame with financial metrics (roe, gross_profit_margin, etc.)
    """
    from zvt.domain import FinanceFactor

    provider = provider or settings.DEFAULT_PROVIDER

    # Convert symbol format
    if "." in symbol:
        parts = symbol.split(".")
        symbol_code = parts[0]
        exchange = parts[1]
    else:
        symbol_code = symbol
        exchange = "SH"

    entity_id = get_entity_id(symbol_code, exchange)

    df = FinanceFactor.query_data(
        provider=provider,
        entity_id=entity_id,
        start_timestamp=start_date,
        end_timestamp=end_date,
        order=FinanceFactor.report_date.desc(),
    )

    return df


def query_all_financial_metrics(
    market: str = "A股",
    provider: str = None,
) -> pd.DataFrame:
    """Query financial metrics for all stocks in market.

    Fetches all stocks in a single batch query instead of per-stock loops.

    Args:
        market: "A股" or "港股" or "ALL"
        provider: Data provider

    Returns:
        DataFrame with financial metrics for multiple stocks,
        including 'symbol' and 'name' columns joined from stock metadata.
    """
    from zvt.domain import FinanceFactor, Stock

    provider = provider or settings.DEFAULT_PROVIDER

    # Determine exchange filter
    exchange_map = {
        "A股": ["sh", "sz"],
        "港股": ["hk"],
        "ALL": None,
    }
    exchanges = exchange_map.get(market, ["sh", "sz"])

    # Build entity_ids filter from stock metadata
    stock_df = Stock.query_data(provider=provider, columns=["entity_id", "code", "name"])
    if exchanges:
        # entity_id format: "stock_{exchange}_{code}"
        stock_df = stock_df[stock_df["entity_id"].str.split("_").str[1].isin(exchanges)]

    entity_ids = stock_df["entity_id"].tolist()
    if not entity_ids:
        return pd.DataFrame()

    # Single batch query for all stocks — latest report per stock
    df = FinanceFactor.query_data(
        provider=provider,
        entity_ids=entity_ids,
        order=FinanceFactor.report_date.desc(),
        columns=[
            "entity_id", "report_date",
            "roe", "rota",
            "gross_profit_margin", "net_margin",
            "op_income_growth_yoy", "net_profit_growth_yoy",
            "basic_eps", "bps",
            "debt_asset_ratio", "current_ratio", "quick_ratio", "cash_flow_ratio",
            "total_op_income", "net_profit",
        ],
    )

    if df.empty:
        return pd.DataFrame()

    # Keep only the latest report per stock
    df = df.drop_duplicates(subset=["entity_id"], keep="first")

    # Join stock name and symbol from metadata
    meta = stock_df.set_index("entity_id")[["code", "name"]]
    df = df.join(meta, on="entity_id")
    df = df.rename(columns={"code": "symbol"})

    return df.reset_index(drop=True)


def get_stock_info(symbol: str, provider: str = None) -> dict:
    """Get basic stock info."""
    from zvt.api import get_stocks

    provider = provider or settings.DEFAULT_PROVIDER

    if "." in symbol:
        parts = symbol.split(".")
        symbol_code = parts[0]
    else:
        symbol_code = symbol

    stocks = get_stocks(provider=provider)
    stock = stocks[stocks["code"] == symbol_code]

    if stock.empty:
        return {}

    return stock.iloc[0].to_dict()