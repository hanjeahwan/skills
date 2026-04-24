# Component Classes

Use this to choose implementation strategy after selecting a source profile.

| Class | Examples | Strategy |
|---|---|---|
| Primitive facade | Button, Tag, Badge, Avatar | shadcn component plus source-compatible props and variants |
| Radix behavior component | Modal, Drawer, Tooltip, Popover, Dropdown, Tabs, Collapse | Radix/headless primitive with source event/default adapters when behavior matches |
| Form control | Input, Select, Checkbox, Radio, Switch, Slider | Preserve controlled/uncontrolled behavior, form attributes, keyboard/IME, a11y, and validation surfaces |
| Data display | Timeline, Steps, List, Card, Tree | Preserve layout/style graph, semantic slots, visual tokens, connectors, and docs demos |
| Date/time | DatePicker, Calendar, TimePicker | Treat parsing, locale, timezone, range logic, disabled dates, and formatting as primary behavior |
| Infrastructure | Form, Table, Upload, Menu | Use phased contracts; migrate supporting primitives before claiming full compatibility |

## Primitive Facade

- Preserve source public props, native passthrough, class/style hooks, semantic slots, refs, and compound static members.
- Use shadcn/Tailwind utilities first; bridge variables only for runtime compatibility.

## Radix Behavior Component

- Match source open/defaultOpen/value/defaultValue precedence, callback timing, focus order, portal behavior, ESC/Tab handling, and stacking context.
- Stop and explain if Radix/headless primitives cannot reproduce a source edge case without custom implementation.

## Form Control

- Verify IME, keyboard, composition, blur/focus order, disabled/readOnly/loading, validation, ARIA, and native form behavior.
- Preserve React node contracts for icons/render props; do not replace compatible node APIs with lucide-only APIs.

## Data Display

- Style graph is behavior. Assert text metrics, slot placement, connector endpoints, marker/icon sizes, state colors, responsive behavior, and viewer shell isolation.

## Date/Time

- Do not migrate date/time components without source-backed locale, timezone, parsing, formatting, disabled, range, and keyboard contracts.

## Infrastructure

- Split infrastructure components into phases with source-backed non-goals for unsupported surfaces.
- Full compatibility requires docs demo parity and verifier evidence for each phase.
