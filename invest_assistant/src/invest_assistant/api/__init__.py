"""API package."""
from fastapi import APIRouter

from .monitor import router as monitor_router
from .stocks import router as stocks_router
from .sync import router as sync_router

api_router = APIRouter()

api_router.include_router(monitor_router)
api_router.include_router(stocks_router)
api_router.include_router(sync_router)