---
phase: 1
slug: database-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pyproject.toml |
| **Quick run command** | `cd backend && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INFRA-01 | unit | `uv run pytest tests/test_db.py -k pool` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | INFRA-02 | unit | `uv run pytest tests/test_db.py -k schema` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | INFRA-03 | unit | `uv run pytest tests/test_db.py -k seed` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | INFRA-04 | unit | `uv run pytest tests/test_health.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_db.py` — stubs for INFRA-01, INFRA-02, INFRA-03
- [ ] `tests/test_health.py` — stubs for INFRA-04
- [ ] `tests/conftest.py` — shared fixtures (mock pool, test settings)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Neon connection works with real DATABASE_URL | INFRA-01 | Requires live Neon instance | Set DATABASE_URL in .env, run `docker compose up backend`, check logs for successful connection |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
