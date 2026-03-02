---
phase: 5
slug: visualizations-chat-panel
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd frontend && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd frontend && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 1 | VIZ-02 | visual | manual verify sparklines | N/A | ⬜ pending |
| TBD | 01 | 1 | VIZ-03 | unit+visual | `vitest run DetailedChart` | ❌ W0 | ⬜ pending |
| TBD | 02 | 1 | VIZ-04 | unit+visual | `vitest run Heatmap` | ❌ W0 | ⬜ pending |
| TBD | 02 | 1 | VIZ-05 | unit+visual | `vitest run PnLChart` | ❌ W0 | ⬜ pending |
| TBD | 03 | 2 | VIZ-09 | unit | `vitest run ChatPanel` | ❌ W0 | ⬜ pending |
| TBD | 03 | 2 | VIZ-10 | unit+visual | `vitest run ActionCard` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test stubs for Lightweight Charts DetailedChart component
- [ ] Test stubs for Recharts Heatmap/Treemap component
- [ ] Test stubs for Recharts P&L line chart
- [ ] Test stubs for ChatPanel + chatStore
- [ ] Test stubs for action card rendering

*Note: Sparklines (VIZ-02) are already implemented in Phase 4 — verification only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sparklines accumulate progressively from SSE | VIZ-02 | Requires live SSE stream observation | Open app, watch sparklines fill in over 30+ seconds |
| Price flash animations on chart | VIZ-03 | Visual animation timing | Click ticker, observe chart updates with price changes |
| Heatmap colors correct for P&L | VIZ-04 | Visual color accuracy | Execute buy, wait for price change, verify green/red |
| Chat panel collapse/expand | VIZ-09 | UI interaction | Click toggle, verify sidebar animates smoothly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
