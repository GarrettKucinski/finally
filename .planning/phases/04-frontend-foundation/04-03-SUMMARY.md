---
phase: 04-frontend-foundation
plan: 03
subsystem: ui
tags: [sse, next.js, zustand, sparkline, svg, streaming, web-streams-api]

# Dependency graph
requires:
  - phase: 04-frontend-foundation (plans 01, 02)
    provides: Next.js scaffold, Zustand price store, SSE hook, WatchlistPanel with placeholder sparkline
provides:
  - SSE streaming via Next.js Route Handler proxy (no buffering, no CORS)
  - Sparkline SVG mini-charts rendering progressively from SSE price history
  - Price history accumulation in Zustand store (capped at 50 points per ticker)
affects: [05-visualizations-chat-panel]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Next.js Route Handler as SSE proxy (Route Handlers take priority over rewrites, avoiding buffering)"
    - "Module-level empty array constant to prevent Zustand selector infinite re-render loops"
    - "Inline SVG polyline sparklines with trend-based coloring (no external charting library)"

key-files:
  created:
    - frontend/src/app/api/stream/prices/route.ts
    - frontend/src/components/watchlist/Sparkline.tsx
  modified:
    - frontend/src/hooks/useSSE.ts
    - frontend/src/stores/priceStore.ts
    - frontend/src/components/watchlist/WatchlistPanel.tsx

key-decisions:
  - "SSE proxy via Route Handler instead of rewrites: Next.js rewrites buffer SSE responses, so a Route Handler at /api/stream/prices pipes the backend stream via Web Streams API"
  - "Module-level EMPTY_HISTORY constant with ?? operator to avoid Zustand selector creating new [] on every call (prevents infinite re-render loop)"
  - "Inline SVG sparklines with trend coloring (green up, red down) rather than external charting library"

patterns-established:
  - "Route Handler SSE proxy: for streaming endpoints, use Route Handlers (which take priority over rewrites) to pipe backend streams without buffering"
  - "Zustand stable references: use module-level constants for fallback values in selectors to prevent re-render loops"

requirements-completed: [UI-07, VIZ-01]

# Metrics
duration: 12min
completed: 2026-03-02
---

# Phase 4 Plan 3: Gap Closure Summary

**SSE streaming through Next.js Route Handler proxy (replacing absolute URLs) with inline SVG sparkline mini-charts accumulating price history from SSE**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-02T16:30:00Z
- **Completed:** 2026-03-02T18:38:07Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 5

## Accomplishments
- SSE now streams through Next.js (port 3000) instead of directly hitting backend (port 8000), eliminating all absolute URLs from frontend source code
- Sparkline mini-charts render in the watchlist panel with trend-based coloring (green for up, red for down), filling progressively from SSE data since page load
- Price history accumulates in Zustand store capped at 50 points per ticker, preventing unbounded memory growth

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix SSE to use relative URL through Next.js rewrites** - `6c41100` (fix)
2. **Task 2: Add price history to Zustand store and implement sparkline component** - `eafab2f` (feat)
3. **Task 3: Verify SSE through rewrites and sparkline rendering** - N/A (human-verify checkpoint, approved)

Additional deviation fix commits:
- `60c9414` - fix(04-03): stable empty array ref in WatchlistRow price history selector
- `8bbbf9c` - fix(04-03): SSE route handler to proxy stream without buffering

## Files Created/Modified
- `frontend/src/app/api/stream/prices/route.ts` - Route Handler that proxies backend SSE stream via Web Streams API (no buffering)
- `frontend/src/components/watchlist/Sparkline.tsx` - Inline SVG sparkline component with trend-based coloring (green/red/blue)
- `frontend/src/hooks/useSSE.ts` - SSE hook using relative `/api/stream/prices` URL, calls appendPriceHistory on each update
- `frontend/src/stores/priceStore.ts` - Added priceHistory accumulation (Record<string, number[]>) with 50-point cap per ticker
- `frontend/src/components/watchlist/WatchlistPanel.tsx` - Replaced sparkline placeholder with actual Sparkline component, stable selector reference

## Decisions Made
- **SSE proxy via Route Handler instead of rewrites:** Next.js rewrites buffer SSE responses, making prices arrive in batches instead of real-time. Created a Route Handler at `frontend/src/app/api/stream/prices/route.ts` that pipes the backend SSE stream via Web Streams API. Route Handlers take priority over rewrites, so REST calls still use the rewrite proxy. This is architecturally clean -- server-side only, uses BACKEND_URL env var, no CORS needed.
- **Module-level EMPTY_HISTORY constant:** The Zustand selector `s.priceHistory[ticker] || []` created a new array on every call, causing getSnapshot infinite re-render loops. Fixed with a module-level `const EMPTY_HISTORY: number[] = []` and `??` operator for stable reference identity.
- **Inline SVG sparklines:** Pure SVG polyline approach (no external library) keeps the bundle minimal. Trend-based coloring (green if last > first, red if last < first) matches trading terminal aesthetics.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Next.js rewrites buffer SSE, breaking real-time streaming**
- **Found during:** Task 3 (human-verify checkpoint)
- **Issue:** SSE events arrived in batches rather than real-time when proxied through Next.js rewrites. The rewrites mechanism buffers responses before forwarding.
- **Fix:** Created a Route Handler at `frontend/src/app/api/stream/prices/route.ts` that uses the Web Streams API to pipe the backend SSE stream without buffering. Route Handlers take priority over rewrites for matching paths, so REST `/api/*` calls still use the rewrite proxy.
- **Files modified:** `frontend/src/app/api/stream/prices/route.ts` (created)
- **Verification:** SSE events stream in real-time through port 3000; prices update every ~500ms
- **Committed in:** `8bbbf9c`

**2. [Rule 1 - Bug] Zustand selector infinite re-render loop from unstable empty array reference**
- **Found during:** Task 3 (human-verify checkpoint)
- **Issue:** `usePriceStore((s) => s.priceHistory[ticker] || [])` created a new `[]` on every call. Since Zustand uses `Object.is` for equality, this triggered getSnapshot infinite loops.
- **Fix:** Added module-level `const EMPTY_HISTORY: number[] = []` and changed selector to use `?? EMPTY_HISTORY` for stable reference identity.
- **Files modified:** `frontend/src/components/watchlist/WatchlistPanel.tsx`
- **Verification:** No infinite re-render loops; sparklines render correctly
- **Committed in:** `60c9414`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes were essential for correct SSE streaming and rendering. The Route Handler approach is architecturally cleaner than the plan's fallback suggestion (which was anticipated). No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 4 (Frontend Foundation) is now fully complete with all 3 plans executed
- SSE streaming, price flash animations, trade execution, positions monitoring, and sparkline mini-charts all working
- Ready for Phase 5 (Visualizations & Chat Panel): detailed charts, portfolio heatmap, P&L chart, AI chat sidebar

## Self-Check: PASSED

All 5 key files verified on disk. All 4 commit hashes verified in git log.

---
*Phase: 04-frontend-foundation*
*Completed: 2026-03-02*
