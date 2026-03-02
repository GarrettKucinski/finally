---
phase: 6
slug: docker-e2e-tests
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright 1.58.2 (E2E), pytest 9.x (backend unit) |
| **Config file** | `test/playwright.config.ts` (Wave 0 creates) |
| **Quick run command** | `cd test && npx playwright test --grep @smoke` |
| **Full suite command** | `cd test && npx playwright test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd test && npx playwright test --grep @smoke`
- **After every plan wave:** Run `cd test && npx playwright test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | OPS-01 | integration | `docker compose up --build -d && curl localhost:3000` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | OPS-02 | integration | `docker compose up --build -d && curl localhost:8000/api/health` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | OPS-03 | e2e | `cd test && npx playwright test` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | OPS-04 | e2e | `cd test && npx playwright test --grep @smoke` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `test/playwright.config.ts` — Playwright config targeting containerized app
- [ ] `test/docker-compose.test.yml` — Test compose extending main compose
- [ ] `test/package.json` — Playwright dependencies

*Wave 0 created during Plan 02 execution.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE price streaming works in Docker | OPS-05 | Requires observing real-time stream | Open browser to localhost:3000, verify prices update |
| Container startup time acceptable | OPS-06 | Subjective threshold | Run `time docker compose up --build`, verify < 60s |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
