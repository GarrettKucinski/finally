# FinAlly — AI Trading Workstation

A dark-themed, Bloomberg-inspired trading terminal with live-streaming market data, simulated portfolio management, and an AI chat assistant that can analyze positions and execute trades via natural language.

Built entirely by coding agents as the capstone for an agentic AI coding course.

## Quick Start

```bash
cp .env.example .env   # add your DATABASE_URL and OPENROUTER_API_KEY
docker compose up       # open http://localhost:3000
```

A default user is pre-seeded with $10,000 in virtual cash and a watchlist of 10 tickers. No login required.

## Architecture

| Layer | Stack |
|-------|-------|
| Frontend | Next.js, TypeScript, Tailwind CSS, Lightweight Charts |
| Backend | FastAPI, Python (uv), LiteLLM |
| Database | Neon Serverless Postgres |
| Real-time | Server-Sent Events (SSE) |
| AI | LiteLLM → OpenRouter (Cerebras inference) |

Two Docker containers orchestrated via `docker-compose.yml`. The frontend proxies `/api/*` to the backend through Next.js rewrites — single port, no CORS.

## Features

- **Live price streaming** — prices flash green/red on change with sparkline mini-charts
- **Simulated trading** — market orders, instant fill, fractional shares
- **Portfolio heatmap** — treemap sized by weight, colored by P&L
- **P&L tracking** — portfolio value chart from periodic snapshots
- **AI assistant** — analyzes positions, suggests and auto-executes trades, manages watchlist

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Neon Postgres connection string |
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for AI chat |
| `MASSIVE_API_KEY` | No | Massive API key for real market data (simulator used if absent) |
| `LLM_MOCK` | No | Set `true` for deterministic mock LLM responses |

## Project Structure

```
frontend/    # Next.js app (port 3000)
backend/     # FastAPI app (port 8000)
planning/    # Project spec and agent docs
test/        # Playwright E2E tests
```

## Documentation

See [`planning/PLAN.md`](planning/PLAN.md) for the full project specification.

## License

See [LICENSE](LICENSE).
