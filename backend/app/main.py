"""
FastAPI application entry point for FinAlly.

Creates the app with a lifespan context manager that wires together:
1. Settings configuration (Pydantic Settings)
2. Database pool + schema + seed (asyncpg → Neon Postgres)
3. Market data subsystem (PriceCache + simulator/Massive source)
4. SSE streaming endpoint

All shared state is stored on app.state for access by route handlers.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import Settings
from .db import close_db, init_db
from .market.cache import PriceCache
from .routes.health import router as health_router
from .routes.portfolio import router as portfolio_router
from .routes.portfolio_history import router as portfolio_history_router
from .market.factory import create_market_data_source
from .market.seed_prices import DEFAULT_WATCHLIST
from .market.stream import create_stream_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown sequence.

    Startup:
        1. Load and validate settings
        2. Initialize database (pool + schema DDL + seed data)
        3. Load watchlist tickers from DB
        4. Create and start market data source
        5. Register SSE streaming router

    Shutdown:
        1. Stop market data source
        2. Close database pool
    """
    # 1. Load settings
    settings = Settings()
    logger.info("Settings loaded successfully.")

    # 2. Initialize database (pool + schema + seed)
    pool = await init_db(settings.database_url)
    app.state.db_pool = pool
    app.state.settings = settings

    # 3. Load default watchlist tickers from DB
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT ticker FROM watchlist WHERE user_id = $1",
            "00000000-0000-0000-0000-000000000001",
        )
    tickers = [row["ticker"] for row in rows] if rows else DEFAULT_WATCHLIST
    logger.info("Watchlist tickers loaded: %s", tickers)

    # 4. Start market data
    cache = PriceCache()
    source = create_market_data_source(cache)
    if tickers:
        await source.start(tickers)
    app.state.price_cache = cache
    app.state.market_source = source

    # 5. Register SSE streaming router
    stream_router = create_stream_router(cache)
    app.include_router(stream_router)

    yield

    # Shutdown
    logger.info("Shutting down...")
    await source.stop()
    await close_db(pool)
    logger.info("Shutdown complete.")


app = FastAPI(title="FinAlly", lifespan=lifespan)
app.include_router(health_router)
app.include_router(portfolio_router)
app.include_router(portfolio_history_router)
