# Phase 3: LLM Chat Integration - Research

**Researched:** 2026-03-02
**Domain:** LLM integration (LiteLLM + OpenRouter + Cerebras), structured outputs, agentic trade execution
**Confidence:** HIGH

## Summary

Phase 3 adds a chat endpoint (`POST /api/chat`) that accepts user messages, builds portfolio context, calls an LLM via LiteLLM/OpenRouter with Cerebras inference, parses structured JSON responses, auto-executes trades and watchlist changes, persists messages, and returns a complete response. A mock mode (`LLM_MOCK=true`) enables testing without an API key.

The technical approach is well-defined by the project's `cerebras-inference` skill and the existing codebase patterns. The backend already has a clean service layer (`services/portfolio.py`, `services/watchlist.py`) that the chat service will reuse directly for trade execution and watchlist management. LiteLLM supports passing Pydantic BaseModel classes directly as `response_format`, which LiteLLM internally converts to a JSON schema -- this is the simplest approach and matches the skill's code snippets. The `extra_body` parameter routes requests through Cerebras as the inference provider on OpenRouter.

**Primary recommendation:** Create a `services/chat.py` that orchestrates context building, LLM calling, action execution, and persistence. Use the existing `execute_trade` and `add_ticker`/`remove_ticker` functions directly. Define a Pydantic model for the structured response. Implement mock mode as a simple function swap based on `settings.llm_mock`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CHAT-01 | `POST /api/chat` accepts user message, returns JSON (message + trades + watchlist_changes) | Route + service layer pattern from Phase 2; Pydantic request/response models |
| CHAT-02 | Chat builds portfolio context (cash, positions with P&L, watchlist with prices, total value) | Reuse `get_portfolio()` and `get_watchlist()` from existing services |
| CHAT-03 | Loads last 20 messages from chat_messages as conversation history | Simple SQL query; `chat_messages` table already exists in schema |
| CHAT-04 | LLM called via LiteLLM -> OpenRouter with Cerebras, structured JSON output | `cerebras-inference` skill provides exact code; `litellm` needs `uv add` |
| CHAT-05 | Trades in LLM response auto-executed through `execute_trade` | Direct reuse of `services/portfolio.execute_trade` |
| CHAT-06 | Watchlist changes auto-executed through watchlist service | Direct reuse of `services/watchlist.add_ticker`/`remove_ticker` |
| CHAT-07 | Failed actions include error details in response | Try/except around each action, collect errors into response |
| CHAT-08 | Messages and actions persisted to chat_messages table | INSERT with role, content, actions JSONB; `json.dumps` for actions column |
| CHAT-09 | `LLM_MOCK=true` returns deterministic mock responses without calling OpenRouter | Function swap: `_call_llm()` vs `_mock_llm_response()` based on `settings.llm_mock` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | latest (>=1.50.0) | Unified LLM API client | Project skill mandates it; supports OpenRouter + structured outputs + provider routing via `extra_body` |
| pydantic | >=2.8.0 (already installed) | Structured output schema + request/response models | Already used throughout; LiteLLM accepts Pydantic BaseModel as `response_format` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncpg | >=0.29.0 (already installed) | DB operations for chat_messages | Already used; INSERT/SELECT for message persistence |
| json (stdlib) | N/A | Serialize actions dict to JSON for JSONB column | `json.dumps()` when writing actions to DB |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LiteLLM | Direct OpenAI SDK | Skill mandates LiteLLM; LiteLLM abstracts provider routing, has built-in structured output support |
| Pydantic response_format | Manual JSON schema dict | Pydantic is cleaner, auto-generates schema, provides validation on parse |
| Synchronous LLM call | Streaming SSE | PLAN explicitly says no streaming; Cerebras is fast enough; structured outputs break with streaming |

**Installation:**
```bash
cd backend && uv add litellm
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── models/
│   └── chat.py           # ChatRequest, ChatResponse, LLMStructuredResponse, TradeAction, WatchlistAction
├── services/
│   └── chat.py           # orchestrate_chat() — context, LLM call, action execution, persistence
├── routes/
│   └── chat.py           # POST /api/chat — thin route handler
└── main.py               # Register chat router
```

### Pattern 1: Service Layer Orchestration (from Phase 2)
**What:** Routes are thin; all business logic lives in services. The chat service orchestrates multiple existing services.
**When to use:** Always for the chat endpoint -- it coordinates portfolio context, LLM calls, trade execution, watchlist changes, and persistence.
**Example:**
```python
# services/chat.py
async def orchestrate_chat(
    pool: Pool,
    price_cache: PriceCache,
    market_source: MarketDataSource,
    settings: Settings,
    user_message: str,
) -> dict:
    """Full chat flow: context -> LLM -> execute actions -> persist -> respond."""
    # 1. Build portfolio context
    portfolio = await get_portfolio(pool, price_cache)
    watchlist = await get_watchlist(pool, price_cache)

    # 2. Load conversation history (last 20 messages)
    history = await _load_history(pool)

    # 3. Call LLM (or mock)
    if settings.llm_mock:
        llm_response = _mock_response(user_message)
    else:
        llm_response = await _call_llm(settings, portfolio, watchlist, history, user_message)

    # 4. Execute trades and watchlist changes
    executed_actions = await _execute_actions(
        pool, price_cache, market_source, llm_response
    )

    # 5. Persist messages
    await _persist_messages(pool, user_message, llm_response, executed_actions)

    # 6. Return response
    return { ... }
```

### Pattern 2: Pydantic Structured Output with LiteLLM
**What:** Define a Pydantic BaseModel for the LLM's response schema; pass it directly as `response_format` to LiteLLM.
**When to use:** For the LLM call to ensure typed, validated responses.
**Example:**
```python
# Source: cerebras-inference skill + LiteLLM docs (Context7)
from pydantic import BaseModel
from litellm import completion

class TradeAction(BaseModel):
    ticker: str
    side: str  # "buy" or "sell"
    quantity: float

class WatchlistAction(BaseModel):
    ticker: str
    action: str  # "add" or "remove"

class LLMResponse(BaseModel):
    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistAction] = []

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

response = completion(
    model=MODEL,
    messages=messages,
    response_format=LLMResponse,
    reasoning_effort="low",
    extra_body=EXTRA_BODY,
)
result = LLMResponse.model_validate_json(response.choices[0].message.content)
```

### Pattern 3: Graceful Action Execution with Error Collection
**What:** Execute each trade/watchlist action in a try/except, collecting successes and failures separately.
**When to use:** When auto-executing LLM-suggested actions (CHAT-05, CHAT-06, CHAT-07).
**Example:**
```python
async def _execute_actions(pool, price_cache, market_source, llm_response):
    results = {"trades": [], "watchlist_changes": [], "errors": []}

    for trade in llm_response.trades:
        try:
            result = await execute_trade(
                pool, price_cache, trade.ticker, trade.side, trade.quantity
            )
            await record_snapshot(pool, price_cache)
            results["trades"].append(result)
        except ValueError as e:
            results["errors"].append({"type": "trade", "detail": str(e), **trade.model_dump()})

    for change in llm_response.watchlist_changes:
        try:
            if change.action == "add":
                await add_ticker(pool, market_source, change.ticker)
            elif change.action == "remove":
                await remove_ticker(pool, market_source, change.ticker)
            results["watchlist_changes"].append(change.model_dump())
        except ValueError as e:
            results["errors"].append({"type": "watchlist", "detail": str(e), **change.model_dump()})

    return results
```

### Pattern 4: Mock Mode as Function Swap
**What:** When `settings.llm_mock` is True, replace the LLM call with a deterministic function that returns a fixed `LLMResponse`.
**When to use:** For CHAT-09, enabling testing without an API key.
**Example:**
```python
def _mock_response(user_message: str) -> LLMResponse:
    """Return a deterministic mock response for testing."""
    return LLMResponse(
        message=f"Mock response: I received your message about '{user_message}'. "
                "As a mock AI assistant, I can confirm the chat system is working correctly.",
        trades=[],
        watchlist_changes=[],
    )
```

### Anti-Patterns to Avoid
- **Calling LLM from route handler:** Route should delegate to service. The chat service orchestrates everything.
- **Fire-and-forget action execution:** All actions must complete before the response is returned. The response must include execution results.
- **Hardcoding system prompt in the service function:** Extract the system prompt to a constant or separate function for maintainability.
- **Not validating LLM output after parsing:** Even with structured outputs, validate field values (e.g., side must be "buy" or "sell", ticker must match pattern).
- **Blocking the event loop with synchronous LiteLLM calls:** LiteLLM's `completion()` is synchronous. Wrap it with `asyncio.to_thread()` or use `acompletion()` (LiteLLM provides async variant).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema generation | Manual dict building | Pydantic `BaseModel` as `response_format` | Pydantic auto-generates valid JSON schema; manual schemas are error-prone |
| LLM provider routing | Custom HTTP client to OpenRouter | LiteLLM `completion()` with `extra_body` | LiteLLM handles auth, retries, response parsing, provider-specific quirks |
| Structured output parsing | Manual JSON parsing + validation | `LLMResponse.model_validate_json(content)` | Pydantic handles type coercion, validation errors, default values |
| Retry logic for malformed responses | Custom retry loop | Simple try/except with one retry (per PLAN decision N4) | Keep it simple: retry once, then return fallback |

**Key insight:** The LLM integration is primarily an orchestration problem, not a library problem. The heavy lifting (trade execution, watchlist management, portfolio context) is already implemented. The chat service just wires existing services together with an LLM call in the middle.

## Common Pitfalls

### Pitfall 1: Synchronous LiteLLM blocking the async event loop
**What goes wrong:** `litellm.completion()` is synchronous and makes HTTP requests. Calling it directly from an async handler blocks the entire event loop, freezing SSE streams and other requests.
**Why it happens:** LiteLLM's default `completion()` is sync. Developers forget they're in an async context.
**How to avoid:** Use `litellm.acompletion()` (the async variant) which is natively async. If `acompletion` has issues with structured outputs, fall back to `asyncio.to_thread(litellm.completion, ...)`.
**Warning signs:** SSE stream freezes during chat requests; other endpoints become unresponsive.

### Pitfall 2: OpenRouter API key not propagated to LiteLLM
**What goes wrong:** LiteLLM expects `OPENROUTER_API_KEY` as an environment variable. If the app loads it via Pydantic Settings but doesn't set it in `os.environ`, LiteLLM can't find it.
**Why it happens:** Pydantic Settings reads from `.env` but doesn't re-export to `os.environ`. LiteLLM reads from `os.environ` directly.
**How to avoid:** Either (a) set `os.environ["OPENROUTER_API_KEY"]` explicitly before calling LiteLLM, or (b) pass `api_key=settings.openrouter_api_key` as a parameter to the `completion()` call. Option (b) is cleaner.
**Warning signs:** 401 errors from OpenRouter; "API key not found" errors from LiteLLM.

### Pitfall 3: LLM returns malformed JSON despite structured output request
**What goes wrong:** The LLM sometimes returns invalid JSON or JSON that doesn't match the schema, causing `model_validate_json()` to raise `ValidationError`.
**Why it happens:** Structured output enforcement varies by provider; Cerebras may not have perfect enforcement; network issues can truncate responses.
**How to avoid:** Per decision N4: retry once on parse failure. If still fails, return a fallback error message with no actions. Never let a parse error crash the endpoint.
**Warning signs:** `ValidationError` from Pydantic during response parsing.

### Pitfall 4: System prompt too long or context window exceeded
**What goes wrong:** Including full portfolio data + 20 messages of history + system prompt can exceed the model's context window, causing truncation or errors.
**Why it happens:** The `gpt-oss-120b` model has a generous context window, but portfolio data with many positions and long chat histories add up.
**How to avoid:** Keep the system prompt concise. Format portfolio context compactly (e.g., table format, not verbose prose). The 20-message limit is already a safeguard. If needed, summarize older messages.
**Warning signs:** LLM responses seem to ignore early context; OpenRouter returns context length errors.

### Pitfall 5: Race conditions between LLM actions and concurrent requests
**What goes wrong:** While the chat endpoint is executing LLM-suggested trades, a manual trade could execute simultaneously, causing inconsistent state.
**Why it happens:** Multiple HTTP requests can arrive concurrently in an async web server.
**How to avoid:** For v1 (single user), this is extremely unlikely. The existing `execute_trade` uses DB transactions for atomicity, which provides sufficient protection. No additional locking needed.
**Warning signs:** Double-deducted cash, position quantities out of sync.

### Pitfall 6: Not persisting user message before LLM call
**What goes wrong:** If the LLM call fails (timeout, error), the user's message is lost.
**Why it happens:** Persisting both messages after the LLM responds means the user message is only saved on success.
**How to avoid:** Persist the user message to `chat_messages` BEFORE calling the LLM. Persist the assistant message after. This ensures the user's message is always saved, even if the LLM call fails.
**Warning signs:** Chat history is missing user messages that got LLM errors.

## Code Examples

Verified patterns from the project skill and official sources:

### LiteLLM Completion with Cerebras (from project skill)
```python
# Source: .claude/skills/cerebras/SKILL.md
from litellm import completion

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

# Text response:
response = completion(model=MODEL, messages=messages, reasoning_effort="low", extra_body=EXTRA_BODY)
result = response.choices[0].message.content

# Structured output response:
response = completion(
    model=MODEL,
    messages=messages,
    response_format=MyBaseModelSubclass,
    reasoning_effort="low",
    extra_body=EXTRA_BODY,
)
result_as_object = MyBaseModelSubclass.model_validate_json(response.choices[0].message.content)
```

### Chat Messages Persistence (SQL)
```python
# Insert user message
await conn.execute(
    "INSERT INTO chat_messages (user_id, role, content, actions) VALUES ($1, $2, $3, $4)",
    DEFAULT_USER_ID,
    "user",
    user_message,
    None,  # user messages have no actions
)

# Insert assistant message with actions
import json
await conn.execute(
    "INSERT INTO chat_messages (user_id, role, content, actions) VALUES ($1, $2, $3, $4::jsonb)",
    DEFAULT_USER_ID,
    "assistant",
    llm_response.message,
    json.dumps(executed_actions),
)

# Load last 20 messages
rows = await conn.fetch(
    "SELECT role, content FROM chat_messages WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20",
    DEFAULT_USER_ID,
)
# Reverse to chronological order for the LLM
history = [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
```

### System Prompt Construction
```python
SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant for a simulated trading platform.

You help users manage their portfolio by:
- Analyzing portfolio composition, risk concentration, and P&L
- Suggesting trades with reasoning
- Executing trades when asked (buy/sell at market price)
- Managing the watchlist (adding/removing tickers)

Be concise and data-driven. Always respond with valid structured JSON.

Current Portfolio State:
{portfolio_context}

Current Watchlist:
{watchlist_context}
"""
```

### Route Handler Pattern (following Phase 2 conventions)
```python
# Source: existing routes/portfolio.py pattern
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.models.common import ErrorResponse
from app.models.chat import ChatRequest
from app.services.chat import orchestrate_chat

router = APIRouter(tags=["chat"])

@router.post("/api/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    pool = request.app.state.db_pool
    price_cache = request.app.state.price_cache
    market_source = request.app.state.market_source
    settings = request.app.state.settings
    try:
        result = await orchestrate_chat(
            pool, price_cache, market_source, settings, body.message
        )
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error="Chat failed", detail=str(e)).model_dump(),
        )
```

### Async LLM Call
```python
# Use litellm.acompletion for async context (non-blocking)
from litellm import acompletion

async def _call_llm(settings, messages, response_model):
    response = await acompletion(
        model=MODEL,
        messages=messages,
        response_format=response_model,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
        api_key=settings.openrouter_api_key,  # Pass explicitly (Pitfall 2)
    )
    return response_model.model_validate_json(response.choices[0].message.content)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JSON schema in `response_format` | Pass Pydantic BaseModel directly | LiteLLM ~1.30+ | Simpler code, auto-schema generation |
| `completion()` sync only | `acompletion()` async variant available | LiteLLM ~1.20+ | Non-blocking in async frameworks |
| OpenAI-only structured outputs | Multi-provider structured output support | LiteLLM ~1.40+ | Works with OpenRouter + Cerebras path |

**Deprecated/outdated:**
- LiteLLM `response_format={"type": "json_object"}` (basic JSON mode): Still works but less strict than JSON schema / Pydantic approach. Use Pydantic BaseModel for true structured outputs.

## Open Questions

1. **`acompletion()` compatibility with `response_format=PydanticModel`**
   - What we know: `completion()` supports it (confirmed by skill + Context7). `acompletion()` is the async wrapper.
   - What's unclear: Whether `acompletion()` passes `response_format` correctly to OpenRouter/Cerebras. The skill examples only show sync `completion()`.
   - Recommendation: Try `acompletion()` first. If structured output fails with `acompletion()`, fall back to `asyncio.to_thread(completion, ...)`. This should be validated early in implementation.

2. **Cerebras inference provider reliability for structured outputs**
   - What we know: The skill specifies `openrouter/openai/gpt-oss-120b` with `{"provider": {"order": ["cerebras"]}}`. OpenRouter routes to Cerebras for fast inference.
   - What's unclear: Whether Cerebras enforces structured output schemas as strictly as OpenAI natively does. Some providers do "best effort" JSON.
   - Recommendation: Implement the retry-once fallback (decision N4) to handle occasional schema violations. Parse with `model_validate_json` and catch `ValidationError`.

3. **JSONB casting for asyncpg**
   - What we know: asyncpg requires explicit type casting for JSONB columns. The `actions` column in `chat_messages` is JSONB.
   - What's unclear: Whether asyncpg handles `json.dumps(dict)` as a string parameter for JSONB, or requires explicit `::jsonb` cast in SQL.
   - Recommendation: Use `$N::jsonb` cast in the SQL query and pass `json.dumps(actions)` as the parameter value. Test early.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && uv run pytest tests/test_chat.py -x -v` |
| Full suite command | `cd backend && uv run pytest tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | POST /api/chat accepts message, returns structured response | unit (route) | `cd backend && uv run pytest tests/test_chat.py::test_chat_endpoint_returns_response -x` | Wave 0 |
| CHAT-02 | Portfolio context included in LLM prompt | unit (service) | `cd backend && uv run pytest tests/test_chat.py::test_context_includes_portfolio -x` | Wave 0 |
| CHAT-03 | Last 20 messages loaded as history | unit (service) | `cd backend && uv run pytest tests/test_chat.py::test_loads_message_history -x` | Wave 0 |
| CHAT-04 | LLM called via LiteLLM with correct model/params | unit (service) | `cd backend && uv run pytest tests/test_chat.py::test_llm_called_with_correct_params -x` | Wave 0 |
| CHAT-05 | Trades in response are auto-executed | unit (service) | `cd backend && uv run pytest tests/test_chat.py::test_trades_auto_executed -x` | Wave 0 |
| CHAT-06 | Watchlist changes in response are auto-executed | unit (service) | `cd backend && uv run pytest tests/test_chat.py::test_watchlist_changes_auto_executed -x` | Wave 0 |
| CHAT-07 | Failed actions include error details | unit (service) | `cd backend && uv run pytest tests/test_chat.py::test_failed_action_includes_error -x` | Wave 0 |
| CHAT-08 | Messages persisted to chat_messages table | unit (service) | `cd backend && uv run pytest tests/test_chat.py::test_messages_persisted -x` | Wave 0 |
| CHAT-09 | LLM_MOCK=true returns mock without calling OpenRouter | unit (service) | `cd backend && uv run pytest tests/test_chat.py::test_mock_mode_no_llm_call -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/test_chat.py -x -v`
- **Per wave merge:** `cd backend && uv run pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_chat.py` -- covers CHAT-01 through CHAT-09
- [ ] Framework install: `cd backend && uv add litellm` -- litellm not yet in dependencies

*(Existing test infrastructure -- pytest, pytest-asyncio, conftest.py with mock_pool/mock_conn -- covers the testing foundation. Only test file and litellm dependency are needed.)*

## Sources

### Primary (HIGH confidence)
- `/websites/litellm_ai` (Context7) - structured outputs with Pydantic BaseModel as response_format, OpenRouter provider support, completion API
- `.claude/skills/cerebras/SKILL.md` (project skill) - exact model, extra_body, and code patterns for Cerebras inference via LiteLLM
- Existing codebase (`backend/app/services/portfolio.py`, `backend/app/services/watchlist.py`) - service layer patterns, execute_trade and watchlist CRUD functions

### Secondary (MEDIUM confidence)
- LiteLLM docs on `acompletion()` - async variant exists and mirrors `completion()` API, but not explicitly tested with Pydantic `response_format` in the Context7 snippets found

### Tertiary (LOW confidence)
- `acompletion()` + `response_format=PydanticModel` combination - not directly verified; flagged in Open Questions for early validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - LiteLLM + Pydantic are mandated by project skill; versions confirmed available
- Architecture: HIGH - Service layer pattern proven in Phase 2; chat service follows same structure
- Pitfalls: HIGH - Async blocking, API key propagation, and malformed JSON are well-documented LLM integration issues

**Research date:** 2026-03-02
**Valid until:** 2026-04-01 (LiteLLM releases frequently but core API is stable)
