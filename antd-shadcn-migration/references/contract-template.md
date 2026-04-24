# Compatibility Contract Template

Create a contract before implementation. Save it in a repo-appropriate location such as `docs/migrations/antd/<component>.md` when the target repo has docs; otherwise include it in the final report.

Use this structure:

```markdown
# Ant Design <Component> Compatibility Contract

Source repo: D:/dev/github/ant-design
Source version: <package.json version or commit>
Target files: <planned files>

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
| Slot | classNames key | styles key | DOM location | Source evidence |
|---|---|---|---|---|

## Runtime behavior
| Behavior | Parity test | Source evidence |
|---|---|---|

## Styling behavior matrix
| Source style branch | Target Tailwind/CSS-variable behavior | Regression assertion | Source evidence |
|---|---|---|---|

## Layout and visual ownership matrix
| Ownership risk | Applies? | Source owner/evidence | Target owner | Required assertion |
|---|---|---|---|---|
| Flex and min-size semantics | <status> | <flex-grow/shrink/basis/min-width/overflow source> | <target classes/CSS vars> | <text rect, wrap, overflow, or overlap assertion> |
| Type/variant/mode style branch | <status> | <branch source files> | <target branch implementation> | <branch-specific geometry/token assertion> |
| Connector or track status source | <status> | <current/previous/next/source status evidence> | <target status owner> | <computed color/status and endpoint assertion> |
| CSS variable containing-block owner | <status> | <variable producer and consumer source> | <root/item/slot owner> | <computed style and containing-block assertion> |
| Responsive media ownership | <status> | <breakpoint/source media behavior> | <SSR-safe subscription or source-backed non-goal> | <viewport switch and SSR/client assertion> |
| Attached visual envelope | <status> | <progress/badge/SVG/indicator source positioning> | <target slot and containing block> | <center, inset, size envelope assertion> |

## Docs demo parity matrix
| Ant demo source | Target demo/story/viewer | Source display structure | Preserved? | Regression assertion |
|---|---|---|---|---|

## Positioning and containing-block matrix
| Element | Source DOM/style evidence | Semantic parent | Positioned ancestor/offsetParent | Containing block | Non-positioned wrapper requirement | Regression assertion |
|---|---|---|---|---|---|---|

## CSS ownership and Ant leakage audit
| Target surface | Forbidden Ant styling source | Allowed source-evidence location | Check command or assertion |
|---|---|---|---|

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
| Audit branch | Owner | Source evidence checked | Verification method | Findings | Closure |
|---|---|---|---|---|---|

## False-pass prevention assertions
| Mismatch class | How it could falsely pass | Source evidence | Assertion that catches it | Owner |
|---|---|---|---|---|

## Independent verifier report
Verifier: <subagent id and model, or user-approved fallback reviewer>
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

## Accessibility and keyboard behavior
| Behavior | Expected result | Source evidence |
|---|---|---|

## Cross-project edge-case gate
| Edge case | Applies? | Evidence | Migration action |
|---|---|---|---|

## Deprecated API decision
| Deprecated API | Source evidence | Decision | Reason |
|---|---|---|---|

## Deliberate non-goals
| Item | Reason | User approval |
|---|---|---|
```

## Contract Closure Rules

- The contract is incomplete until prior learnings have been checked.
- Every implemented public behavior must have source evidence.
- Every applicable edge-case gate item must have a migration action.
- Every benchmark/viewer scope decision must have a contract row.
- Every applicable matrix above must map to a test, browser assertion, benchmark assertion, or source-backed non-goal.
- The layout and visual ownership matrix must be filled for layout, navigation, data-display, progress, overlay, form-control, and any component with connectors, flex distribution, responsive branches, or attached visuals.
- A checklist row cannot be marked `pass` solely by the implementer when browser/demo parity, layout geometry, portal behavior, viewer shell isolation, or learning-regression closure changed; record independent verifier evidence, falsification findings, or a blocker.
- The verification ownership table must identify who implemented, who independently verified, and which side-branch audits were completed or intentionally marked source-backed non-goal.
- The false-pass prevention table must name each mismatch class found during migration and the assertion that would fail if it regressed.
- The independent verifier report must come from a fresh-context subagent before final acceptance. If the environment cannot spawn one, final status is `Migration blocked` unless the user explicitly approves a fallback reviewer path in this contract.
- If benchmark/viewer work is narrowed or skipped, add a `Deliberate non-goals` row naming the scope decision, source-backed reason, and replacement tests/assertions.

## Matrix Requirements

Docs demo parity:

- List each relevant `components/<component>/demo/*.tsx` source fixture.
- Preserve same content, grouping, repeated-data comparisons, headings, controls, dividers, custom icons, token values, and the component docs page's example shell such as one-column/two-column grid, card width, card padding, and demo order unless the contract records a source-backed reason.
- Synthetic, shortened, or nearby demos do not satisfy parity.

Positioning and containing block:

- Record semantic parent, positioned ancestor, `offsetParent`, containing block, and wrappers that must remain non-positioned.
- Apply to absolute, fixed, sticky, transform-based, inset-based, connector, popup, marker, underline, handle, overlay, and slot-placement elements.
- Regression assertions must measure geometry such as endpoint, centerline, placement side, baseline, or containing block.

Layout and visual ownership:

- Preserve Ant flex semantics before applying Tailwind shortcuts. Record `flex-grow`, `flex-shrink`, `flex-basis`, `min-width`, overflow, wrapping, and last-item behavior; assert text rectangle width/height, overflow, and overlap for layout-sensitive slots.
- Do not reuse a default branch for source `type`, `variant`, `mode`, `placement`, or `size` branches unless the source proves they share layout. Each applicable branch needs its own source evidence and assertion.
- For connectors, tracks, rails, separators, and progress bars, record whether visual status comes from current item, previous item, next item, parent state, or token state; assert computed color/status and endpoint geometry.
- CSS variables used by positioned elements must be defined on the containing block or an ancestor that actually reaches the consumer. Record producer, consumer, and containing block.
- Responsive behavior driven by JS media queries must be modeled as an SSR-safe external subscription or recorded as a source-backed non-goal; assert breakpoint switching and non-responsive opt-out where applicable.
- Attached visuals such as progress circles, badges, SVG rings, custom indicators, loading spinners, and overlays must record their owner slot, containing block, inset, center point, and size envelope.

CSS ownership and leakage:

- Target runtime styling must not use Ant `ant-*` selectors, `--ant-*` variables, generated CSS imports, or prefix selectors.
- Those strings may appear only in source-evidence docs, migration contracts, or source comments that explain rejected Ant styling.

Viewer shell and global CSS:

- Demo viewers are evidence surfaces. Their shell CSS must not mask component geometry.
- Check root font, color scheme, global alignment, heading/body resets, starter-template CSS, card sizing, component-specific docs grid/card layout, and viewport behavior.

Refs, static members, warnings:

- Record ref forwarding, imperative methods, compound static members, native prop passthrough, and warnings.
- Deprecated warnings are decision coverage by default, not a requirement to migrate deprecated props.

Independent verification:

- Assign focused subagent branches for source/API, style graph, docs demo parity, browser geometry, contract closure, and learning-regression closure when applicable.
- Assign a fresh-context verifier subagent for browser/demo parity, layout geometry, portal behavior, viewer shell isolation, and learning-regression closure when applicable.
- Verifier findings must compare Ant source evidence to target rendered DOM/CSS and try to disprove the implementer's pass claims.
- Close findings only by fixing implementation, adding a source-backed non-goal, or recording a blocker. Do not close a verifier finding by loosening the assertion.
