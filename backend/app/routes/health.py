"""
Health check endpoint for FinAlly.

Verifies database connectivity by executing SELECT 1 against the pool.
Returns 200 when healthy, 503 when the database is unreachable.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["system"])


@router.get("/api/health")
async def health(request: Request):
    """Health check that verifies database connectivity.

    Returns:
        200: {"status": "healthy", "database": "connected"}
        503: {"status": "unhealthy", "database": "disconnected"}
    """
    pool = request.app.state.db_pool
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"},
        )
