"""
Tests for portfolio and portfolio history route handlers.

Verifies HTTP status codes, response shapes, and error handling for:
- GET /api/portfolio (empty and with positions)
- POST /api/portfolio/trade (buy, sell, validation errors)
- GET /api/portfolio/history (empty and with snapshots)

Uses the established test pattern from test_health.py: mock app.state.db_pool
and app.state.price_cache, use httpx.ASGITransport.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

from app.main import app
from app.market.cache import PriceCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _mock_transaction():
    """Simulate asyncpg conn.transaction() context manager."""
    yield


def _setup_app(
    monkeypatch,
    *,
    cash: float = 10000.0,
    position_row=None,
    positions_list=None,
    snapshots_list=None,
    tickers_prices: list[tuple[str, float]] | None = None,
):
    """Set up app.state with mocked pool and price cache.

    Returns (app, conn) so tests can inspect conn.execute calls.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")

    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=cash)
    conn.fetchrow = AsyncMock(return_value=position_row)
    conn.fetch = AsyncMock(return_value=positions_list or snapshots_list or [])
    conn.execute = AsyncMock()
    conn.transaction = _mock_transaction

    pool = AsyncMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire

    cache = PriceCache()
    if tickers_prices:
        for ticker, price in tickers_prices:
            cache.update(ticker, price)

    app.state.db_pool = pool
    app.state.price_cache = cache

    return app, conn


# ---------------------------------------------------------------------------
# GET /api/portfolio
# ---------------------------------------------------------------------------

async def test_get_portfolio_empty(monkeypatch):
    """GET /api/portfolio with no positions -> 200 with cash=10000, total=10000, positions=[]."""
    test_app, _ = _setup_app(monkeypatch, cash=10000.0, positions_list=[])

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/portfolio")

    assert response.status_code == 200
    data = response.json()
    assert data["cash_balance"] == 10000.0
    assert data["total_value"] == 10000.0
    assert data["positions"] == []


async def test_get_portfolio_with_positions(monkeypatch):
    """GET /api/portfolio with positions -> 200 with enriched positions including P&L."""
    positions = [
        {"ticker": "AAPL", "quantity": 10.0, "avg_cost": 100.0},
        {"ticker": "GOOGL", "quantity": 5.0, "avg_cost": 200.0},
    ]
    test_app, conn = _setup_app(
        monkeypatch,
        cash=5000.0,
        positions_list=positions,
        tickers_prices=[("AAPL", 150.0), ("GOOGL", 180.0)],
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/portfolio")

    assert response.status_code == 200
    data = response.json()
    assert data["cash_balance"] == 5000.0
    # total_value = 5000 + (150*10) + (180*5) = 7400
    assert data["total_value"] == 7400.0
    assert len(data["positions"]) == 2

    aapl = data["positions"][0]
    assert aapl["ticker"] == "AAPL"
    assert aapl["unrealized_pnl"] == 500.0
    assert aapl["pnl_percent"] == 50.0


# ---------------------------------------------------------------------------
# POST /api/portfolio/trade
# ---------------------------------------------------------------------------

async def test_execute_buy(monkeypatch):
    """POST /api/portfolio/trade buy -> 200 with TradeResponse."""
    test_app, conn = _setup_app(
        monkeypatch,
        cash=10000.0,
        tickers_prices=[("AAPL", 150.0)],
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 10},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["side"] == "buy"
    assert data["quantity"] == 10
    assert data["price"] == 150.0
    assert data["total"] == 1500.0


async def test_execute_sell(monkeypatch):
    """POST /api/portfolio/trade sell -> 200 with TradeResponse."""
    position_row = {"quantity": 10.0, "avg_cost": 100.0}
    test_app, conn = _setup_app(
        monkeypatch,
        cash=5000.0,
        position_row=position_row,
        tickers_prices=[("AAPL", 150.0)],
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "sell", "quantity": 5},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["side"] == "sell"
    assert data["quantity"] == 5
    assert data["price"] == 150.0
    assert data["total"] == 750.0


async def test_buy_insufficient_cash(monkeypatch):
    """POST /api/portfolio/trade buy exceeding cash -> 400 with ErrorResponse."""
    test_app, _ = _setup_app(
        monkeypatch,
        cash=100.0,
        tickers_prices=[("AAPL", 150.0)],
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 10},
        )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "detail" in data
    assert "Insufficient cash" in data["detail"]


async def test_sell_insufficient_shares(monkeypatch):
    """POST /api/portfolio/trade sell exceeding position -> 400 with ErrorResponse."""
    position_row = {"quantity": 5.0, "avg_cost": 100.0}
    test_app, _ = _setup_app(
        monkeypatch,
        cash=5000.0,
        position_row=position_row,
        tickers_prices=[("AAPL", 150.0)],
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "sell", "quantity": 10},
        )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "Insufficient shares" in data["detail"]


async def test_trade_invalid_ticker(monkeypatch):
    """POST /api/portfolio/trade with invalid ticker -> 422 validation error."""
    test_app, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "123", "side": "buy", "quantity": 10},
        )

    assert response.status_code == 422


async def test_trade_invalid_side(monkeypatch):
    """POST /api/portfolio/trade with side='hold' -> 422 validation error."""
    test_app, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "hold", "quantity": 10},
        )

    assert response.status_code == 422


async def test_trade_negative_quantity(monkeypatch):
    """POST /api/portfolio/trade with quantity=-5 -> 422 validation error."""
    test_app, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": -5},
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/portfolio/history
# ---------------------------------------------------------------------------

async def test_get_portfolio_history(monkeypatch):
    """GET /api/portfolio/history -> 200 with list of snapshot objects."""
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    snapshots = [
        {"total_value": 10000.0, "recorded_at": now},
        {"total_value": 10100.0, "recorded_at": now},
    ]
    test_app, _ = _setup_app(monkeypatch, snapshots_list=snapshots)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/portfolio/history")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["total_value"] == 10000.0
    assert "recorded_at" in data[0]
    assert data[1]["total_value"] == 10100.0


async def test_get_portfolio_history_empty(monkeypatch):
    """GET /api/portfolio/history with no snapshots -> 200 with empty list."""
    test_app, _ = _setup_app(monkeypatch, snapshots_list=[])

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/portfolio/history")

    assert response.status_code == 200
    data = response.json()
    assert data == []
