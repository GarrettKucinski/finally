---
phase: 7
slug: frontend-polish-e2e-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (E2E via docker-compose.test.yml) |
| **Config file** | test/playwright.config.ts |
| **Quick run command** | `docker compose -f test/docker-compose.test.yml run --rm playwright npx playwright test --grep "chat\|watchlist"` |
| **Full suite command** | `docker compose -f test/docker-compose.test.yml run --rm playwright npx playwright test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Visual inspection of changed component + existing E2E suite
- **After every plan wave:** Run full E2E suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | UI-02 | visual + E2E | `docker compose -f test/docker-compose.test.yml run --rm playwright npx playwright test chat.spec.ts` | ✅ | ⬜ pending |
| 07-01-02 | 01 | 1 | OPS-06 | E2E | `docker compose -f test/docker-compose.test.yml run --rm playwright npx playwright test chat.spec.ts` | ✅ | ⬜ pending |
| 07-01-03 | 01 | 1 | VIZ-09 | E2E | `docker compose -f test/docker-compose.test.yml run --rm playwright npx playwright test watchlist.spec.ts` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Purple accent renders correctly on Send button, user bubbles, floating button | UI-02 | CSS visual correctness | Inspect elements in browser; verify computed color is #753991 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
