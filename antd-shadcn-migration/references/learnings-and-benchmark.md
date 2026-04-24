# Learnings and Benchmark Gate

Use this reference after verification and before final acceptance. It keeps migration experience reusable and prevents false passes.

## Migration Learnings

Every real migration must leave behind reusable learning. Record learnings in the target repository when a docs location exists. Prefer `docs/migrations/antd/learnings.md`; otherwise append them to the component migration contract.

Future migrations must read these records during learning lookup before writing a new contract.

Learning entry format:

```markdown
## <Component> - <short issue title>

id: antd-migration-YYYYMMDD-001
date: <YYYY-MM-DD>
component: <Button | Select | Steps | Modal | ...>
component_class: <primitive | form-control | overlay | data-display | date-time | infrastructure>
target_stack: <Next.js | Vite | Tailwind v4 | shadcn path | test framework>
edge_gates: <01, 04, 07, 14>
status: <local-learning | promoted-to-skill | rejected>
promoted_to: <SKILL.md section or none>
target_repo: <path or repo name>
ant_source: <component path and version/commit>

### Trigger
<error text, failing command, component type, target project config, user request pattern, or test failure pattern>

### Symptom
<failing test, build error, visual issue, browser behavior, or user-visible mismatch>

### Root cause
<logic-level cause tied to Ant source evidence, target project config, shadcn/Radix behavior, Tailwind v4 styling, or test harness behavior>

### Fix
<specific change that resolved the problem>

### Verification
<commands, tests, browser checks, or benchmark assertions that proved the fix>

### Prevention
<future contract row, red test, edge gate action, token mapping, source file to inspect, or non-goal>

### Regression assertion
<one objective assertion that should be added to a test, benchmark, or review checklist>

### Backfill scan
<sibling migrated components and shared primitives scanned, matches found, fixes applied, or source-backed non-goals>

### Skill evolution
<new rule, edge-case gate update, test assertion, source file to inspect, or migration-contract field to add next time>
```

## Regression Assertion Closure

- Every new learning's `Regression assertion` must map to a repo test, benchmark assertion, compatibility contract row, acceptance checklist row, or documented source-backed non-goal.
- If an assertion is intentionally not implemented, record the source-backed reason in the learning and component contract.
- `Learnings captured and promoted` cannot be `pass` while any new learning has an unmapped regression assertion.
- `Learning regression assertions landed` cannot be `pass` until each learning has a landed assertion or source-backed non-goal.
- A promoted learning must set `promoted_to` to an exact `SKILL.md` section, checklist item, contract matrix, or benchmark assertion so future lookup can find the active rule.
- When a learning is promoted, scan already migrated sibling components and shared local primitives for the same failure class before final acceptance. A promoted token, layout, verifier, or demo-parity rule is incomplete if another migrated component in the same target still violates it.
- The backfill scan must record scope, files/components matched, fixes applied, and source-backed non-goals. A generic statement such as "checked siblings" is not sufficient evidence.
- Theme-token and CSS-variable color learnings must backfill both runtime component code and emitted CSS rules, then verify computed colors after styles settle.

Promote a learning into this skill when:

- The same issue appears in two components or two target projects.
- The fix changes how source evidence should be collected.
- The issue reveals a missing cross-project edge-case gate.
- The issue reveals a recurring Tailwind v4, shadcn, Radix, SSR, portal, accessibility, keyboard, token, or ConfigProvider pitfall.
- The issue caused a false pass in tests or benchmark coverage.

Keep one-off target-specific fixes in target repo learnings unless they expose a general rule.

## Benchmark and Viewer Gate

For skill development or migrations claiming full Ant compatibility, create a reviewable benchmark workspace before calling the migration complete.

For real component migrations, make the benchmark/viewer scope decision explicit in the compatibility contract:

- Generate benchmark/viewer artifacts when the migration claims full Ant compatibility, when the user asks for benchmark/viewer coverage, or when visual/layout parity is a primary acceptance risk.
- For narrow migrations, `Benchmark/viewer scope decided` may be `source-backed non-goal`, but only when the contract names the narrowed scope and maps every skipped benchmark assertion to repo tests, browser assertions, or explicit non-goals.
- A viewer is evidence for human review. It never replaces type tests, behavior tests, browser geometry assertions, accessibility tests, no-leakage checks, or contract closure.

## Benchmark Requirements

- Add objective assertions to `evals/evals.json` for every migration requirement that must not regress.
- Include assertions for all 15 cross-project edge-case gate items.
- Include assertions that Ant `style/**` branches and delegated style branches were inspected and converted into a styling behavior matrix.
- Include visual-token assertions for semantic colors, text metrics, marker/icon size, filled versus outlined state, connector color/width, overlay shadows, and spacing tokens as applicable.
- Include layout and visual ownership assertions for flex/min-size semantics, type/variant/mode branch behavior, connector status ownership, CSS variable containing-block ownership, responsive media ownership, and attached visual envelope geometry when applicable.
- Include Tailwind-first styling assertions that fail when static theme-owned styles are implemented as a recreated component token map instead of Tailwind/shadcn utilities, unless each retained variable has a compatibility-bridge reason.
- Include semantic-slot geometry assertions when Ant styles place slots independently.
- Include token-unit assertions when source dimensions are pixel-based.
- Include connector ownership and endpoint assertions for lines, tracks, bars, handles, separators, and underlines.
- Include CSS containing-block assertions for positioned visual elements.
- Include viewer-shell assertions when benchmark demos are used for visual acceptance.
- Include demo-source parity assertions.
- Include no-Ant-CSS-leakage assertions.
- Include contract-matrix assertions for docs demo parity and positioning ownership.
- Include learning-regression closure assertions.
- Include independent verifier assertions that fail when output claims completion without a named custom agent or equivalent fresh-context generic subagent report, verifier-attributed checklist pass decisions, dispatch mode, fallback reason, and closure for rejected rows.
- Include side-branch audit assertions for applicable source/API, style graph, docs demo parity, browser geometry, contract closure, and learning-regression branches.
- Include false-pass prevention assertions that fail when a checklist row is self-certified by the implementer or supported only by screenshots/snapshots.
- Include theme inheritance, Tailwind-first ownership, CSS-variable color emission, transition-settle, and promoted-learning backfill assertions when those learning classes apply.
- Include both `with_skill` and `without_skill` or old-skill baseline runs when evaluating the skill itself.
- Put each run's `grading.json` beside its `outputs/` directory and use expectation objects with exact `text`, `passed`, and `evidence` fields.
- Generate `benchmark.json`, `benchmark.md`, and static `review.html` with skill-creator tooling when available.
- Label scaffolded coverage benchmarks clearly. Do not present a coverage scaffold as a live executor benchmark.
- Treat any failed assertion or applicable uncovered edge case in the `with_skill` run as a blocker unless the user explicitly narrows compatibility scope.
- Grade deprecated API assertions as decision coverage: output must identify deprecated APIs and record whether they are not migrated by default or explicitly requested for legacy compatibility.
- For real component migration, every benchmark assertion should map to a contract row, test, or documented source-backed non-goal.
