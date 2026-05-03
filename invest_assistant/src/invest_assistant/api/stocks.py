"""API routes - stock data endpoints."""
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..providers import (
    query_stock_list,
    query_daily_kdata,
    query_financial_metrics,
    get_stock_info,
    query_all_financial_metrics,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


class StockInfo(BaseModel):
    """Stock basic info."""
    symbol: str
    name: str
    exchange: str
    entity_id: str


class StockListResponse(BaseModel):
    """Stock list response."""
    count: int
    stocks: List[StockInfo]


@router.get("/", response_model=StockListResponse)
async def list_stocks(market: Optional[str] = None):
    """Get list of all stocks."""
    df = query_stock_list()

    if market == "A股":
        df = df[df["exchange"].isin(["SH", "SZ"])]
    elif market == "港股":
        df = df[df["exchange"] == "HK"]

    stocks = [
        StockInfo(
            symbol=row.get("symbol", ""),
            name=row.get("name", ""),
            exchange=row.get("exchange", ""),
            entity_id=row.get("entity_id", ""),
        )
        for _, row in df.iterrows()
    ]

    return StockListResponse(count=len(stocks), stocks=stocks)


@router.get("/{symbol}")
async def get_stock(symbol: str):
    """Get stock basic info."""
    info = get_stock_info(symbol)

    if not info:
        raise HTTPException(status_code=404, detail="Stock not found")

    return info


@router.get("/{symbol}/kline")
async def get_kline(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get stock daily kline data."""
    df = query_daily_kdata(symbol, start_date=start_date, end_date=end_date)

    if df.empty:
        return {"symbol": symbol, "data": []}

    # Convert DataFrame to dict list
    data = df.to_dict("records")

    return {"symbol": symbol, "count": len(data), "data": data}


@router.get("/{symbol}/financial")
async def get_financial(symbol: str):
    """Get stock financial metrics."""
    df = query_financial_metrics(symbol)

    if df.empty:
        return {"symbol": symbol, "data": []}

    # Get latest record
    latest = df.iloc[-1].to_dict()
    latest["period_end"] = str(latest.get("period_end", ""))

    return {"symbol": symbol, "data": latest}


@router.post("/screen")
async def screen_stocks(
    pe_max: Optional[float] = None,
    roe_min: Optional[float] = None,
    revenue_yoy_min: Optional[float] = None,
    market: str = "A股",
):
    """Screen stocks by financial criteria."""
    df = query_all_financial_metrics(market=market)

    if df.empty:
        return {"count": 0, "stocks": []}

    # Apply filters
    if pe_max is not None:
        df = df[df["pe_ttm"] <= pe_max]

    if roe_min is not None:
        df = df[df["roe"] >= roe_min]

    if revenue_yoy_min is not None:
        df = df[df["revenue_yoy"] >= revenue_yoy_min]

    # Limit results
    df = df.head(100)

    stocks = [
        {
            "symbol": row.get("symbol", ""),
            "name": row.get("name", ""),
            "pe_ttm": row.get("pe_ttm"),
            "roe": row.get("roe"),
            "revenue_yoy": row.get("revenue_yoy"),
        }
        for _, row in df.iterrows()
    ]

    return {"count": len(stocks), "stocks": stocks}