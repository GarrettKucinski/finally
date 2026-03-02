"""
Tests for the health check endpoint.

Verifies:
- GET /api/health returns 200 with healthy status when DB is reachable
- GET /api/health returns 503 with unhealthy status when DB is unreachable
- Response Content-Type is application/json
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import httpx
import pytest

from app.main import app


@asynccontextmanager
async def _mock_pool_acquire(return_value=1):
    """Async context manager simulating pool.acquire()."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=return_value)
    yield conn


@asynccontextmanager
async def _mock_pool_acquire_fail():
    """Async context manager that raises on acquire."""
    raise Exception("Connection refused")
    yield  # pragma: no cover


@pytest.fixture
def healthy_app(monkeypatch):
    """Patch app.state.db_pool to simulate a healthy database."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")
    pool = AsyncMock()
    pool.acquire = _mock_pool_acquire
    app.state.db_pool = pool
    return app


@pytest.fixture
def unhealthy_app(monkeypatch):
    """Patch app.state.db_pool to simulate an unreachable database."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")
    pool = AsyncMock()
    pool.acquire = _mock_pool_acquire_fail
    app.state.db_pool = pool
    return app


async def test_health_returns_200_when_db_connected(healthy_app):
    """GET /api/health returns 200 with healthy status when DB is reachable."""
    transport = httpx.ASGITransport(app=healthy_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "healthy", "database": "connected"}


async def test_health_returns_503_when_db_disconnected(unhealthy_app):
    """GET /api/health returns 503 with unhealthy status when DB is unreachable."""
    transport = httpx.ASGITransport(app=unhealthy_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 503
    data = response.json()
    assert data == {"status": "unhealthy", "database": "disconnected"}


async def test_health_response_content_type(healthy_app):
    """Response Content-Type is application/json."""
    transport = httpx.ASGITransport(app=healthy_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert "application/json" in response.headers["content-type"]
