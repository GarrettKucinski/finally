# Phase 4: Frontend Foundation - Research

**Researched:** 2026-03-02
**Domain:** Next.js + React frontend with SSE real-time data, Tailwind CSS dark theme, trading terminal UI
**Confidence:** HIGH

## Summary

Phase 4 is a greenfield frontend build. The `frontend/` directory does not exist yet. The backend is fully implemented with all APIs (portfolio, watchlist, trade, chat, SSE streaming, portfolio history) and well-defined Pydantic response schemas. The frontend must consume these APIs via Next.js rewrites proxy (`/api/*` -> `http://backend:8000`), connect to the SSE price stream, and render a dark-themed trading terminal with live price updates, flash animations, trade execution, and error handling.

The critical architectural decision is state management for high-frequency SSE price data. React Context re-renders all consumers on every state change, which is problematic at ~500ms price update intervals across 10+ tickers. Zustand with selectors is the recommended approach -- components subscribe only to the specific ticker(s) they render, preventing cascade re-renders.

Tailwind CSS v4 (current as of 2026) uses `@theme` directives in CSS instead of `tailwind.config.js`. Next.js 16 is the current stable version and ships with Turbopack, React 19, and the React Compiler. The `create-next-app` CLI scaffolds TypeScript + Tailwind + App Router out of the box.

**Primary recommendation:** Use Next.js 16 with App Router, Tailwind CSS v4 (`@theme` for custom colors), Zustand for price/portfolio state, Sonner for toast notifications, and a custom `useSSE` hook wrapping the native `EventSource` API with reconnection tracking.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | Next.js app with dark terminal aesthetic (backgrounds ~`#0d1117`, muted borders, data-dense layout) | Next.js 16 + Tailwind v4 `@theme` directive for custom dark colors; layout.tsx sets base bg |
| UI-02 | Tailwind CSS with custom dark theme using accent colors: yellow `#ecad0a`, blue `#209dd7`, purple `#753991` | Tailwind v4 `@theme` CSS variables: `--color-accent-yellow`, `--color-primary-blue`, `--color-secondary-purple` |
| UI-03 | SSE client connects to `/api/stream/prices` via native EventSource with auto-reconnect | Custom `useSSE` hook with EventSource, `onmessage`/`onerror`/`onopen` handlers, Zustand store updates |
| UI-04 | Connection status indicator in header: green dot (connected), yellow (reconnecting), red (disconnected) | SSE hook tracks `connectionStatus` state enum; header component reads via Zustand selector |
| UI-05 | Price flash animations: brief green (uptick) or red (downtick) background highlight fading over ~500ms via CSS transitions | CSS `transition: background-color 500ms ease` + Tailwind custom classes; direction from SSE `direction` field |
| UI-06 | Consistent error display (toast or inline) for API errors without crashing the UI | Sonner toast library; centralized fetch wrapper catches errors and calls `toast.error()` |
| UI-07 | All API calls use relative paths (`/api/*`) proxied to backend via Next.js rewrites | `next.config.ts` rewrites: `{ source: '/api/:path*', destination: '${BACKEND_URL}/:path*' }` |
| VIZ-01 | Watchlist panel shows tickers with live-updating current price, change %, and sparkline mini-chart | Zustand price store + watchlist data; sparkline from accumulated SSE history (deferred to Phase 5 per VIZ-02, but panel structure built here) |
| VIZ-06 | Positions table showing ticker, quantity, avg cost, current price, unrealized P&L, and % change | Table component consuming `GET /api/portfolio` response; PortfolioResponse schema has all fields |
| VIZ-07 | Trade bar with ticker input, quantity input, buy button, and sell button for market orders | Form component posting to `POST /api/portfolio/trade` with TradeRequest schema `{ticker, side, quantity}` |
| VIZ-08 | Header displaying portfolio total value (updating live), connection status dot, and cash balance | Header reads from portfolio store (periodically refreshed) + SSE connection status from price store |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.x | React framework with App Router, SSR, rewrites proxy | Current stable; Turbopack default; official React 19 support; Context7 verified |
| React | 19.x | UI library (bundled with Next.js 16) | Ships with Next.js 16; includes React Compiler for automatic memoization |
| TypeScript | 5.x | Type safety | Bundled with `create-next-app`; catches API contract mismatches at build time |
| Tailwind CSS | 4.x | Utility-first CSS | Current stable; `@theme` directive for custom colors; zero-config content detection |
| Zustand | 5.x | State management for prices, portfolio, connection status | Minimal re-renders via selectors; works outside React (SSE handler); tiny bundle (~1KB) |
| Sonner | latest | Toast notifications | Lightweight; works in App Router layouts; shadcn/ui ecosystem standard; Context7 benchmark 92.1 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tailwindcss/postcss | 4.x | PostCSS integration for Tailwind v4 | Required for Tailwind v4 in Next.js |
| postcss | latest | CSS processing | Peer dependency of @tailwindcss/postcss |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Zustand | React Context | Context re-renders ALL consumers on any price change; unacceptable at 500ms update rate for 10+ tickers |
| Zustand | Redux Toolkit | Overkill for this scope; more boilerplate; Zustand achieves same selector-based performance |
| Zustand | Jotai | Similar performance, but Zustand's `getState()/setState()` outside React is cleaner for SSE handler |
| Sonner | react-hot-toast | Both work; Sonner is newer with better defaults, richer types, and shadcn/ui adoption |
| Sonner | react-toastify | Heavier bundle; more opinionated styling that conflicts with custom dark theme |

**Installation:**
```bash
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir
cd frontend
npm install zustand sonner
```

Note: `create-next-app` with `--tailwind` flag automatically configures Tailwind CSS v4, PostCSS, and `globals.css`.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── app/
│   ├── layout.tsx          # Root layout: dark bg, Toaster, font
│   ├── page.tsx            # Main dashboard (server component shell)
│   ├── globals.css         # Tailwind @import + @theme custom colors
│   └── favicon.ico
├── components/
│   ├── layout/
│   │   └── Header.tsx      # Portfolio value, cash, connection status dot
│   ├── watchlist/
│   │   └── WatchlistPanel.tsx  # Ticker list with prices, flash animations
│   ├── portfolio/
│   │   ├── PositionsTable.tsx  # Positions with P&L
│   │   └── TradeBar.tsx        # Buy/sell form
│   └── ui/
│       └── PriceFlash.tsx      # Reusable price cell with flash animation
├── hooks/
│   ├── useSSE.ts           # EventSource connection + reconnect logic
│   └── useApi.ts           # Centralized fetch wrapper with error handling
├── stores/
│   ├── priceStore.ts       # Zustand: live prices from SSE, connection status
│   └── portfolioStore.ts   # Zustand: positions, cash, total value
├── lib/
│   └── api.ts              # Typed API client functions (fetchPortfolio, executeTrade, etc.)
└── types/
    └── api.ts              # TypeScript interfaces matching backend Pydantic models
```

### Pattern 1: Zustand Store for SSE Prices
**What:** A Zustand store holds all live price data and SSE connection status. The SSE hook writes directly to the store using `getState().setState()` outside of React render, and individual components subscribe via selectors.
**When to use:** Any component displaying live prices or connection status.
**Example:**
```typescript
// Source: Context7 /pmndrs/zustand
import { create } from 'zustand'

interface PriceUpdate {
  ticker: string
  price: number
  previous_price: number
  timestamp: number
  change: number
  change_percent: number
  direction: 'up' | 'down' | 'flat'
}

type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected'

interface PriceStore {
  prices: Record<string, PriceUpdate>
  connectionStatus: ConnectionStatus
  updatePrices: (data: Record<string, PriceUpdate>) => void
  setConnectionStatus: (status: ConnectionStatus) => void
}

export const usePriceStore = create<PriceStore>()((set) => ({
  prices: {},
  connectionStatus: 'disconnected',
  updatePrices: (data) =>
    set((state) => ({ prices: { ...state.prices, ...data } })),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
}))
```

### Pattern 2: Custom useSSE Hook
**What:** A hook that manages the EventSource lifecycle, writes price data to Zustand, and tracks connection status.
**When to use:** Mounted once at the app/layout level.
**Example:**
```typescript
// Source: React docs useEffect cleanup pattern + native EventSource API
import { useEffect, useRef } from 'react'
import { usePriceStore } from '@/stores/priceStore'

export function useSSE() {
  const eventSourceRef = useRef<EventSource | null>(null)
  const updatePrices = usePriceStore((s) => s.updatePrices)
  const setConnectionStatus = usePriceStore((s) => s.setConnectionStatus)

  useEffect(() => {
    const es = new EventSource('/api/stream/prices')
    eventSourceRef.current = es

    es.onopen = () => setConnectionStatus('connected')

    es.onmessage = (event) => {
      const data = JSON.parse(event.data)
      updatePrices(data)
    }

    es.onerror = () => {
      // EventSource auto-reconnects; readyState indicates current state
      if (es.readyState === EventSource.CONNECTING) {
        setConnectionStatus('reconnecting')
      } else {
        setConnectionStatus('disconnected')
      }
    }

    return () => {
      es.close()
      setConnectionStatus('disconnected')
    }
  }, [updatePrices, setConnectionStatus])
}
```

### Pattern 3: Price Flash Animation via CSS Transitions
**What:** Apply a CSS class with background-color on price change, then let the transition fade it out.
**When to use:** Every price cell in the watchlist and positions table.
**Example:**
```typescript
// PriceFlash component pattern
'use client'
import { useEffect, useRef, useState } from 'react'

export function PriceFlash({ price, direction }: { price: number; direction: string }) {
  const [flash, setFlash] = useState<'up' | 'down' | null>(null)
  const prevPrice = useRef(price)

  useEffect(() => {
    if (price !== prevPrice.current) {
      setFlash(direction === 'up' ? 'up' : direction === 'down' ? 'down' : null)
      prevPrice.current = price
      const timer = setTimeout(() => setFlash(null), 500)
      return () => clearTimeout(timer)
    }
  }, [price, direction])

  return (
    <span
      className={`
        transition-colors duration-500 ease-out px-1 rounded
        ${flash === 'up' ? 'bg-green-500/30' : ''}
        ${flash === 'down' ? 'bg-red-500/30' : ''}
      `}
    >
      ${price.toFixed(2)}
    </span>
  )
}
```

### Pattern 4: Centralized API Client with Error Handling
**What:** A typed fetch wrapper that handles JSON parsing, error extraction, and toast notifications.
**When to use:** All API calls (portfolio, trade, watchlist).
**Example:**
```typescript
import { toast } from 'sonner'

interface ApiError {
  error: string
  detail: string
}

export async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err: ApiError = await res.json().catch(() => ({
      error: 'Request failed',
      detail: `HTTP ${res.status}`,
    }))
    toast.error(err.detail || err.error)
    throw new Error(err.detail || err.error)
  }
  return res.json()
}
```

### Pattern 5: Next.js Rewrites for API Proxy
**What:** Configure `next.config.ts` to proxy all `/api/*` requests to the backend.
**When to use:** Required for all API communication.
**Example:**
```typescript
// Source: Context7 /vercel/next.js rewrites configuration
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
```

### Anti-Patterns to Avoid
- **Storing SSE data in React Context:** Every price update re-renders every consumer. With 10 tickers at 500ms, this means ~20 full re-render cycles per second across the entire component tree.
- **Polling instead of SSE:** The backend has a purpose-built SSE endpoint. Polling adds latency and wastes bandwidth.
- **Creating EventSource inside a component body (not useEffect):** Creates a new connection every render. Must be in useEffect with cleanup.
- **Using `fetch` with absolute URLs:** Breaks the Docker networking model. All API calls must use relative `/api/*` paths.
- **Server Components for interactive panels:** Watchlist, trade bar, portfolio display all need client-side state and event handlers. Mark them `'use client'`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toast notifications | Custom notification system | Sonner | Handles stacking, auto-dismiss, types (error/success), accessibility, animations |
| State management for real-time data | Custom pub/sub or Context | Zustand | Selector-based subscriptions prevent re-render cascades; works outside React for SSE handler |
| CSS framework / design system | Custom CSS classes | Tailwind CSS | Consistent spacing, responsive utilities, dark mode support, purged bundle size |
| Project scaffolding | Manual webpack/tsconfig | create-next-app --tailwind | Configures TypeScript, Tailwind, PostCSS, ESLint, App Router, Turbopack in one command |
| SSE reconnection logic | Custom retry with backoff | Native EventSource | Browser EventSource has built-in reconnection with configurable retry interval (backend sends `retry: 1000`) |

**Key insight:** The browser's native `EventSource` API already handles reconnection. The backend SSE endpoint sends `retry: 1000\n\n` as its first event, telling the browser to retry after 1 second on disconnect. Do not build custom reconnection logic -- just track the `readyState` to update the connection status indicator.

## Common Pitfalls

### Pitfall 1: SSE Connection in Wrong Lifecycle
**What goes wrong:** EventSource created outside useEffect or without cleanup, causing multiple connections or memory leaks.
**Why it happens:** React 18+ Strict Mode double-invokes effects in development, creating two connections if cleanup is missing.
**How to avoid:** Always create EventSource inside useEffect with a cleanup function that calls `.close()`. In Strict Mode, the first connection closes cleanly and the second takes over.
**Warning signs:** Browser Network tab shows multiple open SSE connections; prices update twice as fast; memory usage climbs.

### Pitfall 2: Re-render Cascade from Price Updates
**What goes wrong:** Entire page re-renders on every price tick (~500ms), causing jank and dropped frames.
**Why it happens:** Using React Context or a single state object for all prices. Every consumer re-renders when any ticker updates.
**How to avoid:** Use Zustand with selectors. Each component subscribes to only the specific ticker it displays: `usePriceStore((s) => s.prices['AAPL'])`.
**Warning signs:** React DevTools shows unnecessary renders; UI feels sluggish; browser main thread blocked.

### Pitfall 3: Flash Animation Stuck or Skipped
**What goes wrong:** Price flash never fades out, or updates arrive faster than the 500ms fade, causing overlapping animations.
**Why it happens:** Using CSS animation instead of transition, or not clearing the flash class after timeout.
**How to avoid:** Use `setTimeout(500)` to remove the flash state. If a new update arrives before timeout fires, clear the previous timeout and start fresh. The CSS `transition-colors duration-500` handles the visual fade.
**Warning signs:** Cells stay green/red permanently; flash appears to "stack" on rapid updates.

### Pitfall 4: Rewrites Not Working in Docker
**What goes wrong:** API calls return 404 or CORS errors in Docker Compose.
**Why it happens:** `BACKEND_URL` not set or set to `localhost` instead of `http://backend:8000`. Next.js rewrites use the server-side URL, not the browser URL.
**How to avoid:** Set `BACKEND_URL=http://backend:8000` in `docker-compose.yml` environment for the frontend service. Use `process.env.BACKEND_URL` in `next.config.ts` with a localhost fallback for local dev.
**Warning signs:** Works locally but fails in Docker; browser console shows 404 on `/api/*` routes.

### Pitfall 5: Server Component Trying to Use Client Hooks
**What goes wrong:** Build error: "useState is not defined" or "useEffect is not a function".
**Why it happens:** Next.js App Router components are Server Components by default. Interactive components must have `'use client'` directive.
**How to avoid:** Add `'use client'` at the top of every file that uses hooks (useState, useEffect, useRef) or event handlers (onClick, onChange). Keep the root `page.tsx` as a Server Component shell that imports client components.
**Warning signs:** Build fails with "X is not defined"; hydration mismatches in browser console.

### Pitfall 6: Tailwind v4 Config Confusion
**What goes wrong:** Trying to use `tailwind.config.js` or `tailwind.config.ts` which is the v3 pattern.
**Why it happens:** Most tutorials and training data reference Tailwind v3 configuration. Tailwind v4 uses CSS `@theme` directives instead.
**How to avoid:** Custom colors go in `globals.css` via `@theme { --color-*: value; }`. No `tailwind.config.*` file needed. PostCSS config uses `@tailwindcss/postcss` plugin (not `tailwindcss`).
**Warning signs:** Tailwind classes not applying; build warnings about missing config; `tailwindcss` used directly as PostCSS plugin.

### Pitfall 7: Number Formatting Inconsistencies
**What goes wrong:** Prices display as `192.3` instead of `$192.30`, P&L shows excessive decimal places.
**Why it happens:** JavaScript floating point + no formatting.
**How to avoid:** Create utility functions for formatting: `formatCurrency(n)` -> `$192.30`, `formatPercent(n)` -> `+2.45%`, `formatQuantity(n)` -> `10.5`. Use `toFixed(2)` for prices and `Intl.NumberFormat` for locale-aware formatting.
**Warning signs:** Inconsistent decimal places across the UI; missing dollar signs; negative P&L not obviously red.

## Code Examples

Verified patterns from official sources:

### Tailwind v4 Custom Theme Colors (globals.css)
```css
/* Source: Context7 /websites/tailwindcss - @theme directive docs */
@import "tailwindcss";

@theme {
  /* FinAlly brand colors */
  --color-accent-yellow: #ecad0a;
  --color-primary-blue: #209dd7;
  --color-secondary-purple: #753991;

  /* Dark theme surfaces */
  --color-surface-primary: #0d1117;
  --color-surface-secondary: #161b22;
  --color-surface-tertiary: #21262d;
  --color-border-default: #30363d;

  /* Semantic colors */
  --color-price-up: #3fb950;
  --color-price-down: #f85149;
  --color-text-primary: #e6edf3;
  --color-text-secondary: #8b949e;
  --color-text-muted: #6e7681;
}
```

### Root Layout with Dark Theme and Toaster
```typescript
// Source: Context7 /vercel/next.js App Router layout + /emilkowalski/sonner setup
import type { Metadata } from 'next'
import { Toaster } from 'sonner'
import './globals.css'

export const metadata: Metadata = {
  title: 'FinAlly - AI Trading Workstation',
  description: 'AI-powered trading terminal with live market data',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-surface-primary text-text-primary min-h-screen">
        {children}
        <Toaster theme="dark" richColors position="bottom-right" />
      </body>
    </html>
  )
}
```

### TypeScript API Types Matching Backend
```typescript
// Types matching backend Pydantic models exactly
export interface PriceUpdate {
  ticker: string
  price: number
  previous_price: number
  timestamp: number
  change: number
  change_percent: number
  direction: 'up' | 'down' | 'flat'
}

export interface WatchlistItem {
  ticker: string
  current_price: number | null
  change: number | null
  change_percent: number | null
  direction: string | null
  added_at: string | null
}

export interface PositionDetail {
  ticker: string
  quantity: number
  avg_cost: number
  current_price: number | null
  unrealized_pnl: number
  pnl_percent: number
}

export interface PortfolioResponse {
  cash_balance: number
  total_value: number
  positions: PositionDetail[]
}

export interface TradeRequest {
  ticker: string
  side: 'buy' | 'sell'
  quantity: number
}

export interface TradeResponse {
  ticker: string
  side: string
  quantity: number
  price: number
  total: number
}

export interface ApiError {
  error: string
  detail: string
}
```

### Connection Status Indicator
```typescript
'use client'
import { usePriceStore } from '@/stores/priceStore'

const STATUS_CONFIG = {
  connected: { color: 'bg-price-up', label: 'Connected' },
  reconnecting: { color: 'bg-accent-yellow', label: 'Reconnecting' },
  disconnected: { color: 'bg-price-down', label: 'Disconnected' },
} as const

export function ConnectionStatus() {
  const status = usePriceStore((s) => s.connectionStatus)
  const config = STATUS_CONFIG[status]

  return (
    <div className="flex items-center gap-2" title={config.label}>
      <span className={`inline-block w-2 h-2 rounded-full ${config.color}`} />
      <span className="text-xs text-text-secondary">{config.label}</span>
    </div>
  )
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `tailwind.config.js` (v3) | `@theme {}` in CSS (v4) | Tailwind v4 (Jan 2025) | No JS config file; CSS-native theming; automatic content detection |
| `next.config.js` (CommonJS) | `next.config.ts` (TypeScript) | Next.js 15+ | Type-safe configuration with `NextConfig` type |
| Pages Router | App Router | Next.js 13+ (stable in 14+) | Server Components default; nested layouts; streaming SSR |
| Manual React.memo | React Compiler (automatic) | React 19 + Next.js 16 | Compiler auto-memoizes; less manual optimization needed |
| `create-next-app` prompts | `--tailwind --typescript --app` flags | Next.js 14+ | One-command scaffold with all options pre-selected |

**Deprecated/outdated:**
- `tailwind.config.js/ts`: Replaced by CSS `@theme` in Tailwind v4. Do not create this file.
- `pages/` directory: App Router in `app/` is the standard. Do not use Pages Router.
- `getServerSideProps` / `getStaticProps`: Replaced by Server Components and `fetch()` in App Router.

## Open Questions

1. **Sparkline chart in watchlist (VIZ-01 partial)**
   - What we know: VIZ-01 requires sparklines in the watchlist panel. VIZ-02 (accumulating SSE data for sparklines) is in Phase 5.
   - What's unclear: Should Phase 4 render a placeholder for the sparkline area, or skip it entirely?
   - Recommendation: Build the watchlist panel with a reserved column/space for sparklines but render a minimal placeholder (e.g., a thin gray line or empty cell). Phase 5 fills it in with actual sparkline data. This avoids layout shifts when sparklines are added.

2. **Portfolio refresh strategy**
   - What we know: Portfolio data comes from `GET /api/portfolio`. Prices update via SSE. The header needs live-updating total value.
   - What's unclear: Should the frontend re-fetch portfolio on every SSE tick, or compute updated values client-side?
   - Recommendation: Fetch portfolio on initial load and after each trade. For live total value in the header, compute it client-side: `total = cash + sum(position.quantity * currentPrice)`. This avoids unnecessary API calls while keeping the header responsive to price changes.

3. **How aggressive to be with `'use client'`**
   - What we know: Most dashboard components need client interactivity. The root layout and page can remain Server Components.
   - What's unclear: Whether to make the entire dashboard a single client component tree or keep granular boundaries.
   - Recommendation: Keep `layout.tsx` and `page.tsx` as Server Components. Import client component trees (Header, WatchlistPanel, PositionsTable, TradeBar) into page.tsx. Each interactive panel is a client component, but they compose independently.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest + React Testing Library |
| Config file | `frontend/vitest.config.mts` (Wave 0 — does not exist yet) |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | Dark terminal aesthetic renders with correct bg color | unit | `npx vitest run src/__tests__/layout.test.tsx -t "dark theme"` | Wave 0 |
| UI-02 | Custom accent colors available via Tailwind classes | unit | `npx vitest run src/__tests__/theme.test.tsx -t "accent colors"` | Wave 0 |
| UI-03 | SSE hook connects and receives price data | unit | `npx vitest run src/__tests__/hooks/useSSE.test.ts` | Wave 0 |
| UI-04 | Connection status reflects SSE state | unit | `npx vitest run src/__tests__/components/ConnectionStatus.test.tsx` | Wave 0 |
| UI-05 | Price flash applies and removes CSS class | unit | `npx vitest run src/__tests__/components/PriceFlash.test.tsx` | Wave 0 |
| UI-06 | API errors display toast without crash | unit | `npx vitest run src/__tests__/lib/api.test.ts -t "error handling"` | Wave 0 |
| UI-07 | API calls use relative /api/* paths | unit | `npx vitest run src/__tests__/lib/api.test.ts -t "relative paths"` | Wave 0 |
| VIZ-01 | Watchlist renders tickers with prices | unit | `npx vitest run src/__tests__/components/WatchlistPanel.test.tsx` | Wave 0 |
| VIZ-06 | Positions table renders all columns | unit | `npx vitest run src/__tests__/components/PositionsTable.test.tsx` | Wave 0 |
| VIZ-07 | Trade bar submits buy/sell orders | unit | `npx vitest run src/__tests__/components/TradeBar.test.tsx` | Wave 0 |
| VIZ-08 | Header shows total value, cash, connection | unit | `npx vitest run src/__tests__/components/Header.test.tsx` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/vitest.config.mts` -- Vitest config with React plugin and jsdom environment
- [ ] `frontend/src/__tests__/` -- Test directory structure
- [ ] Framework install: `npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/dom vite-tsconfig-paths`
- [ ] Test utilities: mock for EventSource, mock for fetch, Zustand store reset between tests

## Sources

### Primary (HIGH confidence)
- Context7 `/vercel/next.js` - rewrites configuration, App Router layout, client components, environment variables
- Context7 `/websites/tailwindcss` - Tailwind v4 `@theme` directive, PostCSS setup, dark mode configuration
- Context7 `/pmndrs/zustand` - Store creation with TypeScript, selectors, `useShallow`, `subscribeWithSelector`
- Context7 `/websites/sonner_emilkowal_ski` - Toaster setup in layout, toast types, richColors
- Context7 `/websites/react_dev` - useEffect cleanup pattern, useCallback memoization, useRef for mutable refs

### Secondary (MEDIUM confidence)
- [Next.js 16.1 blog post](https://nextjs.org/blog/next-16-1) - Turbopack stable, React 19.2, React Compiler stable
- [Next.js installation docs](https://nextjs.org/docs/app/getting-started/installation) - create-next-app flags and defaults
- [Tailwind CSS v4 blog post](https://tailwindcss.com/blog/tailwindcss-v4) - v4 architecture changes
- [Next.js Vitest testing guide](https://nextjs.org/docs/app/guides/testing/vitest) - Official test setup recommendation

### Tertiary (LOW confidence)
- Web search: React state management 2026 comparison - Zustand recommended for real-time dashboards (multiple sources agree)
- Web search: SSE custom hook patterns - Various community patterns; verified core approach against React official useEffect docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via Context7 with current versions; Next.js 16 and Tailwind v4 are current stable
- Architecture: HIGH - Zustand selector pattern for real-time data is well-documented; SSE with EventSource is browser-native; rewrites pattern from official Next.js docs
- Pitfalls: HIGH - Re-render cascade, SSE lifecycle, Tailwind v4 config changes all documented in official sources

**Research date:** 2026-03-02
**Valid until:** 2026-04-01 (30 days -- stable ecosystem, no imminent breaking changes expected)
