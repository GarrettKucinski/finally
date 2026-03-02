"""Watchlist route handlers -- GET, POST, DELETE /api/watchlist.

Thin route layer: delegates to app.services.watchlist for business logic.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.common import ErrorResponse
from app.models.watchlist import AddTickerRequest
from app.services.watchlist import add_ticker, get_watchlist, remove_ticker

router = APIRouter(tags=["watchlist"])


@router.get("/api/watchlist")
async def get_watchlist_endpoint(request: Request):
    """Return all watched tickers with live price data."""
    pool = request.app.state.db_pool
    price_cache = request.app.state.price_cache
    result = await get_watchlist(pool, price_cache)
    return result


@router.post("/api/watchlist", status_code=201)
async def add_ticker_endpoint(request: Request, body: AddTickerRequest):
    """Add a ticker to the watchlist and register with market data source."""
    pool = request.app.state.db_pool
    source = request.app.state.market_source
    try:
        await add_ticker(pool, source, body.ticker)
        return {"ticker": body.ticker, "status": "added"}
    except ValueError as e:
        error_msg = str(e)
        if "already in watchlist" in error_msg:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error="Duplicate",
                    detail=f"{body.ticker} already in watchlist",
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error="Bad request", detail=error_msg
            ).model_dump(),
        )


@router.delete("/api/watchlist/{ticker}")
async def remove_ticker_endpoint(request: Request, ticker: str):
    """Remove a ticker from the watchlist and unregister from market data source."""
    pool = request.app.state.db_pool
    source = request.app.state.market_source
    ticker = ticker.strip().upper()
    try:
        await remove_ticker(pool, source, ticker)
        return {"ticker": ticker, "status": "removed"}
    except ValueError:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="Not found",
                detail=f"{ticker} not in watchlist",
            ).model_dump(),
        )
