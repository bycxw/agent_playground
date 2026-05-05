"""ops — live monitoring service entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

from .config import settings
from .api import api_router
from .persistence import init_db
from . import strategies  # registers built-in strategy types
from . import notification  # wires notification channels from settings
_ = strategies, notification  # silence unused-import linter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Scheduler for background tasks
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting ops service...")
    init_db()
    logger.info("Persistence initialised at %s", settings.DATABASE_URL)

    # Schedule monitor check (every hour during market hours)
    # Example: check at 10:00, 11:00, 12:00, 13:00, 14:00, 15:00
    scheduler.add_job(
        run_monitor_check,
        "cron",
        hour="10,11,12,13,14",
        minute="0",
        id="market_hours_check",
        replace_existing=True,
    )

    # Also check after market close (16:30)
    scheduler.add_job(
        run_monitor_check,
        "cron",
        hour="16",
        minute="30",
        id="after_market_close",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("ops service stopped")


def run_monitor_check():
    """Background job to run monitor check."""
    from .core.monitor import check_all

    try:
        results = check_all()
        if results:
            logger.info(f"Monitor check triggered: {len(results)} rules matched")
    except Exception as e:
        logger.error(f"Monitor check failed: {e}")


app = FastAPI(
    title="ops",
    description="Live monitoring + notifications for the personal quant platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "data_dir": str(settings.DATA_DIR),
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ops",
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "invest_assistant.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )