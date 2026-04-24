# Testing and Acceptance

Use this reference for red tests, browser evidence, acceptance checklist closure, and final report format.

## Testing Requirements

For each component, create failing tests before implementation:

1. Type/API tests for exported types, compound members, current public props, callback signatures, and ref/imperative surfaces.
2. Rendering tests for default markup, native prop passthrough, `className`, `rootClassName`, `style`, `classNames`, and `styles`.
3. Behavior tests ported from Ant Design `__tests__` for events, controlled state, disabled/loading states, keyboard behavior, timers, portals, and warnings.
4. Ref/static/warning tests for applicable components: `forwardRef`, imperative methods, compound static members, native prop passthrough, and developer warnings must either have assertions or a source-backed non-goal.
5. Docs demo parity checks that map every relevant `components/<component>/demo/*.tsx` source fixture to a target demo/story/viewer surface and assert the source docs page shell, including component-specific one-column/two-column grid, card width, spacing, demo order, and repeated example grouping.
6. Styling behavior tests for every applicable Ant `style/**` branch and delegated style branch: orientation, mode, placement, variant, status, RTL, token units, theme-derived color variables, semantic-slot placement, baseline/axis alignment, connector endpoints, containing blocks, and responsive layout.
7. Layout and visual ownership tests for six high-risk styling failures: flex/min-size text collapse, type/variant/mode branch reuse, connector status source, CSS variable containing-block ownership, SSR-safe responsive media behavior, and attached visual envelope/center/inset.
8. Browser assertions for every applicable absolute, fixed, sticky, transform-based, or inset-based visual element: assert `offsetParent`, containing block, endpoint, centerline, placement side, or baseline as appropriate.
9. No-leakage checks for target source and CSS: fail if runtime styling uses `ant-*` selectors, `--ant-*` variables, Ant generated CSS imports, or Ant prefix selectors.
10. Viewer shell checks when a demo viewer is part of acceptance: assert root font, color scheme, global alignment, heading/body resets, component-specific docs grid/card layout, and starter-template CSS do not mask component geometry.
11. Accessibility tests using the target repo's existing a11y tooling where available.
12. Edge-case gate mapping tests that prove every applicable risk is covered by a test, contract row, or source-backed non-goal.
13. Browser or visual checks for interactive components after unit tests pass.
14. Independent verifier subagent checks for browser/demo parity, layout geometry, portal behavior, viewer-shell isolation, and learning-regression closure. The verifier must use source evidence and rendered DOM/CSS to challenge the implementer's checklist status.
15. False-pass prevention assertions for every user-visible mismatch class found during migration. At least one repeatable assertion must fail for the broken geometry, token, event, portal, or demo-parity condition that was observed.
16. Theme inheritance checks for component-private variables that represent colors: assert light/dark or user theme overrides change computed colors through shadcn/Tailwind tokens, not through hard-coded Ant values in runtime code.
17. CSS-variable color rule checks: when a migrated component uses a CSS variable for color, assert an emitted color rule exists and computed color follows the variable in dev, build, and browser tests.
18. Transition-settle checks for computed-style and geometry assertions: if the inspected surface uses `transition-*` or animation utilities, disable transitions in the test surface or wait for two animation frames after style/theme changes before reading computed style, color, size, or connector geometry.
19. Tailwind-first styling ownership checks: the contract must classify retained component CSS variables as `runtime prop bridge`, `user override`, `semantic slot bridge`, `shared geometry`, `connector endpoint`, or `not expressible as static Tailwind`. Static theme color, spacing, border, radius, and typography values should be direct Tailwind utilities or source-backed exceptions.

Do not rely on snapshots alone. Use assertions that describe public behavior.

When unit tests and browser tests coexist, configure runner boundaries before the final loop. Keep Vitest/Jest includes scoped to unit-test files and Playwright/Cypress specs in their own directory. Do not let lint scan `test-results`, `playwright-report`, screenshots, or traces.

## Independent Verification and Side Branches

Use the bundled custom agents for work that benefits from separation between implementation and verification. When a bundled custom agent is unavailable in the current session, spawn a fresh-context generic subagent with the same role, scope, required evidence, and output fields. Record each branch in the contract's verification ownership table, including dispatch mode and fallback reason.

```text
┌────────────────────────────┐
│ Audit/verifier branch       │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ custom-agent callable       │
├────────────────────────────┤
│ else generic-subagent       │
├────────────────────────────┤
│ else self-review-blocked    │
└────────────────────────────┘
```

| Branch | Custom agent or generic fallback role | Use when | Expected output |
|---|---|---|---|
| Source/API audit | `antd_source_auditor` or `source-api-audit generic subagent` | Public props, exports, defaults, rc delegation, or semantic DOM are non-trivial | Source-backed API rows and missing-surface findings |
| Style graph audit | `antd_style_graph_auditor` or `style-graph-audit generic subagent` | Layout, tokens, status, variant, connector, overlay, or responsive styling matters | Style matrix rows and source CSS behavior notes |
| Docs demo parity audit | `antd_demo_parity_auditor` or `demo-parity-audit generic subagent` | Docs demos are part of acceptance | Source demo list, target fixture mapping, shell/grid/card parity findings |
| Browser geometry verifier | `antd_browser_geometry_verifier` or `browser-geometry-verifier generic subagent` | Visual position, connectors, portals, focus rings, underlines, handles, or overlays can drift | DOM/CSS measurements that try to falsify pass claims |
| Contract closure audit | `antd_contract_closure_verifier` or `contract-closure-verifier generic subagent` | The migration is broad, visual, or user-facing | Checklist rows that are pass, source-backed non-goal, or blocked with exact reasons |
| Learning regression audit | `antd_learning_promoter` or `learning-regression generic subagent` | A user correction, verifier finding, or repeated issue generated a learning | Regression assertion mapped to test, contract row, checklist row, benchmark assertion, or source-backed non-goal |

Rules:

- The implementer may not be the final verifier for browser/demo parity, layout geometry, portal behavior, viewer shell isolation, or learning-regression closure.
- Final acceptance requires a fresh-context independent verifier report from either the named custom agent or an equivalent generic subagent. If no subagent capability is available, the migration remains `Migration blocked`; self-audit may attach risk evidence but cannot create a verifier pass.
- Independent verifier output must include either `no findings after source-backed checks` or a list of findings with closure status.
- A verifier finding cannot be closed by weakening the assertion that exposed it. Add or fix the implementation, then rerun the relevant assertion.
- Any `generic-subagent` fallback must use the same table and record `custom-agent-unavailable` as the fallback reason. Any `self-review-blocked` evidence must record `subagent-unavailable` and keep protected rows blocked.
- A checklist row cannot be `pass` when the only evidence is that the implementer looked at the result or a snapshot exists.

## Browser Evidence Priority

Use the user's actual visible browser surface before calling any migrated UI complete.

```text
┌─────────────────────────────┐
│ Codex desktop available?     │
└──────────────┬──────────────┘
       yes     ▼      no
┌────────────────────┐  ┌────────────────────────┐
│ Codex in-app browser│  │ Playwright or agent     │
│ screenshot + inspect│  │ browser fallback        │
└──────────┬─────────┘  └───────────┬────────────┘
           ▼                         ▼
┌───────────────────────────────────────────────┐
│ Automated assertions remain required           │
│ geometry, interaction, a11y, types, lint/build  │
└───────────────────────────────────────────────┘
```

Priority rules:

1. In Codex desktop, use the Codex in-app browser through the Browser Use `iab` backend for visual inspection and screenshots before final acceptance.
2. Use Playwright tests for repeatable assertions, but do not substitute a passing Playwright run for available in-app browser evidence.
3. Outside Codex desktop, or when the in-app browser tool is unavailable after setup, use Playwright or agent-browser and record the fallback reason.
4. For layout migrations, include a visible screenshot or in-app browser observation covering the stress demo that previously failed, not only the happy path.
5. If a user says the component looks far from AntD, add browser assertions for the exact rendered differences instead of treating it as subjective feedback.

## Verification Loop

Use the target repo commands. Verification is not a reporting exercise; every applicable checklist item must be implemented as a contract row, test, browser assertion, source-backed non-goal, or explicit blocker.

```text
1. Contract complete -> every public API row has source evidence
2. Checklist mapped -> every applicable item has implementation and evidence targets
3. Red tests written -> tests fail for missing component behavior
4. Implementation complete -> tests pass without weakening assertions
5. Typecheck -> exported API and consuming examples compile
6. Lint/format -> target repo standards pass
7. Automated browser check -> repeatable behavior is proven
8. Independent verifier check -> a fresh-context subagent probes the migrated demos against source evidence and tries to falsify the checklist
9. False-pass prevention check -> assertions prove the previously observed mismatch class would fail
10. Codex in-app browser check -> affected demos inspected when available
11. Checklist closed -> no applicable item remains unimplemented
```

If a test cannot be ported because architecture differs, document the replacement assertion and source reason.

## Independent Verifier Report

The verifier report is required before final acceptance.

```markdown
## Independent verifier report

Verifier: <subagent id and model, or self-audit when no subagent exists>
Dispatch mode: <custom-agent | generic-subagent | self-review-blocked>
Custom agent: <antd_browser_geometry_verifier | antd_contract_closure_verifier | not available>
Fallback reason: <none | custom-agent-unavailable | subagent-unavailable>
Scope audited: <component surfaces, demos, contracts, tests, browser surfaces>
Inputs inspected: <contract paths, source paths, target paths, commands, screenshots>
Falsification attempts:
- <checklist row>: <source evidence checked> -> <target/browser/assertion checked> -> <pass|fail>
Rejected checklist rows:
- <row or none>
Required fixes:
- <fix or none>
Assertions added or confirmed:
- <test/browser assertion path or source-backed non-goal>
Final verdict: <verified-pass | blocked>
Risk note: <none | no independent subagent available; self-audit only>
```

The verifier must reject any checklist row with blank evidence, placeholder evidence, implementation-only evidence, or no verifier attribution. A `verified-pass` verdict is valid only after required fixes are implemented and rerun.

## Acceptance Checklist

Before saying `Migration completed`, create and close this checklist in the migration contract or final report. Each row must include `status`, `evidence`, `implementation`, and `verified by`. Use only `pass`, `not applicable`, `source-backed non-goal`, or `blocked`.

```markdown
## Acceptance checklist
| Item | Status | Evidence | Implementation | Verified by |
|---|---|---|---|---|
| Target stack verified | <status> | <package/config paths> | <setup or non-goal> | <verifier subagent or source-backed reviewer> |
| Ant source API traced | <status> | <source paths/lines> | <type/API tests or contract rows> | <verifier subagent or source-backed reviewer> |
| Deprecated API decision recorded | <status> | <source paths/lines> | <contract decision> | <verifier subagent or source-backed reviewer> |
| ConfigProvider/default context checked | <status> | <source paths/lines> | <adapter, test, or non-goal> | <verifier subagent or source-backed reviewer> |
| rc/shared primitive delegation checked | <status> | <source paths/lines> | <adapter/test/style matrix row> | <verifier subagent or source-backed reviewer> |
| Semantic DOM slots mapped | <status> | <semantic tests/docs> | <data-slot/classNames/styles tests> | <verifier subagent or source-backed reviewer> |
| Docs demos copied as fixtures | <status> | <demo source paths> | <docs demo parity matrix + viewer/story/demo assertions> | <verifier subagent or source-backed reviewer> |
| Style graph fully translated | <status> | <style import graph paths> | <styling behavior matrix + tests> | <verifier subagent or source-backed reviewer> |
| Layout and visual ownership verified | <status> | <layout ownership matrix paths> | <six-risk assertions or source-backed non-goals> | <verifier subagent or source-backed reviewer> |
| Tailwind-first styling verified | <status> | <target component/CSS paths> | <utility-first audit + retained variable reason table> | <verifier subagent or source-backed reviewer> |
| Theme token inheritance verified | <status> | <target theme/global CSS paths> | <light/dark/user-theme computed-style assertions + CSS emission checks> | <verifier subagent or source-backed reviewer> |
| Token units preserved | <status> | <token source paths> | <computed token assertions> | <verifier subagent or source-backed reviewer> |
| Positioned elements traced | <status> | <render + style paths> | <positioning matrix + offsetParent/containing-block assertions> | <verifier subagent or source-backed reviewer> |
| Connectors/tracks/separators asserted | <status> | <render + style paths> | <endpoint/centerline assertions> | <verifier subagent or source-backed reviewer> |
| Ant CSS leakage prevented | <status> | <target source/CSS paths> | <CSS ownership audit + no-leakage check> | <verifier subagent or source-backed reviewer> |
| Viewer shell/global CSS isolated | <status> | <viewer/global CSS paths> | <viewer shell audit + browser/style assertion> | <verifier subagent or source-backed reviewer> |
| Refs and imperative API verified | <status> | <source paths/docs> | <type/runtime tests or non-goal> | <verifier subagent or source-backed reviewer> |
| Runtime warnings decided | <status> | <source tests/docs> | <warning tests or decision table> | <verifier subagent or source-backed reviewer> |
| Controlled/uncontrolled behavior verified | <status> | <source tests/docs> | <behavior tests or non-goal> | <verifier subagent or source-backed reviewer> |
| Keyboard/focus/IME behavior verified | <status> | <source tests/docs> | <interaction tests or non-goal> | <verifier subagent or source-backed reviewer> |
| Portal/z-index/stacking behavior verified | <status> | <source tests/docs> | <browser tests or non-goal> | <verifier subagent or source-backed reviewer> |
| Locale/date/time behavior verified | <status> | <source tests/docs> | <tests or non-goal> | <verifier subagent or source-backed reviewer> |
| Accessibility verified | <status> | <source tests/docs> | <a11y tests> | <verifier subagent or source-backed reviewer> |
| Browser visual evidence captured | <status> | <Codex in-app screenshot/observation or fallback> | <browser check> | <verifier subagent or source-backed reviewer> |
| Agent execution mode recorded | <status> | <verification ownership table + verifier report> | <custom-agent/generic-subagent/self-review-blocked decision and fallback reason> | <verifier subagent or source-backed reviewer> |
| Independent verifier completed | <status> | <subagent report path or notes> | <falsification findings resolved or blocker> | <fresh-context verifier subagent> |
| Subagent side-branch audits completed | <status> | <subagent notes or dispatch fallback reason> | <branch outputs merged into contract/tests or blocker> | <verifier subagent or source-backed reviewer> |
| False-pass prevention assertions landed | <status> | <failing class and assertion paths> | <repeatable assertions that would fail for the observed mismatch> | <verifier subagent or source-backed reviewer> |
| Benchmark/viewer gate aligned | <status> | <eval/grading paths> | <assertion mapping or scoped non-goal> | <verifier subagent or source-backed reviewer> |
| Benchmark/viewer scope decided | <status> | <contract row or benchmark paths> | <full benchmark/viewer or scoped non-goal> | <verifier subagent or source-backed reviewer> |
| Learnings captured and promoted | <status> | <learning paths> | <skill/rule update or local-learning> | <verifier subagent or source-backed reviewer> |
| Learning regression assertions landed | <status> | <learning paths> | <test/benchmark/contract/checklist mapping or non-goal> | <verifier subagent or source-backed reviewer> |
```

Completion rule:

- `Migration completed` is allowed only when every applicable checklist row is `pass` or `source-backed non-goal`.
- If any row is `blocked`, say `Migration blocked` and name the exact blocker.
- If any applicable row has no implementation, implement the missing test/assertion/contract row first.
- A visual screenshot is evidence, not a substitute for repeatable assertions when the behavior can be measured.
- A passing unit test is not enough when checklist rows require browser geometry, computed style, containing block, portal, or demo-source parity evidence.
- A checklist that was closed only by the implementer is not closed for browser/demo parity, layout geometry, portal behavior, viewer shell isolation, or learning-regression closure.
- `False-pass prevention assertions landed` is `pass` only when the contract names the mismatch class and the test or browser assertion that would catch it.
- `Tailwind-first styling verified` is `pass` only when retained component variables have explicit compatibility reasons and static theme-owned values use Tailwind/shadcn utilities or a source-backed exception.

## Final Response Format

```markdown
Migration completed: <Component>

Files changed:
- <path>

Compatibility evidence:
- Props covered: <n>/<n>
- Behavior tests ported: <n>
- Edge-case gate: <n>/15 covered, <n> not applicable
- Deprecated API decision: <not migrated by default | legacy compatibility requested>
- Tailwind-first styling: <utilities used for static styles; retained variables and reasons>
- Learnings captured: <n> entries, <n> promoted to skill rules
- Known source-backed gaps: <none or list>

Verification:
- <command>: pass
- <command>: pass

Browser evidence:
- Codex in-app browser: <screenshot/observation or unavailable>
- Playwright fallback: <used/not used and reason>
- Agent-browser fallback: <used/not used and reason>

Independent verifier:
- Verifier: <fresh-context subagent id/model or self-audit when no subagent exists>
- Dispatch mode: <custom-agent | generic-subagent | self-review-blocked>
- Fallback reason: <none | custom-agent-unavailable | subagent-unavailable>
- Final verdict: <verified-pass | blocked>
- Rejected rows: <none or list>
- Required fixes: <none or list>

Acceptance checklist:
- Target stack verified: <pass | not applicable | source-backed non-goal>
- Ant source API traced: <pass | not applicable | source-backed non-goal>
- Deprecated API decision recorded: <pass | not applicable | source-backed non-goal>
- ConfigProvider/default context checked: <pass | not applicable | source-backed non-goal>
- rc/shared primitive delegation checked: <pass | not applicable | source-backed non-goal>
- Semantic DOM slots mapped: <pass | not applicable | source-backed non-goal>
- Docs demos copied as fixtures: <pass | not applicable | source-backed non-goal>
- Style graph fully translated: <pass | not applicable | source-backed non-goal>
- Layout and visual ownership verified: <pass | not applicable | source-backed non-goal>
- Tailwind-first styling verified: <pass | not applicable | source-backed non-goal>
- Theme token inheritance verified: <pass | not applicable | source-backed non-goal>
- Token units preserved: <pass | not applicable | source-backed non-goal>
- Positioned elements traced: <pass | not applicable | source-backed non-goal>
- Connectors/tracks/separators asserted: <pass | not applicable | source-backed non-goal>
- Ant CSS leakage prevented: <pass | not applicable | source-backed non-goal>
- Viewer shell/global CSS isolated: <pass | not applicable | source-backed non-goal>
- Refs and imperative API verified: <pass | not applicable | source-backed non-goal>
- Runtime warnings decided: <pass | not applicable | source-backed non-goal>
- Controlled/uncontrolled behavior verified: <pass | not applicable | source-backed non-goal>
- Keyboard/focus/IME behavior verified: <pass | not applicable | source-backed non-goal>
- Portal/z-index/stacking behavior verified: <pass | not applicable | source-backed non-goal>
- Locale/date/time behavior verified: <pass | not applicable | source-backed non-goal>
- Accessibility verified: <pass | not applicable | source-backed non-goal>
- Browser visual evidence captured: <pass | not applicable | source-backed non-goal>
- Agent execution mode recorded: <pass | not applicable | source-backed non-goal>
- Independent verifier completed: <pass | not applicable | source-backed non-goal>
- Subagent side-branch audits completed: <pass | not applicable | source-backed non-goal>
- False-pass prevention assertions landed: <pass | not applicable | source-backed non-goal>
- Benchmark/viewer gate aligned: <pass | not applicable | source-backed non-goal>
- Benchmark/viewer scope decided: <pass | not applicable | source-backed non-goal>
- Learnings captured and promoted: <pass | not applicable | source-backed non-goal>
- Learning regression assertions landed: <pass | not applicable | source-backed non-goal>
```

When `Benchmark/viewer scope decided` is `source-backed non-goal`, include the exact contract row that justifies the narrowed scope.

If any acceptance row is `blocked`, use:

```markdown
Migration blocked: <Component>

Blocker:
- <checklist item>: <why blocked and what is needed>

Completed evidence:
- <short list of completed items>
```
