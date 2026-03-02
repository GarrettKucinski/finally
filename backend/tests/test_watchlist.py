"""
Tests for watchlist route handlers and service layer.

Verifies HTTP status codes, response shapes, error handling, and
market data source synchronization for:
- GET /api/watchlist (with and without tickers)
- POST /api/watchlist (add, lowercase normalization, invalid, duplicate)
- DELETE /api/watchlist/{ticker} (remove, nonexistent)
- Market source add_ticker/remove_ticker calls (WATCH-04, WATCH-05)

Uses the established test pattern from test_health.py / test_portfolio.py:
mock app.state.db_pool, app.state.price_cache, app.state.market_source,
use httpx.ASGITransport.
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

def _setup_app(
    monkeypatch,
    *,
    watchlist_rows=None,
    fetchrow_return=None,
    execute_return="DELETE 1",
    tickers_prices: list[tuple[str, float]] | None = None,
):
    """Set up app.state with mocked pool, price cache, and market source.

    Returns (app, conn, source) so tests can inspect calls.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")

    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=watchlist_rows or [])
    conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    conn.execute = AsyncMock(return_value=execute_return)

    pool = AsyncMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire

    cache = PriceCache()
    if tickers_prices:
        for ticker, price in tickers_prices:
            cache.update(ticker, price)

    source = AsyncMock()
    source.add_ticker = AsyncMock()
    source.remove_ticker = AsyncMock()

    app.state.db_pool = pool
    app.state.price_cache = cache
    app.state.market_source = source

    return app, conn, source


# ---------------------------------------------------------------------------
# GET /api/watchlist
# ---------------------------------------------------------------------------

async def test_get_watchlist(monkeypatch):
    """GET /api/watchlist returns list of tickers with live price data (WATCH-01)."""
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    watchlist = [
        {"ticker": "AAPL", "added_at": now},
        {"ticker": "GOOGL", "added_at": now},
    ]
    test_app, _, _ = _setup_app(
        monkeypatch,
        watchlist_rows=watchlist,
        tickers_prices=[("AAPL", 190.0), ("GOOGL", 175.0)],
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/watchlist")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    aapl = data[0]
    assert aapl["ticker"] == "AAPL"
    assert aapl["current_price"] == 190.0
    assert aapl["direction"] is not None
    assert "added_at" in aapl

    googl = data[1]
    assert googl["ticker"] == "GOOGL"
    assert googl["current_price"] == 175.0


async def test_get_watchlist_empty(monkeypatch):
    """GET /api/watchlist with no tickers -> 200 with empty list."""
    test_app, _, _ = _setup_app(monkeypatch, watchlist_rows=[])

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/watchlist")

    assert response.status_code == 200
    data = response.json()
    assert data == []


# ---------------------------------------------------------------------------
# POST /api/watchlist
# ---------------------------------------------------------------------------

async def test_add_ticker(monkeypatch):
    """POST /api/watchlist with valid ticker -> 201 with {ticker, status: 'added'} (WATCH-02)."""
    # fetchrow returns a row (meaning insert succeeded)
    test_app, _, _ = _setup_app(
        monkeypatch,
        fetchrow_return={"id": "some-uuid"},
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/watchlist",
            json={"ticker": "PYPL"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "PYPL"
    assert data["status"] == "added"


async def test_add_ticker_lowercase(monkeypatch):
    """POST /api/watchlist with lowercase ticker -> 201, ticker normalized to uppercase."""
    test_app, _, _ = _setup_app(
        monkeypatch,
        fetchrow_return={"id": "some-uuid"},
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/watchlist",
            json={"ticker": "pypl"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "PYPL"


async def test_add_invalid_ticker_numeric(monkeypatch):
    """POST /api/watchlist with numeric ticker -> 422 validation error (WATCH-02)."""
    test_app, _, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/watchlist",
            json={"ticker": "123"},
        )

    assert response.status_code == 422


async def test_add_invalid_ticker_too_long(monkeypatch):
    """POST /api/watchlist with ticker >5 chars -> 422 validation error."""
    test_app, _, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/watchlist",
            json={"ticker": "TOOLONG"},
        )

    assert response.status_code == 422


async def test_add_duplicate_ticker(monkeypatch):
    """POST /api/watchlist with ticker already in watchlist -> 409 with ErrorResponse."""
    # fetchrow returns None (ON CONFLICT DO NOTHING, no RETURNING)
    test_app, _, _ = _setup_app(
        monkeypatch,
        fetchrow_return=None,
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/watchlist",
            json={"ticker": "AAPL"},
        )

    assert response.status_code == 409
    data = response.json()
    assert "error" in data
    assert "already in watchlist" in data["detail"]


async def test_add_registers_market_source(monkeypatch):
    """After POST /api/watchlist, source.add_ticker() is called (WATCH-04)."""
    test_app, _, source = _setup_app(
        monkeypatch,
        fetchrow_return={"id": "some-uuid"},
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/watchlist",
            json={"ticker": "PYPL"},
        )

    source.add_ticker.assert_called_once_with("PYPL")


# ---------------------------------------------------------------------------
# DELETE /api/watchlist/{ticker}
# ---------------------------------------------------------------------------

async def test_remove_ticker(monkeypatch):
    """DELETE /api/watchlist/PYPL -> 200 with {ticker, status: 'removed'} (WATCH-03)."""
    test_app, _, _ = _setup_app(
        monkeypatch,
        execute_return="DELETE 1",
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/watchlist/PYPL")

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "PYPL"
    assert data["status"] == "removed"


async def test_remove_nonexistent_ticker(monkeypatch):
    """DELETE /api/watchlist/ZZZZ (not in watchlist) -> 404 with ErrorResponse (WATCH-03)."""
    test_app, _, _ = _setup_app(
        monkeypatch,
        execute_return="DELETE 0",
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/watchlist/ZZZZ")

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "not in watchlist" in data["detail"]


async def test_remove_unregisters_market_source(monkeypatch):
    """After DELETE /api/watchlist/{ticker}, source.remove_ticker() is called (WATCH-05)."""
    test_app, _, source = _setup_app(
        monkeypatch,
        execute_return="DELETE 1",
    )

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.delete("/api/watchlist/PYPL")

    source.remove_ticker.assert_called_once_with("PYPL")
