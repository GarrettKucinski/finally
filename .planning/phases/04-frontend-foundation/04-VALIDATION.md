---
phase: 4
slug: frontend-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (E2E) + manual visual verification |
| **Config file** | frontend/playwright.config.ts (if created) |
| **Quick run command** | `cd frontend && npm run build` |
| **Full suite command** | `cd frontend && npm run build && npm run lint` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run build`
- **After every plan wave:** Run `cd frontend && npm run build && npm run lint`
- **Before `/gsd:verify-work`:** Full build must succeed
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | UI-01 | build | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | UI-02, VIZ-06 | build | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | UI-03, VIZ-01 | build | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | UI-04, VIZ-07 | build | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | UI-05, UI-06 | build | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 2 | UI-07, VIZ-08 | build | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `create-next-app` scaffold — Next.js project with TypeScript + Tailwind
- [ ] Tailwind v4 dark theme configuration with project accent colors
- [ ] Next.js rewrites configuration for `/api/*` proxy

*Wave 0 is integrated into Plan 01 Task 1 (project scaffold).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dark terminal aesthetic | UI-01 | Visual design judgment | Open localhost:3000, verify dark backgrounds (~#0d1117), accent colors visible |
| Price flash animations | UI-03, VIZ-01 | CSS animation timing | Watch prices update, verify green/red flash fading over ~500ms |
| Connection status indicator | UI-04 | SSE state visual | Check header dot: green when connected, stop backend to see red |
| Data-dense layout | UI-01 | Layout judgment | Verify terminal-inspired look, no wasted space |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
