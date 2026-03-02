"""
Shared test configuration for the FinAlly backend test suite.

pytest-asyncio is configured in pyproject.toml with asyncio_mode = "auto"
so all async test functions are automatically treated as asyncio tests.

Provides shared fixtures for database mocking.
"""

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_conn():
    """AsyncMock of an asyncpg connection with execute() and fetchval()."""
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetchval = AsyncMock(return_value=0)
    return conn


@pytest.fixture
def mock_pool(mock_conn):
    """AsyncMock of an asyncpg pool with acquire() context manager."""
    pool = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


@pytest.fixture
def env_with_database_url(monkeypatch):
    """Set DATABASE_URL environment variable for tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")
