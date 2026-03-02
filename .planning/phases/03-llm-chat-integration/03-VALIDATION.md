---
phase: 3
slug: llm-chat-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 3 — Validation Strategy

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
| 03-01-01 | 01 | 1 | CHAT-01 | unit | `cd backend && uv run pytest tests/test_chat.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | CHAT-02 | unit | `cd backend && uv run pytest tests/test_chat.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | CHAT-09 | unit | `cd backend && uv run pytest tests/test_chat.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | CHAT-03 | unit | `cd backend && uv run pytest tests/test_chat.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 1 | CHAT-04 | unit | `cd backend && uv run pytest tests/test_chat.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 1 | CHAT-05 | unit | `cd backend && uv run pytest tests/test_chat.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_chat.py` — stubs for CHAT-01 through CHAT-09
- [ ] `tests/conftest.py` — shared fixtures (extend existing if present)
- [ ] `uv add litellm` — install LiteLLM dependency

*Existing pytest infrastructure from Phase 1-2 covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM response quality | CHAT-06 | Subjective analysis quality | Send portfolio analysis request, verify response is relevant and data-driven |

*Most behaviors have automated verification via mock mode.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
