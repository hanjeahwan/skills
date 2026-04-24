# Ant Design Profile

profile_id: antd
source_library: Ant Design
aliases: antd, ant design, ant-design
source_repo_default: D:/dev/github/ant-design
runtime_css_deny_patterns:
- "\\bant-[a-z0-9-]+"
- "--ant-[a-z0-9-]+"
- "\\[class\\*=[\"']ant-|\\.ant-"
- "from\\s+[\"']antd/dist|import\\s+[\"']antd/dist|from\\s+[\"']antd/es/.*/style|import\\s+[\"']antd/es/.*/style"

## Discovery

Inspect these source paths before writing code:

| Fact type | Primary paths |
|---|---|
| Exports | `components/<component>/index.tsx`, package exports |
| Props/types/defaults | `components/<component>/**/*.tsx`, `interface.ts`, helper types |
| Docs/API | `components/<component>/index.en-US.md`, `index.zh-CN.md` |
| Demos | `components/<component>/demo/**` |
| Tests | `components/<component>/__tests__/**`, semantic tests |
| Styles | `components/<component>/style/**`, token files |
| Context | `components/config-provider/**`, `components/theme/**`, `components/_util/**` |
| Delegation | `@rc-component/*`, rc wrappers, shared utilities |

## AntD-Specific Rules

- `ConfigProvider` can affect size, direction, disabled, locale, theme, popup container, wave, variant, and component-specific defaults.
- Many components delegate behavior to `@rc-component/*`; inspect rc types, callback timing, status derivation, DOM ownership, and style delegation.
- `classNames` and `styles` semantic DOM hooks are first-class APIs. Inspect semantic tests and docs tables.
- Ant cssinjs and `ant-*` selectors are source evidence only. Target runtime styling must use target-owned slots, Tailwind utilities, and bridge variables.
- Ant token values are evidence. Map static colors to shadcn/Tailwind semantic utilities or theme variables; preserve pixel units when Ant tokens are pixel-based.
- Deprecated props are identified and recorded as `default not migrated` unless the user explicitly requests legacy compatibility.
- Docs demos under `components/<component>/demo/**` are fixtures. Synthetic or shortened demos do not satisfy full demo parity.

## Common Edge Cases

- rc/shared primitive behavior hidden below Ant wrapper.
- ConfigProvider defaults and token overrides.
- Semantic DOM `classNames` / `styles` keys.
- Portal, popup container, z-index, transform and stacking context.
- Responsive behavior driven by JS media state.
- IME, keyboard, focus/blur order.
- Date/time/locale/timezone behavior for date components.
- Infrastructure components such as Table/Form require phased contracts.
