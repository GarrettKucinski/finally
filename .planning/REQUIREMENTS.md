# Requirements: FinAlly -- AI Trading Workstation

**Defined:** 2026-03-02
**Core Value:** Users can watch live-streaming prices, trade a simulated portfolio, and chat with an AI assistant that can both analyze and execute trades -- all in a single, polished dark-themed terminal UI.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Database & Infrastructure

- [x] **INFRA-01**: Backend initializes asyncpg connection pool on startup with Neon Postgres (`statement_cache_size=0`)
- [x] **INFRA-02**: Backend creates all tables on startup via `CREATE TABLE IF NOT EXISTS` (users, users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages)
- [x] **INFRA-03**: Backend seeds default user (fixed UUID, $10,000 cash) and 10 watchlist tickers if tables are empty
- [x] **INFRA-04**: `GET /api/health` returns 200 with DB connectivity check

### Portfolio

- [x] **PORT-01**: `GET /api/portfolio` returns current positions, cash balance, total portfolio value, and unrealized P&L per position
- [x] **PORT-02**: `POST /api/portfolio/trade` executes a market order (buy or sell) at the current cached price with instant fill
- [x] **PORT-03**: Buy validation rejects trades when user has insufficient cash
- [x] **PORT-04**: Sell validation rejects trades when user has insufficient shares
- [x] **PORT-05**: Trade execution updates positions (upsert) and cash balance atomically within a DB transaction
- [x] **PORT-06**: Position row is deleted when quantity reaches 0 after a sell
- [x] **PORT-07**: Trade history is appended to the trades table on every execution (ticker, side, quantity, price, timestamp)
- [x] **PORT-08**: Background task records portfolio value snapshot every 30 seconds
- [x] **PORT-09**: Portfolio snapshot is recorded immediately after each trade execution
- [x] **PORT-10**: Background task deletes portfolio snapshots older than 24 hours
- [x] **PORT-11**: `GET /api/portfolio/history` returns portfolio value snapshots over time

### Watchlist

- [x] **WATCH-01**: `GET /api/watchlist` returns current watchlist tickers with latest prices from the price cache
- [x] **WATCH-02**: `POST /api/watchlist` adds a ticker to the watchlist (validated: 1-5 uppercase alpha characters)
- [x] **WATCH-03**: `DELETE /api/watchlist/{ticker}` removes a ticker from the watchlist
- [x] **WATCH-04**: Adding a watchlist ticker also registers it with the live market data source (keeps SSE stream in sync)
- [x] **WATCH-05**: Removing a watchlist ticker also unregisters it from the live market data source

### Chat

- [x] **CHAT-01**: `POST /api/chat` accepts a user message and returns a complete JSON response (message + optional trades + optional watchlist_changes)
- [x] **CHAT-02**: Chat endpoint builds portfolio context (cash, positions with P&L, watchlist with live prices, total value) and includes it in the LLM prompt
- [x] **CHAT-03**: Chat endpoint loads the last 20 messages from chat_messages table as conversation history
- [ ] **CHAT-04**: LLM is called via LiteLLM -> OpenRouter with Cerebras inference, requesting structured JSON output
- [ ] **CHAT-05**: Trades in LLM response are auto-executed through the same `execute_trade` path as manual trades
- [ ] **CHAT-06**: Watchlist changes in LLM response are auto-executed through the watchlist service
- [ ] **CHAT-07**: Failed trade/watchlist actions include error details in the response so the LLM can inform the user
- [x] **CHAT-08**: Chat messages and executed actions are persisted to the chat_messages table (role, content, actions JSONB)
- [x] **CHAT-09**: When `LLM_MOCK=true`, backend returns deterministic mock responses without calling OpenRouter

### Frontend Core

- [ ] **UI-01**: Next.js app with dark terminal aesthetic (backgrounds ~`#0d1117`, muted borders, data-dense layout)
- [ ] **UI-02**: Tailwind CSS with custom dark theme using accent colors: yellow `#ecad0a`, blue `#209dd7`, purple `#753991`
- [ ] **UI-03**: SSE client connects to `/api/stream/prices` via native EventSource with auto-reconnect
- [ ] **UI-04**: Connection status indicator in header: green dot (connected), yellow (reconnecting), red (disconnected)
- [ ] **UI-05**: Price flash animations: brief green (uptick) or red (downtick) background highlight fading over ~500ms via CSS transitions
- [ ] **UI-06**: Consistent error display (toast or inline) for API errors without crashing the UI
- [ ] **UI-07**: All API calls use relative paths (`/api/*`) proxied to backend via Next.js rewrites

### Visualization

- [ ] **VIZ-01**: Watchlist panel shows tickers with live-updating current price, change %, and sparkline mini-chart
- [ ] **VIZ-02**: Sparkline mini-charts accumulate price history from SSE since page load and render progressively
- [ ] **VIZ-03**: Clicking a ticker in the watchlist shows a detailed chart in the main chart area using Lightweight Charts
- [ ] **VIZ-04**: Portfolio heatmap (treemap) with rectangles sized by portfolio weight and colored by P&L (green=profit, red=loss)
- [ ] **VIZ-05**: P&L chart showing total portfolio value over time as a line chart from portfolio_snapshots data
- [ ] **VIZ-06**: Positions table showing ticker, quantity, avg cost, current price, unrealized P&L, and % change
- [ ] **VIZ-07**: Trade bar with ticker input, quantity input, buy button, and sell button for market orders
- [ ] **VIZ-08**: Header displaying portfolio total value (updating live), connection status dot, and cash balance
- [ ] **VIZ-09**: AI chat panel (docked/collapsible sidebar) with message input, scrolling conversation history, and loading indicator
- [ ] **VIZ-10**: AI-executed trades and watchlist changes rendered as structured visual cards inline in chat (not just text)

### DevOps

- [ ] **OPS-01**: `frontend/Dockerfile` builds and serves the Next.js app on port 3000
- [ ] **OPS-02**: `backend/Dockerfile` builds and serves the FastAPI app on port 8000 via uvicorn
- [ ] **OPS-03**: `docker-compose.yml` orchestrates both services with proper networking and environment variables
- [ ] **OPS-04**: Frontend proxies `/api/*` to `http://backend:8000` via Next.js rewrites (no CORS needed)
- [ ] **OPS-05**: `docker compose up` starts both services from a single command with no manual setup
- [ ] **OPS-06**: E2E tests via Playwright in `test/docker-compose.test.yml` with `LLM_MOCK=true`
- [ ] **OPS-07**: `.env.example` committed with all required/optional environment variables documented

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Authentication

- **AUTH-01**: User can sign up with email and password
- **AUTH-02**: User can log in and receive a session
- **AUTH-03**: Multi-user data isolation (per-user portfolios, watchlists, chat history)

### Advanced Trading

- **TRADE-01**: Limit orders with pending order management
- **TRADE-02**: Stop-loss orders
- **TRADE-03**: Options, futures, or crypto asset support

### Data & Analytics

- **DATA-01**: Historical price data from external APIs
- **DATA-02**: Backtesting engine for trading strategies
- **DATA-03**: Advanced analytics and reporting

### Notifications

- **NOTIF-01**: In-app notifications for price alerts
- **NOTIF-02**: Portfolio threshold alerts

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| User authentication / login | Single pre-seeded default user for v1; schema supports future multi-user via user_id FKs |
| Limit orders / order book | Eliminates order book, matching engine, partial fills -- dramatically simpler portfolio math |
| Real-time LLM token streaming | Cerebras is fast enough; loading indicator sufficient; streaming breaks structured output parsing |
| Mobile-native app | Desktop-first terminal aesthetic; web is functional on tablet |
| Cloud deployment (Terraform) | Stretch goal, not core build |
| WebSockets | SSE is sufficient for one-way server->client push |
| Docker volumes | All persistent data in Neon Postgres |
| Historical price data / backtesting | Fundamental architecture change; charts use SSE data accumulated since page load |
| Social features / leaderboards | Tonal mismatch with professional terminal aesthetic |
| Confirmation dialogs for AI trades | Auto-execution without confirmation IS the demo -- zero stakes, maximum wow factor |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1: Database Foundation | Complete |
| INFRA-02 | Phase 1: Database Foundation | Complete |
| INFRA-03 | Phase 1: Database Foundation | Complete |
| INFRA-04 | Phase 1: Database Foundation | Complete |
| PORT-01 | Phase 2: Portfolio & Watchlist APIs | Complete |
| PORT-02 | Phase 2: Portfolio & Watchlist APIs | Complete |
| PORT-03 | Phase 2: Portfolio & Watchlist APIs | Complete |
| PORT-04 | Phase 2: Portfolio & Watchlist APIs | Complete |
| PORT-05 | Phase 2: Portfolio & Watchlist APIs | Complete |
| PORT-06 | Phase 2: Portfolio & Watchlist APIs | Complete |
| PORT-07 | Phase 2: Portfolio & Watchlist APIs | Complete |
| PORT-08 | Phase 2: Portfolio & Watchlist APIs | Complete |
| PORT-09 | Phase 2: Portfolio & Watchlist APIs | Complete |
| PORT-10 | Phase 2: Portfolio & Watchlist APIs | Complete |
| PORT-11 | Phase 2: Portfolio & Watchlist APIs | Complete |
| WATCH-01 | Phase 2: Portfolio & Watchlist APIs | Complete |
| WATCH-02 | Phase 2: Portfolio & Watchlist APIs | Complete |
| WATCH-03 | Phase 2: Portfolio & Watchlist APIs | Complete |
| WATCH-04 | Phase 2: Portfolio & Watchlist APIs | Complete |
| WATCH-05 | Phase 2: Portfolio & Watchlist APIs | Complete |
| CHAT-01 | Phase 3: LLM Chat Integration | Complete |
| CHAT-02 | Phase 3: LLM Chat Integration | Complete |
| CHAT-03 | Phase 3: LLM Chat Integration | Complete |
| CHAT-04 | Phase 3: LLM Chat Integration | Pending |
| CHAT-05 | Phase 3: LLM Chat Integration | Pending |
| CHAT-06 | Phase 3: LLM Chat Integration | Pending |
| CHAT-07 | Phase 3: LLM Chat Integration | Pending |
| CHAT-08 | Phase 3: LLM Chat Integration | Complete |
| CHAT-09 | Phase 3: LLM Chat Integration | Complete |
| UI-01 | Phase 4: Frontend Foundation | Pending |
| UI-02 | Phase 4: Frontend Foundation | Pending |
| UI-03 | Phase 4: Frontend Foundation | Pending |
| UI-04 | Phase 4: Frontend Foundation | Pending |
| UI-05 | Phase 4: Frontend Foundation | Pending |
| UI-06 | Phase 4: Frontend Foundation | Pending |
| UI-07 | Phase 4: Frontend Foundation | Pending |
| VIZ-01 | Phase 4: Frontend Foundation | Pending |
| VIZ-06 | Phase 4: Frontend Foundation | Pending |
| VIZ-07 | Phase 4: Frontend Foundation | Pending |
| VIZ-08 | Phase 4: Frontend Foundation | Pending |
| VIZ-02 | Phase 5: Visualizations & Chat Panel | Pending |
| VIZ-03 | Phase 5: Visualizations & Chat Panel | Pending |
| VIZ-04 | Phase 5: Visualizations & Chat Panel | Pending |
| VIZ-05 | Phase 5: Visualizations & Chat Panel | Pending |
| VIZ-09 | Phase 5: Visualizations & Chat Panel | Pending |
| VIZ-10 | Phase 5: Visualizations & Chat Panel | Pending |
| OPS-01 | Phase 6: Docker & E2E Tests | Pending |
| OPS-02 | Phase 6: Docker & E2E Tests | Pending |
| OPS-03 | Phase 6: Docker & E2E Tests | Pending |
| OPS-04 | Phase 6: Docker & E2E Tests | Pending |
| OPS-05 | Phase 6: Docker & E2E Tests | Pending |
| OPS-06 | Phase 6: Docker & E2E Tests | Pending |
| OPS-07 | Phase 6: Docker & E2E Tests | Pending |

**Coverage:**
- v1 requirements: 53 total
- Mapped to phases: 53
- Unmapped: 0

---
*Requirements defined: 2026-03-02*
*Last updated: 2026-03-02 after roadmap creation (traceability populated)*
