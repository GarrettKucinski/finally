"""Chat models for the LLM integration.

Defines request/response schemas for the POST /api/chat endpoint and
the structured output schema that the LLM is instructed to return.
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""

    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v


class TradeAction(BaseModel):
    """A trade the LLM wants to execute."""

    ticker: str
    side: str  # "buy" or "sell"
    quantity: float


class WatchlistAction(BaseModel):
    """A watchlist change the LLM wants to make."""

    ticker: str
    action: str  # "add" or "remove"


class LLMResponse(BaseModel):
    """Structured output schema sent to the LLM via response_format.

    The LLM returns JSON matching this schema. LiteLLM + Pydantic
    handle schema generation and parsing.
    """

    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistAction] = []


class ChatResponse(BaseModel):
    """Response returned to the frontend from POST /api/chat."""

    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistAction] = []
    executed_actions: dict = {}
