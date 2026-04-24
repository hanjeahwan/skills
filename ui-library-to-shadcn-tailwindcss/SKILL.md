---
name: ui-library-to-shadcn-tailwindcss
description: Migrates React UI library components from AntD, MUI, Chakra, Mantine, Headless UI, Radix Themes, or unknown source libraries into shadcn/ui + Tailwind CSS v4 projects while preserving public API, behavior, accessibility, docs demos, Tailwind-first styling, verification contracts, and independent subagent evidence. Triggers on UI library migration, component port, shadcn migration, Tailwind v4 conversion, and profile-based migration planning.
argument-hint: "[source library and component, e.g. AntD Steps or MUI Autocomplete]"
user-invocable: true
---

# UI Library to shadcn/Tailwind CSS Migration

Migrate source UI library components into project-owned shadcn/ui + Tailwind CSS v4 code. The target always owns the implementation; the source library is evidence for public API, behavior, demos, accessibility, and style semantics.

This skill uses profiles. Known source libraries load a profile. Unknown source libraries first run profile discovery, produce a temporary profile in the migration contract, then migrate.

## Reference Map

Read only the references needed for the current task:

- Source library discovery, profile selection, and cross-project edge cases: [references/source-library-discovery.md](references/source-library-discovery.md)
- Compatibility contract template and required matrices: [references/contract-template.md](references/contract-template.md)
- Tests, browser evidence, acceptance checklist, and final report: [references/testing-and-acceptance.md](references/testing-and-acceptance.md)
- Migration learnings, profile evolution, and benchmark/viewer gate: [references/learnings-and-profile-evolution.md](references/learnings-and-profile-evolution.md)
- Component-class migration strategy: [references/component-classes.md](references/component-classes.md)
- Ant Design profile: [profiles/antd.md](profiles/antd.md)
- New profile template: [profiles/profile-template.md](profiles/profile-template.md)

Use bundled scripts when applicable:

```bash
node scripts/check-skill-structure.mjs
node scripts/check-migration-contract.mjs docs/migrations/ui/<component>.md
node scripts/check-migration-contract.mjs docs/migrations/ui/<component>.md --allow-blocked
node scripts/check-no-source-css.mjs --profile profiles/antd.md src/components src/styles
```

Use `--allow-blocked` only for draft/blocker review. Final acceptance must run the contract checker without it.

## Workflow

```text
┌─────────────────────────────┐
│ Receive library/component    │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Select or build profile      │
│ no API guessing              │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Source/API/style/demo audits │
│ via custom/generic subagents │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Build compatibility contract │
│ profile, demos, style, tests │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Write failing parity tests   │
│ types, DOM, events, a11y     │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Implement with shadcn/Radix  │
│ Tailwind-first styling       │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Verify, falsify, fix loop    │
│ tests, browser, subagents    │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Capture learnings + profile  │
│ evolution/backfill           │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Close checklist + report     │
└─────────────────────────────┘
```

## Non-Negotiable Rules

1. Do not guess source library APIs. Trace props, defaults, exports, events, refs, slots, warnings, accessibility, and edge behavior to docs, source, tests, examples, declarations, or generated types.
2. Do not import the source UI library as a runtime dependency in migrated components unless the contract records a deliberate adapter exception.
3. Do not preserve source library CSS runtimes as target styling. Rebuild with Tailwind CSS v4 utilities, shadcn conventions, CSS variables only as compatibility bridges, and target-owned theme tokens.
4. Do not treat styling as optional. Inspect source style/theme graphs and translate layout, tokens, state matrices, variants, placement, responsive behavior, motion, and slot geometry.
5. If behavior delegates to an internal primitive, headless hook, shared package, theme layer, or third-party primitive, inspect the delegated implementation before coding.
6. Do not use source-library class names, generated CSS, CSS variables, or prefix selectors as target runtime styling. They are source evidence only.
7. Preserve semantic DOM through target-owned `data-slot`, shadcn-style class composition, compatible slot APIs, and minimal bridge variables.
8. Use shadcn/ui source ownership as the implementation model. Add copied shadcn/Radix source when useful, then adapt directly while preserving source public API.
9. Use Radix/headless primitives only when they match the behavior domain. Keep source library prop names and callback signatures at the public boundary.
10. Write failing parity tests before implementation for each migrated behavior group.
11. Require a fresh-context independent verifier subagent before final acceptance. The implementer may prepare candidate checklist statuses, but cannot be the only party marking demo parity, layout geometry, portal behavior, viewer shell isolation, contract closure, or learning/profile closure as pass.
12. Prefer installed custom agents. If unavailable but subagent capability exists, spawn fresh-context generic subagents with equivalent role prompts and record dispatch mode.
13. If exact compatibility conflicts with shadcn/Tailwind architecture, stop and explain the conflict before editing.

## Intake

Extract these facts from the request and repo before editing:

```markdown
Migration scope: <source library + component names>
Source profile: <known profile path | temporary profile required>
Source repo/docs/package path: <resolved evidence source>
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

1. Read [references/source-library-discovery.md](references/source-library-discovery.md) before writing any contract or code.
2. Select a source profile. Use `profiles/antd.md` for Ant Design. If no profile matches, run `ui_profile_builder` or equivalent generic subagent and record a temporary profile in the contract.
3. Search target repo learnings and existing migration contracts before planning. Record `No prior migration learnings found` when none exist.
4. Classify the component with [references/component-classes.md](references/component-classes.md).
5. Create the compatibility contract from [references/contract-template.md](references/contract-template.md). The contract is incomplete until profile decision, library discovery evidence, and every applicable matrix has evidence and action.
6. Split independent side-branch audits before coding when API, style graph, docs demo, portal, layout geometry, profile discovery, or contract-closure risk exists.
7. Write failing tests and browser assertions using [references/testing-and-acceptance.md](references/testing-and-acceptance.md). Assertions must fail for the exact visible mismatch they protect.
8. Implement the compatible facade over shadcn/Radix/headless internals and Tailwind-first styling.
9. Run the target repo verification loop. Keep unit/browser/lint artifacts separated.
10. Spawn independent verifier subagents for browser/demo parity, layout geometry, portal behavior, viewer shell, contract closure, and learning/profile closure.
11. Capture browser evidence. In Codex desktop, use the Codex in-app browser when available; Playwright or agent-browser is fallback evidence.
12. Record learnings, regression assertions, profile updates, and sibling-component backfill scans using [references/learnings-and-profile-evolution.md](references/learnings-and-profile-evolution.md).
13. Close the acceptance checklist. Do not say `Migration completed` while any applicable row is unimplemented, self-certified, or blocked.

## Subagent Work Distribution

Use subagents to keep evidence collection and verification independent from the implementation path.

Custom agents are installed by copying `.toml` templates into Codex's documented agent directories. Do not use a bundled install script.

```bash
mkdir -p ~/.codex/agents
cp <skill-path>/agents/*.toml ~/.codex/agents/

mkdir -p .codex/agents
cp <skill-path>/agents/*.toml .codex/agents/
```

Storage and precedence:

| Type | Path | Availability | Precedence |
|---|---|---|---|
| Project custom agents | `.codex/agents/` | Current project only | Higher |
| Global custom agents | `~/.codex/agents/` | All projects | Lower |

Project-specific agents override global agents when names conflict. If using Codex agent configuration, keep it in `.codex/config.toml` under `[agents]`.

Codex does not auto-spawn custom subagents. Delegate explicitly to the named custom agent in the prompt/tool call, or spawn a fresh-context generic subagent with the same role when the custom agent is not loaded.

Installation is not proof that a custom agent is callable in the current session. Every audit branch records one dispatch mode:

- `custom-agent`: the named bundled custom agent is installed and callable now.
- `generic-subagent`: the named custom agent is unavailable, not loaded, or not callable, so the implementer spawned a fresh-context generic subagent with the same role and output contract.
- `self-review-blocked`: no subagent capability exists. Self-audit may collect provisional evidence, but protected rows remain `blocked`.

Default branches:

- `ui_profile_builder`: unknown library discovery and temporary profile generation.
- `ui_source_auditor`: source/API/type/default/ref/event audit.
- `ui_style_graph_auditor`: style/theme/token/layout/connector/responsive audit.
- `ui_demo_parity_auditor`: docs demo/example parity audit.
- `ui_browser_geometry_verifier`: browser geometry, computed style, portal, overflow, and viewer-shell falsification.
- `ui_contract_closure_verifier`: contract/checklist closure and self-certification rejection.
- `ui_learning_promoter`: learning regression closure and profile/core rule promotion.

Default schedule:

1. Before implementation, run `ui_profile_builder` for unknown libraries, then `ui_source_auditor`, `ui_style_graph_auditor`, and `ui_demo_parity_auditor` in parallel when applicable.
2. After implementation and local verification, run `ui_browser_geometry_verifier` and `ui_contract_closure_verifier`.
3. After user feedback, verifier findings, or test failures, run `ui_learning_promoter`.

The implementer can run tests, but cannot be the final verifier for protected rows. Evidence must come from a named custom agent or equivalent fresh-context generic subagent. If no subagent capability exists, final status is `Migration blocked` unless the row is a source-backed non-goal.

## Styling Architecture

```text
┌────────────────────────────────────┐
│ Compatible public component         │
│ source props, exports, refs         │
└───────────────┬────────────────────┘
                ▼
┌────────────────────────────────────┐
│ Compatibility adapter               │
│ defaults, events, slots, warnings   │
└───────────────┬────────────────────┘
                ▼
┌────────────────────────────────────┐
│ shadcn/Radix/headless implementation│
│ primitives, cn(), cva variants      │
└───────────────┬────────────────────┘
                ▼
┌────────────────────────────────────┐
│ Tailwind v4 styling                 │
│ utilities first, bridge vars only   │
└────────────────────────────────────┘
```

- Use Tailwind utilities as the default styling layer for static layout, typography, spacing, borders, radii, and theme colors.
- Use existing shadcn/Tailwind semantic utilities such as `text-foreground`, `text-muted-foreground`, `border-border`, `bg-background`, `bg-primary`, and `text-primary-foreground` whenever values are static.
- Use component CSS variables only as compatibility bridge variables for runtime props, user overrides, semantic slot hooks, shared cross-node geometry, connector endpoints, or values Tailwind cannot know at build time.
- Bind retained variables to target theme tokens. Do not freeze source library color literals in runtime component code unless the contract records a source-backed compatibility exception.
- Preserve fixed pixel token units when the source token is pixel-based.

## Completion Gate

Before saying `Migration completed`, every applicable checklist row from [references/testing-and-acceptance.md](references/testing-and-acceptance.md) must be `pass` or `source-backed non-goal`.

Blockers when applicable and unimplemented:

- Profile decision and library discovery evidence.
- Docs demo parity matrix.
- Style graph translation.
- Tailwind-first styling ownership.
- Theme token inheritance.
- Source CSS leakage prevention.
- Positioned element ownership and containing block.
- Connector, track, separator, underline, handle, or overlay geometry.
- Browser visual evidence.
- Agent execution mode decision.
- Independent verifier completion.
- False-pass prevention assertions.
- Learning/profile regression closure and sibling backfill.

Self-certified pass is invalid for demo parity, layout geometry, connector endpoints, portal stacking, viewer shell isolation, contract closure, or learning/profile closure.

## Final Report

Use the final response template in [references/testing-and-acceptance.md](references/testing-and-acceptance.md). Include changed files, profile decision, compatibility coverage, Tailwind-first styling summary, source CSS leakage result, browser evidence source, independent verifier report, verification commands, checklist statuses, and learnings/profile updates.

## Stop Conditions

Stop and ask for alignment when:

- The source library profile cannot be built from available docs/source evidence.
- The user requests visual similarity but rejects public API parity.
- The source component depends on infrastructure that is not yet migrated.
- Tailwind v4 or shadcn setup is absent and the user has not approved adding it.
- Radix/shadcn behavior cannot reproduce a source edge case without custom implementation.
- The requested scope is too broad to verify in one pass.
