"""Pydantic models for portfolio and trade API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class TradeRequest(BaseModel):
    """Request body for POST /api/portfolio/trade.

    Validates:
    - ticker: 1-5 uppercase alpha characters (stripped and uppercased)
    - side: 'buy' or 'sell' (stripped and lowercased)
    - quantity: positive float (fractional shares supported)
    """

    ticker: str
    side: str
    quantity: float

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalpha() or not (1 <= len(v) <= 5):
            raise ValueError("Ticker must be 1-5 uppercase alpha characters")
        return v

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("buy", "sell"):
            raise ValueError("Side must be 'buy' or 'sell'")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v


class TradeResponse(BaseModel):
    """Response for a successful trade execution."""

    ticker: str
    side: str
    quantity: float
    price: float
    total: float


class PositionDetail(BaseModel):
    """A single position enriched with live price and P&L data."""

    ticker: str
    quantity: float
    avg_cost: float
    current_price: float | None
    unrealized_pnl: float
    pnl_percent: float


class PortfolioResponse(BaseModel):
    """Complete portfolio state including cash, total value, and positions."""

    cash_balance: float
    total_value: float
    positions: list[PositionDetail]


class SnapshotPoint(BaseModel):
    """A single portfolio value snapshot for the P&L chart."""

    total_value: float
    recorded_at: str  # ISO format timestamp
