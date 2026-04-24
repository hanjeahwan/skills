# Component Classes

Classify each component before implementation. Use the class to choose source files, tests, browser assertions, and whether the migration must be phased.

| Class | Examples | Migration approach |
|---|---|---|
| Primitive facade | Button, Tag, Badge, Avatar | shadcn component plus Ant-compatible props and variants |
| Radix behavior component | Modal, Drawer, Tooltip, Popover, Dropdown, Tabs, Collapse | Radix primitive with Ant event/default adapters when behavior matches |
| Form control | Checkbox, Radio, Switch, Input, Select, Slider, Rate | Preserve controlled/uncontrolled value, status, disabled, size, focus, keyboard, IME behavior |
| Data display | Table, Tree, List, Descriptions | Source-first behavior audit; implement incrementally with contract tests |
| Date/time | DatePicker, Calendar, TimePicker | Verify date library and locale behavior before code; preserve format/parsing callbacks |
| Infrastructure | ConfigProvider, theme, message, notification | Treat as architecture work; do not migrate casually component-by-component |

## Primitive Facade

- Start from the closest shadcn source component when it exists.
- Preserve Ant public props, native passthrough, `className`, `rootClassName`, `style`, semantic slots, refs, and compound static members.
- Use `cva()` only when there is a real variant matrix; otherwise prefer direct `cn()` branches.

## Radix Behavior Component

- Use Radix primitives for dialog, popover, select, tooltip, accordion, tabs, checkbox, switch, slider, progress, and menu-like behavior only when source behavior aligns.
- Preserve Ant event names, callback signatures, default open/value behavior, portal behavior, ESC/Tab/focus order, and z-index/stacking context.
- Stop and explain if Radix cannot faithfully reproduce an Ant edge case without custom implementation.

## Form Control

- Controlled and uncontrolled semantics are first-class contract rows.
- Test callback timing, value precedence, disabled/loading/status states, IME composition, keyboard navigation, focus/blur order, and ARIA.
- Preserve passed React nodes for icon-like props; do not replace Ant-compatible node contracts with lucide-only APIs.

## Data Display

- Treat as phased migration. Do not one-shot Table, Tree, or infrastructure-heavy surfaces.
- Build contract slices: rendering, column/item model, selection, expansion, sorting/filtering, virtualization, accessibility, styling, and empty/loading states.
- Each phase needs source evidence and acceptance checklist closure.

## Date/Time

- Date library, locale, timezone, parsing, formatting, disabled date/time, panel state, and input behavior are separate compatibility surfaces.
- Do not infer date parsing or formatting behavior from docs examples alone.

## Infrastructure

- ConfigProvider, theme, message, and notification affect other components. Treat them as architecture work.
- Do not migrate an infrastructure dependency as a side effect of a leaf component unless the contract scopes and verifies the infrastructure behavior.
