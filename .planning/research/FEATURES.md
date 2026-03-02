# Feature Research: AI Trading Workstation / Simulated Trading Platform

> Research dimension: Features
> Project: FinAlly -- AI Trading Workstation
> Context: Brownfield -- market data streaming (SSE, simulator, Massive API) is complete. Researching features needed for the remaining platform.
> Date: 2026-03-01

---

## Executive Summary

AI trading workstations sit at the intersection of three product categories: (1) paper/simulated trading platforms, (2) professional trading terminals, and (3) AI-assisted investment tools. The table-stakes bar is set by platforms like TradingView, thinkorswim, and Webull's paper trading -- users expect real-time streaming data, instant trade execution, portfolio tracking, and a polished dark-theme UI. The differentiating frontier is AI chat that can both analyze and act -- natural-language trade execution with auto-execution is rare and impressive. FinAlly's sweet spot is combining a Bloomberg-inspired terminal aesthetic with an AI copilot that actually executes trades, all in a zero-stakes simulated environment that makes auto-execution feel safe and fluid.

---

## Table Stakes (Must Have or Users Leave)

These are baseline expectations. Every credible simulated trading platform and terminal-style dashboard ships these. Missing any of them signals "unfinished product."

### TS-1. Real-Time Price Streaming

| Attribute | Detail |
|-----------|--------|
| Description | Live-updating prices for watched tickers, with visual uptick/downtick indicators (green/red flash) |
| Complexity | **Already complete** -- SSE streaming via `/api/stream/prices` is built |
| Dependencies | Price cache (built), SSE endpoint (built), EventSource on frontend (to build) |
| Why table stakes | Every trading platform from Robinhood to Bloomberg shows live prices. Users expect sub-second visual feedback on price changes. Platforms without it feel static and dead. |
| Reference implementations | TradingView live tickers, Bloomberg real-time quotes, Webull streaming |

### TS-2. Portfolio Dashboard with Positions Table

| Attribute | Detail |
|-----------|--------|
| Description | Tabular view of all holdings: ticker, quantity, average cost, current price, unrealized P&L, and percentage change. Plus a header showing total portfolio value and cash balance. |
| Complexity | **Medium** -- backend `GET /api/portfolio` endpoint + frontend table component with live price integration |
| Dependencies | Price cache (for current prices), positions/users_profile tables (schema defined), SSE stream (for live updates to current price column) |
| Why table stakes | This is the single most-visited view on any trading platform. Paper trading simulators like Warrior Trading, StockHero, and TradingView all show this. Users cannot evaluate their performance without it. |
| Reference implementations | thinkorswim positions tab, Robinhood holdings screen, TradingView paper trading portfolio |

### TS-3. Trade Execution (Buy/Sell)

| Attribute | Detail |
|-----------|--------|
| Description | Market orders only -- user selects ticker, enters quantity, clicks Buy or Sell. Instant fill at current cached price. Cash balance and positions update immediately. |
| Complexity | **Medium** -- `POST /api/portfolio/trade` with validation (sufficient cash for buys, sufficient shares for sells), position upsert logic, trade history append |
| Dependencies | Price cache (fill price), positions table, users_profile table (cash balance), trades table (history log) |
| Why table stakes | The core verb of a trading platform. Without buy/sell, there is no platform -- just a price ticker. Even the simplest paper trading apps (CME simulator, Investopedia) support market orders. |
| Reference implementations | Every trading platform. CME Trading Simulator, Investopedia stock simulator, Webull paper trading |

### TS-4. Watchlist Management (Add/Remove Tickers)

| Attribute | Detail |
|-----------|--------|
| Description | Users can add tickers to and remove tickers from their watchlist. The watchlist drives which tickers appear in the streaming price grid. |
| Complexity | **Low** -- CRUD endpoints (`GET/POST/DELETE /api/watchlist`), simple UI with add input and remove button per row |
| Dependencies | Watchlist table (schema defined), ticker validation (1-5 uppercase alpha), price cache (to show current prices alongside tickers) |
| Why table stakes | Personalization of what you watch is fundamental. Every platform from Yahoo Finance to Bloomberg lets you curate a watchlist. The default 10 tickers get stale fast. |
| Reference implementations | TradingView watchlists, Yahoo Finance portfolio, Bloomberg MOST function |

### TS-5. Trade History Log

| Attribute | Detail |
|-----------|--------|
| Description | Append-only record of all executed trades with ticker, side, quantity, price, and timestamp. Viewable in the UI. |
| Complexity | **Low** -- trades table already defined in schema; display is a simple sorted table |
| Dependencies | Trade execution (TS-3) writes rows; frontend reads and displays them |
| Why table stakes | Users need to see what happened. Without history, trades feel ephemeral and unverifiable. Every broker and simulator shows an activity/history log. |
| Reference implementations | Robinhood activity feed, thinkorswim order history, Interactive Brokers trade log |

### TS-6. Connection Status Indicator

| Attribute | Detail |
|-----------|--------|
| Description | Visual indicator (colored dot in header) showing SSE connection state: green (connected), yellow (reconnecting), red (disconnected) |
| Complexity | **Low** -- EventSource `onopen`, `onerror`, `onclose` event handlers mapped to a status atom/state |
| Dependencies | SSE connection (TS-1 frontend implementation) |
| Why table stakes | Real-time platforms must communicate liveness. Users staring at frozen prices need to know if the feed is down or if prices genuinely have not moved. Bloomberg, TradingView, and all professional terminals show connection state. |
| Reference implementations | TradingView connection indicator, Bloomberg terminal status bar |

### TS-7. Dark Terminal-Style Theme

| Attribute | Detail |
|-----------|--------|
| Description | Dark background (~`#0d1117`), muted borders, data-dense layout. Professional trading aesthetic. Green/red for gain/loss. Accent colors: yellow `#ecad0a`, blue `#209dd7`, purple `#753991`. |
| Complexity | **Medium** -- Tailwind custom theme config, consistent application across all components, ensuring readability and contrast |
| Dependencies | None -- pure styling, but affects every component |
| Why table stakes | Dark themes are universal in trading software (Bloomberg, TradingView dark mode, thinkorswim). A light or generic theme immediately signals "not a real trading tool." The aesthetic IS the product identity for a terminal-style app. |
| Reference implementations | Bloomberg Terminal (iconic dark + colored text), OpenBB Terminal, TradingView dark mode |

### TS-8. Responsive Error Handling

| Attribute | Detail |
|-----------|--------|
| Description | Consistent error responses (`{"error": "...", "detail": "..."}`) with proper HTTP status codes. Frontend displays errors clearly (toast/inline) without crashing. Covers insufficient cash, insufficient shares, invalid tickers, server errors. |
| Complexity | **Low-Medium** -- backend Pydantic error model + frontend error display component + per-endpoint validation |
| Dependencies | All API endpoints |
| Why table stakes | Broken or silent errors destroy trust instantly. Users who click "Buy" and get no feedback, or see a raw 500 error, will not return. |
| Reference implementations | Any production trading platform |

---

## Differentiators (Competitive Advantage)

These features move FinAlly from "yet another paper trading simulator" to "this is genuinely impressive and novel." They represent the AI-native and visualization-rich aspects that most platforms lack.

### D-1. AI Chat Assistant with Natural Language Trade Execution

| Attribute | Detail |
|-----------|--------|
| Description | A chat panel where users converse with an LLM that understands their portfolio context (positions, P&L, cash, watchlist with live prices). The LLM can analyze holdings, suggest trades, and -- critically -- auto-execute trades and watchlist changes through structured output. No confirmation dialog. |
| Complexity | **High** -- system prompt engineering, structured output schema (message + trades + watchlist_changes), LLM call via LiteLLM/OpenRouter, auto-execution pipeline that validates and executes each trade/watchlist action, error aggregation, chat history persistence (last 20 messages), mock mode for testing |
| Dependencies | Trade execution (TS-3), watchlist management (TS-4), portfolio endpoint (TS-2) for context injection, price cache for live prices in context, chat_messages table |
| Why differentiating | Very few platforms offer an AI that can both analyze AND act. FinAlly's simulated environment removes the need for confirmation, creating a uniquely fluid "just do it" AI trading experience. This is the capstone feature of the project -- it demonstrates agentic AI capabilities. |
| Reference implementations | MiDash (natural language trading), Composer (AI strategy builder), QuantConnect Mia (agentic AI for quant strategies) |

### D-2. Portfolio Heatmap (Treemap Visualization)

| Attribute | Detail |
|-----------|--------|
| Description | Treemap where each rectangle represents a position, sized by portfolio weight (position value / total portfolio value), colored by P&L (green gradient for profit, red gradient for loss). Updates as prices stream in. |
| Complexity | **Medium-High** -- requires a treemap charting library or custom canvas rendering, real-time data binding to SSE price updates, color interpolation based on P&L percentage |
| Dependencies | Portfolio positions (TS-2), live prices from SSE (TS-1), calculated P&L per position |
| Why differentiating | Heatmaps are a power-user visualization found in Bloomberg, Finviz, and TradingView Pro -- but rarely in paper trading simulators. Most simulators show a flat table. A live-updating treemap immediately signals "professional tool" and provides instant visual comprehension of portfolio composition and health. |
| Reference implementations | Finviz heatmap, TradingView stock heatmap, Bloomberg PORT function |

### D-3. Sparkline Mini-Charts in Watchlist

| Attribute | Detail |
|-----------|--------|
| Description | Small inline price charts beside each ticker in the watchlist, built progressively from SSE data accumulated since page load. Shows recent price trajectory at a glance without clicking into a detail view. |
| Complexity | **Medium** -- requires accumulating price history per ticker on the frontend (in-memory array), rendering small canvas/SVG sparklines, managing memory (cap array length), re-rendering efficiently on new data points |
| Dependencies | SSE price stream (TS-1), watchlist (TS-4) |
| Why differentiating | Sparklines in a watchlist are found in Bloomberg and high-end terminals but almost never in paper trading simulators. They add significant information density -- users can scan 10 tickers and immediately see which are trending up, down, or sideways without clicking anything. This is a signature "data-rich terminal" feature. |
| Reference implementations | Bloomberg watchlist with sparklines, Google Finance ticker cards, Yahoo Finance trending tickers |

### D-4. P&L Chart (Portfolio Value Over Time)

| Attribute | Detail |
|-----------|--------|
| Description | Line chart showing total portfolio value over time, using data from `portfolio_snapshots` table. Snapshots taken every 30 seconds by a background task and immediately after each trade. 24-hour retention with automated cleanup. |
| Complexity | **Medium** -- backend background task for periodic snapshots, `GET /api/portfolio/history` endpoint, frontend line chart (Lightweight Charts or Recharts), snapshot-on-trade hook |
| Dependencies | Portfolio valuation logic (cash + sum of position values at current prices), price cache, portfolio_snapshots table, trade execution (to trigger immediate snapshot) |
| Why differentiating | Most paper trading platforms show current P&L but not a time-series chart of portfolio value. This transforms a static number into a narrative -- users can see the impact of their trades and market movements over time. The 30-second granularity makes it feel alive. |
| Reference implementations | Robinhood portfolio chart (the iconic green/red line), thinkorswim account balance graph |

### D-5. Detailed Ticker Chart (Click-to-Expand)

| Attribute | Detail |
|-----------|--------|
| Description | Clicking a ticker in the watchlist opens a larger chart in the main content area showing price over time. Uses Lightweight Charts for canvas-based rendering. Data accumulated from SSE since page load (same as sparklines but with more detail). |
| Complexity | **Medium** -- Lightweight Charts integration, ticker selection state management, price history accumulation (shared with sparklines), responsive chart sizing |
| Dependencies | SSE price stream (TS-1), watchlist (TS-4), sparkline data store (can be shared with D-3) |
| Why differentiating | While basic charts are table stakes, a smooth click-to-expand interaction from watchlist sparkline to detailed chart creates a cohesive, terminal-like workflow. The fact that it builds progressively from SSE (rather than loading historical data) is a unique real-time experience. |
| Reference implementations | TradingView chart panel, Bloomberg GP function, Lightweight Charts demos |

### D-6. AI Actions Displayed Inline in Chat

| Attribute | Detail |
|-----------|--------|
| Description | When the AI executes trades or modifies the watchlist, these actions are rendered as distinct visual elements (cards/badges) within the chat conversation -- not just mentioned in text. Shows ticker, side, quantity, fill price, and success/failure status. |
| Complexity | **Medium** -- structured `actions` JSONB field in chat_messages table, frontend rendering of action cards within chat bubbles, success/error state per action |
| Dependencies | AI chat (D-1), trade execution (TS-3), watchlist management (TS-4) |
| Why differentiating | Most AI chat interfaces just return text. Showing executed actions as structured, visually distinct elements makes the AI feel like a real agent that does things, not just a chatbot that talks about things. This is the key visual proof of agentic capability. |
| Reference implementations | Slack bot action confirmations, GitHub Copilot inline suggestions, MiDash trade confirmations |

---

## Anti-Features (Deliberately NOT Building)

These are features that might seem obvious or that competitors have, but that FinAlly should intentionally exclude. Each omission is a deliberate design decision that reduces complexity, maintains focus, or avoids misleading users.

### AF-1. Limit Orders, Stop-Loss, and Advanced Order Types

- **Why NOT**: Market orders only. Adding limit/stop orders requires an order book, pending order management, order matching engine, partial fills, and order lifecycle UI. The plan explicitly calls this out: "Eliminates order book, limit order logic, partial fills -- dramatically simpler portfolio math."
- **Complexity saved**: Very High
- **Risk of including**: Scope explosion. Order management alone is a multi-sprint feature in production trading platforms.

### AF-2. User Authentication and Multi-User Support

- **Why NOT**: Single pre-seeded default user, no login screen. The schema supports `user_id` for future multi-user, but v1 is explicitly single-user. Adding auth means login/signup UI, session management, JWT/cookie handling, password hashing, and per-user data isolation.
- **Complexity saved**: High
- **Risk of including**: Delays the impressive demo experience. "No login required" is a feature.

### AF-3. Real Historical Price Data and Backtesting

- **Why NOT**: Charts are built from SSE data accumulated since page load, not from historical APIs. Backtesting requires historical data ingestion, strategy definition, simulation engine, and results visualization. This is an entire product category (QuantConnect, Composer) -- not a feature to bolt on.
- **Complexity saved**: Very High
- **Risk of including**: Fundamental architecture change.

### AF-4. Options, Futures, Crypto, or Multi-Asset Trading

- **Why NOT**: Equities only (US stock tickers). Each additional asset class brings its own pricing models, trading rules, and UI requirements.
- **Complexity saved**: Very High per asset class
- **Risk of including**: Dilutes the core experience.

### AF-5. Confirmation Dialogs for AI-Initiated Trades

- **Why NOT**: Deliberate design decision. Auto-execution without confirmation IS the point -- it demonstrates agentic AI in a zero-stakes environment. The plan states: "It's a simulated environment with fake money, so the stakes are zero. It creates an impressive, fluid demo experience."
- **Complexity saved**: Low (this would be simple to add)
- **Risk of including**: Destroys the "wow factor."

### AF-6. Mobile-First or Native Mobile App

- **Why NOT**: Desktop-first, data-dense layout. Trading terminals are wide-screen experiences.
- **Complexity saved**: Medium
- **Risk of including**: Compromises the terminal aesthetic.

### AF-7. Social Features, Leaderboards, or Gamification

- **Why NOT**: FinAlly is a professional-feeling workstation, not a gamified trading app. Bloomberg does not have achievement badges.
- **Complexity saved**: Medium-High
- **Risk of including**: Tonal mismatch.

### AF-8. Token-by-Token LLM Streaming

- **Why NOT**: Cerebras inference is fast enough that a loading indicator is sufficient. Streaming complicates structured output parsing -- you cannot parse a JSON schema incrementally.
- **Complexity saved**: Medium
- **Risk of including**: Complicates the auto-execution pipeline.

---

## Feature Dependency Map

```
                    TS-1 SSE Price Streaming [COMPLETE]
                    /          |           \
                   /           |            \
            TS-4 Watchlist   TS-2 Portfolio  TS-6 Connection Status
               |            /     |      \
               |           /      |       \
          D-3 Sparklines  TS-3 Trade    TS-5 Trade History
               |          Execution
               |           /    \
          D-5 Detail     D-4 P&L     D-1 AI Chat Assistant
              Chart      Chart       /        |         \
                                    /         |          \
                              D-6 AI      (uses TS-3)  (uses TS-4)
                              Actions     Trade Exec   Watchlist Mgmt
                              Inline
```

### Critical Path (blocking order)

1. **TS-2 Portfolio Dashboard** and **TS-4 Watchlist Management** (can be parallel) -- both depend only on TS-1 which is complete
2. **TS-3 Trade Execution** -- depends on TS-2 (portfolio state) and price cache
3. **TS-5 Trade History** -- depends on TS-3
4. **D-4 P&L Chart** -- depends on TS-3 (snapshot-on-trade) and portfolio valuation
5. **D-1 AI Chat** -- depends on TS-2, TS-3, TS-4 (needs portfolio context, trade execution, and watchlist management)
6. **D-6 AI Actions Inline** -- depends on D-1

### Parallelizable work

- TS-7 (Dark theme) can proceed anytime -- it is pure styling
- TS-6 (Connection status) can proceed with SSE frontend work
- D-3 (Sparklines) and D-5 (Detail chart) can proceed once SSE is connected on frontend
- D-2 (Heatmap) can proceed once TS-2 is done

---

## Complexity Summary

| Feature | Complexity | Status |
|---------|-----------|--------|
| TS-1 SSE Price Streaming | Medium | COMPLETE |
| TS-2 Portfolio Dashboard | Medium | To build |
| TS-3 Trade Execution | Medium | To build |
| TS-4 Watchlist Management | Low | To build |
| TS-5 Trade History | Low | To build |
| TS-6 Connection Status | Low | To build |
| TS-7 Dark Terminal Theme | Medium | To build |
| TS-8 Error Handling | Low-Medium | To build |
| D-1 AI Chat + Auto-Execute | High | To build |
| D-2 Portfolio Heatmap | Medium-High | To build |
| D-3 Sparkline Mini-Charts | Medium | To build |
| D-4 P&L Chart | Medium | To build |
| D-5 Detail Ticker Chart | Medium | To build |
| D-6 AI Actions Inline | Medium | To build |

---

## Key Insights from Research

1. **The AI auto-execution is the killer feature.** MiDash, Composer, and QuantConnect Mia are the only comparable products, and none of them offer zero-confirmation auto-execution. FinAlly's simulated environment makes this safe and creates a demo experience that is genuinely novel.

2. **Paper trading is commoditized; the terminal aesthetic is not.** Dozens of paper trading apps exist (Webull, Investopedia, CME simulator). What they lack is the Bloomberg-inspired, data-dense, professional feel. The dark theme and information density ARE the product differentiation on the visual side.

3. **Heatmap + sparklines signal "professional tool."** These visualizations are found in Bloomberg and Finviz but almost never in paper trading simulators. Adding them elevates FinAlly from "student project" to "impressive workstation."

4. **SSE is the right choice and well-proven.** Research confirms approximately 80% of real-time price streaming use cases are better served by SSE than WebSocket. The key frontend optimization is batched re-renders (every 300-500ms) rather than per-message re-renders.

5. **Anti-features are as important as features.** The deliberate omission of limit orders, auth, backtesting, and confirmation dialogs keeps the scope achievable and the demo tight. Every anti-feature removed is a week of development saved.
