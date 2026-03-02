# Pitfalls Research: AI Trading Workstation

> Research dimension: Pitfalls
> Project: FinAlly -- AI Trading Workstation
> Context: Brownfield -- market data streaming complete. Building: Neon Postgres (asyncpg), portfolio/trade execution, LLM integration (LiteLLM/OpenRouter/Cerebras), Next.js frontend with SSE, Docker Compose.
> Date: 2026-03-01

---

## 1. Neon Postgres with asyncpg

### 1.1 Prepared Statement Cache Conflicts with Neon's Connection Pooler

**The Pitfall:** asyncpg aggressively caches prepared statements on each connection. Neon's connection pooler (PgBouncer in transaction mode) rotates the underlying Postgres connection between requests. When asyncpg tries to use a cached prepared statement on a different backend connection, Postgres returns `prepared statement does not exist`, crashing the query.

**Warning Signs:**
- `asyncpg.exceptions.InvalidSQLStatementNameError: prepared statement "__asyncpg_stmt_XX__" does not exist`
- Errors are intermittent (depends on whether you get the same backend connection)
- Works fine locally but fails in production with pooled connections

**Prevention Strategy:**
- Use Neon's direct (non-pooled) connection endpoint for asyncpg, OR
- Disable prepared statement caching: `asyncpg.create_pool(dsn, statement_cache_size=0)`
- The Neon docs explicitly recommend `statement_cache_size=0` for pooled connections
- If using the pooled endpoint (port 5432 with `-pooler` suffix), ALWAYS set `statement_cache_size=0`
- If using the direct endpoint (port 5432 without `-pooler`), prepared statements work normally

**Phase:** Database layer setup

---

### 1.2 Neon Cold Start Latency on First Connection

**The Pitfall:** Neon serverless Postgres suspends compute after 5 minutes of inactivity (free tier). The first connection after suspension takes 500ms-2s for cold start. If the FastAPI lifespan creates the connection pool and immediately runs schema initialization, the first query may time out with default asyncpg timeouts.

**Warning Signs:**
- `asyncio.TimeoutError` on first database operation after idle period
- App works fine after the first request but the initial startup fails
- Health check passes locally but fails in CI/CD

**Prevention Strategy:**
- Set generous connection timeout on pool creation: `asyncpg.create_pool(dsn, timeout=30, command_timeout=30)`
- Add retry logic for the initial schema creation (3 retries with exponential backoff)
- Consider sending a lightweight query (SELECT 1) as a warm-up before schema init
- For the health check endpoint, include a database ping to detect cold start issues

**Phase:** Database layer setup

---

### 1.3 Missing SSL Configuration for Neon

**The Pitfall:** Neon requires SSL connections. The `DATABASE_URL` includes `?sslmode=require`, but asyncpg needs explicit SSL context for some deployment environments. If the SSL parameter is silently dropped during URL parsing, connections fail with cryptic errors.

**Warning Signs:**
- `asyncpg.exceptions.ConnectionDoesNotExistError` or SSL handshake failures
- Works with `psql` command line but not with asyncpg
- Error mentions "server does not support SSL"

**Prevention Strategy:**
- asyncpg handles `sslmode=require` in the DSN correctly in most cases
- If issues arise, explicitly create an SSL context: `ssl=ssl.create_default_context()`
- Test the connection string in isolation during startup and log success/failure clearly
- The Pydantic Settings validation should reject DATABASE_URL values missing `sslmode=require`

**Phase:** Database layer setup

---

### 1.4 Race Conditions in Trade Execution Without Transactions

**The Pitfall:** A trade involves: (1) check cash/shares, (2) update positions, (3) update cash balance, (4) insert trade record. Without a database transaction, a concurrent request (e.g., from the LLM auto-executing while the user manually trades) could read stale cash/position data, leading to double-spending or overselling.

**Warning Signs:**
- Cash balance goes negative (should be impossible)
- Position quantity goes negative on sell
- Two simultaneous buys both succeed despite insufficient total cash

**Prevention Strategy:**
- Wrap the entire trade execution in a single database transaction using `async with pool.acquire() as conn: async with conn.transaction():`
- Use `SELECT ... FOR UPDATE` on the user's profile row to lock it during the trade
- In v1 single-user mode this is low-risk, but building it correctly from the start prevents bugs when scaling
- Test with concurrent trade requests to verify atomicity

**Phase:** Trade execution implementation

---

## 2. Portfolio Math and Trade Execution

### 2.1 Floating-Point Arithmetic for Money

**The Pitfall:** The schema uses `DOUBLE PRECISION` for cash_balance, quantity, avg_cost, and price. Floating-point math introduces rounding errors: `0.1 + 0.2 = 0.30000000000000004`. Over many trades, these errors accumulate. A user who buys and sells the same position multiple times may end up with $9,999.99 instead of $10,000.

**Warning Signs:**
- Cash balance shows excessive decimal places ($9999.999999997)
- Buy then sell of the same quantity at the same price doesn't return exact original cash
- Tiny phantom positions remain after selling "all" shares

**Prevention Strategy:**
- Round cash calculations to 2 decimal places after each trade
- Round quantities to a reasonable precision (8 decimal places for fractional shares)
- Use Python's `round()` function on all trade math results before DB storage
- In the frontend, format all money values with `toFixed(2)` for display
- Accept that this is a simulated environment and sub-cent precision is not critical
- Do NOT switch to NUMERIC/DECIMAL — the plan explicitly uses DOUBLE PRECISION and this is fine for a simulator

**Phase:** Trade execution implementation

---

### 2.2 Average Cost Calculation on Partial Sells

**The Pitfall:** The average cost formula for buys is straightforward: `new_avg = (old_qty * old_avg + buy_qty * buy_price) / (old_qty + buy_qty)`. But on a partial sell, the average cost should NOT change — you're reducing quantity at the existing average cost. If the sell formula incorrectly recalculates avg_cost, it corrupts the P&L for remaining shares.

**Warning Signs:**
- Average cost changes after a sell (it shouldn't)
- Unrealized P&L jumps after selling part of a position
- Selling and rebuying at the same price shows a phantom gain/loss

**Prevention Strategy:**
- On BUY: `new_avg = (old_qty * old_avg + buy_qty * price) / (old_qty + buy_qty)`
- On SELL: `avg_cost stays the same`, only `quantity` decreases
- On full sell (quantity reaches 0): delete the position row entirely (per plan decision Q3)
- Test edge cases: buy 10, sell 5, buy 5 at different price, sell all — verify P&L is correct at each step

**Phase:** Trade execution implementation

---

### 2.3 Using Stale Cached Price for Trade Fill

**The Pitfall:** The plan says to fill trades at the latest value in the price cache with no staleness check. If the market data source stops updating (Massive API rate limit, simulator crash), the cached prices become stale. Trades fill at old prices, creating phantom gains/losses when the source recovers.

**Warning Signs:**
- Prices in the watchlist appear frozen
- Trades fill at prices far from the eventual "current" price
- Portfolio P&L changes dramatically when the data source reconnects

**Prevention Strategy:**
- This is acceptable per the plan (decision Q7: "No staleness check"), but still allow the trade (for demo purposes)
- Consider exposing the last-update timestamp in the health check response so operators can detect data staleness
- Do NOT block trades on staleness in v1 (single-user demo), but log it clearly

**Phase:** Trade execution implementation

---

## 3. LLM Structured Output Parsing

### 3.1 LiteLLM Does Not Recognize OpenRouter Structured Output Support

**The Pitfall:** LiteLLM's `supports_response_schema` function returns `False` for OpenRouter-prefixed models because OpenRouter is not in LiteLLM's list of providers that globally support structured outputs. The `response_format` parameter gets silently stripped, and the LLM returns freeform text instead of JSON.

**Warning Signs:**
- LLM responses are conversational text instead of JSON
- `json.loads()` fails with `Expecting value: line 1 column 1`
- Retry logic fires on every single request

**Prevention Strategy:**
- Use the `extra_body` parameter to bypass LiteLLM's schema check and pass the format directly to OpenRouter:
  ```python
  response = await litellm.acompletion(
      model="openrouter/openai/gpt-oss-120b",
      messages=messages,
      extra_body={
          "response_format": {
              "type": "json_schema",
              "json_schema": {"name": "chat_response", "schema": schema_dict}
          }
      },
  )
  ```
- Always validate the parsed JSON against the expected Pydantic model, not just that it's valid JSON
- Test this integration early -- do not assume structured outputs work because the API call succeeds

**Phase:** LLM integration

---

### 3.2 Malformed JSON from LLM Despite Structured Output Mode

**The Pitfall:** Even with structured output mode enabled, LLMs can produce: trailing commas, unescaped control characters, truncated JSON, or markdown code fences around the JSON. The plan specifies "retry once, then return fallback."

**Warning Signs:**
- `json.JSONDecodeError` in production logs from the chat endpoint
- Chat always returns "I encountered an error processing your request"

**Prevention Strategy:**
- Strip markdown code fences before parsing: `content.strip().removeprefix("```json").removesuffix("```").strip()`
- Validate with Pydantic and provide per-field defaults:
  ```python
  class ChatResponse(BaseModel):
      message: str
      trades: list[TradeAction] = []
      watchlist_changes: list[WatchlistAction] = []
  ```
- If both attempts fail, return the raw LLM text as the `message` field with empty actions
- Log the raw LLM response body on parse failure for debugging

**Phase:** LLM integration

---

### 3.3 LLM Hallucinating Invalid Trade Parameters

**The Pitfall:** The LLM may produce trades for tickers not in the watchlist, quantities that exceed available cash/shares, negative quantities, or side values other than "buy"/"sell".

**Warning Signs:**
- Portfolio shows positions in tickers the user never watched
- Cash balance goes negative from LLM-initiated trades

**Prevention Strategy:**
- Route ALL LLM-specified trades through the exact same trade execution function used by the manual trade endpoint — no special path
- Collect per-trade results (success or failure with reason) and include them in the chat response's `actions` field
- Validate ticker format, side, and quantity before attempting execution
- If a trade fails validation, include the error in the response message

**Phase:** LLM integration

---

### 3.4 Chat Context Window Overflow

**The Pitfall:** The plan sends last 20 messages plus portfolio context plus system prompt. If the portfolio has many positions and the conversation is long, total tokens may exceed context limits.

**Warning Signs:**
- LLM API returns `context_length_exceeded` error
- Responses become incoherent or ignore conversation history

**Prevention Strategy:**
- Estimate token count before sending (rough: 1 token per 4 characters)
- If over budget, reduce history from 20 to 10, then 5 messages
- Summarize portfolio context for large portfolios (top 5 positions by value)
- Set `max_tokens` on the LLM call to leave headroom for the response

**Phase:** LLM integration

---

## 4. SSE Consumption in Next.js (via Proxy)

### 4.1 Next.js Rewrite Proxy Buffers SSE Events

**The Pitfall:** Next.js rewrites proxy `/api/stream/prices` to the backend. Intermediate layers may buffer the response, holding SSE events until the buffer fills.

**Warning Signs:**
- Prices don't appear on page load, then suddenly all appear at once
- Works when connecting directly to `:8000` but not through `:3000`

**Prevention Strategy:**
- Backend already sends `X-Accel-Buffering: no` and `Cache-Control: no-cache` headers
- Disable Next.js compression for SSE: `compress: false` in `next.config.ts` if events are being buffered
- Test with `curl -N http://localhost:3000/api/stream/prices` to verify real-time delivery

**Phase:** Frontend build (SSE client setup)

---

### 4.2 EventSource Reconnection Thundering Herd

**The Pitfall:** EventSource has built-in reconnection. If the backend restarts, all clients reconnect simultaneously.

**Prevention Strategy:**
- Add random jitter to the `retry` value in the SSE endpoint
- Implement a single shared EventSource instance (singleton pattern)

**Phase:** Frontend build (SSE client setup)

---

### 4.3 Memory Leak from Uncleared EventSource on React Component Unmount

**The Pitfall:** If the React component creating EventSource unmounts without calling `eventSource.close()`, connections accumulate. React Strict Mode double-mounts in dev.

**Prevention Strategy:**
- Use `useEffect` cleanup: `return () => es.close();`
- Create a custom hook (`usePriceStream`) encapsulating the lifecycle
- Track active connection with a ref for Strict Mode compatibility

**Phase:** Frontend build (SSE client setup)

---

## 5. Real-Time Financial UI Performance

### 5.1 Excessive Re-Renders from SSE Price Updates

**The Pitfall:** 500ms updates for 10+ tickers causes 50+ re-renders per second if price state is a single object.

**Prevention Strategy:**
- Use per-ticker selectors with Zustand: `const price = useStore((s) => s.prices[ticker])`
- Use `React.memo` on ticker row components with custom comparator
- Consider `useRef` + `requestAnimationFrame` for flash animations (bypass render cycle)

**Phase:** Frontend build (watchlist component)

---

### 5.2 Price Flash Animation Stacking

**The Pitfall:** 500ms updates overlap with 500ms fade animation, creating permanent colored backgrounds.

**Prevention Strategy:**
- Two-phase: add flash class (immediate), remove after 150ms (triggers CSS fade-out transition)
- CSS: `transition: background-color 400ms ease-out` on class removal
- Ensure animation lifecycle is shorter than update interval

**Phase:** Frontend build (watchlist component)

---

### 5.3 Lightweight Charts Memory Leak on Rapid Updates

**The Pitfall:** Continuous `series.update()` calls grow internal data arrays unbounded.

**Prevention Strategy:**
- Cap data series to a rolling window (last 2 hours for detail, 200 points for sparklines)
- Create/destroy chart instance on ticker change: `return () => chart.remove()`
- Profile memory during 30-minute sessions

**Phase:** Frontend build (chart components)

---

### 5.4 Portfolio Heatmap Layout Thrashing

**The Pitfall:** Treemap recalculates layout on every 500ms price tick, making rectangles jump around.

**Prevention Strategy:**
- Update colors (P&L) on every tick, but recalculate layout only every 5-10 seconds
- Only recalculate sizes on trade execution (weight changes slowly)
- CSS transitions on color, NOT on position/size

**Phase:** Frontend build (portfolio visualization)

---

## 6. Docker Multi-Service Orchestration

### 6.1 depends_on Does Not Wait for Backend Readiness

**The Pitfall:** `depends_on` waits for container start, not app readiness. Frontend starts before backend is listening.

**Prevention Strategy:**
- Add healthcheck to backend service using `/api/health`
- Use `depends_on` with `condition: service_healthy`
- Implement `/api/health` early

**Phase:** Docker/deployment setup

---

### 6.2 Frontend Build Fails Because BACKEND_URL is Docker-Internal

**The Pitfall:** `BACKEND_URL=http://backend:8000` doesn't resolve at build time in Dockerfile.

**Prevention Strategy:**
- Set dummy `BACKEND_URL=http://localhost:8000` at build time, override at runtime
- Verify rewrites are evaluated at runtime (they are in Next.js)

**Phase:** Docker/deployment setup

---

### 6.3 Inconsistent .env Between Services

**Prevention Strategy:**
- Create `.env.example` with all variables and comments
- Use `env_file: .env` for backend, explicit `environment:` for frontend
- Add startup log printing configuration (redacting secrets)

**Phase:** Docker/deployment setup

---

## 7. Cross-Cutting Concerns

### 7.1 Portfolio Snapshot Task Outlives FastAPI Shutdown

**Prevention Strategy:**
- Cancel all background tasks in lifespan `finally` block
- Follow same pattern as market data source `stop()`
- Set Docker `stop_grace_period: 15s`

**Phase:** Portfolio history / background tasks

---

### 7.2 Chat Message Persistence and LLM Call Are Not Atomic

**Prevention Strategy:**
- Save user message BEFORE calling LLM
- Save assistant message + actions after trade execution
- If save fails, log error but don't undo trades
- Frontend shows optimistic UI, reconciles on reload

**Phase:** LLM integration / chat persistence

---

### 7.3 Watchlist-Market Source Synchronization

**The Pitfall:** Watchlist endpoint updates DB but forgets to call `source.add_ticker()`/`source.remove_ticker()`.

**Prevention Strategy:**
- Endpoint handler must BOTH update DB AND call market source method
- Write integration test: add ticker via API, verify it appears in SSE stream within 2 seconds

**Phase:** Watchlist CRUD implementation

---

### 7.4 Missing CORS for Direct Backend Access in Dev

**Prevention Strategy:**
- Add permissive CORS middleware gated to debug mode
- Document that production path is through `:3000` rewrites

**Phase:** Backend API setup

---

## Summary: Pitfall Priority by Phase

| Phase | Critical Pitfalls | IDs |
|-------|-------------------|-----|
| **Database Layer** | Prepared statement cache, cold start, SSL, transactions | 1.1, 1.2, 1.3, 1.4 |
| **Trade Execution** | Float math, avg cost formula, price staleness, races | 2.1, 2.2, 2.3, 1.4 |
| **LLM Integration** | OpenRouter structured output, JSON parsing, hallucinated trades, context overflow | 3.1, 3.2, 3.3, 3.4 |
| **Frontend SSE** | Proxy buffering, EventSource cleanup, reconnection | 4.1, 4.2, 4.3 |
| **Frontend UI** | Re-render perf, flash stacking, chart memory, treemap thrashing | 5.1, 5.2, 5.3, 5.4 |
| **Docker Setup** | depends_on readiness, build-time env, env consistency | 6.1, 6.2, 6.3 |
| **Cross-Cutting** | Background task shutdown, chat atomicity, watchlist sync, CORS | 7.1, 7.2, 7.3, 7.4 |

---

*Pitfalls analysis: 2026-03-01*
