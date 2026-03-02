"""
Database pool lifecycle for FinAlly.

Provides:
- init_db(database_url) -> asyncpg.Pool: create pool, run schema DDL, seed default data
- close_db(pool): gracefully close the pool
- _seed_if_empty(conn): conditionally insert seed data when users table is empty

The pool uses statement_cache_size=0 for Neon serverless Postgres compatibility
(Neon's connection pooler does not support prepared statements).
"""

from __future__ import annotations

import logging
import pathlib

import asyncpg

logger = logging.getLogger(__name__)

# Load SQL files once at module import time
_SCHEMA_DIR = pathlib.Path(__file__).parent / "schema"
_TABLES_SQL = (_SCHEMA_DIR / "tables.sql").read_text()
_SEED_SQL = (_SCHEMA_DIR / "seed.sql").read_text()


async def init_db(database_url: str) -> asyncpg.Pool:
    """Create the asyncpg connection pool, run schema DDL, and seed if empty.

    Args:
        database_url: Postgres connection string (e.g., from Neon).

    Returns:
        An initialized asyncpg.Pool ready for use.
    """
    logger.info("Creating database connection pool...")
    pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=2,
        max_size=10,
        statement_cache_size=0,
    )

    async with pool.acquire() as conn:
        logger.info("Running schema DDL (CREATE TABLE IF NOT EXISTS)...")
        await conn.execute(_TABLES_SQL)

        await _seed_if_empty(conn)

    logger.info("Database initialization complete.")
    return pool


async def _seed_if_empty(conn: asyncpg.Connection) -> None:
    """Insert default seed data if the default user doesn't exist.

    Checks for the specific default user UUID. If missing, executes seed.sql.
    This handles the case where the DB has stale data from previous runs
    but the default user was removed or never created.
    """
    default_user_id = "00000000-0000-0000-0000-000000000001"
    exists = await conn.fetchval(
        "SELECT 1 FROM users WHERE id = $1", default_user_id
    )
    if not exists:
        logger.info("Default user not found — seeding default data...")
        await conn.execute(_SEED_SQL)
        logger.info("Seed data inserted.")
    else:
        logger.info("Default user exists — skipping seed.")


async def close_db(pool: asyncpg.Pool) -> None:
    """Gracefully close the database connection pool."""
    logger.info("Closing database connection pool...")
    await pool.close()
    logger.info("Database pool closed.")
