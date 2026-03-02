# Phase 5: Visualizations & Chat Panel - Research

**Researched:** 2026-03-02
**Domain:** Frontend visualization (charting, treemaps) and AI chat UI
**Confidence:** HIGH

## Summary

Phase 5 adds the differentiating visual features to the FinAlly trading workstation: a detailed ticker chart using Lightweight Charts, a portfolio heatmap (treemap) colored by P&L, a P&L history line chart, and a collapsible AI chat sidebar with inline action cards. The sparkline mini-charts already exist from Phase 4 (04-03) but VIZ-02 requires verifying they accumulate data from SSE progressively -- this is already implemented in the priceStore's `appendPriceHistory` with `MAX_HISTORY_POINTS = 50`.

The frontend currently uses React 19.2.3, Next.js 16.1.6, Tailwind v4, Zustand 5, and Sonner for toasts. No charting libraries are installed yet. The Dashboard component has placeholder areas for the chart and chat panel. The backend chat endpoint (`POST /api/chat`) returns a fully structured JSON response with `message`, `trades`, `watchlist_changes`, and `executed_actions` -- no streaming involved.

**Primary recommendation:** Use Lightweight Charts v5.1 (vanilla JS, no React wrapper) for the detailed ticker chart with direct DOM integration via useRef/useEffect. Use Recharts v2.15+ for both the P&L line chart and portfolio treemap -- it supports React 19, is SVG-based (simpler for these use cases), and provides both `AreaChart` and `Treemap` components. Build the chat panel as a pure React component with no additional dependencies.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIZ-02 | Sparkline mini-charts accumulate price history from SSE since page load and render progressively | Already implemented in Phase 4 (priceStore.appendPriceHistory + Sparkline component). Verify only. |
| VIZ-03 | Clicking a ticker in the watchlist shows a detailed chart in the main chart area using Lightweight Charts | Lightweight Charts v5.1 with useRef/useEffect pattern for React integration; LineSeries for price-over-time; real-time update() method for SSE data |
| VIZ-04 | Portfolio heatmap (treemap) with rectangles sized by portfolio weight and colored by P&L | Recharts Treemap with `content` prop for custom SVG rendering; color positions green/red based on pnl_percent; size by portfolio weight |
| VIZ-05 | P&L chart showing total portfolio value over time as line chart from portfolio_snapshots data | Recharts AreaChart with ResponsiveContainer; data from `GET /api/portfolio/history`; dark theme styling |
| VIZ-09 | AI chat panel (collapsible sidebar) with message input, scrolling history, and loading indicator | Pure React + Zustand chat store; `POST /api/chat` integration; collapsible sidebar in Dashboard layout |
| VIZ-10 | AI-executed trades and watchlist changes rendered as structured visual cards inline in chat | Custom ChatActionCard components parsing `executed_actions` from chat response; styled cards for trades and watchlist changes |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lightweight-charts | 5.1.0 | Detailed ticker chart (canvas-based, financial-grade) | TradingView's official library; 35kB gzipped; purpose-built for financial data; canvas rendering for performance; no peer dependencies |
| recharts | 2.15+ | P&L line chart and portfolio treemap | React-native declarative API; supports React 19 (peer dep); SVG-based (good for these use cases); includes both AreaChart and Treemap |
| zustand | 5.0.11 (already installed) | Chat state management | Already used for priceStore and portfolioStore; consistent pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner | 2.0.7 (already installed) | Error toasts for chat failures | Already integrated via apiFetch |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Recharts Treemap | @nivo/treemap | Nivo has richer treemap features but adds a heavy D3 dependency chain; React 19 support was late; Recharts is already needed for P&L chart |
| Recharts AreaChart | Lightweight Charts (second instance) | LC is canvas-based and great for tick data, but overkill for a simple P&L line chart; Recharts AreaChart is simpler and already a dependency |
| lightweight-charts-react-wrapper | Direct useRef/useEffect | Wrappers add abstraction; direct integration is simpler, more controllable, and avoids wrapper compatibility issues with React 19 |

**Installation:**
```bash
cd frontend && npm install lightweight-charts recharts
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── components/
│   ├── chart/
│   │   └── TickerChart.tsx       # Lightweight Charts wrapper (useRef/useEffect)
│   ├── portfolio/
│   │   ├── PositionsTable.tsx    # (existing)
│   │   ├── TradeBar.tsx          # (existing)
│   │   ├── PortfolioHeatmap.tsx  # Recharts Treemap
│   │   └── PnLChart.tsx          # Recharts AreaChart
│   ├── chat/
│   │   ├── ChatPanel.tsx         # Collapsible sidebar container
│   │   ├── ChatMessage.tsx       # Individual message bubble
│   │   └── ChatActionCard.tsx    # Inline trade/watchlist action card
│   ├── watchlist/
│   │   ├── WatchlistPanel.tsx    # (existing, needs onClick handler)
│   │   └── Sparkline.tsx         # (existing)
│   ├── layout/
│   │   └── Header.tsx            # (existing)
│   └── ui/
│       └── PriceFlash.tsx        # (existing)
├── stores/
│   ├── priceStore.ts             # (existing)
│   ├── portfolioStore.ts         # (existing)
│   └── chatStore.ts              # NEW: chat messages, loading state, send action
├── hooks/
│   └── useSSE.ts                 # (existing)
├── lib/
│   ├── api.ts                    # (existing, add sendChat + fetchPortfolioHistory)
│   └── format.ts                 # (existing)
└── types/
    └── api.ts                    # (existing, add ChatResponse types)
```

### Pattern 1: Lightweight Charts React Integration (useRef/useEffect)
**What:** Wrap Lightweight Charts in a React component using refs for DOM access and effects for lifecycle
**When to use:** For the detailed ticker chart (VIZ-03)
**Example:**
```typescript
// Source: https://tradingview.github.io/lightweight-charts/tutorials/react/simple
import { createChart, LineSeries, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts';
import { useEffect, useRef } from 'react';

interface TickerChartProps {
  ticker: string;
  data: { time: number; value: number }[];
}

export function TickerChart({ ticker, data }: TickerChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#161b22' },
        textColor: '#8b949e',
      },
      grid: {
        vertLines: { color: '#21262d' },
        horzLines: { color: '#21262d' },
      },
      width: containerRef.current.clientWidth,
      height: 300,
    });

    const series = chart.addSeries(LineSeries, {
      color: '#209dd7',
      lineWidth: 2,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      chart.applyOptions({ width: containerRef.current!.clientWidth });
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [ticker]); // Recreate chart when ticker changes

  // Update data when it changes
  useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      seriesRef.current.setData(data);
      chartRef.current?.timeScale().fitContent();
    }
  }, [data]);

  return <div ref={containerRef} />;
}
```

### Pattern 2: Recharts Treemap with P&L Coloring
**What:** Treemap where each position is sized by portfolio weight and colored by P&L
**When to use:** For the portfolio heatmap (VIZ-04)
**Example:**
```typescript
// Source: https://recharts.github.io/en-US/examples/CustomContentTreemap/
import { Treemap, ResponsiveContainer } from 'recharts';

interface HeatmapPosition {
  name: string;      // ticker
  size: number;      // portfolio weight (absolute value of position)
  pnlPercent: number; // for color calculation
}

function CustomizedContent(props: any) {
  const { x, y, width, height, name, pnlPercent } = props;

  // Interpolate color: green for profit, red for loss
  const intensity = Math.min(Math.abs(pnlPercent) / 10, 1); // cap at 10%
  const fill = pnlPercent >= 0
    ? `rgba(63, 185, 80, ${0.3 + intensity * 0.7})`   // price-up green
    : `rgba(248, 81, 73, ${0.3 + intensity * 0.7})`;   // price-down red

  return (
    <g>
      <rect x={x} y={y} width={width} height={height}
        fill={fill} stroke="#30363d" strokeWidth={2} />
      {width > 40 && height > 20 && (
        <text x={x + width / 2} y={y + height / 2}
          textAnchor="middle" dominantBaseline="central"
          fill="#e6edf3" fontSize={12} fontFamily="monospace">
          {name}
        </text>
      )}
    </g>
  );
}

// Usage:
<ResponsiveContainer width="100%" height={200}>
  <Treemap data={positions} dataKey="size"
    content={<CustomizedContent />} isAnimationActive={false} />
</ResponsiveContainer>
```

### Pattern 3: Chat Store with Zustand
**What:** Centralized chat state following existing store patterns
**When to use:** For the AI chat panel (VIZ-09, VIZ-10)
**Example:**
```typescript
import { create } from 'zustand';
import { apiFetch } from '@/lib/api';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  trades?: { ticker: string; side: string; quantity: number }[];
  watchlist_changes?: { ticker: string; action: string }[];
  executed_actions?: {
    trades: any[];
    watchlist_changes: any[];
    errors: any[];
  };
}

interface ChatStore {
  messages: ChatMessage[];
  loading: boolean;
  send: (message: string) => Promise<void>;
}

export const useChatStore = create<ChatStore>()((set, get) => ({
  messages: [],
  loading: false,
  send: async (message) => {
    set((s) => ({
      messages: [...s.messages, { role: 'user', content: message }],
      loading: true,
    }));
    try {
      const res = await apiFetch<ChatResponse>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message }),
      });
      set((s) => ({
        messages: [...s.messages, {
          role: 'assistant',
          content: res.message,
          trades: res.trades,
          watchlist_changes: res.watchlist_changes,
          executed_actions: res.executed_actions,
        }],
        loading: false,
      }));
    } catch {
      set({ loading: false });
    }
  },
}));
```

### Pattern 4: Collapsible Sidebar Layout
**What:** Dashboard layout with a collapsible right-side chat panel
**When to use:** For integrating the chat panel into the existing Dashboard
**Example:**
```typescript
// Dashboard layout modification
<div className="flex h-screen flex-col">
  <Header />
  <div className="flex flex-1 overflow-hidden">
    <aside className="w-80 ..."><WatchlistPanel /></aside>
    <main className="flex-1 ...">
      {/* Chart, heatmap, positions, trade bar */}
    </main>
    <aside className={`${chatOpen ? 'w-96' : 'w-0'} transition-all ...`}>
      <ChatPanel />
    </aside>
  </div>
</div>
```

### Anti-Patterns to Avoid
- **Re-creating Lightweight Charts on every render:** Store chart/series refs and use `update()` or `setData()` to push new data. Only recreate when the selected ticker changes.
- **Passing entire priceHistory to TickerChart without memoization:** The priceHistory updates every ~500ms via SSE. Use `useMemo` or a selector that returns the specific ticker's data to avoid unnecessary re-renders.
- **Fetching chat history on mount:** The backend stores history, but the frontend starts fresh each session. Loading 20 past messages on mount would show stale context. Start with an empty conversation.
- **Polling portfolio/history in the chart component:** Fetch once on mount + after each trade, not on a timer. The P&L chart data comes from `GET /api/portfolio/history` which returns snapshot data recorded by the backend.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Financial chart with time axis, crosshair, zoom | Custom canvas chart | Lightweight Charts v5.1 | Time axis formatting, crosshair snapping, zoom/pan, proper financial data handling are deeply complex |
| SVG treemap layout algorithm | Manual rectangle packing | Recharts Treemap | Squarified treemap layout is a well-studied algorithm; getting aspect ratios right is non-trivial |
| Responsive chart containers | Manual ResizeObserver | Recharts ResponsiveContainer / LC resize handler | Edge cases with debouncing, SSR, initial render timing |
| Chat message auto-scroll | Manual scrollTop management | `scrollIntoView` with a sentinel ref | Handles edge cases like user scrolling up to read history |

**Key insight:** Charting involves subtle complexities (time zones, axis tick formatting, responsive resize, animation timing) that are invisible until they break. Use battle-tested libraries.

## Common Pitfalls

### Pitfall 1: Lightweight Charts Memory Leak on Unmount
**What goes wrong:** Chart instance not properly removed when component unmounts or ticker changes
**Why it happens:** `chart.remove()` must be called in the useEffect cleanup; forgetting this leaks canvas elements and event listeners
**How to avoid:** Always call `chart.remove()` in the useEffect return function; null out refs after removal
**Warning signs:** Growing memory usage when switching between tickers; "detached HTMLDivElement" in Chrome DevTools heap snapshot

### Pitfall 2: Lightweight Charts Time Data Format
**What goes wrong:** Chart shows no data or throws errors about time ordering
**Why it happens:** Lightweight Charts requires time values in ascending order and as Unix timestamps (seconds, not milliseconds) or ISO date strings
**How to avoid:** Convert SSE timestamp (which may be in seconds already -- check priceStore) to the correct format; sort data by time before `setData()`
**Warning signs:** Console errors about "time values must be in ascending order"

### Pitfall 3: Recharts Treemap with Zero-Size Nodes
**What goes wrong:** Treemap crashes or renders invisible rectangles when a position has zero value
**Why it happens:** Treemap layout algorithm divides by total size; zero or negative sizes cause division issues
**How to avoid:** Filter out zero-quantity positions; use absolute value of position market value for sizing (not P&L); ensure `dataKey` points to a positive number
**Warning signs:** Empty treemap, console errors, or positions disappearing

### Pitfall 4: Chat Panel Re-Rendering Entire Message List
**What goes wrong:** All messages re-render on every new message or loading state change
**Why it happens:** Messages array reference changes on every update; components re-render if parent state changes
**How to avoid:** Memoize individual ChatMessage components; use stable keys; keep loading state separate from messages in selectors
**Warning signs:** Visible flicker in chat history when typing; slow response after many messages

### Pitfall 5: SSE Price Data Feeding Lightweight Charts
**What goes wrong:** Chart data grows unbounded or updates cause performance issues
**Why it happens:** SSE pushes price updates every ~500ms for all tickers; naively storing all updates for the selected ticker creates unbounded growth
**How to avoid:** Use the existing `priceHistory` from priceStore (already capped at 50 points); convert to Lightweight Charts time format before passing as data
**Warning signs:** Chart becoming slow after extended use; browser tab memory climbing

### Pitfall 6: Portfolio Refresh After AI Trade Execution
**What goes wrong:** Chat shows "Bought 10 AAPL" but positions table and header still show old data
**Why it happens:** Chat response includes executed_actions but portfolio store is not refreshed
**How to avoid:** After a successful chat response that includes executed trades, call `portfolioStore.refresh()` and reload watchlist if watchlist_changes were executed
**Warning signs:** Stale portfolio data after AI executes a trade

## Code Examples

### Lightweight Charts Dark Theme Configuration
```typescript
// Source: https://tradingview.github.io/lightweight-charts/tutorials/react/simple
const chartOptions = {
  layout: {
    background: { type: ColorType.Solid, color: '#161b22' }, // surface-secondary
    textColor: '#8b949e', // text-secondary
  },
  grid: {
    vertLines: { color: '#21262d' }, // surface-tertiary
    horzLines: { color: '#21262d' },
  },
  crosshair: {
    vertLine: { color: '#30363d', labelBackgroundColor: '#161b22' },
    horzLine: { color: '#30363d', labelBackgroundColor: '#161b22' },
  },
  timeScale: {
    borderColor: '#30363d', // border-default
    timeVisible: true,
    secondsVisible: false,
  },
  rightPriceScale: {
    borderColor: '#30363d',
  },
};
```

### Recharts Dark Theme P&L Area Chart
```typescript
// Source: https://context7.com/recharts/recharts/llms.txt
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import type { SnapshotPoint } from '@/types/api';

interface PnLChartProps {
  data: SnapshotPoint[];
}

export function PnLChart({ data }: PnLChartProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
        <defs>
          <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#209dd7" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#209dd7" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="recorded_at"
          tick={{ fill: '#6e7681', fontSize: 10 }}
          tickLine={false}
          axisLine={{ stroke: '#30363d' }}
          tickFormatter={(v) => new Date(v).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        />
        <YAxis
          tick={{ fill: '#6e7681', fontSize: 10 }}
          tickLine={false}
          axisLine={{ stroke: '#30363d' }}
          tickFormatter={(v) => `$${v.toLocaleString()}`}
          domain={['dataMin - 100', 'dataMax + 100']}
        />
        <Tooltip
          contentStyle={{ backgroundColor: '#161b22', border: '1px solid #30363d', color: '#e6edf3' }}
          labelFormatter={(v) => new Date(v).toLocaleString()}
          formatter={(v: number) => [`$${v.toFixed(2)}`, 'Portfolio Value']}
        />
        <Area
          type="monotone"
          dataKey="total_value"
          stroke="#209dd7"
          fill="url(#pnlGradient)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
```

### Chat Response Types (add to types/api.ts)
```typescript
export interface ChatTradeAction {
  ticker: string;
  side: string;
  quantity: number;
}

export interface ChatWatchlistAction {
  ticker: string;
  action: string;
}

export interface ChatExecutedActions {
  trades: Array<{
    ticker: string;
    side: string;
    quantity: number;
    price: number;
    total: number;
  }>;
  watchlist_changes: Array<{ ticker: string; action: string }>;
  errors: Array<{ type: string; detail: string; ticker: string }>;
}

export interface ChatResponse {
  message: string;
  trades: ChatTradeAction[];
  watchlist_changes: ChatWatchlistAction[];
  executed_actions: ChatExecutedActions;
}
```

### API Function for Chat (add to lib/api.ts)
```typescript
export function sendChat(message: string): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}
```

### WatchlistPanel Ticker Selection (modification to existing)
```typescript
// Add selectedTicker state to Dashboard or a new store
// WatchlistRow gets onClick prop
<div
  onClick={() => onSelect(ticker)}
  className={`group flex items-center gap-2 border-b border-border-default px-3 py-2 cursor-pointer
    ${selected ? 'bg-surface-tertiary' : 'hover:bg-surface-tertiary'}`}
>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Lightweight Charts v4 API (`chart.addLineSeries()`) | v5 API (`chart.addSeries(LineSeries, opts)`) | v5.0 (2024) | Import series types as values; addSeries takes type + options |
| Recharts Cell component for custom colors | `content` prop with custom SVG component | Recharts 2.x | Cell deprecated in Recharts 4.0; content prop is the recommended approach |
| React wrapper libraries for LC | Direct useRef/useEffect integration | 2024-2025 | Wrapper libraries lag behind LC updates; direct integration is simpler with modern React |

**Deprecated/outdated:**
- `chart.addLineSeries()` / `chart.addAreaSeries()`: Replaced by `chart.addSeries(LineSeries)` in v5
- Recharts `<Cell>` component: Deprecated, will be removed in Recharts 4.0; use `content` prop instead

## Open Questions

1. **Lightweight Charts time format for SSE data**
   - What we know: SSE `PriceUpdate.timestamp` is a number. priceStore's `priceHistory` stores only prices (no timestamps). Lightweight Charts needs `{ time, value }` pairs.
   - What's unclear: Whether to store timestamps alongside prices in priceHistory, or reconstruct timestamps from the update sequence
   - Recommendation: Modify `priceHistory` in the store to store `{ time: number; value: number }[]` instead of just `number[]`. This requires updating Sparkline to extract values only. Alternatively, keep the simple number array for sparklines and create a separate `chartHistory` that stores timestamped data for the selected ticker only.

2. **Treemap data when no positions exist**
   - What we know: Recharts Treemap requires at least one data item with a positive size
   - What's unclear: Exact behavior with empty array
   - Recommendation: Show a "No positions" placeholder when positions array is empty; only render Treemap when positions.length > 0

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | No frontend test framework installed yet |
| Config file | None -- would need vitest or jest setup |
| Quick run command | N/A |
| Full suite command | N/A |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIZ-02 | Sparklines accumulate SSE price data progressively | manual-only | Visual verification that sparklines fill in over time | N/A -- already implemented |
| VIZ-03 | Click ticker shows detailed Lightweight Chart | manual-only | Visual verification; LC is canvas-based (hard to unit test) | N/A |
| VIZ-04 | Portfolio heatmap sizes by weight, colors by P&L | manual-only | Visual verification of treemap rendering | N/A |
| VIZ-05 | P&L chart shows portfolio value over time | manual-only | Visual verification of line chart from snapshot data | N/A |
| VIZ-09 | Chat panel sends messages, shows history, loading state | smoke | `curl -X POST /api/chat -d '{"message":"hello"}'` verifies backend; frontend is manual | N/A |
| VIZ-10 | AI trades/watchlist changes shown as cards in chat | manual-only | Visual verification after AI executes an action | N/A |

### Sampling Rate
- **Per task commit:** Visual verification in browser (no automated frontend tests)
- **Per wave merge:** Backend pytest: `cd backend && uv run pytest -x`
- **Phase gate:** Manual visual verification of all 6 requirements + backend tests pass

### Wave 0 Gaps
- [ ] No frontend test framework installed -- all VIZ requirements are visual/interactive and best verified manually or via E2E tests (Phase 6)
- [ ] Backend tests exist and pass; no new backend changes needed for Phase 5

## Sources

### Primary (HIGH confidence)
- /tradingview/lightweight-charts (Context7) - React integration, series API, real-time updates, data format
- /recharts/recharts (Context7) - AreaChart, Treemap, ResponsiveContainer, CustomTooltip patterns
- Lightweight Charts official docs: https://tradingview.github.io/lightweight-charts/tutorials/react/simple - Basic React integration
- Lightweight Charts official docs: https://tradingview.github.io/lightweight-charts/tutorials/react/advanced - Advanced React patterns

### Secondary (MEDIUM confidence)
- Recharts React 19 support verified: https://github.com/recharts/recharts/issues/4558 - Confirmed v2.15+ supports React 19 peer dep
- Nivo React 19 support: https://github.com/plouc/nivo/issues/2618 - Confirmed resolved but exact version unclear
- Recharts Treemap custom content: https://recharts.github.io/en-US/examples/CustomContentTreemap/ - CustomizedContent pattern
- Lightweight Charts v5.1.0 release: https://github.com/tradingview/lightweight-charts/releases - Latest version, 35kB bundle

### Tertiary (LOW confidence)
- Recharts `react-is` override requirement for React 19 - may or may not be needed with v2.15+; flagged for validation during install

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Lightweight Charts and Recharts are well-documented, widely used, and verified via Context7
- Architecture: HIGH - Direct integration patterns confirmed in official docs; existing codebase patterns (Zustand, useRef) are well-established
- Pitfalls: HIGH - Common issues documented in official sources and verified against the actual codebase structure

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (30 days -- both libraries are stable)
