"""
Tests for background snapshot tasks.

Verifies:
- snapshot_recorder_loop calls record_snapshot on each iteration (PORT-08)
- snapshot_recorder_loop handles errors gracefully (logs, continues)
- snapshot_cleanup_loop deletes records older than 24 hours (PORT-10)
- snapshot_cleanup_loop handles errors gracefully (logs, continues)
- snapshot_cleanup_loop sleeps 300 seconds (5 minutes) between runs

Uses unittest.mock.patch to mock asyncio.sleep (raises CancelledError
after first call to test the loop runs one iteration).
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.snapshots import snapshot_cleanup_loop, snapshot_recorder_loop


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_pool():
    """Create a mock pool with acquire() returning a mock connection."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="DELETE 3")
    pool = AsyncMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire
    return pool, conn


# ---------------------------------------------------------------------------
# snapshot_recorder_loop
# ---------------------------------------------------------------------------

async def test_snapshot_recorder_loop():
    """snapshot_recorder_loop calls record_snapshot on each iteration (PORT-08)."""
    pool = AsyncMock()
    cache = MagicMock()
    call_count = 0

    async def mock_sleep(seconds):
        nonlocal call_count
        call_count += 1
        assert seconds == 30, f"Expected 30s sleep, got {seconds}"
        raise asyncio.CancelledError()

    with patch("app.tasks.snapshots.record_snapshot", new_callable=AsyncMock) as mock_record, \
         patch("app.tasks.snapshots.asyncio.sleep", side_effect=mock_sleep):
        with pytest.raises(asyncio.CancelledError):
            await snapshot_recorder_loop(pool, cache)

        mock_record.assert_called_once_with(pool, cache)
        assert call_count == 1


async def test_snapshot_recorder_handles_errors():
    """If record_snapshot raises, loop continues (logs error, does not crash)."""
    pool = AsyncMock()
    cache = MagicMock()
    iteration = 0

    async def mock_sleep(seconds):
        nonlocal iteration
        iteration += 1
        if iteration >= 2:
            raise asyncio.CancelledError()

    with patch("app.tasks.snapshots.record_snapshot", new_callable=AsyncMock, side_effect=RuntimeError("DB error")) as mock_record, \
         patch("app.tasks.snapshots.asyncio.sleep", side_effect=mock_sleep):
        with pytest.raises(asyncio.CancelledError):
            await snapshot_recorder_loop(pool, cache)

        # Should have been called twice (once per iteration before cancel)
        assert mock_record.call_count == 2


# ---------------------------------------------------------------------------
# snapshot_cleanup_loop
# ---------------------------------------------------------------------------

async def test_snapshot_cleanup():
    """snapshot_cleanup_loop executes DELETE for records older than 24 hours (PORT-10)."""
    pool, conn = _make_mock_pool()

    async def mock_sleep(seconds):
        raise asyncio.CancelledError()

    with patch("app.tasks.snapshots.asyncio.sleep", side_effect=mock_sleep):
        with pytest.raises(asyncio.CancelledError):
            await snapshot_cleanup_loop(pool)

    conn.execute.assert_called_once_with(
        "DELETE FROM portfolio_snapshots WHERE recorded_at < NOW() - INTERVAL '24 hours'"
    )


async def test_snapshot_cleanup_handles_errors():
    """If DELETE raises, loop continues (logs error, does not crash)."""
    pool = AsyncMock()
    iteration = 0

    @asynccontextmanager
    async def failing_acquire():
        raise RuntimeError("DB connection failed")
        yield  # pragma: no cover

    pool.acquire = failing_acquire

    async def mock_sleep(seconds):
        nonlocal iteration
        iteration += 1
        if iteration >= 2:
            raise asyncio.CancelledError()

    with patch("app.tasks.snapshots.asyncio.sleep", side_effect=mock_sleep):
        with pytest.raises(asyncio.CancelledError):
            await snapshot_cleanup_loop(pool)

    # Loop ran twice without crashing
    assert iteration == 2


async def test_snapshot_cleanup_interval():
    """snapshot_cleanup_loop sleeps 300 seconds (5 minutes) between runs."""
    pool, conn = _make_mock_pool()
    sleep_values = []

    async def mock_sleep(seconds):
        sleep_values.append(seconds)
        raise asyncio.CancelledError()

    with patch("app.tasks.snapshots.asyncio.sleep", side_effect=mock_sleep):
        with pytest.raises(asyncio.CancelledError):
            await snapshot_cleanup_loop(pool)

    assert sleep_values == [300]
