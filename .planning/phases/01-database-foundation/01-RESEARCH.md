# Phase 1: Database Foundation - Research

**Researched:** 2026-03-02
**Domain:** asyncpg + Neon Postgres, FastAPI lifespan, Pydantic Settings, SQL schema initialization
**Confidence:** HIGH

## Summary

Phase 1 establishes the database foundation for the FinAlly backend: connecting to Neon serverless Postgres via asyncpg, initializing all 7 tables on startup, seeding the default user and watchlist, and exposing a health check endpoint. The existing backend has a fully working market data subsystem (`backend/app/market/`) but no main FastAPI application entry point, no database layer, and no Settings class yet.

The core stack is already installed in `pyproject.toml`: asyncpg 0.31.0, pydantic-settings 2.13.1, and FastAPI 0.135.1. No additional dependencies are needed. The critical technical detail is that Neon's serverless proxy requires `statement_cache_size=0` when using asyncpg's connection pool (Neon uses PgBouncer-style connection pooling internally, which conflicts with asyncpg's default prepared statement caching). SSL is handled automatically -- asyncpg parses `sslmode=require` from the DATABASE_URL DSN string.

**Primary recommendation:** Create a `Settings` class with Pydantic Settings, a `db.py` module for pool lifecycle, a `schema/` directory with raw SQL, a FastAPI `main.py` with lifespan event that initializes DB + market data, and a `/api/health` endpoint that verifies DB connectivity.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Backend initializes asyncpg connection pool on startup with Neon Postgres (`statement_cache_size=0`) | asyncpg `create_pool()` accepts `statement_cache_size` via `**connect_kwargs`; Neon requires `=0` due to PgBouncer-style connection pooling; pool created in FastAPI lifespan |
| INFRA-02 | Backend creates all tables on startup via `CREATE TABLE IF NOT EXISTS` (users, users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages) | asyncpg `pool.execute()` runs raw SQL; use `CREATE TABLE IF NOT EXISTS` so repeated startups are safe; all 7 tables defined in PLAN.md section 7 |
| INFRA-03 | Backend seeds default user (fixed UUID, $10,000 cash) and 10 watchlist tickers if tables are empty | Conditional seed: check `SELECT COUNT(*) FROM users`, if 0 then INSERT; use fixed UUID for idempotency; 10 tickers from `DEFAULT_WATCHLIST` in seed_prices.py |
| INFRA-04 | `GET /api/health` returns 200 with DB connectivity check | FastAPI router with simple `SELECT 1` query via pool; return JSON with status and db connectivity flag |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncpg | 0.31.0 | Async Postgres driver + connection pool | Already in pyproject.toml; fastest Python Postgres driver; native async; binary protocol |
| pydantic-settings | 2.13.1 | Environment variable management | Already in pyproject.toml; validates config on startup (fail-fast); type coercion; `.env` file support |
| FastAPI | 0.135.1 | Web framework with lifespan support | Already in pyproject.toml; `lifespan` async context manager is the modern startup/shutdown pattern |
| pydantic | 2.x | API request/response schemas + Settings base | Already in pyproject.toml (transitive via FastAPI and pydantic-settings) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uvicorn | 0.32.0+ | ASGI server | Already in pyproject.toml; runs FastAPI app (`uvicorn app.main:app`) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncpg (raw SQL) | SQLAlchemy async | ORM adds complexity; PLAN.md specifies raw SQL via asyncpg; schema is simple enough |
| Raw SQL files | Alembic migrations | Overkill for v1; `CREATE TABLE IF NOT EXISTS` is sufficient; no migration history needed |

**Installation:** No new dependencies needed -- everything is already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── __init__.py              # (exists, empty)
├── main.py                  # NEW: FastAPI app, lifespan, router includes
├── config.py                # NEW: Pydantic Settings class
├── db.py                    # NEW: Pool lifecycle (init_db, close_db, get_pool)
├── schema/                  # NEW: SQL schema files
│   ├── __init__.py
│   ├── tables.sql           # All CREATE TABLE IF NOT EXISTS statements
│   └── seed.sql             # Default user + watchlist INSERT statements
├── routes/                  # NEW: API route modules
│   └── health.py            # GET /api/health endpoint
└── market/                  # (exists, complete)
    ├── __init__.py
    ├── models.py
    ├── interface.py
    ├── cache.py
    ├── seed_prices.py
    ├── simulator.py
    ├── massive_client.py
    ├── factory.py
    └── stream.py
```

### Pattern 1: FastAPI Lifespan with asyncpg Pool

**What:** Use the modern `@asynccontextmanager` lifespan pattern to manage the asyncpg pool and market data source lifecycle.
**When to use:** Always -- this is the FastAPI-recommended approach (deprecated alternatives: `on_startup`/`on_shutdown`).

```python
# Source: FastAPI official docs (https://fastapi.tiangolo.com/advanced/events/)
# + asyncpg docs (https://magicstack.github.io/asyncpg/current/api/index.html)
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create pool, init schema, seed data, start market data
    pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10,
        statement_cache_size=0,  # REQUIRED for Neon
    )
    app.state.db_pool = pool

    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)  # CREATE TABLE IF NOT EXISTS ...
        await _seed_if_empty(conn)

    # Start market data (existing subsystem)
    cache = PriceCache()
    source = create_market_data_source(cache)
    await source.start(DEFAULT_WATCHLIST)
    app.state.price_cache = cache
    app.state.market_source = source

    yield  # App is running

    # Shutdown: stop market data, close pool
    await source.stop()
    await pool.close()

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: Pydantic Settings for Configuration

**What:** Single `Settings` class that validates all env vars on import, with `.env` file support.
**When to use:** Always -- fail fast on missing config.

```python
# Source: pydantic-settings docs (https://github.com/pydantic/pydantic-settings)
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    openrouter_api_key: str = ""
    massive_api_key: str = ""
    llm_mock: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
```

Note: The PLAN.md specifies `openrouter_api_key` as required, but for Phase 1 (no LLM integration yet) it should default to empty string to avoid blocking startup. It can be tightened later in Phase 3.

### Pattern 3: SQL Schema in Separate Files

**What:** Keep SQL DDL in `.sql` files, loaded and executed at startup.
**When to use:** When schema is non-trivial (7 tables) and readability matters.

```python
# Load SQL from file at module level
from pathlib import Path

SCHEMA_SQL = (Path(__file__).parent / "schema" / "tables.sql").read_text()
SEED_SQL = (Path(__file__).parent / "schema" / "seed.sql").read_text()
```

Alternative: Define SQL as Python string constants in `db.py`. Either works; separate files are cleaner for 7 tables.

### Pattern 4: Conditional Seeding (Idempotent)

**What:** Check if data exists before inserting seed data. Use a fixed UUID for the default user.
**When to use:** On every startup -- must be safe to run repeatedly.

```python
async def _seed_if_empty(conn):
    count = await conn.fetchval("SELECT COUNT(*) FROM users")
    if count == 0:
        await conn.execute(SEED_SQL)
```

### Pattern 5: Health Check with DB Ping

**What:** Simple endpoint that verifies DB connectivity.
**When to use:** Docker health checks, load balancers, monitoring.

```python
@router.get("/api/health")
async def health_check(request: Request):
    pool = request.app.state.db_pool
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"},
        )
```

### Anti-Patterns to Avoid

- **Global mutable pool variable:** Do not use a module-level `pool = None` that gets mutated. Use `app.state.db_pool` to store the pool on the FastAPI app instance. This is the standard FastAPI pattern and avoids import-order issues.
- **`on_startup`/`on_shutdown` events:** Deprecated in favor of `lifespan`. The lifespan pattern guarantees cleanup happens even on errors.
- **Running schema as multiple `execute()` calls:** Execute the entire DDL as a single string (asyncpg handles multiple statements in one `execute()` call). This is atomic and faster.
- **Hardcoding connection params instead of DSN:** The `DATABASE_URL` contains host, port, user, password, database, and SSL mode. Pass it as `dsn=` to `create_pool()` -- do not parse it manually.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connection pooling | Custom pool/retry logic | `asyncpg.create_pool()` | Built-in pool with min/max size, connection recycling, health checks |
| Config validation | Manual `os.environ.get()` with checks | `pydantic_settings.BaseSettings` | Type coercion, validation errors, `.env` file support, single source of truth |
| SSL context for Neon | Manual `ssl.create_default_context()` | DSN `?sslmode=require` | asyncpg parses `sslmode` from DSN automatically; Neon URLs already include it |
| UUID generation | Python `uuid.uuid4()` for PKs | `gen_random_uuid()` in Postgres | DB-generated UUIDs are the standard pattern; matches PLAN.md schema |
| App lifecycle management | Manual try/finally blocks | FastAPI `lifespan` context manager | Guaranteed cleanup, integrated with framework |

**Key insight:** asyncpg + Pydantic Settings handle all the hard parts (pooling, SSL, validation). The implementation is wiring these together with the FastAPI lifespan, plus writing SQL DDL.

## Common Pitfalls

### Pitfall 1: Missing `statement_cache_size=0` for Neon

**What goes wrong:** asyncpg caches prepared statements by default (cache size=100). Neon's serverless proxy uses PgBouncer-style transaction pooling, which reassigns connections between requests. Prepared statements created on one physical connection become invalid when the pooler routes to a different backend connection. You get errors like `prepared statement "__asyncpg_stmt_XX__" does not exist`.
**Why it happens:** Neon's connection pooler operates in transaction mode, not session mode. Prepared statements are session-scoped in Postgres.
**How to avoid:** Pass `statement_cache_size=0` to `asyncpg.create_pool()`. This disables the prepared statement cache entirely.
**Warning signs:** Intermittent `InvalidCachedStatementError` or `prepared statement does not exist` errors, especially under load.

### Pitfall 2: Pool Size Too Large for Neon Free Tier

**What goes wrong:** Neon free tier has a connection limit. Setting `min_size=10` (asyncpg default) immediately opens 10 connections, which may hit the limit.
**Why it happens:** asyncpg's default pool min/max is both 10.
**How to avoid:** Use `min_size=2, max_size=10` (or smaller). Neon free tier typically allows up to ~100 connections, but being conservative is wise for a single-backend app.
**Warning signs:** `too many connections` errors on startup.

### Pitfall 3: Schema SQL Execution Order (Foreign Keys)

**What goes wrong:** If tables with FOREIGN KEY constraints are created before the referenced table, you get `relation "X" does not exist` errors.
**Why it happens:** `CREATE TABLE IF NOT EXISTS` still validates FK references.
**How to avoid:** Order the DDL statements correctly: `users` first, then tables that reference `users(id)`. The order should be: users -> users_profile -> watchlist -> positions -> trades -> portfolio_snapshots -> chat_messages.
**Warning signs:** `relation "users" does not exist` during startup.

### Pitfall 4: Seed Data Race with `IF NOT EXISTS`

**What goes wrong:** If two backend instances start simultaneously, both might see `COUNT(*) = 0` and try to insert the same seed data, causing unique constraint violations.
**Why it happens:** Check-then-insert is not atomic without a lock.
**How to avoid:** For v1 (single instance), this is not a real concern. But for defense-in-depth, use `INSERT ... ON CONFLICT DO NOTHING` for the seed data.
**Warning signs:** `UniqueViolationError` on the seed user's email or UUID.

### Pitfall 5: Forgetting to Close Pool on Shutdown

**What goes wrong:** Orphaned connections that prevent Neon from scaling to zero.
**Why it happens:** Not calling `pool.close()` on shutdown.
**How to avoid:** The `lifespan` pattern guarantees `pool.close()` runs after `yield`, even if the app crashes.
**Warning signs:** Neon dashboard shows idle connections after app stops.

### Pitfall 6: The `.env` File Path

**What goes wrong:** Pydantic Settings looks for `.env` relative to the current working directory, not relative to the Python file. When running from Docker or a different directory, it may not find the file.
**Why it happens:** `SettingsConfigDict(env_file=".env")` uses CWD.
**How to avoid:** In development, run from project root. In Docker, the `ENV` or `env_file` in `docker-compose.yml` provides variables directly (the `.env` file path matters less). For robustness, environment variables always take priority over the `.env` file anyway.
**Warning signs:** Settings validation errors when running from unexpected directories.

## Code Examples

Verified patterns from official sources:

### Creating the asyncpg Pool with Neon-Compatible Settings

```python
# Source: asyncpg docs (https://magicstack.github.io/asyncpg/current/api/index.html)
# + Neon guide (https://neon.com/guides/fastapi-async)
import asyncpg

pool = await asyncpg.create_pool(
    dsn="postgresql://user:pass@ep-xyz.us-east-2.aws.neon.tech/finally?sslmode=require",
    min_size=2,
    max_size=10,
    statement_cache_size=0,  # Required for Neon's connection pooler
)
```

### Executing DDL with asyncpg

```python
# Source: asyncpg docs
async with pool.acquire() as conn:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL
        );
    """)
```

### Full Lifespan Pattern

```python
# Source: FastAPI docs (https://fastapi.tiangolo.com/advanced/events/)
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    pool = await asyncpg.create_pool(dsn=settings.database_url, statement_cache_size=0)
    app.state.db_pool = pool
    yield
    # Shutdown
    await pool.close()

app = FastAPI(lifespan=lifespan)
```

### Pydantic Settings with `.env` File

```python
# Source: pydantic-settings docs (https://github.com/pydantic/pydantic-settings)
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    openrouter_api_key: str = ""
    massive_api_key: str = ""
    llm_mock: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()  # Validates immediately; raises if DATABASE_URL is missing
```

### Conditional Seed with Conflict Handling

```python
# Idempotent seed: safe to run on every startup
async def seed_default_data(conn):
    count = await conn.fetchval("SELECT COUNT(*) FROM users")
    if count == 0:
        await conn.execute("""
            INSERT INTO users (id, email, password)
            VALUES ('00000000-0000-0000-0000-000000000001', 'default@finally.app', 'placeholder')
            ON CONFLICT DO NOTHING;

            INSERT INTO users_profile (user_id, cash_balance)
            VALUES ('00000000-0000-0000-0000-000000000001', 10000.0)
            ON CONFLICT DO NOTHING;
        """)
        # Insert watchlist tickers...
```

### Health Check Endpoint

```python
# Source: Standard FastAPI pattern
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["system"])

@router.get("/api/health")
async def health(request: Request):
    pool = request.app.state.db_pool
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)},
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` async context manager | FastAPI 0.93+ (2023) | Guaranteed cleanup; single function for startup+shutdown |
| `pydantic.BaseSettings` (v1) | `pydantic_settings.BaseSettings` (v2) | Pydantic v2 (2023) | Separate package; `SettingsConfigDict` replaces `class Config` |
| `asyncpg.connect()` for each request | `asyncpg.create_pool()` with pool | Always recommended | Connection reuse; dramatically lower latency |

**Deprecated/outdated:**
- `@app.on_event("startup")` / `@app.on_event("shutdown")`: Deprecated since FastAPI 0.93. Use `lifespan` instead.
- `pydantic.BaseSettings` in pydantic v1: Moved to `pydantic-settings` package in v2.
- `asyncpg.connect()` for production use: Always use `create_pool()` for web apps.

## Open Questions

1. **Pool `min_size` value for Neon free tier**
   - What we know: Neon free tier has connection limits (~100). asyncpg defaults to `min_size=10`.
   - What's unclear: Exact Neon free tier connection limit varies by plan. The Neon guide example uses `min_size=1`.
   - Recommendation: Use `min_size=2, max_size=10`. Conservative but sufficient for single-backend. If issues arise, reduce `max_size`.

2. **Whether to use `pool.execute()` or `conn.execute()` for schema init**
   - What we know: `pool.execute()` acquires a connection internally, runs the query, and releases. `pool.acquire()` gives explicit control.
   - What's unclear: Whether asyncpg can run multi-statement DDL in a single `execute()` call vs needing to split.
   - Recommendation: Use `async with pool.acquire() as conn: await conn.execute(full_ddl)`. asyncpg handles multi-statement strings. Using an explicit connection ensures all DDL runs on the same connection within one round-trip.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.0+ with pytest-asyncio 0.24.0+ |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd backend && uv run pytest tests/test_db.py -x -v` |
| Full suite command | `cd backend && uv run pytest tests/ -v --cov=app` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | asyncpg pool created with `statement_cache_size=0` | unit (mock pool) | `cd backend && uv run pytest tests/test_db.py::test_pool_created_with_cache_disabled -x` | Wave 0 |
| INFRA-02 | All 7 tables created via `CREATE TABLE IF NOT EXISTS` | unit (verify SQL) | `cd backend && uv run pytest tests/test_db.py::test_schema_creates_all_tables -x` | Wave 0 |
| INFRA-03 | Default user seeded with $10k + 10 tickers; skipped on rerun | unit (mock conn) | `cd backend && uv run pytest tests/test_db.py::test_seed_default_data -x` | Wave 0 |
| INFRA-04 | `GET /api/health` returns 200 with DB check | integration (TestClient) | `cd backend && uv run pytest tests/test_health.py::test_health_endpoint -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && uv run pytest tests/test_db.py tests/test_health.py -x -v`
- **Per wave merge:** `cd backend && uv run pytest tests/ -v --cov=app`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_db.py` -- covers INFRA-01, INFRA-02, INFRA-03 (pool creation, schema, seeding)
- [ ] `tests/test_health.py` -- covers INFRA-04 (health endpoint)
- [ ] `tests/test_config.py` -- covers Settings validation (fail-fast on missing DATABASE_URL)
- [ ] `tests/conftest.py` -- needs update: add fixtures for mock pool and TestClient with lifespan

## Sources

### Primary (HIGH confidence)

- asyncpg official docs (https://magicstack.github.io/asyncpg/current/api/index.html) - `connect()` parameters including `statement_cache_size`, `create_pool()` API, DSN `sslmode` parsing
- FastAPI official docs (https://fastapi.tiangolo.com/advanced/events/) - lifespan async context manager pattern
- pydantic-settings GitHub (https://github.com/pydantic/pydantic-settings) - `BaseSettings`, `SettingsConfigDict`, `.env` file loading
- Context7 /websites/magicstack_github_io_asyncpg_current - asyncpg pool creation, connection parameters
- Context7 /websites/fastapi_tiangolo - FastAPI lifespan events, startup/shutdown
- Context7 /pydantic/pydantic-settings - BaseSettings configuration

### Secondary (MEDIUM confidence)

- Neon FastAPI async guide (https://neon.com/guides/fastapi-async) - `create_pool` example with `min_size=1, max_size=10`; SSL via DSN
- asyncpg FAQ (https://magicstack.github.io/asyncpg/current/faq.html) - PgBouncer compatibility, `statement_cache_size=0` recommendation
- asyncpg GitHub issue #507 (https://github.com/MagicStack/asyncpg/issues/507) - `statement_cache_size=0` for connection poolers

### Tertiary (LOW confidence)

- None -- all critical claims verified through primary or secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed and version-verified (asyncpg 0.31.0, pydantic-settings 2.13.1, FastAPI 0.135.1)
- Architecture: HIGH - Patterns verified through official docs (FastAPI lifespan, asyncpg pool, Pydantic Settings)
- Pitfalls: HIGH - `statement_cache_size=0` requirement confirmed through asyncpg FAQ and multiple sources; other pitfalls are standard asyncpg/Neon knowledge

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable stack, unlikely to change)
