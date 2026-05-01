"""API routes - data sync endpoints."""
from fastapi import APIRouter, BackgroundTasks

from ..data import sync_all, sync_stock_meta, sync_financial_data, sync_daily_kdata

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/all")
async def sync_all_data(background_tasks: BackgroundTasks):
    """Trigger full data sync in background."""
    background_tasks.add_task(sync_all)
    return {"message": "Full sync started in background"}


@router.post("/meta")
async def sync_meta():
    """Sync stock metadata."""
    result = sync_stock_meta()
    return result


@router.post("/financial")
async def sync_financial():
    """Sync financial data."""
    result = sync_financial_data()
    return result


@router.post("/kline")
async def sync_kline():
    """Sync daily kline data."""
    result = sync_daily_kdata()
    return result