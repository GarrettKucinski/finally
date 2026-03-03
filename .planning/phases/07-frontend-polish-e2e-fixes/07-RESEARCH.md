# Phase 7: Frontend Polish & E2E Fixes - Research

**Researched:** 2026-03-02
**Domain:** Frontend CSS theming, accessibility, event propagation, E2E test selectors
**Confidence:** HIGH

## Summary

Phase 7 is a focused gap-closure phase addressing 4 minor tech debt items identified in the v1.0 milestone audit. All issues are well-understood, localized to specific files, and require straightforward fixes with no new library dependencies. The root causes are: (1) a CSS custom property name mismatch between globals.css and component references, (2) a missing `aria-label` on the floating chat button, (3) an E2E test selector that depends on the button's accessible name, and (4) a missing `e.stopPropagation()` call on the watchlist remove button.

The fixes touch 4 frontend source files and 1 E2E test file. No backend changes are needed. No new dependencies. Total scope is approximately 10 lines of code changes across 5 files.

**Primary recommendation:** Fix the CSS token name in `globals.css` (add `--color-accent-purple` alias or rename references), add `aria-label="AI"` to the floating button in Dashboard.tsx, update the E2E test selector to match, and add `e.stopPropagation()` to the WatchlistRow remove button.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-02 | Tailwind CSS with custom dark theme using accent colors: yellow `#ecad0a`, blue `#209dd7`, purple `#753991` | CSS token fix: `--color-accent-purple` is undefined; only `--color-secondary-purple` exists. Three components reference the undefined token. Fix by adding the alias token to `@theme` in globals.css. |
| VIZ-09 | AI chat panel (docked/collapsible sidebar) with message input, scrolling conversation history, and loading indicator | Floating chat button accessible name: button uses `title="Open AI Chat"` but E2E test expects `getByRole('button', { name: 'AI' })`. Fix by adding `aria-label="AI"` which takes precedence over `title` in accessible name computation. |
| OPS-06 | E2E tests via Playwright in `test/docker-compose.test.yml` with `LLM_MOCK=true` | Chat collapse/reopen E2E test (`chat.spec.ts` line 27) uses `getByRole('button', { name: 'AI' })`. After fixing the floating button's aria-label, the test selector will match correctly. |
</phase_requirements>

## Standard Stack

### Core (Already Installed -- No Changes)

| Library | Version | Purpose | Relevant to Phase 7 |
|---------|---------|---------|---------------------|
| Tailwind CSS | ^4 | Utility-first CSS with @theme | CSS token definition in globals.css |
| Next.js | 16.1.6 | Frontend framework | No changes needed |
| React | 19.2.3 | UI library | Event handling (stopPropagation) |
| Playwright | 1.52.0 | E2E testing | Test selector fix |

### Supporting

No new libraries needed. All fixes use existing APIs and patterns.

### Alternatives Considered

None. This phase has no library choices to make -- it is purely about fixing existing code.

**Installation:** No installation needed.

## Architecture Patterns

### Relevant File Map

```
frontend/src/
  app/globals.css                   # Fix 1: Add --color-accent-purple token
  components/
    Dashboard.tsx                   # Fix 2: Add aria-label="AI" to floating button
    watchlist/WatchlistPanel.tsx     # Fix 4: Add e.stopPropagation() to remove button
    chat/ChatPanel.tsx              # Verify: Uses --color-accent-purple (Send button)
    chat/ChatMessage.tsx            # Verify: Uses --color-accent-purple (user bubbles)
test/tests/
  chat.spec.ts                     # Fix 3: Verify/update E2E selector (may work after Fix 2)
```

### Pattern 1: Tailwind v4 @theme CSS Token Definition

**What:** In Tailwind v4, `@theme` in CSS replaces `tailwind.config.js` for defining design tokens. Variable names follow the pattern `--color-{name}: value`, which generates utility classes like `bg-{name}`, `text-{name}`, etc.

**Current state in globals.css:**
```css
@theme {
  --color-secondary-purple: #753991;  /* Generates: bg-secondary-purple */
  /* Missing: --color-accent-purple */  /* Would generate: bg-accent-purple */
}
```

**Components referencing the undefined token:**
1. `ChatPanel.tsx:105` -- `bg-[var(--color-accent-purple)]` (CSS variable syntax)
2. `ChatMessage.tsx:32` -- `bg-[var(--color-accent-purple)]/20` (CSS variable syntax with opacity)
3. `Dashboard.tsx:130` -- `bg-accent-purple` (Tailwind utility class) + `shadow-accent-purple/30`

**Fix:** Add `--color-accent-purple: #753991` to the `@theme` block. This is preferred over renaming references because:
- Three files reference `accent-purple` vs one file defining `secondary-purple`
- "Accent" more accurately describes how the color is used (for interactive elements)
- Both names can coexist if needed (semantic aliases for the same color)

**Source:** Context7 Tailwind CSS v4 documentation confirms `@theme` variable naming generates utility classes by stripping `--color-` prefix.

### Pattern 2: Accessible Name Computation for Buttons

**What:** When Playwright's `getByRole('button', { name: 'X' })` matches elements, it computes the accessible name per the W3C Accessible Name specification. The priority order is:
1. `aria-labelledby` (references another element's text)
2. `aria-label` (explicit label string)
3. Text content of the element
4. `title` attribute (fallback)

**Current state:** The floating button in Dashboard.tsx has:
- No `aria-label`
- No text content (only an SVG child)
- `title="Open AI Chat"` (fallback accessible name)

**E2E test expects:** `getByRole('button', { name: 'AI' })`

**Analysis of current behavior:** Playwright's `name` matching is case-insensitive substring by default. "AI" IS a substring of "Open AI Chat", so the selector might actually match the `title` fallback. However, the milestone audit flagged this as a mismatch. The safest fix is to add an explicit `aria-label` which:
- Takes priority over `title` in accessible name computation
- Is the standard practice for icon-only buttons
- Makes the button accessible to screen readers
- Guarantees the E2E selector works

**Fix:** Add `aria-label="AI"` to the floating button element.

### Pattern 3: Event Propagation in Nested Click Handlers

**What:** When a click handler is on a child element inside a parent that also has a click handler, the event bubbles up. This causes both handlers to fire.

**Current state in WatchlistPanel.tsx:**
```tsx
// Parent: WatchlistRow div has onClick={() => onSelect?.(ticker)}
// Child: Remove button has onClick={() => onRemove(ticker)}
// Missing: e.stopPropagation() on the remove button
```

**Impact:** Clicking the remove button triggers both `onRemove(ticker)` AND `onSelect(ticker)`. This causes:
1. The ticker gets selected in the chart area
2. Then it gets removed from the watchlist
3. Brief visual jitter / unnecessary state update

**Fix:** Add `e.stopPropagation()` to the remove button's onClick:
```tsx
onClick={(e) => { e.stopPropagation(); onRemove(ticker); }}
```

### Anti-Patterns to Avoid

- **Renaming the CSS variable instead of adding the alias:** Would require updating 3 component files instead of 1 CSS file. More churn, more risk.
- **Using `title` instead of `aria-label` for accessible name:** `title` is a fallback in the accessible name computation and its behavior can vary across browsers/screen readers. `aria-label` is the explicit, reliable choice for icon-only buttons.
- **Changing the E2E test selector without fixing the component:** The E2E test is correctly written per best practices (role-based selectors). The component should be fixed to have a proper accessible name, not the test weakened to use a less robust selector.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Accessible names | Custom data attributes + querySelector | `aria-label` + Playwright `getByRole` | Standard accessibility APIs; works across all testing tools |
| Event isolation | Custom event delegation system | `e.stopPropagation()` | Native browser API; one line, zero complexity |
| CSS token aliases | Duplicate inline styles | `@theme` variable | Tailwind v4's design system; single source of truth |

**Key insight:** Every fix in this phase uses standard platform APIs (ARIA, DOM events, CSS custom properties). No custom abstractions needed.

## Common Pitfalls

### Pitfall 1: CSS Variable vs Tailwind Utility Class Syntax Mismatch
**What goes wrong:** Dashboard.tsx uses `bg-accent-purple` (Tailwind utility), while ChatPanel.tsx and ChatMessage.tsx use `bg-[var(--color-accent-purple)]` (CSS variable in arbitrary value syntax). Both need the `--color-accent-purple` token to exist in `@theme`, but for different reasons.
**Why it happens:** Two developers or two phases chose different syntactic approaches to reference the same color.
**How to avoid:** Adding `--color-accent-purple` to `@theme` fixes BOTH usage patterns -- the Tailwind utility `bg-accent-purple` is generated from the variable, and `var(--color-accent-purple)` resolves to the CSS custom property value.
**Warning signs:** Elements rendering with transparent/missing backgrounds where a color was expected.

### Pitfall 2: Multiple Buttons Matching a Substring Selector
**What goes wrong:** `getByRole('button', { name: 'AI' })` could match multiple buttons if "AI" appears in other button names (e.g., "AI Assistant" text near a button).
**Why it happens:** Playwright's default name matching is case-insensitive substring.
**How to avoid:** Use `aria-label="AI"` on the specific button. If ambiguity remains, use `{ exact: true }` in the selector or add more specificity.
**Warning signs:** Playwright "strict mode violation" errors about multiple elements matching.

### Pitfall 3: stopPropagation Breaking Other Functionality
**What goes wrong:** Adding `stopPropagation()` to the remove button could theoretically prevent other event listeners higher in the tree from receiving the event.
**Why it happens:** Overly broad event delegation patterns.
**How to avoid:** In this case, the only parent handler is the row's `onSelect` click handler, which is exactly what we want to prevent. No other handlers are affected. The fix is safe.
**Warning signs:** Features that depend on event bubbling from the remove button (none exist in this codebase).

### Pitfall 4: Tailwind v4 @theme Variable Not Regenerating Utilities
**What goes wrong:** After adding a new `@theme` variable, the Tailwind utility class might not be available until the dev server or build process restarts.
**Why it happens:** Tailwind v4's JIT engine may cache the set of known utility classes.
**How to avoid:** Restart the dev server after modifying `@theme`. In Docker builds, this isn't an issue since `npm run build` runs fresh.
**Warning signs:** Utility class works in dev after restart but not before.

## Code Examples

Verified patterns from the existing codebase:

### Fix 1: Add CSS Token to globals.css

```css
/* frontend/src/app/globals.css */
@theme {
  --color-accent-yellow: #ecad0a;
  --color-primary-blue: #209dd7;
  --color-secondary-purple: #753991;
  --color-accent-purple: #753991;       /* ADD THIS LINE */
  --color-surface-primary: #0d1117;
  /* ... rest unchanged */
}
```

This single addition generates the `bg-accent-purple`, `text-accent-purple`, `shadow-accent-purple` utility classes AND makes `var(--color-accent-purple)` resolve correctly.

### Fix 2: Add aria-label to Floating Button

```tsx
/* frontend/src/components/Dashboard.tsx, line ~128 */
<button
  onClick={() => setChatOpen(true)}
  className="fixed bottom-6 right-6 z-10 flex h-14 w-14 items-center justify-center rounded-full bg-accent-purple text-white shadow-lg shadow-accent-purple/30 transition-transform hover:scale-110 hover:shadow-accent-purple/50 active:scale-95"
  title="Open AI Chat"
  aria-label="AI"                      /* ADD THIS ATTRIBUTE */
>
```

### Fix 3: E2E Test Selector (Verify -- May Already Work)

```typescript
/* test/tests/chat.spec.ts, line 27 */
// Current:
await page.getByRole('button', { name: 'AI' }).click();
// After Fix 2, this will match because aria-label="AI" is the accessible name.
// No change needed to the test file IF we use aria-label="AI" exactly.
```

### Fix 4: stopPropagation on Remove Button

```tsx
/* frontend/src/components/watchlist/WatchlistPanel.tsx, line ~65 */
<button
  onClick={(e) => { e.stopPropagation(); onRemove(ticker); }}
  className="ml-1 opacity-0 transition-opacity group-hover:opacity-100 text-text-muted hover:text-price-down"
  title={`Remove ${ticker}`}
>
  x
</button>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| tailwind.config.js for colors | @theme in CSS for Tailwind v4 | Tailwind v4 (2024) | CSS-native config, no JS config file |
| title attribute for icon buttons | aria-label for icon buttons | W3C ARIA best practice (long-standing) | Reliable accessible name across all browsers and assistive tech |
| data-testid selectors in E2E | getByRole with accessible name | Playwright best practice | Tests mirror user/assistive tech interaction |

**Deprecated/outdated:**
- `tailwind.config.js` / `tailwind.config.ts`: Still works in Tailwind v4 but @theme in CSS is the primary approach. This project already uses @theme.

## Open Questions

None. All four fixes are well-defined with clear root causes, specific file locations, and verified solutions. No external research gaps remain.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Playwright 1.52.0 (E2E) |
| Config file | `test/playwright.config.ts` |
| Quick run command | `cd test && npx playwright test tests/chat.spec.ts --project=chromium` |
| Full suite command | `cd test && npx playwright test --project=chromium` |

Note: Frontend has no unit test framework (no jest/vitest). All Phase 7 requirements are best validated by E2E tests and visual inspection via TypeScript compilation.

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-02 | Purple accent color renders on Send button, user bubbles, floating button | e2e + build | `cd frontend && npm run build` (TypeScript validates class usage; E2E verifies visible rendering) | Partial -- build exists, no specific color assertion test |
| VIZ-09 | Floating chat button has accessible name matching E2E selector | e2e | `cd test && npx playwright test tests/chat.spec.ts -g "collapse and reopen" --project=chromium` | Yes -- `test/tests/chat.spec.ts` line 16 |
| OPS-06 | Chat collapse/reopen E2E test passes | e2e | `cd test && npx playwright test tests/chat.spec.ts -g "collapse and reopen" --project=chromium` | Yes -- `test/tests/chat.spec.ts` line 16 |

### Sampling Rate

- **Per task commit:** `cd frontend && npm run build` (fast, validates Tailwind token + TypeScript)
- **Per wave merge:** Full Playwright suite via `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit playwright`
- **Phase gate:** Full E2E suite green, specifically `chat.spec.ts` "collapse and reopen" test passing

### Wave 0 Gaps

None -- existing test infrastructure covers all phase requirements. The `chat.spec.ts` "can collapse and reopen chat panel" test (line 16) is the primary validation. No new test files or framework changes needed.

## Sources

### Primary (HIGH confidence)

- **Context7 `/tailwindlabs/tailwindcss.com`** -- Tailwind v4 @theme directive, CSS variable naming, utility class generation
- **Context7 `/microsoft/playwright.dev`** -- Playwright getByRole, accessible name matching, name option semantics
- **Project source files** -- Direct inspection of globals.css, Dashboard.tsx, WatchlistPanel.tsx, ChatPanel.tsx, ChatMessage.tsx, chat.spec.ts

### Secondary (MEDIUM confidence)

- **W3C Accessible Name specification** -- Referenced by Playwright docs for name computation priority (aria-label > text content > title)
- **`.planning/v1.0-MILESTONE-AUDIT.md`** -- Source of all 4 tech debt items with file/line references

### Tertiary (LOW confidence)

None. All findings are verified against primary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new libraries, all fixes use existing project patterns
- Architecture: HIGH -- All files inspected, exact line numbers known, fixes are 1-3 lines each
- Pitfalls: HIGH -- Edge cases are minimal for these types of fixes

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable -- no library version sensitivity)
