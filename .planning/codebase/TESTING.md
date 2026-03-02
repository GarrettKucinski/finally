# Testing Patterns

**Analysis Date:** 2026-03-01

## Test Framework

**Runner:**
- Framework: `pytest` 8.3.0+
- Config location: `backend/pyproject.toml`
- Async mode: `asyncio_mode = "auto"` — all async test functions are automatically treated as asyncio tests
- Test discovery: `testpaths = ["tests"]` — pytest only scans the `tests/` directory

**Assertion Library:**
- Python's built-in `assert` statements (standard pytest approach)
- Example: `assert source._tickers == {"AAPL", "GOOGL", "MSFT"}`

**Run Commands:**
```bash
# From backend/ directory:
python -m pytest                           # Run all tests
python -m pytest tests/market/test_models.py  # Run a specific file
python -m pytest -v                        # Verbose output
python -m pytest --cov=app                 # Coverage report
python -m pytest -k "test_step"            # Run tests matching pattern
```

**Dependencies:**
- `pytest>=8.3.0` — test runner
- `pytest-asyncio>=0.24.0` — async test support
- `pytest-cov>=5.0.0` — coverage reporting

## Test File Organization

**Location:** Tests live in `backend/tests/` mirroring the `backend/app/` structure

**Structure:**
```
backend/
├── app/
│   └── market/
│       ├── models.py
│       ├── cache.py
│       ├── simulator.py
│       └── ...
└── tests/
    ├── conftest.py          # Shared fixtures
    └── market/
        ├── test_models.py
        ├── test_cache.py
        ├── test_simulator.py
        └── ...
```

**Naming Convention:**
- Test files: `test_<module_name>.py` matching the module being tested
- Test classes: `Test<Component><Aspect>` — one class per logical grouping
- Test methods: `test_<behavior>` or `test_<condition>_<expected_result>`
- Example: `test_models.py` has `TestPriceUpdateProperties`, `TestPriceUpdateSerialization`, `TestPriceUpdateImmutability`

## Test Structure

**Typical Test Class Organization:**

```python
"""
Tests for app.market.models — PriceUpdate dataclass.

11 tests covering:
- Computed properties: change, change_percent, direction
- Edge cases: zero previous price, equal prices (flat), negative change
- to_dict() serialization
- Frozen immutability
"""

from dataclasses import FrozenInstanceError
from app.market.models import PriceUpdate


class TestPriceUpdateProperties:
    """Tests for computed properties."""

    def test_direction_up(self):
        update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00)
        assert update.direction == "up"

    def test_direction_down(self):
        update = PriceUpdate(ticker="AAPL", price=189.00, previous_price=190.00)
        assert update.direction == "down"
```

**Docstrings:**
- Module-level docstring lists the component being tested and scope
- Test class docstring explains what aspect is being tested
- Test methods have no docstrings — the method name is self-documenting
- Example class docstring: `"""Tests for computed properties."""`

**Fixtures:**
- Defined with `@pytest.fixture` decorator
- Minimal setup — each fixture does one thing
- Example from `test_factory.py`:
  ```python
  @pytest.fixture
  def cache() -> PriceCache:
      return PriceCache()
  ```
- Fixtures are passed as function parameters: `def test_something(cache: PriceCache):`

**Setup and Teardown:**
- No explicit `setUp()` or `tearDown()` — use fixtures instead
- For async cleanup, use `@pytest.fixture` with `yield`:
  ```python
  @pytest.fixture
  async def source(cache: PriceCache):
      source = SimulatorDataSource(price_cache=cache, update_interval=0.05)
      yield source
      await source.stop()  # Cleanup
  ```

## Async Testing

**Pattern:**
- Mark test methods as `async def`: `async def test_start_seeds_cache_immediately(self, ...)`
- Pytest-asyncio automatically detects and runs them
- Example from `test_simulator_source.py`:
  ```python
  async def test_start_seeds_cache_immediately(self, source: SimulatorDataSource, cache: PriceCache):
      """After start(), the cache already has prices — no need to wait for a tick."""
      await source.start(["AAPL", "GOOGL"])
      await source.stop()

      assert cache.get("AAPL") is not None
      assert cache.get("GOOGL") is not None
  ```

**Testing Async Iteration:**
- Use helper function to collect async generator output:
  ```python
  async def _collect_events(cache, request, max_events=10, interval=0.01):
      """Collect up to `max_events` yielded strings from _generate_events."""
      events = []
      async for event in _generate_events(cache, request, interval=interval):
          events.append(event)
          if len(events) >= max_events:
              break
      return events
  ```

**Testing asyncio.Task Management:**
- Create dummy tasks to test cleanup:
  ```python
  async def test_stop_cancels_task(self, source):
      async def dummy_loop():
          try:
              await asyncio.sleep(1000)
          except Exception:
              pass
      source._task = asyncio.create_task(dummy_loop())
      await source.stop()
      assert source._task is None
  ```

## Mocking

**Framework:** `unittest.mock` (Python standard library)

**Patterns:**

**1. Simple Mock Objects:**
```python
from unittest.mock import MagicMock

snapshot = MagicMock()
snapshot.ticker = "AAPL"
snapshot.last_trade.price = 191.50
snapshot.last_trade.timestamp = 1709312400000.0
```

**2. Mocking Methods:**
```python
from unittest.mock import patch

with patch.object(source, "_fetch_snapshots", return_value=snapshots):
    await source._poll_once()
```

**3. Async Mocks:**
```python
from unittest.mock import AsyncMock

request = MagicMock()
request.is_disconnected = AsyncMock(return_value=False)
```

**4. Side Effects (Exceptions):**
```python
with patch.object(source, "_fetch_snapshots", side_effect=Exception("API error")):
    await source._poll_once()  # Should not raise
```

**5. Mock Assertion:**
```python
mock_fetch.assert_not_called()
mock_fetch.assert_called_once()
```

**What to Mock:**
- External APIs (Massive REST client)
- System dependencies (file I/O, network)
- Complex objects that are hard to construct (Cholesky matrices)
- Control flow (e.g., `request.is_disconnected()` to simulate client disconnect)

**What NOT to Mock:**
- The code under test itself
- Simple data classes and models (construct real instances)
- The cache (test real behavior; it's thread-safe and deterministic)
- Business logic (test the actual computation, not mocks)

## Test Fixtures

**Common Fixtures:**

**Cache Fixture (co-located in test files):**
```python
@pytest.fixture
def cache() -> PriceCache:
    return PriceCache()
```

**Source Fixture (with configuration):**
```python
@pytest.fixture
def source(cache: PriceCache) -> SimulatorDataSource:
    return SimulatorDataSource(price_cache=cache, update_interval=0.05)
```

**Monkeypatch (pytest built-in):**
- Isolate environment variable tests
- Example from `test_factory.py`:
  ```python
  def test_no_api_key_returns_simulator(self, cache: PriceCache, monkeypatch: pytest.MonkeyPatch):
      monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
      source = create_market_data_source(cache)
      assert isinstance(source, SimulatorDataSource)
  ```

## Coverage

**Configuration:**
- Location: `pyproject.toml`
- Settings:
  ```toml
  [tool.coverage.run]
  source = ["app"]
  omit = ["tests/*"]
  ```

**Generate Report:**
```bash
python -m pytest --cov=app --cov-report=html
```

**Requirements:** None enforced (no minimum threshold in CI), but coverage is tracked

## Test Types

**Unit Tests (Majority):**
- Scope: Single class or function
- Isolation: Heavy mocking of dependencies
- Examples:
  - `test_models.py` — tests PriceUpdate dataclass properties in isolation
  - `test_cache.py` — tests PriceCache methods (no simulator, no Massive client)
  - `test_simulator.py` — tests GBMSimulator math engine (synchronous, deterministic)

**Integration Tests:**
- Scope: Multiple components working together
- Real dependencies (not mocked)
- Examples:
  - `test_simulator_source.py` — tests SimulatorDataSource (async wrapper) + GBMSimulator + PriceCache
  - `test_stream.py` — tests SSE generator + PriceCache + mock Request
  - `test_massive.py` — tests MassiveDataSource + mocked REST client (not real Massive API)

**E2E Tests:**
- Location: `test/` directory (separate from unit/integration tests)
- Framework: Playwright
- Infrastructure: separate `docker-compose.test.yml`
- Run: against both frontend and backend containers
- Environment: `LLM_MOCK=true` for determinism
- Not currently exercised (only core market data is built)

## Common Test Patterns

**Arrange-Act-Assert (AAA):**
```python
def test_direction_up(self):
    # Arrange
    update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00)
    # Act & Assert (combined in simple cases)
    assert update.direction == "up"
```

**Testing Edge Cases:**
```python
def test_change_percent_zero_previous_price(self):
    """Zero previous_price returns 0.0 (no division by zero)."""
    update = PriceUpdate(ticker="AAPL", price=100.00, previous_price=0.0)
    assert update.change_percent == 0.0
```

**Testing Multiple Aspects:**
```python
async def test_to_dict_values(self):
    update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00, timestamp=1709312400.0)
    result = update.to_dict()
    assert result["ticker"] == "AAPL"
    assert result["price"] == 191.50
    assert result["previous_price"] == 190.00
    assert result["timestamp"] == 1709312400.0
    assert result["direction"] == "up"
```

**Testing Thread Safety:**
```python
def test_concurrent_updates_do_not_corrupt(self):
    cache = PriceCache()
    errors = []

    def updater(ticker: str, prices: list[float]) -> None:
        try:
            for price in prices:
                cache.update(ticker, price)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=updater, args=("AAPL", [float(i) for i in range(1, 51)])),
        threading.Thread(target=updater, args=("GOOGL", [float(i) * 2 for i in range(1, 51)])),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert "AAPL" in cache
    assert "GOOGL" in cache
```

**Testing Immutability:**
```python
def test_frozen_raises_on_assignment(self):
    update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00)
    try:
        update.price = 200.0  # type: ignore[misc]
        assert False, "Should have raised FrozenInstanceError"
    except (FrozenInstanceError, AttributeError):
        pass  # Either exception is acceptable
```

**Testing Exception Handling:**
```python
async def test_poll_handles_api_error(self, source: MassiveDataSource, cache: PriceCache):
    """API errors are caught and logged — the source never crashes."""
    source._client = MagicMock()
    source._tickers = ["AAPL"]
    with patch.object(source, "_fetch_snapshots", side_effect=Exception("API error")):
        await source._poll_once()  # Should not raise
```

## Test Coverage Status

**Currently Tested (Market Data Component):**
- `test_models.py` — 11 tests (PriceUpdate properties, serialization, immutability)
- `test_cache.py` — 13 tests (cache operations, thread safety, version counter)
- `test_simulator.py` — 17 tests (GBM math, price generation, correlation)
- `test_simulator_source.py` — 10+ tests (async lifecycle, add/remove ticker)
- `test_massive.py` — 13 tests (REST polling, snapshot parsing, error handling)
- `test_factory.py` — 7 tests (source selection based on env vars)
- `test_stream.py` — 13+ tests (SSE streaming, change detection, disconnection handling)

**Total:** ~84 tests covering market data component

**Untested (Not Yet Built):**
- Portfolio (positions, trades, cash balance)
- Chat (LLM integration, structured output parsing)
- Database (schema, migrations, queries)
- API routes (FastAPI endpoints, request/response validation)
- Frontend (React components, styling, interactivity)

---

*Testing analysis: 2026-03-01*
