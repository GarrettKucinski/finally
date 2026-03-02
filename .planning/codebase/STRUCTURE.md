# Codebase Structure

**Analysis Date:** 2026-03-01

## Directory Layout

```
finally/
├── backend/                           # FastAPI backend (uv project)
│   ├── app/                           # Python package root
│   │   ├── __init__.py
│   │   └── market/                    # Market data subsystem (complete)
│   │       ├── __init__.py            # Public API exports
│   │       ├── models.py              # PriceUpdate frozen dataclass
│   │       ├── interface.py           # MarketDataSource ABC
│   │       ├── cache.py               # PriceCache thread-safe store
│   │       ├── simulator.py           # GBMSimulator + SimulatorDataSource
│   │       ├── massive_client.py      # MassiveDataSource (REST polling)
│   │       ├── factory.py             # create_market_data_source() selector
│   │       ├── seed_prices.py         # SEED_PRICES, params, correlation
│   │       └── stream.py              # SSE streaming endpoint factory
│   ├── tests/                         # Test suite mirroring app/ structure
│   │   ├── __init__.py
│   │   ├── conftest.py                # pytest-asyncio configuration
│   │   └── market/                    # Market data tests
│   │       ├── __init__.py
│   │       ├── test_models.py         # PriceUpdate tests
│   │       ├── test_cache.py          # PriceCache tests (13 tests)
│   │       ├── test_simulator.py      # GBMSimulator math tests
│   │       ├── test_simulator_source.py # SimulatorDataSource lifecycle
│   │       ├── test_massive.py        # MassiveDataSource polling logic
│   │       ├── test_factory.py        # Source selection logic
│   │       └── test_stream.py         # SSE streaming tests
│   ├── pyproject.toml                 # uv project config, dependencies
│   ├── uv.lock                        # Lockfile (164KB, reproducible builds)
│   └── .gitkeep                       # Empty marker
│
├── frontend/                          # Next.js frontend (TypeScript)
│   └── (currently empty, to be built)
│
├── planning/                          # Project documentation
│   ├── PLAN.md                        # Full project specification
│   ├── MARKET_DATA_COMPLETE.md        # Market data subsystem reference
│   └── archive/                       # Previous design docs
│       ├── MARKET_DATA_DESIGN.md
│       ├── MARKET_DATA_REVIEW.md
│       ├── MASSIVE_API.md
│       ├── MARKET_SIMULATOR.md
│       ├── MARKET_INTERFACE.md
│
├── .planning/                         # GSD codebase analysis output (this directory)
│   └── codebase/                      # Write ARCHITECTURE.md, STRUCTURE.md here
│
├── .claude/                           # AI agent configuration
├── .github/                           # GitHub workflows
├── test/                              # E2E tests (Playwright, docker-compose.test.yml)
├── .env                               # Environment variables (gitignored)
├── .env.example                       # Template for .env
├── docker-compose.yml                 # Orchestrate frontend + backend
├── Dockerfile                         # (not yet created; will be split into frontend/ and backend/)
├── README.md
├── CLAUDE.md                          # Agent instructions (this file)
└── .gitignore
```

## Directory Purposes

**`backend/`:**
- Purpose: FastAPI application (Python 3.12+, managed by uv)
- Contains: Application code, tests, configuration
- Key files: `pyproject.toml` (dependencies), `app/` (source code), `tests/` (test suite)

**`backend/app/`:**
- Purpose: Main Python package (imported as `from app.market import ...`)
- Contains: All application code organized by domain
- Key files: `__init__.py` (package marker), `market/` (market data subsystem)

**`backend/app/market/`:**
- Purpose: Market data subsystem — complete, tested, production-ready
- Contains: Price generation (simulator or Massive), caching, SSE streaming
- Key files:
  - `cache.py` — shared thread-safe store
  - `interface.py` — abstract contract
  - `simulator.py` — GBM implementation
  - `massive_client.py` — REST polling implementation
  - `factory.py` — runtime source selection
  - `stream.py` — SSE endpoint

**`backend/tests/`:**
- Purpose: Test suite (pytest + pytest-asyncio)
- Contains: Unit tests mirroring `app/` structure
- Key files: `conftest.py` (shared configuration), `market/` (8 test modules with 60+ tests)

**`frontend/`:**
- Purpose: Next.js application (TypeScript, React)
- Contains: (To be built) Pages, components, styles, client-side logic
- Key files: (Not yet present) `pages/`, `components/`, `lib/`, `styles/`

**`planning/`:**
- Purpose: Project-wide documentation for AI agents
- Contains: Specifications, design decisions, status summaries
- Key files: `PLAN.md` (full spec), `MARKET_DATA_COMPLETE.md` (market data summary)

**`.planning/codebase/`:**
- Purpose: Output directory for GSD codebase analysis documents
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, INTEGRATIONS.md, CONCERNS.md (as they are written)

**`test/`:**
- Purpose: End-to-end tests (Playwright, browser automation)
- Contains: E2E test scripts, `docker-compose.test.yml` for isolated test environment

## Key File Locations

**Entry Points:**
- Backend app: `backend/app/` (no main.py yet; will be created)
- Frontend app: `frontend/` (structure TBD; uses Next.js standard)
- Tests: `backend/tests/market/` (run with `pytest`)

**Configuration:**
- Backend dependencies: `backend/pyproject.toml`
- Backend config (future): `backend/app/config.py` or similar (not yet created)
- Environment variables: `.env` file (not committed; `.env.example` shows template)

**Core Logic:**
- **Market simulator**: `backend/app/market/simulator.py` (~270 lines) — GBM math
- **REST polling**: `backend/app/market/massive_client.py` (~180 lines) — Polygon.io integration
- **Cache**: `backend/app/market/cache.py` (~100 lines) — thread-safe storage
- **SSE streaming**: `backend/app/market/stream.py` (~100 lines) — live price push
- **Models**: `backend/app/market/models.py` (~65 lines) — immutable data types

**Testing:**
- Test config: `backend/pyproject.toml` (`[tool.pytest.ini_options]`)
- Test conftest: `backend/tests/conftest.py` (minimal; pytest-asyncio configured in pyproject)
- Market data tests: `backend/tests/market/test_*.py` (8 modules, 60+ tests total)

## Naming Conventions

**Files:**
- Lowercase, snake_case: `simulator.py`, `seed_prices.py`, `cache.py`
- Test files: `test_*.py` (matches pytest discovery)
- Public interfaces: match the main class name, e.g., `interface.py` exports `MarketDataSource`

**Directories:**
- Lowercase, plural for collections: `backend/tests/market/` (test suite)
- Domain-based grouping: `backend/app/market/` (all market data in one module)
- Clear hierarchy: `backend/` → `app/` → `market/` (service → package → domain)

**Python Modules:**
- Private modules (internal implementation): prefixed with `_` if needed (currently none)
- Public API: listed in `__init__.py` via `__all__` (see `backend/app/market/__init__.py`)
- Imports use absolute paths: `from app.market import PriceCache` (not relative)

**Classes:**
- PascalCase: `PriceCache`, `PriceUpdate`, `MarketDataSource`, `SimulatorDataSource`, `GBMSimulator`
- Abstract classes: end in `-Source` (e.g., `MarketDataSource`)

**Functions:**
- snake_case: `create_market_data_source()`, `create_stream_router()`
- Factory functions: start with `create_`

**Variables:**
- snake_case: `price_cache`, `api_key`, `ticker`
- Constants (module-level): UPPER_CASE: `SEED_PRICES`, `DEFAULT_DT`, `CORRELATION_GROUPS`

## Where to Add New Code

**New Feature (e.g., portfolio, trades):**
- Primary code: `backend/app/portfolio/` (new module, mirroring `market/` structure)
- Tests: `backend/tests/portfolio/test_*.py`
- Entry point: Add route via FastAPI `@app.post()` in main (to be created)

**New Component (Frontend):**
- Implementation: `frontend/components/ComponentName/ComponentName.tsx`
- Styles: `frontend/components/ComponentName/ComponentName.module.css` (or Tailwind inline)
- Tests (if any): `frontend/components/ComponentName/__tests__/` or `.test.tsx` alongside

**Shared Utilities:**
- Backend helpers: `backend/app/lib/` (to be created as needed)
- Frontend helpers: `frontend/lib/` (to be created as needed)
- Market-specific utilities: `backend/app/market/` (already established)

**Configuration & Secrets:**
- Environment variables: `.env` file (template in `.env.example`)
- Backend settings: `backend/app/config.py` (to be created using Pydantic Settings)
- Frontend env: `.env.local` in `frontend/` (Next.js convention)

## Special Directories

**`backend/schema/`:**
- Purpose: (To be created) SQL schema definitions, migrations, seed scripts
- Generated: No (hand-written SQL or Alembic migrations)
- Committed: Yes (schema is part of source control)

**`backend/tests/`:**
- Purpose: Comprehensive test suite
- Generated: No (hand-written tests)
- Committed: Yes (tests are part of source control)
- Run: `pytest` from `backend/` directory

**`planning/`:**
- Purpose: Shared documentation for all agents
- Generated: No (hand-edited design docs)
- Committed: Yes (planning is part of source control)

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis output
- Generated: Yes (written by `/gsd:map-codebase`)
- Committed: Yes (provides context for other GSD commands)

**`.claude/`:**
- Purpose: AI agent configuration (skills, commands, plugins)
- Generated: No (defined by the orchestrator)
- Committed: Yes (part of the agent runtime)

**`test/`:**
- Purpose: E2E and integration tests
- Generated: No (hand-written Playwright scripts)
- Committed: Yes (tests are part of source control)

---

*Structure analysis: 2026-03-01*
