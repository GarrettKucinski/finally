---
phase: 04-frontend-foundation
plan: 02
subsystem: ui
tags: [react, zustand, tailwind-v4, sse, price-flash, trading-terminal, typescript]

# Dependency graph
requires:
  - phase: 04-frontend-foundation/01
    provides: Zustand stores (priceStore, portfolioStore), SSE hook, typed API client, Tailwind color tokens
  - phase: 02-portfolio-watchlist-apis
    provides: REST endpoints for portfolio, watchlist, and trade execution
provides:
  - Header with live portfolio value, cash balance, and SSE connection status indicator
  - WatchlistPanel with per-ticker live prices, flash animations, and add/remove controls
  - PriceFlash reusable component for green/red flash on price change (~500ms fade)
  - PositionsTable with 6 columns including live-computed P&L from SSE prices
  - TradeBar with ticker/quantity inputs and buy/sell execution via API
  - Dashboard layout composing all panels in terminal-inspired full-viewport grid
  - Number formatting utilities (currency, percent, quantity)
affects: [05-visualizations-chat]

# Tech tracking
tech-stack:
  added: []
  patterns: [price-flash-animation, per-ticker-store-subscription, live-pnl-computation, server-client-component-split]

key-files:
  created:
    - frontend/src/lib/format.ts
    - frontend/src/components/ui/PriceFlash.tsx
    - frontend/src/components/layout/Header.tsx
    - frontend/src/components/watchlist/WatchlistPanel.tsx
    - frontend/src/components/portfolio/PositionsTable.tsx
    - frontend/src/components/portfolio/TradeBar.tsx
    - frontend/src/components/Dashboard.tsx
  modified:
    - frontend/src/app/page.tsx
    - frontend/src/hooks/useSSE.ts
    - backend/app/main.py
    - backend/app/db.py

key-decisions:
  - "PriceFlash uses useRef for timer to handle rapid updates without stale closures"
  - "WatchlistRow is a separate child component subscribing per-ticker to avoid re-rendering entire list"
  - "Header computes live portfolio total from SSE prices (cashBalance + sum of positions * livePrice)"
  - "PositionsTable computes live P&L from price store instead of using static API values"
  - "SSE EventSource connects directly to backend:8000 with CORS (bypasses Next.js rewrites for streaming)"

patterns-established:
  - "Price flash: useRef timer + CSS transition-colors duration-500 for ~500ms green/red fade"
  - "Per-ticker subscription: extract WatchlistRow child component using usePriceStore(s => s.prices[ticker])"
  - "Live computation: compute P&L and totals from SSE price store in render, not from API response"
  - "Dashboard composition: Server Component page.tsx -> Client Component Dashboard.tsx (mounts useSSE)"

requirements-completed: [VIZ-01, VIZ-06, VIZ-07, VIZ-08, UI-05]

# Metrics
duration: 5min
completed: 2026-03-02
---

# Phase 4 Plan 02: UI Components Summary

**Interactive trading dashboard with live-streaming watchlist, price flash animations, positions table with real-time P&L, and trade execution bar**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-02T16:01:41Z
- **Completed:** 2026-03-02T16:38:40Z
- **Tasks:** 3 (2 auto + 1 verification checkpoint)
- **Files modified:** 11

## Accomplishments
- Built complete trading terminal UI with Header, WatchlistPanel, PositionsTable, TradeBar, and Dashboard layout
- PriceFlash component delivers green/red background flash on price changes with ~500ms CSS transition fade
- WatchlistPanel supports add/remove tickers with per-ticker store subscriptions for optimal re-render performance
- PositionsTable computes live P&L from SSE price data, updating on every tick without API re-fetch
- TradeBar executes market orders via API with toast notifications and automatic portfolio refresh
- Fixed SSE connection to bypass Next.js rewrites and connect EventSource directly to backend with CORS support
- Fixed database seed logic to handle stale default user by checking UUID instead of row count

## Task Commits

Each task was committed atomically:

1. **Task 1: Create formatting utilities, PriceFlash, Header, and WatchlistPanel** - `1b8b890` (feat)
2. **Task 2: Create PositionsTable, TradeBar, and compose Dashboard layout** - `e6c76b1` (feat)
3. **Task 3: Visual verification checkpoint** - approved by user (no commit, verification-only)

**Deviation fixes (applied during verification):**
- `c60afc6` - fix(db): check for default user by UUID instead of counting all users
- `071e682` - fix(db): handle stale default user with wrong UUID in Neon
- `5f2e58c` - fix(sse): connect EventSource directly to backend, add CORS

## Files Created/Modified
- `frontend/src/lib/format.ts` - Currency, percent, and quantity formatting utilities
- `frontend/src/components/ui/PriceFlash.tsx` - Reusable price cell with green/red flash animation
- `frontend/src/components/layout/Header.tsx` - Portfolio value, cash balance, connection status dot
- `frontend/src/components/watchlist/WatchlistPanel.tsx` - Watchlist with live prices, add/remove controls, sparkline placeholder
- `frontend/src/components/portfolio/PositionsTable.tsx` - 6-column positions table with live P&L computation
- `frontend/src/components/portfolio/TradeBar.tsx` - Trade form with ticker, quantity, buy/sell buttons
- `frontend/src/components/Dashboard.tsx` - Client component composing all panels with SSE hook
- `frontend/src/app/page.tsx` - Server component shell rendering Dashboard
- `frontend/src/hooks/useSSE.ts` - Modified to connect EventSource directly to backend URL
- `backend/app/main.py` - Added CORS middleware for direct SSE connections
- `backend/app/db.py` - Fixed default user seeding to use UUID check

## Decisions Made
- PriceFlash uses `useRef` for both previous price and timer to prevent stale closures and handle rapid SSE updates
- WatchlistRow extracted as a child component that subscribes per-ticker to the price store, preventing full-list re-renders on any single price change
- Header computes live portfolio total from SSE prices rather than waiting for portfolio API refresh
- PositionsTable computes unrealized P&L live from price store data rather than using static values from the API response
- SSE EventSource connects directly to `backend:8000` (or `localhost:8000`) with CORS, bypassing Next.js rewrites which were interfering with the streaming connection

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SSE EventSource connection through Next.js rewrites not streaming**
- **Found during:** Task 3 (visual verification)
- **Issue:** EventSource connected via `/api/stream/prices` through Next.js rewrites was not properly streaming SSE events; the proxy was buffering or breaking the connection
- **Fix:** Changed useSSE hook to connect EventSource directly to `http://localhost:8000/api/stream/prices` (or `NEXT_PUBLIC_BACKEND_URL`), and added CORS middleware to the FastAPI backend to allow cross-origin SSE connections
- **Files modified:** `frontend/src/hooks/useSSE.ts`, `backend/app/main.py`
- **Verification:** SSE stream connects successfully, prices update in real-time
- **Committed in:** `5f2e58c`

**2. [Rule 1 - Bug] Default user seeding failed on Neon with stale data**
- **Found during:** Task 3 (visual verification)
- **Issue:** Database seeding counted all users to decide whether to seed, but Neon database had a stale user row with a different UUID from a previous session, causing the default user seed to be skipped
- **Fix:** Changed seed logic to check for the specific default user UUID (`00000000-0000-0000-0000-000000000001`) instead of counting all users; handles both missing and mismatched UUID cases
- **Files modified:** `backend/app/db.py`, `backend/tests/test_db.py`
- **Verification:** Backend starts cleanly with correct default user seeded
- **Committed in:** `c60afc6`, `071e682`

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes were necessary for the application to function correctly during verification. No scope creep.

## Issues Encountered
- Next.js rewrites proxy buffered SSE responses, preventing real-time streaming -- resolved by direct EventSource connection to backend with CORS
- Neon database retained stale user data between development sessions -- resolved by UUID-based seed check

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All core UI components in place for Phase 5 (visualizations and chat)
- Chart placeholders ready for Lightweight Charts integration (sparklines, main chart area)
- Chat panel placeholder area available in the Dashboard layout
- Portfolio heatmap and P&L chart can be added alongside existing PositionsTable
- No blockers identified

## Self-Check: PASSED

All 8 created/modified frontend files verified present on disk. All 5 task and deviation commits (1b8b890, e6c76b1, 5f2e58c, 071e682, c60afc6) verified in git log.

---
*Phase: 04-frontend-foundation*
*Completed: 2026-03-02*
