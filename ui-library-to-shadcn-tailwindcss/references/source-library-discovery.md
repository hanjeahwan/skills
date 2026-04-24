# Source Library Discovery

Use this before writing a contract or implementation. It selects a profile, discovers unknown libraries, and verifies the shadcn + Tailwind CSS v4 target.

## Profile Selection

1. Match the user request against `profiles/*.md` aliases.
2. If exactly one profile matches, record `Profile decision: <profile path>` in the contract.
3. If no profile matches, dispatch `ui_profile_builder` or an equivalent generic subagent before migration.
4. If multiple profiles match, inspect package names/imports in the target/source request and choose the source-backed profile.
5. Never infer APIs from naming similarity across libraries.

## Library Discovery Gate

For unknown libraries, the profile builder must produce a temporary profile in the migration contract:

| Required field | Evidence |
|---|---|
| Source docs/source/package | URL, package, repo path, or installed source path |
| API extraction path | docs table, source types, declarations, generated types, or tests |
| Demo/examples path | docs examples, storybook, examples directory, or source fixtures |
| Theme/token model | CSS variables, design tokens, provider theme, style functions, or static CSS |
| Slot/class/style API | slot props, class maps, style maps, data attributes, override APIs |
| Internal primitives | headless hooks, wrapped packages, context providers, portals |
| Deprecated/legacy policy | docs/source evidence and default migration decision |
| Source CSS leakage deny patterns | source class, prefix, variable, generated CSS import regexes |

If discovery cannot produce these facts, use `Migration blocked` and name the missing evidence.

## Target Stack Detection

Before implementing, read the target project:

1. `package.json` for React, Tailwind, shadcn/Radix dependencies, test framework, scripts, and package manager.
2. `components.json` for shadcn aliases, component path, style, icon library, and `cn` utility alias.
3. Global CSS for Tailwind v4 syntax: `@import "tailwindcss";`, `@theme`, custom variants, and design tokens.
4. Existing `components/ui/**` files to match local shadcn style.
5. Existing tests and stories to place parity tests in the right framework.
6. TypeScript major version and alias rules.
7. Unit/browser test runner boundaries.

## Styling Source Rules

- Treat source style/theme files as behavioral source, not decoration.
- Prefer Tailwind utilities for static target-owned styling.
- Use component CSS variables only as compatibility bridges for runtime props, user overrides, semantic slot hooks, shared geometry, connector endpoints, or values Tailwind cannot know at build time.
- Map source colors to shadcn/Tailwind semantic utilities or theme variables. Do not freeze source color literals in runtime code unless the contract records a source-backed exception.
- Preserve source pixel token units when the source token is pixel-based.
- Trace positioned elements from real source DOM/CSS: semantic parent, positioned ancestor, `offsetParent`, containing block, and non-positioned wrappers.
- For connectors/tracks/rails/separators/progress bars, trace status/color ownership and assert endpoints/centerlines.
- If source responsive behavior is JS-driven, model it with an SSR-safe external subscription or record a source-backed non-goal.
- Source class names and variables are evidence only, not target selectors.

## Learning Lookup

Before writing the contract, search target repo notes by source library, component name, component class, edge gates, failure text, and target stack:

1. `docs/migrations/**`, `docs/solutions/**`, `docs/architecture/**`, and existing component contracts.
2. Current skill instructions and promoted rules.
3. Nearby migrated source-library-compatible components.
4. Prior benchmark/viewer artifacts if retained.

Record results in `## Prior learning applied`. If none exist, record `No prior migration learnings found`.

## Cross-Project Edge Case Gate

Complete this gate before coding:

1. Tailwind v4 configured.
2. shadcn configuration and aliases verified.
3. Source behavior may live in internal primitives or delegated packages.
4. Source provider/context may affect defaults, locale, theme, size, disabled state, portal container, or motion.
5. Slot/class/style APIs must be mapped when exposed.
6. Controlled/uncontrolled state and callback timing must match.
7. Portal, z-index, scroll container, transform, and stacking context must be checked.
8. SSR/RSC and client-only requirements must be checked.
9. Tailwind Preflight may change native defaults.
10. Icon/render-prop contracts must preserve React nodes and callback signatures.
11. Keyboard, focus, blur, IME, Escape, Enter, Tab, and arrow-key behavior must be tested where applicable.
12. Date, time, locale, timezone, parsing, and formatting are separate compatibility surfaces.
13. Infrastructure components need phased contracts.
14. Source tokens map to target-owned Tailwind/shadcn theme, not a copied source token system.
15. Snapshot-only verification is insufficient.
