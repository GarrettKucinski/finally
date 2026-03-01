"""
SSE streaming endpoint factory for live price updates.

Creates a FastAPI router with a GET /api/stream/prices endpoint that pushes
price updates to connected browser clients via Server-Sent Events.

The generator uses version-based change detection to avoid sending redundant
data when prices haven't changed (important for the Massive source which only
updates every 15 seconds).

Usage:
    cache = PriceCache()
    stream_router = create_stream_router(cache)
    app.include_router(stream_router)
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .cache import PriceCache


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Create the SSE streaming router with a reference to the price cache.

    Uses a factory pattern to inject the PriceCache without global state.
    The router is created fresh each call and should be included in the app
    once during startup.
    """
    router = APIRouter(prefix="/api/stream", tags=["streaming"])

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        """SSE endpoint that streams live price updates to the client.

        Sends a JSON payload of all current prices whenever the cache version
        changes. The payload is a dict keyed by ticker symbol.

        The client should use the native EventSource API:
            const source = new EventSource('/api/stream/prices');
            source.onmessage = (e) => { const prices = JSON.parse(e.data); }
        """
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    return router


async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted price events.

    Checks the cache version every `interval` seconds. Only sends data when
    the version has changed, avoiding redundant transmission.

    SSE format:
        retry: 1000\\n\\n        (reconnect after 1s on disconnect)
        data: {JSON payload}\\n\\n
    """
    # Tell the client to retry after 1 second if the connection drops
    yield "retry: 1000\n\n"

    last_version = -1

    try:
        while True:
            if await request.is_disconnected():
                break

            current_version = price_cache.version
            if current_version != last_version:
                last_version = current_version
                prices = price_cache.get_all()

                if prices:
                    data = {
                        ticker: update.to_dict()
                        for ticker, update in prices.items()
                    }
                    payload = json.dumps(data)
                    yield f"data: {payload}\n\n"

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass
