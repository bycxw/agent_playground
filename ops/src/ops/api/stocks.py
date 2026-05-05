"""API routes - stock data endpoints."""
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from data import (
    query_stock_list,
    query_daily_kdata,
    query_financial_metrics,
    get_stock_info,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


class StockInfo(BaseModel):
    """Stock basic info. `symbol` is canonical 'SH600000' form."""
    symbol: str
    name: str
    exchange: str
    code: str


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
            symbol=row["symbol"],
            name=row["name"],
            exchange=row["exchange"],
            code=row["code"],
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

    latest = df.iloc[-1].to_dict()
    if latest.get("report_date") is not None:
        latest["report_date"] = str(latest["report_date"])
    return {"symbol": symbol, "data": latest}