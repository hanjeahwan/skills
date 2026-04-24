# Compatibility Contract Template

Create a contract before implementation. Save it as `docs/migrations/ui/<source-library>-<component>.md` when the target repo has docs; otherwise include it in the final report.

```markdown
# <Source Library> <Component> Compatibility Contract

Source library: <library>
Source profile: <profiles/<id>.md | temporary profile in this contract>
Source evidence version: <version, commit, docs version, or package version>
Target files: <planned files>

## Profile decision
| Library signal | Matched profile | Decision | Evidence |
|---|---|---|---|

## Library discovery evidence
| Required field | Evidence | Status |
|---|---|---|
| Source docs/source/package | <path/url/package> | <pass|blocked> |
| API extraction path | <source> | <pass|blocked> |
| Demo/examples path | <source> | <pass|blocked> |
| Theme/token model | <source> | <pass|blocked> |
| Slot/class/style API | <source> | <pass|blocked> |
| Internal primitives | <source or non-goal> | <pass|source-backed non-goal|blocked> |
| Deprecated/legacy policy | <source> | <pass|blocked> |
| Source CSS deny patterns | <profile regexes> | <pass|blocked> |

## Prior learning applied
| Learning ID/title | Trigger match | Edge gates | Source | Applies? | Action |
|---|---|---|---|---|---|

## Public exports
| Export | Type/value | Source evidence |
|---|---|---|

## Props
| Prop | Type | Default | Behavior | Source evidence |
|---|---|---|---|---|

## Semantic DOM and styling hooks
| Slot | Source hook/API | Target data-slot/class/style | Source evidence |
|---|---|---|---|

## Runtime behavior
| Behavior | Parity test | Source evidence |
|---|---|---|

## Styling behavior matrix
| Source style branch | Target Tailwind/CSS-variable behavior | Regression assertion | Source evidence |
|---|---|---|---|

## Layout and visual ownership matrix
| Ownership risk | Applies? | Source owner/evidence | Target owner | Required assertion |
|---|---|---|---|---|
| Flex and min-size semantics | <status> | <source> | <target> | <assertion> |
| Type/variant/mode style branch | <status> | <source> | <target> | <assertion> |
| Connector or track status source | <status> | <source> | <target> | <assertion> |
| CSS variable containing-block owner | <status> | <source> | <target> | <assertion> |
| Responsive media ownership | <status> | <source> | <target> | <assertion> |
| Attached visual envelope | <status> | <source> | <target> | <assertion> |
| Tailwind-first styling ownership | <status> | <source> | <target> | <assertion> |
| Theme-token color ownership | <status> | <source> | <target> | <assertion> |
| CSS-variable color emission | <status> | <source> | <target> | <assertion> |

## Docs demo parity matrix
| Source demo/example | Target demo/story/viewer | Source display structure | Preserved? | Regression assertion |
|---|---|---|---|---|

## Positioning and containing-block matrix
| Element | Source DOM/style evidence | Semantic parent | Positioned ancestor/offsetParent | Containing block | Non-positioned wrapper requirement | Regression assertion |
|---|---|---|---|---|---|---|

## CSS ownership and source leakage audit
| Target surface | Forbidden source styling | Allowed source-evidence location | Check command or assertion |
|---|---|---|---|

## Tailwind-first styling audit
| Target surface | Static styles expressed as Tailwind utilities | Retained component variables | Retained variable reason | Regression assertion |
|---|---|---|---|---|

## Viewer shell and global CSS audit
| Viewer/global style surface | Risk checked | Evidence | Isolation or assertion |
|---|---|---|---|

## Refs, static members, and imperative API
| API surface | Source evidence | Target behavior | Regression assertion |
|---|---|---|---|

## Runtime warnings and developer feedback
| Warning or feedback | Source evidence | Decision | Regression assertion or non-goal |
|---|---|---|---|

## Verification ownership and subagent audit log
| Audit branch | Dispatch mode | Agent or subagent role | Owner | Source evidence checked | Verification method | Findings | Closure |
|---|---|---|---|---|---|---|---|

## Subagent dispatch log
| Branch | Dispatch mode | Agent/subagent | Fallback reason | Output location or summary |
|---|---|---|---|---|

## False-pass prevention assertions
| Mismatch class | How it could falsely pass | Source evidence | Assertion that catches it | Owner |
|---|---|---|---|---|

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

## Accessibility and keyboard behavior
| Behavior | Expected result | Source evidence |
|---|---|---|

## Cross-project edge-case gate
| Edge case | Applies? | Evidence | Migration action |
|---|---|---|---|

## Deprecated API decision
| Deprecated/legacy API | Source evidence | Decision | Reason |
|---|---|---|---|

## Deliberate non-goals
| Item | Reason | User approval |
|---|---|---|

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

## Contract Closure Rules

- The contract is incomplete until profile decision and library discovery evidence are recorded.
- Every implemented public behavior must have source evidence.
- Every applicable matrix must map to a test, browser assertion, benchmark assertion, contract row, or source-backed non-goal.
- The Tailwind-first audit must justify retained component CSS variables. Variables without compatibility reasons must be replaced by Tailwind utilities or marked as source-backed exceptions.
- The source leakage audit must use deny patterns from the selected profile.
- The verification ownership table and subagent dispatch log must identify dispatch mode and verifier attribution.
- The independent verifier report must come from a named custom agent or equivalent fresh-context generic subagent before final acceptance. If no subagent capability exists, protected rows remain `blocked`.
- Verifier findings close only by fixing implementation, adding source-backed non-goal, or recording blocker. Do not close by weakening assertions.

