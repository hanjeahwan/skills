---
name: antd-shadcn-migration
description: Migrates and ports Ant Design React components from the local ant-design source tree into shadcn/ui + Tailwind CSS v4 projects while preserving 1:1 public API, TypeScript types, runtime behavior, accessibility, semantic DOM hooks, docs demos, tests, and migration evidence. Use for AntD migration, antd to shadcn, component port, compatible Button/Select/Table, 1:1 API clone, or migration planning before code.
argument-hint: "[component-name or migration scope]"
user-invocable: true
---

# Ant Design to shadcn/Tailwind v4 Migration

Migrate Ant Design components by preserving the external contract and rebuilding internals with project-owned shadcn/Radix source and Tailwind CSS v4 tokens.

Default source repository:

```text
D:/dev/github/ant-design
```

This skill treats "1:1" as public API and behavior compatibility, not as copying Ant Design's cssinjs runtime. Users should be able to give a component name and get a migration contract, implementation, verification loop, fix loop, and acceptance report.

## Reference Map

Read only the references needed for the current task:

- Source discovery and the 15 cross-project edge cases: [references/source-and-target-discovery.md](references/source-and-target-discovery.md)
- Compatibility contract template and required matrices: [references/contract-template.md](references/contract-template.md)
- Tests, browser evidence, acceptance checklist, and final report: [references/testing-and-acceptance.md](references/testing-and-acceptance.md)
- Migration learnings, regression closure, benchmark, and viewer gate: [references/learnings-and-benchmark.md](references/learnings-and-benchmark.md)
- Component-class migration strategy: [references/component-classes.md](references/component-classes.md)

Use the bundled scripts when applicable:

```bash
node scripts/check-skill-structure.mjs
node scripts/install-custom-agents.mjs --scope user
node scripts/install-custom-agents.mjs --scope project --target <repo>
node scripts/check-migration-contract.mjs docs/migrations/antd/<component>.md
node scripts/check-migration-contract.mjs docs/migrations/antd/<component>.md --allow-blocked
node scripts/check-no-ant-css.mjs src/components src/styles
```

Use `--allow-blocked` only for draft/blocker review. Final acceptance must run the contract checker without it.

## Workflow

```text
┌─────────────────────────────┐
│ Receive component scope      │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Verify source + target facts │
│ no API guessing             │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Lookup migration learnings   │
│ prior fixes, known traps     │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Inspect Ant style graph      │
│ layout, tokens, state matrix │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Build compatibility contract │
│ props, demos, style, tests   │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Write failing parity tests   │
│ types, DOM, events, a11y     │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Implement with shadcn/Radix  │
│ and Tailwind v4 tokens       │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Run verification loop        │
│ tests, typecheck, browser    │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Independent verifier +       │
│ side-branch audits           │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Capture browser evidence     │
│ Codex in-app first if avail  │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Capture migration learnings  │
│ failures, fixes, prevention  │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Close checklist + report     │
└─────────────────────────────┘
```

## Non-Negotiable Rules

1. Do not guess Ant Design APIs. Trace every prop, default, export, event, ref, semantic slot, warning, and edge behavior to source files, docs, demos, tests, or generated declarations.
2. Do not import `antd` as a runtime dependency in migrated components. The target owns the source code.
3. Do not preserve Ant Design cssinjs. Rebuild styling with Tailwind CSS v4 utilities, CSS variables, and `@theme` tokens.
4. Do not treat styling as optional. Inspect the full Ant `components/<component>/style/**` graph and translate layout, tokens, state matrices, RTL, variants, status, placement, and responsive behavior.
5. If the component delegates to another Ant component, shared primitive, rc wrapper, utility hook, or token layer, inspect that delegated implementation and style graph too.
6. Do not use Ant `ant-*` class names, `--ant-*` variables, generated CSS, or prefix selectors as the target styling layer. They are source evidence only.
7. Preserve semantic DOM through target-owned `data-slot`, shadcn-style class composition, `classNames`/`styles` slot APIs, and minimal target-owned CSS variables.
8. Use shadcn/ui source ownership as the implementation model. Add copied shadcn source when useful, then adapt it directly.
9. Use Radix primitives only when they match the behavior domain. Keep Ant prop names and callback signatures at the public boundary.
10. Write failing parity tests before implementation for each migrated behavior group.
11. Keep visual evidence, semantic evidence, and implementation commentary separate.
12. Require a fresh-context independent verifier subagent before final acceptance. The implementer may prepare candidate checklist statuses, but cannot be the only party that marks browser/demo parity, layout geometry, portal behavior, viewer shell isolation, or learning-regression closure as pass.
13. Prefer installed custom agents, but do not block only because they are not loaded in the current session. When custom agents are unavailable and subagent capability exists, the implementer must spawn fresh-context generic subagents with equivalent role prompts and record the dispatch mode.
14. If exact compatibility conflicts with shadcn/Tailwind architecture, stop and explain the conflict before editing.

## Intake

Extract these answers from the user request and repository context before editing:

```markdown
Migration scope: <component names or package surface>
Ant Design source path: <default D:/dev/github/ant-design unless overridden>
Target project path: <repo receiving migrated components>
Target framework: <Next.js | Vite | Remix | other>
Target package manager: <pnpm | npm | yarn | bun>
Tailwind version: <must verify v4 package/config>
shadcn status: <components.json exists? cn utility exists? UI path?>
Compatibility bar: <exact public API | selected API subset approved by user>
Verification command set: <typecheck, test, lint, browser/story command>
```

Ask only when a missing answer changes file placement, package manager commands, or compatibility scope. Otherwise infer from files and state the assumption.

## Required Execution Steps

1. Read [references/source-and-target-discovery.md](references/source-and-target-discovery.md) before writing any contract or code.
2. Search target repo learnings and existing migration contracts before planning. Record `No prior migration learnings found` when none exist.
3. Classify the component with [references/component-classes.md](references/component-classes.md).
4. Create the compatibility contract from [references/contract-template.md](references/contract-template.md). The contract is incomplete until every applicable matrix has evidence and an action.
5. Split independent side-branch audits before coding when the component has meaningful API, style graph, docs demo, portal, layout geometry, or contract-closure risk. Select the agent dispatch mode and record owners in the contract.
6. Write failing tests and browser assertions using [references/testing-and-acceptance.md](references/testing-and-acceptance.md). Assertions must be able to fail for the exact visible mismatch they protect.
7. Implement the Ant-compatible facade over shadcn/Radix internals and Tailwind v4 styling.
8. Run the target repo verification loop. If a browser runner creates transient directories, keep lint/test boundaries separate.
9. Spawn a fresh-context independent verifier subagent for browser/demo parity, layout geometry, portal behavior, viewer shell, and learning-regression closure. Use an installed custom agent when callable; otherwise spawn a generic subagent with the equivalent role prompt. The verifier must compare source evidence to rendered DOM/CSS and try to falsify the checklist.
10. Capture browser evidence. In Codex desktop, use the Codex in-app browser before final acceptance when available; Playwright or agent-browser is fallback evidence, not a substitute for available in-app inspection.
11. Record learnings, regression assertions, and promoted-learning backfill scans using [references/learnings-and-benchmark.md](references/learnings-and-benchmark.md).
12. Close the acceptance checklist. Do not say `Migration completed` while any applicable row is unimplemented, self-certified, or blocked.

## Subagent Work Distribution

Use subagents for independent branches that can run without blocking the implementer. The goal is not parallelism for its own sake; the goal is to keep evidence collection and verification independent from the code path that may be biased toward passing.

Install the bundled custom agent templates when the environment has not loaded them yet:

```bash
node scripts/install-custom-agents.mjs --scope user
node scripts/install-custom-agents.mjs --scope project --target <repo>
```

Installation is not proof that a custom agent is callable in the current session. Every audit branch must record one dispatch mode:

- `custom-agent`: the named bundled custom agent is installed and callable now.
- `generic-subagent`: the named custom agent is unavailable, not loaded, or not callable, so the implementer spawned a fresh-context generic subagent with the same role, scope, required evidence, and output contract as the matching `agents/*.toml` file.
- `self-review-blocked`: no subagent capability exists. The implementer may collect provisional self-audit evidence, but protected rows stay `blocked` and final acceptance is invalid unless the user explicitly narrows scope in the contract.

```text
┌────────────────────────────┐
│ Need audit/verifier branch  │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Named custom agent callable?│
└───────┬────────────────────┘
        │ yes
        ▼
┌────────────────────────────┐
│ Use installed custom agent  │
└────────────────────────────┘
        │ no
        ▼
┌────────────────────────────┐
│ Fresh-context subagent      │
│ capability available?       │
└───────┬────────────────────┘
        │ yes
        ▼
┌────────────────────────────┐
│ Spawn generic subagent with │
│ equivalent role prompt      │
└────────────────────────────┘
        │ no
        ▼
┌────────────────────────────┐
│ Self-review only; protected │
│ rows remain blocked         │
└────────────────────────────┘
```

Delegate these branches with the named custom agents when applicable:

- `antd_source_auditor`: Source/API/type graph audit.
- `antd_style_graph_auditor`: Ant style graph, token, layout, connector, and responsive audit.
- `antd_demo_parity_auditor`: Docs demo parity and fixture audit.
- `antd_browser_geometry_verifier`: Browser geometry, containing-block, connector, portal, computed-style, overflow, and viewer-shell verification.
- `antd_contract_closure_verifier`: Contract/checklist closure and self-certification rejection.
- `antd_learning_promoter`: Learning regression closure and skill-rule promotion.

When using `generic-subagent`, use the same branch names and outputs:

- `source-api-audit generic subagent`: equivalent to `antd_source_auditor`.
- `style-graph-audit generic subagent`: equivalent to `antd_style_graph_auditor`.
- `demo-parity-audit generic subagent`: equivalent to `antd_demo_parity_auditor`.
- `browser-geometry-verifier generic subagent`: equivalent to `antd_browser_geometry_verifier`.
- `contract-closure-verifier generic subagent`: equivalent to `antd_contract_closure_verifier`.
- `learning-regression generic subagent`: equivalent to `antd_learning_promoter`.

A generic subagent must be fresh-context, must not be the implementer, must use the matching custom agent template as its role prompt source, and must include the same evidence, falsification, and final verdict fields required by that template.

Default schedule:

1. Before implementation, run `antd_source_auditor`, `antd_style_graph_auditor`, and `antd_demo_parity_auditor` in parallel when their scopes apply.
2. After implementation and local verification, run `antd_browser_geometry_verifier` and `antd_contract_closure_verifier`.
3. After user feedback, verifier findings, or test failures, run `antd_learning_promoter`.

The implementer can run tests, but cannot be the final verifier for browser/demo parity, layout geometry, portal behavior, viewer shell isolation, contract closure, or learning-regression closure. Evidence may come from a named custom agent or a fresh-context generic subagent using the equivalent role prompt. If no subagent capability exists, self-audit can document risk and findings, but protected checklist rows remain `blocked`.

## Implementation Architecture

```text
┌────────────────────────────────────┐
│ Ant-compatible public component     │
│ props, exports, refs, static fields │
└───────────────┬────────────────────┘
                ▼
┌────────────────────────────────────┐
│ Compatibility adapter               │
│ defaults, events, semantic slots    │
└───────────────┬────────────────────┘
                ▼
┌────────────────────────────────────┐
│ shadcn/Radix implementation         │
│ primitives, cn(), cva variants      │
└───────────────┬────────────────────┘
                ▼
┌────────────────────────────────────┐
│ Tailwind v4 styling                 │
│ utilities, @theme, CSS variables    │
└────────────────────────────────────┘
```

Public API layer:

- Export the same default and named types when the target scope requires them.
- Preserve compound members, native prop passthrough, ARIA/data attributes, and ref forwarding when present.
- Identify deprecated props and record them as `default not migrated` unless the user explicitly requests legacy compatibility.

Adapter layer:

- Normalize Ant sugar props into internal variant values.
- Apply ConfigProvider/default behavior explicitly.
- Map events while preserving Ant callback signatures and controlled/uncontrolled precedence.
- Use local utilities for repeated compatibility logic; avoid broad abstractions until at least two components need the same helper.

Styling layer:

- Use `@import "tailwindcss";` and CSS-first Tailwind v4 configuration.
- Use Tailwind utilities as the default styling layer for static layout, typography, spacing, borders, radii, and theme colors. The target project already owns the shadcn/Tailwind theme, so do not recreate a component-local Ant token system by default.
- Express Ant token equivalents through existing shadcn/Tailwind semantic utilities such as `text-foreground`, `text-muted-foreground`, `border-border`, `bg-background`, `bg-primary`, and `text-primary-foreground` whenever the value is static.
- Use component CSS variables only as compatibility bridge variables for Ant runtime props, user overrides, semantic slot hooks, shared cross-node geometry, connector endpoints, or values Tailwind cannot know at build time. Each component variable must have a recorded reason in the contract.
- Bind any retained component variables to shadcn/Tailwind theme tokens such as `--primary`, `--foreground`, `--muted-foreground`, `--border`, and `--destructive`; do not freeze Ant hex/rgba defaults in runtime component code unless the contract records a source-backed compatibility requirement.
- Emit CSS-variable color usage through the component CSS layer or another unambiguous generated color rule. Do not rely on ambiguous Tailwind v4 arbitrary value classes such as `text-[var(--component-color)]` unless browser evidence proves they compiled as color rules.
- Keep static color defaults in CSS where they can inherit the user theme. Runtime TypeScript may assign state-specific variable names, but must not own theme color literals.
- Preserve fixed pixel token units when Ant source tokens are pixel-based.
- Assert computed styles for user-visible tokens: text metrics, colors, fills, borders, shadows, spacing, connector widths, marker/icon sizes, and opacity.

## Completion Gate

Before saying `Migration completed`, every applicable checklist row from [references/testing-and-acceptance.md](references/testing-and-acceptance.md) must be `pass` or `source-backed non-goal`.

The following are blockers when applicable and unimplemented:

- Docs demo parity matrix.
- Style graph translation.
- Tailwind-first styling ownership.
- Theme token inheritance.
- CSS-variable color emission.
- Token unit preservation.
- Positioned element ownership and containing block.
- Connector, track, separator, underline, handle, or overlay geometry.
- Ant CSS leakage prevention.
- Viewer shell/global CSS isolation.
- Ref, static member, and imperative API verification.
- Runtime warning decision.
- Browser visual evidence.
- Agent execution mode decision.
- Independent verifier completion for browser/demo parity changes.
- Subagent side-branch audit closure.
- False-pass prevention assertions.
- Benchmark/viewer scope decision.
- Learning regression assertion closure.
- Promoted learning backfill across sibling migrated components.

If any row is `blocked`, use `Migration blocked` and name the exact blocker. A screenshot is evidence, not a replacement for repeatable assertions when behavior can be measured. A passing unit test is not enough when browser geometry, computed style, containing block, portal, or demo-source parity evidence is required.

Self-certified pass is invalid for browser/demo parity, layout geometry, connector endpoints, portal stacking, viewer shell isolation, or learning-regression closure. A pass requires independent verifier subagent evidence, resolved findings, and at least one source-backed assertion that would have failed for the observed mismatch class.

## Final Report

Use the final response template in [references/testing-and-acceptance.md](references/testing-and-acceptance.md). Include:

- Changed files.
- Props and behavior coverage.
- 15 edge-case gate coverage.
- Deprecated API decision.
- Tailwind-first styling summary.
- Agent execution mode and fallback reason.
- Browser evidence source: Codex in-app browser, Playwright fallback, or agent-browser fallback.
- Independent verifier subagent report, rejected rows, and required fixes.
- Verification commands.
- Acceptance checklist statuses.
- Learnings captured and regression assertions landed.

## Stop Conditions

Stop and ask for alignment when:

- The user requests visual similarity but rejects public API parity.
- The source component depends on infrastructure that is not yet migrated.
- Tailwind v4 or shadcn setup is absent and the user has not approved adding it.
- Radix/shadcn behavior cannot faithfully reproduce an Ant edge case without custom implementation.
- The requested "1:1" scope is too broad to verify in one pass, such as all Ant components.

Do not continue with an implementation that hides an unverified compatibility gap.
