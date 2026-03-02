"""
Unit tests for the database pool lifecycle and schema/seed SQL files.

Tests verify:
- asyncpg pool is created with correct parameters (statement_cache_size=0, min/max size)
- tables.sql contains all 7 CREATE TABLE IF NOT EXISTS statements in FK-safe order
- seed.sql contains default user, profile, and watchlist with ON CONFLICT DO NOTHING
- _seed_if_empty seeds when users table is empty, skips when data exists
- close_db closes the pool
"""

import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Path to SQL files for content verification
SCHEMA_DIR = pathlib.Path(__file__).parent.parent / "app" / "schema"


class TestPoolCreation:
    """Tests for init_db pool creation parameters."""

    @pytest.mark.asyncio
    async def test_pool_created_with_cache_disabled(self, monkeypatch):
        """init_db creates asyncpg pool with statement_cache_size=0 (Neon compat)."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)  # user exists, skip seed

        # Make pool.acquire() work as async context manager
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool) as mock_create:
            from app.db import init_db

            await init_db("postgresql://user:pass@host/db")
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["statement_cache_size"] == 0

    @pytest.mark.asyncio
    async def test_pool_min_max_size(self, monkeypatch):
        """init_db creates pool with min_size=2, max_size=10."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)

        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool) as mock_create:
            from app.db import init_db

            await init_db("postgresql://user:pass@host/db")
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["min_size"] == 2
            assert call_kwargs["max_size"] == 10


class TestSchemaSql:
    """Tests for tables.sql content."""

    def test_schema_sql_contains_all_tables(self):
        """tables.sql contains CREATE TABLE IF NOT EXISTS for all 7 tables."""
        sql = (SCHEMA_DIR / "tables.sql").read_text()
        expected_tables = [
            "users",
            "users_profile",
            "watchlist",
            "positions",
            "trades",
            "portfolio_snapshots",
            "chat_messages",
        ]
        for table in expected_tables:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in sql, f"Missing table: {table}"

    def test_schema_sql_table_order(self):
        """tables.sql creates users first (FK dependency), then dependent tables."""
        sql = (SCHEMA_DIR / "tables.sql").read_text()
        users_pos = sql.index("CREATE TABLE IF NOT EXISTS users")
        # All dependent tables must come after users
        for table in ["users_profile", "watchlist", "positions", "trades", "portfolio_snapshots", "chat_messages"]:
            table_pos = sql.index(f"CREATE TABLE IF NOT EXISTS {table}")
            assert table_pos > users_pos, f"{table} must come after users table"


class TestSeedSql:
    """Tests for seed.sql content."""

    def test_seed_sql_contains_default_user(self):
        """seed.sql inserts user with fixed UUID and email 'default@finally.app'."""
        sql = (SCHEMA_DIR / "seed.sql").read_text()
        assert "00000000-0000-0000-0000-000000000001" in sql
        assert "default@finally.app" in sql

    def test_seed_sql_contains_user_profile(self):
        """seed.sql inserts users_profile with cash_balance 10000.0."""
        sql = (SCHEMA_DIR / "seed.sql").read_text()
        assert "users_profile" in sql
        assert "10000" in sql

    def test_seed_sql_contains_watchlist(self):
        """seed.sql inserts all 10 DEFAULT_WATCHLIST tickers."""
        sql = (SCHEMA_DIR / "seed.sql").read_text()
        tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]
        for ticker in tickers:
            assert ticker in sql, f"Missing watchlist ticker: {ticker}"

    def test_seed_uses_on_conflict(self):
        """seed.sql uses ON CONFLICT DO NOTHING for idempotency."""
        sql = (SCHEMA_DIR / "seed.sql").read_text()
        assert "ON CONFLICT" in sql
        assert "DO NOTHING" in sql


class TestSeedIfEmpty:
    """Tests for _seed_if_empty conditional seeding logic."""

    @pytest.mark.asyncio
    async def test_seed_if_empty_seeds_when_count_zero(self):
        """_seed_if_empty executes seed SQL when users table has 0 rows."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=0)
        mock_conn.execute = AsyncMock()

        from app.db import _seed_if_empty

        await _seed_if_empty(mock_conn)
        # Should have called execute with the seed SQL
        assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_seed_if_empty_skips_when_data_exists(self):
        """_seed_if_empty does NOT execute seed SQL when users table has rows."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.execute = AsyncMock()

        from app.db import _seed_if_empty

        await _seed_if_empty(mock_conn)
        # fetchval was called to check count, but execute should NOT be called for seed
        mock_conn.fetchval.assert_called_once()
        mock_conn.execute.assert_not_called()


class TestCloseDb:
    """Tests for close_db."""

    @pytest.mark.asyncio
    async def test_close_db_closes_pool(self):
        """close_db awaits pool.close()."""
        mock_pool = AsyncMock()

        from app.db import close_db

        await close_db(mock_pool)
        mock_pool.close.assert_awaited_once()
