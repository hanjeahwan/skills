# Source and Target Discovery

Use this reference before writing a migration contract or implementation. It defines the source evidence that must be collected and the target project facts that determine the migration path.

## Required Fact Sources

Inspect relevant source files under the Ant Design repository. Use exact paths and line numbers in the contract notes.

Default source repository:

```text
D:/dev/github/ant-design
```

| Fact type | Primary paths |
|---|---|
| Component exports | `components/<component>/index.tsx`, root package exports |
| Props and types | `components/<component>/**/*.tsx`, `components/<component>/**/*.ts`, `interface.ts`, helper type files |
| Defaults and runtime behavior | Main implementation files, hooks, context consumers, utility modules |
| Docs API table | `components/<component>/index.en-US.md`, `index.zh-CN.md` |
| Examples and edge cases | `components/<component>/demo/**` |
| Existing behavior tests | `components/<component>/__tests__/**` |
| Styling semantics | `components/<component>/style/**`, semantic tests, token files |
| Cross-component context | `components/config-provider/**`, `components/theme/**`, `components/_util/**` |
| Shared test helpers | `tests/utils`, `tests/shared/**` |

## Ant Source Patterns

- Many public components delegate behavior to `@rc-component/*`. Inspect wrapped rc types and behavior before assuming the Ant wrapper contains the full contract.
- `ConfigProvider` can supply defaults, size, variant, direction, disabled state, theme, popup container, wave behavior, and locale. Inspect `components/config-provider/context.ts` and component-specific config consumers.
- `classNames` and `styles` semantic DOM hooks are first-class APIs. Inspect `components/_util/hooks/useMergeSemantic.ts`, component `semantic.test.tsx`, and docs `Semantic DOM` tables.
- Treat style files as behavioral source, not decoration. Follow every file imported by `components/<component>/style/index.ts` and record orientation, mode, placement, variant, status, RTL, responsive branches, and token use before coding.
- If a component renders through another Ant component or shared primitive, inspect that delegated implementation and style graph too. Visible contract may live in a shared component, rc wrapper, utility hook, or token layer.
- Helper files often contain compatibility behavior. Record helper behavior in the contract instead of inlining assumptions.
- Demo and screenshot helpers scan `components/<component>/demo/**`; demos are behavior evidence, not just documentation.

## Styling Source Rules

- Migrate style from Ant token meaning and state matrices, not screenshots.
- Every docs demo that depends on component layout must have a migrated styling assertion.
- Visual parity tests must include computed style checks for visible tokens that users compare by eye: font size, line height, text color, semantic colors, filled versus outlined state, icon or marker container size, border color, background color, connector color, connector width, shadows, spacing, and state opacity.
- When Ant style files position semantic slots independently, test those slot geometries directly: split slots, label/control relationships, adornments, extra/actions areas, title/content pairs, baseline alignment, axis relationships, and bidirectional placement.
- Preserve Ant pixel token units when the source token is pixel-based. Do not convert fixed source dimensions to `rem` unless the source is font-relative.
- Connector elements are behavioral DOM, not decoration. For separators, progress tracks, underlines, selection bars, connector lines, resize handles, and similar elements, record semantic parent and assert endpoint geometry.
- CSS positioning ownership must be traced from the real Ant DOM and generated styles. For absolute, fixed, sticky, transform-based, or inset-based elements, record semantic parent, positioned ancestor, `offsetParent`, containing block, and any wrapper that must remain non-positioned.
- Preserve Ant flex and min-size semantics before using Tailwind shortcuts such as `flex-1`, `min-w-0`, `truncate`, or `break-words`. Record source `flex-grow`, `flex-shrink`, `flex-basis`, `min-width`, overflow, wrap behavior, and last-item rules when text or slots participate in layout.
- Treat every source `type`, `variant`, `mode`, `placement`, `size`, and responsive style branch as a separate behavior surface until source evidence proves it shares layout with the default branch.
- For connectors, rails, tracks, separators, progress bars, and similar visuals, trace whether status/color comes from current state, previous item, next item, parent state, or token state. Do not infer color ownership from the visible item alone.
- CSS variables consumed by positioned visuals must be defined on the containing block or a reachable ancestor. Record the variable producer, consumer, and inheritance path before coding.
- If Ant responsive behavior is driven by JavaScript media state, model it with an SSR-safe subscription pattern in the target or record a source-backed non-goal.
- Attached visuals such as progress rings, badges, SVG indicators, loading marks, and overlay adornments require owner-slot, containing-block, inset, center, and size-envelope evidence.
- Source `ant-*` classes are evidence for semantic locations, not target selectors.

## Target Stack Detection

Before implementing, read the target project:

1. `package.json` for React, Tailwind, shadcn/Radix dependencies, test framework, scripts, and package manager.
2. `components.json` for shadcn aliases, component path, style, icon library, and `cn` utility alias.
3. Global CSS for Tailwind v4 syntax: `@import "tailwindcss";`, `@theme`, custom variants, and design tokens.
4. Existing `components/ui/**` files to match local shadcn style.
5. Existing tests and stories to place parity tests in the right framework.
6. TypeScript major version and alias rules. For TypeScript 6+, prefer `paths` without `baseUrl` unless the target repo already depends on `baseUrl`; re-run `npx shadcn@latest info --json` after alias changes.
7. Test runner boundaries. If unit tests and browser tests coexist, explicitly separate discovery patterns and ignore generated browser artifacts such as `playwright-report` and `test-results` in lint.

If shadcn is missing, initialize or add components using the target repo's package manager and current shadcn CLI pattern:

```bash
npx shadcn@latest add button dialog popover select
```

## Learning Lookup

Before writing the compatibility contract, search for previous Ant-to-shadcn migration learnings by component name, component class, edge-gate IDs, trigger text, failing command, error message, and target-stack facts.

Search in this order:

1. Target repo migration notes, especially `docs/migrations/antd/learnings.md`, `docs/migrations/antd/**`, `docs/solutions/**`, `docs/architecture/**`, and existing component contracts.
2. Current skill instructions and promoted rules.
3. Nearby target repo code for already migrated Ant-compatible components.
4. Prior benchmark/viewer artifacts if the target repo keeps them.

Record lookup results in the contract:

```markdown
## Prior learning applied
| Learning ID/title | Trigger match | Edge gates | Source | Applies? | Action |
|---|---|---|---|---|---|
| <id or issue> | <component/config/error/test pattern> | <01, 07, 14> | <path or skill section> | yes/no | <contract row, test, implementation constraint, or non-goal> |
```

If no prior learnings exist, record `No prior migration learnings found`. An empty lookup is still evidence.

When a learning applies, convert it into a compatibility contract row, red parity test, edge-case gate action, Tailwind v4 token requirement, source inspection requirement, or source-backed non-goal.

## Cross-Project Edge Case Gate

Before writing a contract or implementation, complete this gate. Mark each item as `applies`, `not applicable`, or `blocked`, and cite file/source evidence.

1. Tailwind v4 is configured; if not, block styling work until the target styling path is decided.
2. shadcn configuration may be non-standard; read `components.json`, aliases, `cn` location, icon library, and UI component directory.
3. Ant behavior may live in `@rc-component/*`; inspect wrapped component APIs and behavior for delegated components.
4. `ConfigProvider` may affect defaults, size, direction, disabled state, locale, theme, wave, or popup container behavior.
5. `classNames` and `styles` semantic DOM slots are mandatory when source exposes them.
6. Controlled and uncontrolled state must match source callback timing and value precedence.
7. Portal, z-index, scroll container, transform, and stacking-context behavior must be checked for overlay/popup components.
8. SSR and React Server Components must be checked; client-only components need the target repo's established `"use client"` pattern.
9. Tailwind Preflight may change native element defaults; define base styles explicitly where Ant reset previously did.
10. Icon contracts must preserve passed React nodes; do not replace Ant-compatible `icon` props with lucide-only APIs.
11. IME composition, keyboard navigation, focus, blur, Escape, Enter, Tab, and arrow-key behavior must be tested where interactive input is involved.
12. Date, time, locale, timezone, parsing, and formatting are a separate compatibility surface for date/time components.
13. Table, Form, and other infrastructure components require phased migration contracts rather than one-shot ports.
14. Ant tokens must map to target-owned Tailwind v4 semantic CSS variables, not copied as Ant cssinjs or generated CSS.
15. Snapshot-only verification is insufficient; every migration needs behavior, type, accessibility, and browser assertions appropriate to the component.

Deprecated APIs are not migrated by default. Identify deprecated props, warnings, and docs, then record them as `default not migrated` unless the user explicitly requests legacy API support.
