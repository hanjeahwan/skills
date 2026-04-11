---
name: prototype-lab
description: Creates and manages sandboxed prototypes in src/prototypes/ for non-technical exploration without modifying production code. Provides scaffolding, sandbox enforcement, and verification for handoff. Triggers when prototyping features, creating UI mocks, verifying readiness, archiving, or discussing prototype migration.
argument-hint: "[prototype-name or action]"
user-invocable: true
---

# Prototype Lab

Sandboxed prototyping for non-technical users. Reuse the platform's design system without modifying production code.

## Required Reading

Before any action, read the relevant foundation docs. This skill is an orchestrator — the docs contain the actual rules.

| When | Read |
|---|---|
| Always (first action) | [PROTOTYPE.md](../../../docs/PROTOTYPE.md) — authoritative sandbox rules, directory convention, allowed/forbidden imports, component customization strategies, lifecycle |
| Scaffolding or building UI | [FRONTEND.md](../../../docs/FRONTEND.md) — component conventions, state management, provider tree |
| Choosing page layout | [docs/ui-patterns/](../../../docs/ui-patterns/) — match page type (dashboards, listing-pages, forms, detail-pages, dialogs-and-drawers, feedback-and-states) |
| Styling or theming | [DESIGN.md](../../../docs/DESIGN.md) — tokens, layout patterns, responsive strategy, theming |
| Adding i18n keys | [I18N.md](../../../docs/I18N.md) — key naming, copy rules |
| Checking import boundaries | [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) — invariants section, import hierarchy |

## Detect Mode

| User intent | Mode |
|---|---|
| "create prototype", "scaffold", "new prototype", no prototype exists yet | **Scaffold** |
| Editing files under `src/prototypes/` | **Guard** |
| "verify", "check", "is it ready", "review prototype" | **Verify** |
| "archive prototype", "abandon", "remove prototype" | **Archive** |

Migration is handled by engineers via [PROTOTYPE.md](../../../docs/PROTOTYPE.md) § "Migration (Engineer Handoff)". Not part of this skill.

If intent is ambiguous, ask one clarifying question (use AskUserQuestion in Claude Code, `request_user_input` in Codex, `ask_user` in Gemini; fall back to numbered options and wait for reply).

---

## 1. Scaffold Mode

Create a new sandboxed prototype.

### Phase 1: Gather inputs

Ask the user:

1. **Project name** (kebab-case, e.g., `candidate-eval`)
2. **Route type:**
   - **App shell** (default) — sidebar + header, route at `src/app/(app)/prototype/<name>/page.tsx`
   - **Standalone** — minimal layout, route at `src/app/(prototype)/prototype/<name>/page.tsx`
3. **Brief purpose** (one sentence for the doc)
4. **Scope classification:**
   - **Quick** — single component, <100 LOC, no data layer
   - **Standard** (default) — multiple components, mock data, 1-2 views
   - **Complex** — multi-tab, charts/tables/forms, rich interactions, mock data layer

### Phase 2: Create files

Read [PROTOTYPE.md](../../../docs/PROTOTYPE.md) § "Directory Convention" for the full module structure. Create subdirectories as needed based on scope.

For the root component (`index.tsx`):
- App shell prototypes must use `Header` + `Main` layout — study any `src/features/*/index.tsx` for the pattern (all production features follow it)
- Read the matching page-type guide in [docs/ui-patterns/](../../../docs/ui-patterns/)

Create the route file (thin re-export only):
- App shell: `src/app/(app)/prototype/<name>/page.tsx`
- Standalone: `src/app/(prototype)/prototype/<name>/page.tsx`

Create the prototype doc: read [template.md](../../../docs/prototypes/template.md), fill in fields, save as `docs/prototypes/<name>.md`.

### Phase 3: Build verification

Run `pnpm run build`. Fix until green.

### Phase 4: Handoff

Present next steps (use the platform's question tool):

1. **Continue building** — enters Guard mode with sandbox enforcement
2. **Done for now** — scaffold complete, return to user
3. **Share doc** — display the generated prototype doc

Output closing summary:

```
Scaffold complete!

Prototype: src/prototypes/<name>/
Route: /prototype/<name>
Doc: docs/prototypes/<name>.md
Status: active | Scope: <quick|standard|complex>

Next step: [selected option]
```

---

## 2. Guard Mode

Active whenever editing files under `src/prototypes/`. Enforce sandbox constraints on every file change.

**Rules source:** [PROTOTYPE.md](../../../docs/PROTOTYPE.md) — read the Allowed Imports, Forbidden Imports, Read-Only Shared Code, Data, and Component Customization Strategies sections. Do not memorize — re-read on each session.

Enforcement points:
- **Import boundaries** — after each file edit, use the native content-search tool (e.g., Grep in Claude Code) to verify no forbidden imports per [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) § "Invariants"
- **Component customization** — when a shared component doesn't fit, consult [PROTOTYPE.md](../../../docs/PROTOTYPE.md) § "Component Customization Strategies" (5 strategies with decision guide) before writing code
- **Page layout** — match the page type to [docs/ui-patterns/](../../../docs/ui-patterns/) before creating new views
- **Component conventions** — follow [FRONTEND.md](../../../docs/FRONTEND.md) for naming, patterns, and state approach
- **Mock-only data** — hardcoded values or `@faker-js/faker` only; no server calls
- **Dependency tracking** — record new npm packages in `docs/prototypes/<name>.md` § "Dependencies Added"
- **Auto-fix before stopping** — every time work pauses or the user is done for the session, run the fix cycle (see below) so code is always commit-ready. Non-technical users cannot fix lint/type errors themselves

### Fix cycle (run before every pause or handoff)

This is the most critical enforcement in the skill. Non-technical users depend on code being commit-ready at all times.

1. Run `pnpm run lint:fix` — auto-fixes formatting and lint issues
2. Run `tsc --noEmit` — if type errors, fix them, re-run until clean
3. Run `pnpm run build` — if build errors, fix them, re-run until clean

Never leave code in a state that would fail pre-commit hooks. If errors cannot be auto-fixed, fix them manually before returning control to the user.

---

## 3. Verify Mode

Quality gate before marking a prototype as ready for handoff. Run when work is believed complete.

### Phase 1: Fix cycle

Run the fix cycle from Guard Mode above. All three steps must pass before proceeding.

### Phase 2: Import boundary audit

Use native content-search tools (e.g., Grep in Claude Code) to scan all files under `src/prototypes/<name>/` for forbidden imports (`@/server/*`, `@/features/*`, `@/prototypes/<other>/`). Cross-reference against [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) § "Invariants". Fix violations, then re-run fix cycle.

### Phase 3: Self-review

Spawn a review subagent to check: unused imports, dead code, `console.log`, unsafe type assertions, missing validation wiring, over-complexity. Fix high/medium findings, then re-run fix cycle.

### Phase 4: Doc completeness

Read [template.md](../../../docs/prototypes/template.md) to identify required sections. Then read `docs/prototypes/<name>.md` and verify each section is filled in. Fix gaps.

### Phase 5: Status decision

Present options (use the platform's question tool):

1. **Mark as ready** — update doc status to `ready`, add Completion Summary section, add status history entry
2. **Continue iterating** — stay `active`, return to Guard mode
3. **Archive** — enter Archive mode

Output closing summary when marked ready:

```
Prototype verified and ready for handoff!

Prototype: <name>
Route: /prototype/<name>
Doc: docs/prototypes/<name>.md
Status: ready

Verification:
  Build: Pass | Type check: Pass
  Import boundaries: Pass
  Self-review: N fixes applied
  Doc: Complete

Recommended next step: Engineer reviews docs/prototypes/<name>.md for migration planning
```

---

## 4. Archive Mode

Per [PROTOTYPE.md](../../../docs/PROTOTYPE.md) § "Archiving (Abandoned Prototypes)":

1. Delete `src/prototypes/<name>/` and its route file
2. Remove i18n keys added solely for this prototype
3. Remove npm dependencies added solely for this prototype
4. Update `docs/prototypes/<name>.md` status to `archived` with reason and date

Output: `Prototype archived: <name> — reason: <reason>`

---

## Feedback Loop

```
Scaffold -> Guard (build features) -> Verify -> [fix] -> Verify -> Ready
               ^                                  |
               +---- Continue iterating ----------+
```

## Status Lifecycle

Per [PROTOTYPE.md](../../../docs/PROTOTYPE.md) § "Status Lifecycle":

`active` -> `ready` -> `migrated` (or `active`/`ready` -> `archived`)

---

## Reference

- Canonical rules: [PROTOTYPE.md](../../../docs/PROTOTYPE.md)
- Doc template: [template.md](../../../docs/prototypes/template.md)
- Architecture boundaries: [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md)
- UI patterns: [docs/ui-patterns/](../../../docs/ui-patterns/)
- Component conventions: [FRONTEND.md](../../../docs/FRONTEND.md)
- Design tokens: [DESIGN.md](../../../docs/DESIGN.md)
