---
phase: 2
slug: portfolio-watchlist-apis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio 0.24+ |
| **Config file** | `backend/pyproject.toml` (`[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) |
| **Quick run command** | `cd backend && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -v --cov=app` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -v --cov=app`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | PORT-01 | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_get_portfolio_empty -x` | Wave 0 | ⬜ pending |
| 02-01-02 | 01 | 1 | PORT-01 | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_get_portfolio_with_positions -x` | Wave 0 | ⬜ pending |
| 02-01-03 | 01 | 1 | PORT-02 | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_execute_buy -x` | Wave 0 | ⬜ pending |
| 02-01-04 | 01 | 1 | PORT-02 | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_execute_sell -x` | Wave 0 | ⬜ pending |
| 02-01-05 | 01 | 1 | PORT-03 | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_buy_insufficient_cash -x` | Wave 0 | ⬜ pending |
| 02-01-06 | 01 | 1 | PORT-04 | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_sell_insufficient_shares -x` | Wave 0 | ⬜ pending |
| 02-02-01 | 02 | 1 | PORT-05 | unit | `cd backend && uv run pytest tests/test_trade_service.py::test_trade_atomic -x` | Wave 0 | ⬜ pending |
| 02-02-02 | 02 | 1 | PORT-06 | unit | `cd backend && uv run pytest tests/test_trade_service.py::test_sell_all_deletes_position -x` | Wave 0 | ⬜ pending |
| 02-02-03 | 02 | 1 | PORT-07 | unit | `cd backend && uv run pytest tests/test_trade_service.py::test_trade_creates_log_entry -x` | Wave 0 | ⬜ pending |
| 02-02-04 | 02 | 1 | PORT-09 | unit | `cd backend && uv run pytest tests/test_trade_service.py::test_snapshot_after_trade -x` | Wave 0 | ⬜ pending |
| 02-03-01 | 03 | 1 | PORT-08 | unit | `cd backend && uv run pytest tests/test_snapshots.py::test_snapshot_recorder_loop -x` | Wave 0 | ⬜ pending |
| 02-03-02 | 03 | 1 | PORT-10 | unit | `cd backend && uv run pytest tests/test_snapshots.py::test_snapshot_cleanup -x` | Wave 0 | ⬜ pending |
| 02-03-03 | 03 | 1 | PORT-11 | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_get_portfolio_history -x` | Wave 0 | ⬜ pending |
| 02-04-01 | 03 | 1 | WATCH-01 | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_get_watchlist -x` | Wave 0 | ⬜ pending |
| 02-04-02 | 03 | 1 | WATCH-02 | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_add_ticker -x` | Wave 0 | ⬜ pending |
| 02-04-03 | 03 | 1 | WATCH-02 | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_add_invalid_ticker -x` | Wave 0 | ⬜ pending |
| 02-04-04 | 03 | 1 | WATCH-03 | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_remove_ticker -x` | Wave 0 | ⬜ pending |
| 02-04-05 | 03 | 1 | WATCH-03 | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_remove_nonexistent_ticker -x` | Wave 0 | ⬜ pending |
| 02-04-06 | 03 | 1 | WATCH-04 | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_add_registers_market_source -x` | Wave 0 | ⬜ pending |
| 02-04-07 | 03 | 1 | WATCH-05 | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_remove_unregisters_market_source -x` | Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_portfolio.py` — stubs for PORT-01, PORT-02, PORT-03, PORT-04, PORT-11
- [ ] `tests/test_trade_service.py` — stubs for PORT-05, PORT-06, PORT-07, PORT-09
- [ ] `tests/test_snapshots.py` — stubs for PORT-08, PORT-10
- [ ] `tests/test_watchlist.py` — stubs for WATCH-01, WATCH-02, WATCH-03, WATCH-04, WATCH-05

*Existing infrastructure (pytest, pytest-asyncio, httpx) covers framework needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
