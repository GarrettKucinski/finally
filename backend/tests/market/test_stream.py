"""
Tests for app.market.stream — SSE streaming endpoint.

Tests covering:
- _generate_events: retry header, version-based change detection, JSON payload format,
  empty cache skipping, client disconnection, CancelledError handling
- create_stream_router: router creation, endpoint registration, response headers
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from app.market.cache import PriceCache
from app.market.stream import _generate_events, create_stream_router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_request(*, disconnected_after: int | None = None) -> MagicMock:
    """Create a mock Request whose is_disconnected() returns False,
    then True after `disconnected_after` calls (if set).
    """
    request = MagicMock()
    call_count = 0

    async def is_disconnected() -> bool:
        nonlocal call_count
        call_count += 1
        if disconnected_after is not None and call_count > disconnected_after:
            return True
        return False

    request.is_disconnected = is_disconnected
    return request


async def _collect_events(
    cache: PriceCache,
    request: MagicMock,
    max_events: int = 10,
    interval: float = 0.01,
) -> list[str]:
    """Collect up to `max_events` yielded strings from _generate_events."""
    events: list[str] = []
    async for event in _generate_events(cache, request, interval=interval):
        events.append(event)
        if len(events) >= max_events:
            break
    return events


# ---------------------------------------------------------------------------
# _generate_events unit tests
# ---------------------------------------------------------------------------

class TestGenerateEventsRetryHeader:
    """First yielded value is the retry directive."""

    async def test_first_event_is_retry(self):
        cache = PriceCache()
        request = _make_mock_request(disconnected_after=0)
        events = await _collect_events(cache, request, max_events=1)
        assert events[0] == "retry: 1000\n\n"


class TestGenerateEventsVersionDetection:
    """Events are only sent when the cache version changes."""

    async def test_sends_data_when_version_changes(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        # Disconnect after 2 is_disconnected calls (1 loop iteration)
        request = _make_mock_request(disconnected_after=2)
        events = await _collect_events(cache, request, max_events=5, interval=0.01)
        # Should have retry + one data event
        assert events[0] == "retry: 1000\n\n"
        assert len(events) >= 2
        assert events[1].startswith("data: ")

    async def test_skips_when_version_unchanged(self):
        """If version doesn't change between iterations, no duplicate data is sent."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        # Allow 3 iterations then disconnect
        request = _make_mock_request(disconnected_after=4)
        events = await _collect_events(cache, request, max_events=10, interval=0.01)
        # retry + exactly one data event (version doesn't change between iterations)
        data_events = [e for e in events if e.startswith("data: ")]
        assert len(data_events) == 1


class TestGenerateEventsPayloadFormat:
    """SSE data payloads are correctly formatted JSON."""

    async def test_payload_is_valid_json(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00, timestamp=1000.0)
        request = _make_mock_request(disconnected_after=1)
        events = await _collect_events(cache, request, max_events=5, interval=0.01)
        data_events = [e for e in events if e.startswith("data: ")]
        assert len(data_events) >= 1
        # Strip "data: " prefix and trailing "\n\n"
        raw = data_events[0][len("data: "):].rstrip("\n")
        parsed = json.loads(raw)
        assert "AAPL" in parsed

    async def test_payload_contains_ticker_fields(self):
        cache = PriceCache()
        cache.update("AAPL", 191.50, timestamp=1000.0)
        request = _make_mock_request(disconnected_after=1)
        events = await _collect_events(cache, request, max_events=5, interval=0.01)
        data_events = [e for e in events if e.startswith("data: ")]
        raw = data_events[0][len("data: "):].rstrip("\n")
        parsed = json.loads(raw)
        ticker_data = parsed["AAPL"]
        assert ticker_data["ticker"] == "AAPL"
        assert ticker_data["price"] == 191.50
        assert "previous_price" in ticker_data
        assert "direction" in ticker_data
        assert "change" in ticker_data
        assert "change_percent" in ticker_data
        assert "timestamp" in ticker_data

    async def test_payload_multiple_tickers(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00, timestamp=1000.0)
        cache.update("GOOGL", 175.00, timestamp=1000.0)
        request = _make_mock_request(disconnected_after=1)
        events = await _collect_events(cache, request, max_events=5, interval=0.01)
        data_events = [e for e in events if e.startswith("data: ")]
        raw = data_events[0][len("data: "):].rstrip("\n")
        parsed = json.loads(raw)
        assert "AAPL" in parsed
        assert "GOOGL" in parsed

    async def test_sse_data_line_format(self):
        """Each data event uses proper SSE framing: 'data: ...\n\n'."""
        cache = PriceCache()
        cache.update("AAPL", 190.00, timestamp=1000.0)
        request = _make_mock_request(disconnected_after=1)
        events = await _collect_events(cache, request, max_events=5, interval=0.01)
        data_events = [e for e in events if e.startswith("data: ")]
        assert data_events[0].endswith("\n\n")


class TestGenerateEventsEmptyCache:
    """Empty cache does not produce data events."""

    async def test_no_data_event_when_cache_empty(self):
        cache = PriceCache()
        request = _make_mock_request(disconnected_after=2)
        events = await _collect_events(cache, request, max_events=5, interval=0.01)
        data_events = [e for e in events if e.startswith("data: ")]
        assert len(data_events) == 0


class TestGenerateEventsDisconnection:
    """Generator exits cleanly when client disconnects."""

    async def test_stops_on_disconnect(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        request = _make_mock_request(disconnected_after=1)
        events = await _collect_events(cache, request, max_events=100, interval=0.01)
        # Should terminate rather than hitting max_events
        assert len(events) < 100

    async def test_handles_cancelled_error(self):
        """CancelledError is caught gracefully (not propagated)."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        gen = _generate_events(cache, request, interval=0.01)
        # Consume retry header
        await gen.__anext__()
        # Consume first data event
        await gen.__anext__()
        # Throw CancelledError — should be caught
        try:
            await gen.athrow(asyncio.CancelledError)
        except StopAsyncIteration:
            pass  # Generator exited cleanly


# ---------------------------------------------------------------------------
# create_stream_router tests
# ---------------------------------------------------------------------------

class TestCreateStreamRouter:
    """Router factory creates a working FastAPI router."""

    def test_router_has_prices_route(self):
        cache = PriceCache()
        router = create_stream_router(cache)
        route_names = [getattr(r, "name", None) for r in router.routes]
        assert "stream_prices" in route_names

    def test_router_prefix(self):
        cache = PriceCache()
        router = create_stream_router(cache)
        assert router.prefix == "/api/stream"

    def test_router_tags(self):
        cache = PriceCache()
        router = create_stream_router(cache)
        assert "streaming" in router.tags
