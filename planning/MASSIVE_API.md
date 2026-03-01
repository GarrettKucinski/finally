# Massive (Polygon.io) API Reference

Research documentation for integrating the Massive financial data API into FinAlly.

> **Note:** Polygon.io rebranded to **Massive** (massive.com) in late 2025. The API base URL `api.polygon.io` still works during the transition. The Python package was renamed from `polygon-api-client` to `massive`.

---

## Authentication

Two methods supported — prefer the header approach:

```
# Query parameter (legacy)
GET https://api.polygon.io/v2/...?apiKey=YOUR_KEY

# Authorization header (preferred)
Authorization: Bearer YOUR_KEY
```

API keys: https://massive.com/dashboard/api-keys

---

## Rate Limits

| Plan | Limit | Suggested Poll Interval |
|------|-------|------------------------|
| Free | 5 req/min | 15 seconds |
| Developer ($7/mo) | ~100 req/sec | 2-5 seconds |
| Starter ($29/mo) | ~100 req/sec | 1-2 seconds |

When rate-limited, the API returns `429 Too Many Requests` with an optional `Retry-After` header.

---

## Primary Endpoint: Snapshot (Multiple Tickers)

This is the endpoint FinAlly should use. A single call returns current prices for all watchlist tickers.

```
GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,MSFT
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `tickers` | No | Comma-separated ticker list. Omit for ALL tickers (10k+). |
| `include_otc` | No | Include OTC securities. Default: `false` |

### Response

```json
{
  "status": "OK",
  "count": 3,
  "tickers": [
    {
      "ticker": "AAPL",
      "todaysChange": 0.98,
      "todaysChangePerc": 0.82,
      "updated": 1605195848258266000,
      "day": {
        "o": 119.62, "h": 120.53, "l": 118.81,
        "c": 120.42, "v": 28727868, "vw": 119.73
      },
      "min": {
        "o": 120.44, "h": 120.47, "l": 120.37,
        "c": 120.42, "v": 270796, "vw": 120.41,
        "av": 133963, "n": 5, "t": 1684428600000
      },
      "prevDay": {
        "o": 117.19, "h": 119.63, "l": 116.44,
        "c": 119.49, "v": 46691331, "vw": 118.25
      },
      "lastQuote": {
        "p": 120.46, "P": 120.47, "s": 8, "S": 4,
        "t": 1605195929997325600
      },
      "lastTrade": {
        "p": 120.42, "s": 536,
        "t": 1605195848258266000, "x": 4, "c": [63]
      }
    }
  ]
}
```

### Field Reference

| Path | Type | Description |
|------|------|-------------|
| `ticker` | string | Ticker symbol |
| `todaysChange` | float | Absolute change from previous close |
| `todaysChangePerc` | float | Percentage change from previous close |
| `updated` | int | Nanosecond Unix timestamp |
| **day** | | |
| `day.o/h/l/c` | float | Today's OHLC |
| `day.v` | int | Today's volume |
| `day.vw` | float | Today's VWAP |
| **min** | | |
| `min.o/h/l/c` | float | Most recent minute bar OHLC |
| `min.v` | int | Minute volume |
| `min.vw` | float | Minute VWAP |
| `min.av` | int | Accumulated volume today |
| `min.t` | int | Minute bar start (Unix ms) |
| **prevDay** | | |
| `prevDay.o/h/l/c` | float | Previous day OHLC |
| `prevDay.v` | int | Previous day volume |
| **lastTrade** | | |
| `lastTrade.p` | float | Last trade price |
| `lastTrade.s` | int | Last trade size (shares) |
| `lastTrade.t` | int | Timestamp (nanoseconds) |
| `lastTrade.x` | int | Exchange ID |
| **lastQuote** | | |
| `lastQuote.p` | float | Bid price |
| `lastQuote.P` | float | Ask price |
| `lastQuote.s/S` | int | Bid/Ask size |

**Snapshot data resets daily at 3:30 AM EST** and begins repopulating around 4:00 AM EST.

---

## Other Useful Endpoints

### Single Ticker Snapshot

```
GET /v2/snapshot/locale/us/markets/stocks/tickers/{stocksTicker}
```

Response is the same structure but with a singular `ticker` object instead of a `tickers` array. Only useful if fetching one stock.

### Previous Close

```
GET /v2/aggs/ticker/{stocksTicker}/prev?adjusted=true
```

```json
{
  "status": "OK",
  "results": [{
    "T": "AAPL", "o": 115.55, "h": 117.59, "l": 114.13,
    "c": 115.97, "v": 131704427, "vw": 116.31, "t": 1605042000000
  }]
}
```

Not needed for FinAlly — the snapshot already includes `prevDay`.

### Grouped Daily Bars (All Tickers for a Date)

```
GET /v2/aggs/grouped/locale/us/market/stocks/{YYYY-MM-DD}?adjusted=true
```

Returns daily bars for every traded stock. Very large response — better for batch analysis than real-time.

### Last Trade / Last Quote

```
GET /v2/last/trade/{stocksTicker}
GET /v2/last/nbbo/{stocksTicker}
```

Single ticker only. Wasteful on the free tier when the snapshot gives you the same data for all tickers in one call.

---

## Why Snapshot Is the Right Choice for FinAlly

1. **Single API call** for all watchlist tickers — critical on the free tier (5 calls/min)
2. Returns `day.c` (current price) and `prevDay.c` (previous close) in one response
3. Pre-calculated `todaysChange` and `todaysChangePerc`
4. Includes `lastTrade.p` for the most recent trade price
5. The `tickers` param accepts a comma-separated list — fetch exactly what the watchlist needs

---

## Python Implementation

### Async Client with httpx

```python
import asyncio
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)
BASE_URL = "https://api.polygon.io"


class MassiveClient:
    """Async client for the Massive (Polygon.io) REST API."""

    def __init__(self, api_key: str, poll_interval: float = 15.0) -> None:
        self.poll_interval = poll_interval
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=10.0),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30.0,
            ),
        )

    async def fetch_snapshot(self, tickers: list[str]) -> dict:
        """Fetch current snapshot for multiple tickers in a single call."""
        response = await self._client.get(
            "/v2/snapshot/locale/us/markets/stocks/tickers",
            params={"tickers": ",".join(tickers)},
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()
```

### Parsing the Response

```python
from dataclasses import dataclass


@dataclass
class PriceUpdate:
    ticker: str
    price: float
    prev_close: float
    change: float
    change_percent: float
    timestamp: datetime


def parse_snapshot(data: dict) -> list[PriceUpdate]:
    """Parse snapshot response into PriceUpdate objects."""
    updates = []
    for td in data.get("tickers", []):
        day = td.get("day", {})
        prev_day = td.get("prevDay", {})
        updated_ns = td.get("updated", 0)

        updates.append(PriceUpdate(
            ticker=td["ticker"],
            price=day.get("c", 0.0),
            prev_close=prev_day.get("c", 0.0),
            change=td.get("todaysChange", 0.0),
            change_percent=td.get("todaysChangePerc", 0.0),
            timestamp=datetime.fromtimestamp(
                updated_ns / 1e9, tz=timezone.utc
            ) if updated_ns else datetime.now(timezone.utc),
        ))
    return updates
```

### Polling Loop with Rate Limit Handling

```python
async def poll_loop(
    client: MassiveClient,
    tickers: list[str],
    price_cache: dict,
) -> None:
    """Background task that polls the Massive API and updates the price cache."""
    while True:
        try:
            data = await client.fetch_snapshot(tickers)
            for td in data.get("tickers", []):
                symbol = td["ticker"]
                day = td.get("day", {})
                prev = td.get("prevDay", {})
                price_cache[symbol] = {
                    "price": day.get("c", 0.0),
                    "previous_price": prev.get("c", 0.0),
                    "change": td.get("todaysChange", 0.0),
                    "change_percent": td.get("todaysChangePerc", 0.0),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limited, backing off 60s")
                await asyncio.sleep(60)
                continue
            logger.error("HTTP error: %s", e)
        except Exception as e:
            logger.error("Poll error: %s", e)

        await asyncio.sleep(client.poll_interval)
```

### Retry with Exponential Backoff

```python
async def fetch_with_retry(
    client: MassiveClient,
    tickers: list[str],
    max_retries: int = 3,
) -> dict:
    """Fetch snapshot with retry logic for transient failures."""
    for attempt in range(max_retries + 1):
        try:
            return await client.fetch_snapshot(tickers)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = float(
                    e.response.headers.get("Retry-After", 2 ** attempt)
                )
                await asyncio.sleep(retry_after)
                continue
            if e.response.status_code >= 500 and attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            raise
        except httpx.TimeoutException:
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            raise
```

---

## Pydantic Models for Response Parsing

```python
from pydantic import BaseModel, Field, field_validator, model_validator


class PolygonTickerSnapshot(BaseModel):
    """Parse a single ticker from the Polygon snapshot response."""

    ticker: str
    todays_change: float = Field(alias="todaysChange", default=0.0)
    todays_change_perc: float = Field(alias="todaysChangePerc", default=0.0)
    updated: int = 0

    last_trade_price: float = 0.0
    prev_close: float = 0.0

    @model_validator(mode="before")
    @classmethod
    def extract_nested(cls, data: dict) -> dict:
        """Flatten nested Polygon response structure."""
        if isinstance(data, dict):
            data["last_trade_price"] = data.get("lastTrade", {}).get("p", 0.0)
            data["prev_close"] = data.get("prevDay", {}).get("c", 0.0)
        return data


class PolygonSnapshotResponse(BaseModel):
    """Top-level snapshot response."""

    status: str
    count: int = 0
    tickers: list[PolygonTickerSnapshot] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        if v != "OK":
            raise ValueError(f"Polygon API returned non-OK status: {v!r}")
        return v
```

---

## Key URLs

| Resource | URL |
|----------|-----|
| Massive Docs | https://massive.com/docs/ |
| Snapshot Endpoint Docs | https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot |
| Pricing | https://massive.com/pricing |
| Python Client (PyPI) | `pip install -U massive` |
| Python Client (GitHub) | https://github.com/polygon-io/client-python |
