# Testing and Acceptance

Use this reference for red tests, browser evidence, independent verification, acceptance checklist closure, and final response format.

## Testing Requirements

For each component, create failing tests before implementation:

1. Type/API tests for exports, compound members, current public props, callbacks, and ref/imperative surfaces.
2. Rendering tests for default markup, native prop passthrough, `className`, `style`, slot class/style APIs, and data attributes.
3. Behavior tests ported from source docs/tests for events, controlled state, disabled/loading states, keyboard behavior, timers, portals, and warnings.
4. Docs demo parity checks mapping every relevant source demo/example to a target demo/story/viewer surface.
5. Styling behavior tests for style/theme branches: orientation, mode, placement, variant, status, RTL, token units, semantic-slot placement, baseline/axis alignment, connectors, containing blocks, and responsive layout.
6. Tailwind-first styling ownership checks: retained component variables must be classified as runtime prop bridge, user override, semantic slot bridge, shared geometry, connector endpoint, or not expressible as static Tailwind.
7. No-leakage checks using selected profile deny patterns.
8. Browser geometry assertions for absolute, fixed, sticky, transform-based, inset-based, connector, portal, focus-ring, handle, or overlay elements.
9. Viewer shell checks when demo viewer is part of acceptance.
10. Accessibility checks using target repo tooling where available.
11. Edge-case gate mapping proving every applicable risk is covered by a test, contract row, or source-backed non-goal.
12. Independent verifier subagent checks for demo parity, layout geometry, portal behavior, viewer shell isolation, contract closure, and learning/profile closure.
13. False-pass prevention assertions for every user-visible mismatch class found during migration.
14. Theme inheritance and CSS-variable color emission checks when component variables represent colors.
15. Transition-settle checks before reading computed style or geometry when transitions/animations apply.

Snapshots alone are insufficient.

## Independent Verification and Side Branches

Use bundled custom agents when callable. If unavailable, spawn a fresh-context generic subagent with the same role and output contract. Record dispatch mode and fallback reason.

| Branch | Custom agent or fallback role | Use when | Expected output |
|---|---|---|---|
| Profile discovery | `ui_profile_builder` or `profile-builder generic subagent` | Source library has no matching profile | Temporary profile and missing evidence |
| Source/API audit | `ui_source_auditor` or `source-api-audit generic subagent` | Public API, defaults, refs, internal delegation matter | Source-backed API rows and blockers |
| Style graph audit | `ui_style_graph_auditor` or `style-graph-audit generic subagent` | Layout, tokens, variants, connector, overlay, responsive styling matters | Style matrix and geometry assertions |
| Docs demo parity audit | `ui_demo_parity_auditor` or `demo-parity-audit generic subagent` | Demos/examples are acceptance evidence | Source demo list and target mapping findings |
| Browser geometry verifier | `ui_browser_geometry_verifier` or `browser-geometry-verifier generic subagent` | Visual geometry or computed style can drift | DOM/CSS measurements falsifying pass claims |
| Contract closure audit | `ui_contract_closure_verifier` or `contract-closure-verifier generic subagent` | Migration is broad, visual, or user-facing | Checklist pass/non-goal/blocked decisions |
| Learning/profile audit | `ui_learning_promoter` or `learning-regression generic subagent` | User correction, test failure, or repeated issue occurs | Regression assertion and profile/core rule updates |

Protected checklist rows cannot be passed solely by the implementer.

## Browser Evidence Priority

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

## Independent Verifier Report

```markdown
## Independent verifier report

Verifier: <subagent id and model, or self-audit when no subagent exists>
Dispatch mode: <custom-agent | generic-subagent | self-review-blocked>
Custom agent: <ui_browser_geometry_verifier | ui_contract_closure_verifier | not available>
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

## Acceptance Checklist

Each row must include `status`, `evidence`, `implementation`, and `verified by`. Use only `pass`, `not applicable`, `source-backed non-goal`, or `blocked`.

```markdown
## Acceptance checklist
| Item | Status | Evidence | Implementation | Verified by |
|---|---|---|---|---|
| Target stack verified | <status> | <package/config paths> | <setup or non-goal> | <verifier> |
| Profile decision recorded | <status> | <profile path or temporary profile> | <profile decision table> | <verifier> |
| Library discovery evidence complete | <status> | <docs/source/package paths> | <discovery table> | <verifier> |
| Source API traced | <status> | <source paths/lines> | <type/API tests or contract rows> | <verifier> |
| Deprecated/legacy API decision recorded | <status> | <source paths/lines> | <contract decision> | <verifier> |
| Provider/default context checked | <status> | <source paths/lines> | <adapter, test, or non-goal> | <verifier> |
| Internal primitive delegation checked | <status> | <source paths/lines> | <adapter/test/style row> | <verifier> |
| Semantic DOM slots mapped | <status> | <semantic tests/docs> | <data-slot/slot API tests> | <verifier> |
| Docs demos copied as fixtures | <status> | <demo source paths> | <demo parity matrix + assertions> | <verifier> |
| Style graph fully translated | <status> | <style/theme graph paths> | <styling behavior matrix + tests> | <verifier> |
| Layout and visual ownership verified | <status> | <layout matrix paths> | <risk assertions or non-goals> | <verifier> |
| Tailwind-first styling verified | <status> | <target component/CSS paths> | <utility-first audit + retained variable reasons> | <verifier> |
| Theme token inheritance verified | <status> | <target theme/global CSS paths> | <computed-style assertions> | <verifier> |
| Token units preserved | <status> | <token source paths> | <computed token assertions> | <verifier> |
| Positioned elements traced | <status> | <render + style paths> | <positioning matrix + browser assertions> | <verifier> |
| Connectors/tracks/separators asserted | <status> | <render + style paths> | <endpoint/centerline assertions> | <verifier> |
| Source CSS leakage prevented | <status> | <target paths + profile deny patterns> | <no-leakage check> | <verifier> |
| Viewer shell/global CSS isolated | <status> | <viewer/global CSS paths> | <viewer shell audit> | <verifier> |
| Refs and imperative API verified | <status> | <source paths/docs> | <type/runtime tests or non-goal> | <verifier> |
| Runtime warnings decided | <status> | <source tests/docs> | <warning tests or decision table> | <verifier> |
| Controlled/uncontrolled behavior verified | <status> | <source tests/docs> | <behavior tests or non-goal> | <verifier> |
| Keyboard/focus/IME behavior verified | <status> | <source tests/docs> | <interaction tests or non-goal> | <verifier> |
| Portal/z-index/stacking behavior verified | <status> | <source tests/docs> | <browser tests or non-goal> | <verifier> |
| Locale/date/time behavior verified | <status> | <source tests/docs> | <tests or non-goal> | <verifier> |
| Accessibility verified | <status> | <source tests/docs> | <a11y tests> | <verifier> |
| Browser visual evidence captured | <status> | <Codex in-app or fallback> | <browser check> | <verifier> |
| Agent execution mode recorded | <status> | <dispatch log + verifier report> | <dispatch decision> | <verifier> |
| Independent verifier completed | <status> | <subagent report> | <findings resolved or blocker> | <fresh-context verifier> |
| Subagent side-branch audits completed | <status> | <subagent notes> | <branch outputs merged> | <verifier> |
| False-pass prevention assertions landed | <status> | <assertion paths> | <repeatable assertions> | <verifier> |
| Benchmark/viewer scope decided | <status> | <contract row or benchmark paths> | <full artifacts or non-goal> | <verifier> |
| Learnings/profile updates captured | <status> | <learning/profile paths> | <rule update or local learning> | <verifier> |
| Learning regression assertions landed | <status> | <learning paths> | <test/contract/checklist mapping> | <verifier> |
```

## Final Response Format

```markdown
Migration completed: <Source Library> <Component>

Files changed:
- <path>

Compatibility evidence:
- Profile decision: <profile path | temporary profile>
- Props covered: <n>/<n>
- Behavior tests ported: <n>
- Edge-case gate: <n>/15 covered, <n> not applicable
- Deprecated/legacy API decision: <not migrated by default | legacy compatibility requested>
- Tailwind-first styling: <utilities used; retained variables and reasons>
- Known source-backed gaps: <none or list>

Verification:
- <command>: pass

Browser evidence:
- Codex in-app browser: <screenshot/observation or unavailable>
- Playwright fallback: <used/not used and reason>

Independent verifier:
- Verifier: <fresh-context subagent id/model>
- Dispatch mode: <custom-agent | generic-subagent | self-review-blocked>
- Fallback reason: <none | custom-agent-unavailable | subagent-unavailable>
- Final verdict: <verified-pass | blocked>
- Rejected rows: <none or list>
```

If any acceptance row is `blocked`, use `Migration blocked` and name the exact blocker.
