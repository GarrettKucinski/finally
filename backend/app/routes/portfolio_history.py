"""Portfolio history route handler for FinAlly.

Provides:
- GET /api/portfolio/history: Portfolio value snapshots over time (for P&L chart)
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["portfolio"])

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


@router.get("/api/portfolio/history")
async def get_portfolio_history(request: Request):
    """Get portfolio value snapshots ordered by time.

    Returns:
        200: List of {total_value, recorded_at} objects
    """
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = $1 ORDER BY recorded_at",
            DEFAULT_USER_ID,
        )

    return [
        {
            "total_value": round(row["total_value"], 2),
            "recorded_at": row["recorded_at"].isoformat(),
        }
        for row in rows
    ]
