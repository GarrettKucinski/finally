# Coding Conventions

**Analysis Date:** 2026-03-01

## Naming Patterns

**Files:**
- Module files use lowercase with underscores: `cache.py`, `market_data.py`, `seed_prices.py`
- Test files follow pytest convention: `test_cache.py`, `test_simulator.py` (matching the module name)
- Router/factory files: `factory.py`, `stream.py`, `interface.py`

**Functions:**
- Async functions use snake_case: `async def start()`, `async def poll_once()`
- Regular functions use snake_case: `def step()`, `def create_market_data_source()`
- Private/internal functions prefixed with single underscore: `_generate_events()`, `_poll_loop()`, `_rebuild_cholesky()`
- Factory functions prefixed with `create_`: `create_market_data_source()`, `create_stream_router()`
- Helper functions in tests prefixed with underscore: `_make_mock_request()`, `_collect_events()`

**Classes:**
- Use PascalCase: `PriceCache`, `MarketDataSource`, `PriceUpdate`, `GBMSimulator`, `SimulatorDataSource`, `MassiveDataSource`
- Test classes use `Test` prefix: `TestPriceCacheFirstUpdate`, `TestGBMSimulatorInit`, `TestGenerateEventsRetryHeader`
- Test subclasses organize related tests: `class TestPriceCacheFirstUpdate:`, `class TestPriceCacheSubsequentUpdates:` (one class per logical grouping)

**Variables:**
- Instance variables use snake_case: `self._tickers`, `self._prices`, `self._lock`, `self._event_prob`
- Private instance variables are prefixed with single underscore: `self._prices`, `self._cache`, `self._task`
- Constants use UPPERCASE_WITH_UNDERSCORES: `TRADING_SECONDS_PER_YEAR`, `DEFAULT_DT`, `SEED_PRICES`, `CORRELATION_GROUPS`
- Type variables and dict keys use snake_case: `timestamp_ms`, `ticker`, `price_cache`

**Type Hints:**
- Use Python 3.12+ style union syntax: `float | None` not `Optional[float]`
- Use `list[str]` not `List[str]`
- Use `dict[str, float]` not `Dict[str, float]`
- Always include return type hints: `def step(self) -> dict[str, float]:`

## Code Style

**Formatting:**
- Line length: 100 characters (ruff config: `line-length = 100`)
- Use 4 spaces for indentation (Python standard)
- Use `from __future__ import annotations` at the top of every module for forward references

**Import Organization:**
- Order: standard library, third-party, local imports
- Imports are alphabetically sorted within groups
- Example from `simulator.py`:
  ```python
  from __future__ import annotations

  import asyncio
  import logging
  import math
  import random

  import numpy as np

  from .cache import PriceCache
  from .interface import MarketDataSource
  from .seed_prices import (...)
  ```

**Docstrings:**
- Module-level docstrings at the top of every file describing purpose, key classes/functions, and usage patterns
- Triple-quoted docstrings for all classes and public methods
- Format: one-line summary, blank line, detailed explanation, then Args/Returns if needed
- Example from `models.py`:
  ```python
  class PriceUpdate:
      """Immutable snapshot of a single ticker's price at a point in time.

      Created by PriceCache.update() and shared across all readers.
      Safe to cache, copy, and pass between async tasks without locking.
      """
  ```
- Function docstrings include purpose, Args, Returns sections when relevant
- Comments explain the "why" not the "what"

## Linting & Formatting

**Linter:**
- Tool: `ruff` (fast Python linter)
- Config in `pyproject.toml`: `line-length = 100`, `target-version = "py312"`
- Selected rules: `["E", "F", "I", "UP"]` — pycodestyle errors, Pyflakes, isort imports, pyupgrade

**Application:**
- No `.prettierrc` file — code uses ruff's built-in defaults
- No automated formatter configured — assumes manual formatting follows ruff rules
- Developers should run `ruff check --fix` to auto-fix linting issues

## Error Handling

**Patterns:**
- Use specific exception types: catch `AttributeError`, `TypeError`, `ValueError` as appropriate
- Log errors with context: `logger.error(f"Failed to poll: {e}")`
- In background tasks, wrap in try-except to prevent task death: all `_poll_loop()`, `_run_loop()` have exception handling
- Gracefully degrade: if an individual API snapshot fails to parse, skip it and continue; if the entire API call fails, log and retry on next interval
- For client connections, catch `asyncio.CancelledError` explicitly when cleaning up: `except asyncio.CancelledError: pass`

**Example from `massive_client.py`:**
```python
try:
    # API call or processing
except Exception as e:
    logger.error(f"Failed to poll: {e}")
    # Continue to next iteration
```

## Logging

**Framework:** Python `logging` module with `logger = logging.getLogger(__name__)`

**Patterns:**
- One logger per module: `logger = logging.getLogger(__name__)` at module level
- Log startup events: "Using SimulatorDataSource", "MASSIVE_API_KEY found"
- Log errors with context: include the operation and exception message
- Use appropriate levels: `logger.info()` for startup/configuration, `logger.error()` for exceptions
- All loggers created at module level, never inline

**Example:**
```python
logger = logging.getLogger(__name__)
# ...
logger.info("MASSIVE_API_KEY found — using MassiveDataSource")
logger.error(f"Failed to poll: {e}")
```

## Module Design

**Public API Pattern:**
- Each package (e.g., `app.market`) defines an `__init__.py` with `__all__` listing public exports
- Example `app.market.__init__.py`:
  ```python
  from .cache import PriceCache
  from .factory import create_market_data_source
  from .interface import MarketDataSource
  from .models import PriceUpdate
  from .stream import create_stream_router

  __all__ = [
      "PriceUpdate",
      "PriceCache",
      "MarketDataSource",
      "create_market_data_source",
      "create_stream_router",
  ]
  ```
- Downstream code imports only from the package, not internal modules

**Dataclass Usage:**
- Use frozen dataclasses for immutable data: `@dataclass(frozen=True, slots=True)`
- Slots optimize memory and prevent accidental attribute assignment
- Example: `PriceUpdate` is immutable to ensure thread-safe sharing across async tasks

**Abstract Base Classes:**
- Use `ABC` and `@abstractmethod` to define interfaces
- All implementations must provide all abstract methods
- Example: `MarketDataSource` is ABC; both `SimulatorDataSource` and `MassiveDataSource` implement it

**Factory Pattern:**
- Functions prefixed with `create_`: `create_market_data_source()`, `create_stream_router()`
- Factories encapsulate object creation logic and dependency injection
- Return the abstract interface type, not the concrete class
- Example: `create_market_data_source()` returns `MarketDataSource` (the ABC) not `SimulatorDataSource`

## Thread Safety

**Locking:**
- Use `threading.Lock()` for protecting shared mutable state
- Acquired with context manager: `with self._lock:`
- Used in `PriceCache` because the Massive client runs synchronous REST calls via `asyncio.to_thread()`, which executes in a thread pool
- Version counters bumped inside the lock to ensure readers see consistent snapshots

## Comments & Documentation

**When to Comment:**
- Explain non-obvious math: GBM formula includes a detailed comment showing the equation and variable meanings
- Explain correlation matrices: CORRELATION_GROUPS has inline comments explaining sector groupings
- Explain design decisions: comments explain why Cholesky is not built for single-ticker case
- Do NOT comment obvious code: `self._prices.pop(ticker, None)` needs no comment

**Docstrings:**
- Every public class and function has a docstring
- Module docstrings list key exports and usage patterns
- Docstrings use triple quotes and follow PEP 257

## Type Safety

**Pattern:**
- All functions have complete type hints: parameters and return types
- Use `| None` for optionals: `def get(self, ticker: str) -> PriceUpdate | None:`
- Use proper container types: `dict[str, float]`, `list[str]`, not bare `dict` or `list`
- Justify any `# type: ignore` comments (rare; seen in tests when deliberately breaking types)

---

*Convention analysis: 2026-03-01*
