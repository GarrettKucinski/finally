"""Chat route handler for POST /api/chat.

Thin route that delegates all logic to the chat service.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.chat import ChatRequest
from app.models.common import ErrorResponse
from app.services.chat import orchestrate_chat

router = APIRouter(tags=["chat"])


@router.post("/api/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    """Send a message to the AI assistant and receive a structured response."""
    pool = request.app.state.db_pool
    price_cache = request.app.state.price_cache
    market_source = request.app.state.market_source
    settings = request.app.state.settings
    try:
        result = await orchestrate_chat(
            pool, price_cache, market_source, settings, body.message
        )
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error="Chat failed", detail=str(e)).model_dump(),
        )
