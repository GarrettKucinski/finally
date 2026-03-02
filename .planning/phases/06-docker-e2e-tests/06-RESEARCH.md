# Phase 6: Docker & E2E Tests - Research

**Researched:** 2026-03-02
**Domain:** Docker containerization, Docker Compose orchestration, Playwright E2E testing
**Confidence:** HIGH

## Summary

Phase 6 containerizes the existing frontend (Next.js 16) and backend (FastAPI/uv) into Docker images, orchestrates them with `docker-compose.yml`, and validates the deployed stack with Playwright E2E tests running from a separate `test/docker-compose.test.yml`.

The codebase is fully built (Phases 1-5 complete). All API calls already use relative `/api/*` paths proxied via Next.js rewrites (`next.config.ts`), and the SSE stream is proxied through a Next.js Route Handler (`src/app/api/stream/prices/route.ts`). The `BACKEND_URL` environment variable is already referenced in both locations. Docker networking simply needs to set `BACKEND_URL=http://backend:8000` for the frontend container, matching the existing design in PLAN.md.

The `.env.example` already exists with all required variables documented. It needs one minor update to add `BACKEND_URL` as an explicit entry (currently commented out).

**Primary recommendation:** Use multi-stage Docker builds for both services (Next.js standalone output, uv with venv copy pattern), a minimal `docker-compose.yml` with two services, and a separate `test/docker-compose.test.yml` that extends the main compose file and adds a Playwright container targeting Chromium only.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OPS-01 | `frontend/Dockerfile` builds and serves Next.js on port 3000 | Next.js standalone output mode + multi-stage build (see Architecture Patterns) |
| OPS-02 | `backend/Dockerfile` builds and serves FastAPI on port 8000 via uvicorn | uv Docker pattern with venv copy + uvicorn CMD (see Architecture Patterns) |
| OPS-03 | `docker-compose.yml` orchestrates both services with networking and env vars | Standard compose file with internal networking, `env_file`, and `BACKEND_URL` (see Code Examples) |
| OPS-04 | Frontend proxies `/api/*` to `http://backend:8000` via Next.js rewrites | Already implemented in `next.config.ts` and SSE route handler; Docker networking makes `backend` resolvable |
| OPS-05 | `docker compose up` starts both services from single command with no manual setup | Compose file + Dockerfiles with proper health checks and `depends_on` (see Code Examples) |
| OPS-06 | E2E tests via Playwright in `test/docker-compose.test.yml` with `LLM_MOCK=true` | Playwright container image + test compose extending main compose (see Architecture Patterns) |
| OPS-07 | `.env.example` committed with all required/optional environment variables documented | Already exists at `.env.example`; needs `BACKEND_URL` uncommented |
</phase_requirements>

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|-------------|---------|---------|--------------|
| Docker | 24+ | Container runtime | Industry standard for containerization |
| Docker Compose | v2 (built-in) | Multi-container orchestration | `docker compose` (v2) is the current standard; v1 `docker-compose` is deprecated |
| Node.js | 22-slim (LTS) | Frontend base image | LTS release for production stability; Next.js 16 requires Node 18.18+ |
| `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` | Latest | Backend base image with uv + Python 3.12 | Official Astral uv image; matches pyproject.toml `requires-python = ">=3.12"` |
| Next.js standalone output | 16.1.6 | Optimized production build | Reduces Docker image size by 80%+; bundles only required `node_modules` |
| Playwright | 1.58.2 | E2E browser testing | Latest stable; official Docker image `mcr.microsoft.com/playwright:v1.58.2-noble` |
| @playwright/test | 1.58.2 | Test runner + assertions | Bundled test framework with auto-wait, web-first assertions |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `mcr.microsoft.com/playwright:v1.58.2-noble` | 1.58.2 | Pre-built Playwright Docker image | For the test compose file; includes browsers pre-installed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Standalone output | `npm start` with full node_modules | 5-10x larger image; standalone is the documented Docker pattern for Next.js |
| uv base image | `python:3.12-slim` + pip install uv | Extra layer; official uv image is faster and smaller |
| Playwright Docker | Cypress in Docker | Playwright has better Docker support, official images, and faster execution |

**Installation (test directory):**
```bash
npm init -y
npm install -D @playwright/test@1.58.2
```

## Architecture Patterns

### Recommended Project Structure

```
finally/
├── frontend/
│   ├── Dockerfile              # Multi-stage: deps → build → runner
│   ├── .dockerignore           # Exclude node_modules, .next, .env
│   └── ...
├── backend/
│   ├── Dockerfile              # uv base: deps → app → run
│   ├── .dockerignore           # Exclude .venv, __pycache__, .env
│   └── ...
├── test/
│   ├── docker-compose.test.yml # Extends main compose + adds playwright
│   ├── playwright.config.ts    # Points to frontend:3000
│   ├── package.json            # @playwright/test dependency
│   ├── tsconfig.json           # TypeScript config for tests
│   └── tests/
│       ├── watchlist.spec.ts   # Watchlist CRUD flows
│       ├── trading.spec.ts     # Buy/sell flows
│       ├── portfolio.spec.ts   # Portfolio display flows
│       └── chat.spec.ts        # AI chat flows (mocked)
├── docker-compose.yml          # Primary: frontend + backend
├── .env                        # (gitignored) actual secrets
└── .env.example                # Template with all vars documented
```

### Pattern 1: Next.js Standalone Docker Build (3-stage)

**What:** Multi-stage Dockerfile leveraging `output: 'standalone'` to create a minimal production image.
**When to use:** Always for Next.js Docker deployments.

The `next.config.ts` must include `output: 'standalone'` alongside the existing `rewrites` config. The standalone build produces a self-contained `server.js` that includes a minimal set of `node_modules`.

**Stage 1 (deps):** Install npm dependencies using lockfile
**Stage 2 (builder):** Copy source, build with `npm run build`
**Stage 3 (runner):** Copy only `.next/standalone`, `.next/static`, and `public`; run `node server.js`

Key details:
- `HOSTNAME=0.0.0.0` environment variable is required for the standalone server to listen on all interfaces (not just localhost)
- Static assets (`public/` and `.next/static/`) must be copied manually into the standalone directory
- Uses `node:22-slim` as the base for a small image

### Pattern 2: FastAPI/uv Docker Build

**What:** Docker build using the official uv image, installing dependencies in a venv, then running uvicorn.
**When to use:** Always for this project's backend.

The pattern uses the official `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` base image which includes both Python 3.12 and uv pre-installed. Dependencies are installed via `uv sync --locked --no-dev` (skipping dev dependencies like pytest and ruff). The app is served with `uvicorn` directly.

Key details:
- `UV_COMPILE_BYTECODE=1` for faster startup
- `UV_LINK_MODE=copy` required when using cache mounts
- The backend reads `.env` via Pydantic Settings, but in Docker the env vars come from `env_file` in compose; the Settings `env_file=".env"` in code will simply not find a `.env` file inside the container (which is fine -- env vars take precedence)
- The `app/schema/*.sql` files are loaded at import time via `pathlib` so they MUST be included in the image

### Pattern 3: Docker Compose Networking

**What:** Docker Compose creates a default bridge network where services are resolvable by service name.
**When to use:** For all inter-container communication.

When `docker-compose.yml` defines services `frontend` and `backend`, the frontend container can reach the backend at `http://backend:8000`. This is already the value that `BACKEND_URL` defaults to in `next.config.ts` and the SSE route handler.

Key details:
- No explicit `networks:` block needed -- compose creates a default network automatically
- `depends_on` with a health check ensures the backend is ready before the frontend starts
- The backend health endpoint (`GET /api/health`) already exists for the health check

### Pattern 4: Playwright E2E with Docker Compose

**What:** A separate `docker-compose.test.yml` that includes the app services and adds a Playwright test runner container.
**When to use:** For CI/CD and local E2E testing.

The test compose file uses `include` (Docker Compose v2.20+) or duplicates service definitions to spin up the full app stack plus a Playwright container. The Playwright container connects to the frontend via the Docker network at `http://frontend:3000`.

Key details:
- Tests run with `LLM_MOCK=true` for deterministic mock responses
- The Playwright container uses `mcr.microsoft.com/playwright:v1.58.2-noble` which has Chromium pre-installed
- `playwright.config.ts` in the test directory sets `baseURL: process.env.BASE_URL || 'http://localhost:3000'`
- In Docker, `BASE_URL=http://frontend:3000` is passed as an environment variable
- Tests should only target Chromium (single browser) to keep execution fast

### Anti-Patterns to Avoid

- **Building without `.dockerignore`:** Without it, `node_modules/`, `.venv/`, `.next/`, and `.env` get copied into the build context, making builds slow and potentially leaking secrets
- **Using `npm install` instead of `npm ci`:** `npm ci` uses the lockfile exactly and is faster in CI/Docker contexts
- **Running as root in containers:** Use a non-root user (`node` for Next.js, created user for backend) for security
- **Hardcoding ports in Dockerfiles:** Use `EXPOSE` for documentation but let compose handle port mapping
- **Skipping health checks:** Without health checks, `depends_on` only waits for the container to start, not for the app to be ready

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser installation for E2E | Manual Chromium install | `mcr.microsoft.com/playwright:v1.58.2-noble` | Browser version must match Playwright version exactly |
| Python dependency resolution in Docker | `pip install -r requirements.txt` | `uv sync --locked` | uv resolves from lockfile, is 10-100x faster, handles native deps |
| Node.js production bundling | Manual file selection | `output: 'standalone'` | Next.js traces dependencies automatically; manual selection misses files |
| Container health checking | Custom scripts | Docker Compose `healthcheck` with `curl` or `wget` | Built-in retry/interval/timeout logic |
| E2E test waiting for app readiness | Custom polling scripts | Playwright `webServer.url` or `depends_on` with health checks | Built-in wait-until-ready with timeout |

**Key insight:** Docker and Playwright both have mature built-in solutions for orchestration, health checking, and browser management. Custom scripts for any of these are fragile and error-prone.

## Common Pitfalls

### Pitfall 1: Next.js Standalone Missing Static Assets
**What goes wrong:** After building with `output: 'standalone'`, the production server returns 404 for static files (CSS, JS, images).
**Why it happens:** The standalone build only includes `server.js` and traced dependencies. Static assets in `public/` and `.next/static/` are not included automatically.
**How to avoid:** Explicitly copy `public/` and `.next/static/` into the standalone directory in the Dockerfile:
```dockerfile
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/static ./.next/static
```
**Warning signs:** Page loads with no styling, broken images, JavaScript errors.

### Pitfall 2: Next.js Standalone Listens Only on localhost
**What goes wrong:** The container starts but is not accessible from outside (port mapping doesn't work).
**Why it happens:** By default, the standalone server binds to `127.0.0.1` (localhost only). Inside a container, this means only processes inside the container can connect.
**How to avoid:** Set `HOSTNAME=0.0.0.0` environment variable so the server listens on all interfaces.
**Warning signs:** `docker compose up` succeeds but `http://localhost:3000` times out.

### Pitfall 3: Backend `.env` File Not Found in Container
**What goes wrong:** Pydantic Settings looks for `.env` file inside the container and fails or ignores variables.
**Why it happens:** The `.env` file is in the project root and is gitignored; it's not copied into the container.
**How to avoid:** Don't copy `.env` into the image. Use `env_file: .env` in `docker-compose.yml` which injects variables as real environment variables. Pydantic Settings reads env vars first, before `.env` file.
**Warning signs:** `ValidationError` on startup about missing `DATABASE_URL`.

### Pitfall 4: Docker Build Context Includes `.venv` or `node_modules`
**What goes wrong:** Docker build takes minutes and the image is gigabytes.
**Why it happens:** Without `.dockerignore`, the entire directory (including local `.venv` and `node_modules`) is sent as the build context.
**How to avoid:** Create `.dockerignore` in both `frontend/` and `backend/` excluding local artifacts.
**Warning signs:** Build context is hundreds of MB, build takes 5+ minutes.

### Pitfall 5: Playwright Browser Version Mismatch
**What goes wrong:** Playwright tests fail with "Browser not found" or crash on launch.
**Why it happens:** The `@playwright/test` npm package version must exactly match the Docker image tag version (e.g., both must be 1.58.2).
**How to avoid:** Pin both to the same version. Use `mcr.microsoft.com/playwright:v1.58.2-noble` with `@playwright/test@1.58.2`.
**Warning signs:** Error messages about missing browser executables.

### Pitfall 6: SSE Connection Fails Through Docker Proxy
**What goes wrong:** Live price streaming doesn't work in the containerized app.
**Why it happens:** The SSE proxy route handler (`src/app/api/stream/prices/route.ts`) uses `BACKEND_URL` to connect to the backend. If this isn't set correctly in Docker, the proxy fails.
**How to avoid:** Ensure `BACKEND_URL=http://backend:8000` is set in the frontend container's environment. The route handler already reads `process.env.BACKEND_URL`.
**Warning signs:** Connection status shows "disconnected", no price updates.

### Pitfall 7: Playwright Tests Start Before App Is Ready
**What goes wrong:** First few tests fail with connection refused or timeout errors.
**Why it happens:** `depends_on` without health checks only waits for the container to start, not the application.
**How to avoid:** Use `depends_on` with `condition: service_healthy` and define `healthcheck` in compose. The backend has `GET /api/health`; the frontend can be checked with a simple HTTP request.
**Warning signs:** Flaky first tests that pass on retry.

### Pitfall 8: Google Fonts Fail in Docker Build
**What goes wrong:** Next.js build fails because it can't download Geist Mono font from Google Fonts.
**Why it happens:** The layout uses `Geist_Mono` from `next/font/google`, which fetches fonts during build time. Docker builds may lack internet access in some environments.
**How to avoid:** This generally works in standard Docker builds. If it fails, ensure the build stage has network access (default Docker behavior). As a fallback, `next/font` caches fonts in `.next/cache` which can be preserved between builds.
**Warning signs:** Build error about font download failure.

## Code Examples

### Frontend Dockerfile (OPS-01)

```dockerfile
# Stage 1: Install dependencies
FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: Build
FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 3: Production runner
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy standalone build + static assets
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

### Backend Dockerfile (OPS-02)

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Environment variables for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1

# Install dependencies first (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy application code
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml (OPS-03, OPS-04, OPS-05)

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      backend:
        condition: service_healthy
```

### test/docker-compose.test.yml (OPS-06)

```yaml
include:
  - path: ../docker-compose.yml

services:
  # Override backend to use LLM_MOCK
  backend:
    environment:
      - LLM_MOCK=true

  playwright:
    image: mcr.microsoft.com/playwright:v1.58.2-noble
    working_dir: /tests
    volumes:
      - ./:/tests
    environment:
      - BASE_URL=http://frontend:3000
      - CI=true
    depends_on:
      frontend:
        condition: service_started
    command: npx playwright test --project=chromium
```

### test/playwright.config.ts

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
```

### Example E2E Test: Watchlist

```typescript
import { test, expect } from '@playwright/test';

test.describe('Watchlist', () => {
  test('default watchlist appears with 10 tickers', async ({ page }) => {
    await page.goto('/');
    // Wait for SSE prices to start streaming
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('GOOGL')).toBeVisible();
    await expect(page.getByText('MSFT')).toBeVisible();
  });

  test('shows $10,000 starting balance', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('$10,000')).toBeVisible({ timeout: 15000 });
  });
});
```

### .dockerignore Files

**frontend/.dockerignore:**
```
node_modules
.next
.env*
*.tsbuildinfo
next-env.d.ts
README.md
```

**backend/.dockerignore:**
```
.venv
__pycache__
.pytest_cache
.mypy_cache
.ruff_cache
tests
.env*
*.pyc
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `docker-compose` (v1, Python) | `docker compose` (v2, Go plugin) | 2023 | v1 is deprecated; v2 is the default in Docker Desktop |
| `output: 'export'` for Docker | `output: 'standalone'` | Next.js 12+ | Standalone includes server + minimal deps; export is for static sites only |
| `pip install` in Docker | `uv sync --locked` | 2024 | 10-100x faster, lockfile-based, reproducible |
| Separate Playwright install step | Pre-built Playwright Docker images | 2022+ | `mcr.microsoft.com/playwright:*` includes browsers; no `npx playwright install` needed |
| `docker-compose.override.yml` | `include` directive | Compose v2.20 (2023) | Cleaner composition; explicit about what's included |

**Deprecated/outdated:**
- `docker-compose` CLI (v1): Replaced by `docker compose` (v2). Use `docker compose` in all documentation.
- `version:` key in compose files: No longer required or used in Compose v2.
- `links:` in compose: Replaced by default DNS-based service discovery on the compose network.

## Open Questions

1. **Compose `include` directive support**
   - What we know: `include` was added in Docker Compose v2.20 (mid-2023). Most Docker Desktop installations have it.
   - What's unclear: Some older CI environments may not support it.
   - Recommendation: Use `include` as the primary approach. If CI compatibility is a concern, the test compose file can duplicate service definitions instead. For this project (local-first demo), `include` is fine.

2. **Google Fonts in Docker build**
   - What we know: `next/font/google` downloads fonts at build time. Standard Docker builds have internet access.
   - What's unclear: Whether restrictive corporate networks or CI environments block this.
   - Recommendation: Proceed with the standard approach. If font download fails in Docker, the fallback is system monospace fonts (acceptable for a demo).

3. **Playwright image architecture (ARM64 / Apple Silicon)**
   - What we know: Microsoft provides `linux/amd64` Playwright images. Apple Silicon Macs use ARM64.
   - What's unclear: Whether `mcr.microsoft.com/playwright:v1.58.2-noble` has ARM64 variants or requires emulation.
   - Recommendation: Docker Desktop on Apple Silicon transparently emulates x86_64 containers. Performance is slightly slower but functional. If this is an issue, tests can also be run on the host machine against the containerized app.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Playwright 1.58.2 with @playwright/test |
| Config file | `test/playwright.config.ts` (created in Phase 6) |
| Quick run command | `cd test && npx playwright test --project=chromium` |
| Full suite command | `docker compose -f test/docker-compose.test.yml run --rm playwright` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OPS-01 | Frontend Dockerfile builds and serves on port 3000 | smoke | `docker compose up -d frontend && curl -f http://localhost:3000` | No - Wave 0 |
| OPS-02 | Backend Dockerfile builds and serves on port 8000 | smoke | `docker compose up -d backend && curl -f http://localhost:8000/api/health` | No - Wave 0 |
| OPS-03 | docker-compose.yml orchestrates both services | smoke | `docker compose up -d && curl -f http://localhost:3000 && curl -f http://localhost:8000/api/health` | No - Wave 0 |
| OPS-04 | Frontend proxies /api/* to backend | e2e | Playwright test: navigate to app, verify API data loads | No - Wave 0 |
| OPS-05 | `docker compose up` works end-to-end | e2e | Playwright test: full user flow (watchlist + prices) | No - Wave 0 |
| OPS-06 | E2E tests run in docker-compose.test.yml | e2e | `docker compose -f test/docker-compose.test.yml run --rm playwright` | No - Wave 0 |
| OPS-07 | .env.example has all variables documented | manual-only | Visual inspection (already exists, minor update) | N/A |

### Sampling Rate
- **Per task commit:** Manual `docker compose up` smoke test
- **Per wave merge:** `docker compose -f test/docker-compose.test.yml run --rm playwright`
- **Phase gate:** Full E2E suite green via test compose

### Wave 0 Gaps
- [ ] `frontend/Dockerfile` -- containerizes the Next.js app
- [ ] `frontend/.dockerignore` -- excludes build artifacts from context
- [ ] `backend/Dockerfile` -- containerizes the FastAPI app
- [ ] `backend/.dockerignore` -- excludes venv/tests from context
- [ ] `docker-compose.yml` -- orchestrates both services
- [ ] `test/docker-compose.test.yml` -- test runner compose
- [ ] `test/playwright.config.ts` -- Playwright configuration
- [ ] `test/package.json` -- @playwright/test dependency
- [ ] `test/tests/*.spec.ts` -- E2E test files

## Sources

### Primary (HIGH confidence)
- Context7 `/vercel/next.js/v16.1.6` - standalone output mode, Docker deployment docs
- Context7 `/microsoft/playwright.dev` - Docker CI configuration, test configuration, webServer option
- Context7 `/websites/fastapi_tiangolo` - FastAPI Docker containerization patterns
- https://docs.astral.sh/uv/guides/integration/docker/ - Official uv Docker guide (multi-stage, env vars, cache mounts)
- https://github.com/astral-sh/uv-docker-example - Official uv Docker example Dockerfile
- https://github.com/vercel/next.js/blob/canary/examples/with-docker/Dockerfile - Official Next.js Docker example

### Secondary (MEDIUM confidence)
- https://www.npmjs.com/package/@playwright/test - Playwright latest version (1.58.2)
- https://github.com/blueimp/playwright-example - Docker Compose Playwright pattern

### Tertiary (LOW confidence)
- None. All findings verified against primary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools/versions verified against official sources and Context7
- Architecture: HIGH - Patterns directly from official Next.js, FastAPI, uv, and Playwright documentation
- Pitfalls: HIGH - Common issues well-documented; verified against multiple sources

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (30 days -- stable tools, no expected breaking changes)
