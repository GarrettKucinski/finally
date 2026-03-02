"""Pydantic models for watchlist API requests and responses."""

from pydantic import BaseModel, field_validator


class AddTickerRequest(BaseModel):
    """Request body for POST /api/watchlist.

    Accepts a ticker string, strips whitespace, and uppercases it.
    Validates it is 1-5 alpha characters only.
    """

    ticker: str

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalpha() or not (1 <= len(v) <= 5):
            raise ValueError("Ticker must be 1-5 uppercase alpha characters")
        return v


class WatchlistItem(BaseModel):
    """Single item in the watchlist response, enriched with live price data."""

    ticker: str
    current_price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    direction: str | None = None
    added_at: str | None = None  # ISO format
