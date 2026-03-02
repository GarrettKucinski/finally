---
phase: 06-docker-e2e-tests
plan: 01
subsystem: infra
tags: [docker, docker-compose, nextjs-standalone, uv, fastapi, containerization]

# Dependency graph
requires:
  - phase: 05-visualizations-chat-panel
    provides: Complete frontend and backend applications ready for containerization
provides:
  - Frontend Dockerfile with 3-stage multi-stage build and standalone output
  - Backend Dockerfile with uv-based production build
  - docker-compose.yml orchestrating both services with healthcheck
  - .dockerignore files for both services
affects: [06-02-PLAN (E2E tests use docker-compose infrastructure)]

# Tech tracking
tech-stack:
  added: [docker, docker-compose]
  patterns: [multi-stage-docker-build, uv-docker-pattern, compose-healthcheck, standalone-nextjs]

key-files:
  created:
    - frontend/Dockerfile
    - frontend/.dockerignore
    - backend/Dockerfile
    - backend/.dockerignore
    - docker-compose.yml
  modified:
    - frontend/next.config.ts
    - .env.example

key-decisions:
  - "Node 22-slim base image for frontend stages (matches project Node version)"
  - "Official uv base image (ghcr.io/astral-sh/uv:python3.12-bookworm-slim) for backend"
  - "Python stdlib urllib for healthcheck (no curl install needed)"
  - "HOSTNAME=0.0.0.0 for standalone Next.js server to listen on all interfaces"

patterns-established:
  - "Multi-stage frontend build: deps -> builder -> runner with standalone output"
  - "uv Docker pattern: mount-cache deps first, then COPY source and sync"
  - "Compose healthcheck with service_healthy condition for startup ordering"

requirements-completed: [OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, OPS-07]

# Metrics
duration: 1min
completed: 2026-03-02
---

# Phase 06 Plan 01: Docker Infrastructure Summary

**Multi-stage Dockerfiles for Next.js (standalone) and FastAPI (uv), orchestrated via docker-compose with healthcheck-gated startup**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-02T22:58:36Z
- **Completed:** 2026-03-02T22:59:48Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Frontend Dockerfile with 3-stage build producing minimal standalone Next.js image with non-root user
- Backend Dockerfile using official uv base image with cached dependency layer and compiled bytecode
- docker-compose.yml with backend healthcheck (Python urllib against /api/health) and frontend depends_on condition
- Both .dockerignore files exclude development artifacts from build context
- next.config.ts updated with `output: 'standalone'` preserving existing rewrites
- .env.example updated with clearer BACKEND_URL documentation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Dockerfiles, .dockerignore files, and update next.config.ts** - `6cd9298` (feat)
2. **Task 2: Create docker-compose.yml and update .env.example** - `d02b967` (feat)

## Files Created/Modified
- `frontend/Dockerfile` - 3-stage multi-stage build: deps (npm ci), builder (next build), runner (standalone + static)
- `frontend/.dockerignore` - Excludes node_modules, .next, .env, tsbuildinfo
- `backend/Dockerfile` - uv-based FastAPI build with cache mounts, compiled bytecode, production-only deps
- `backend/.dockerignore` - Excludes .venv, __pycache__, tests, .env, .pyc
- `docker-compose.yml` - Two-service orchestration with healthcheck, env_file, BACKEND_URL
- `frontend/next.config.ts` - Added output: 'standalone' alongside existing rewrites
- `.env.example` - Updated BACKEND_URL comment from generic to Docker-specific documentation

## Decisions Made
- Used `node:22-slim` as base image for all frontend stages (matches project's Node version)
- Used official `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` for backend (recommended by uv docs)
- Healthcheck uses Python stdlib `urllib.request` instead of curl (avoids installing extra packages)
- Set `HOSTNAME=0.0.0.0` in frontend runner stage so standalone server binds all interfaces
- No explicit networks block in docker-compose (Compose v2 creates default network automatically)
- No `version:` key in docker-compose.yml (deprecated in Compose v2)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Docker infrastructure complete and ready for `docker compose up`
- E2E test infrastructure (Plan 06-02) can build on this docker-compose.yml
- Manual verification: run `docker compose build` and `docker compose up` to confirm containers start correctly

## Self-Check: PASSED

All 7 files verified present. Both task commits (6cd9298, d02b967) verified in git log.

---
*Phase: 06-docker-e2e-tests*
*Completed: 2026-03-02*
