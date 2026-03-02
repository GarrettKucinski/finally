"""Portfolio route handlers for FinAlly.

Provides:
- GET /api/portfolio: Current positions, cash balance, total value, unrealized P&L
- POST /api/portfolio/trade: Execute a market order (buy or sell)

Routes stay thin -- all business logic lives in app.services.portfolio.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.common import ErrorResponse
from app.models.portfolio import TradeRequest
from app.services.portfolio import execute_trade, get_portfolio, record_snapshot

router = APIRouter(tags=["portfolio"])


@router.get("/api/portfolio")
async def get_portfolio_endpoint(request: Request):
    """Get current portfolio state with positions enriched by live prices.

    Returns:
        200: PortfolioResponse with cash_balance, total_value, positions (with P&L)
    """
    pool = request.app.state.db_pool
    price_cache = request.app.state.price_cache
    result = await get_portfolio(pool, price_cache)
    return result


@router.post("/api/portfolio/trade")
async def trade_endpoint(request: Request, body: TradeRequest):
    """Execute a market order at the current cached price.

    Args:
        body: TradeRequest with ticker, side ('buy'/'sell'), and quantity

    Returns:
        200: TradeResponse with execution details
        400: ErrorResponse for insufficient cash/shares or missing price
    """
    pool = request.app.state.db_pool
    price_cache = request.app.state.price_cache
    try:
        result = await execute_trade(
            pool, price_cache, body.ticker, body.side, body.quantity
        )
        # Record snapshot after successful trade (PORT-09)
        await record_snapshot(pool, price_cache)
        return result
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(error="Trade failed", detail=str(e)).model_dump(),
        )
