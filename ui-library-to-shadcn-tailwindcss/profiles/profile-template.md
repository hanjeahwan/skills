# Source Library Profile Template

profile_id: <library-id>
source_library: <display name>
aliases: <comma-separated trigger names>
source_repo_default: <path, package, docs URL, or unknown>
runtime_css_deny_patterns:
- "<source class selector regex>"
- "<source css variable regex>"

## Discovery

| Fact type | Primary paths or docs |
|---|---|
| Exports | <source> |
| Props/types/defaults | <source> |
| Docs/API | <source> |
| Demos/examples | <source> |
| Tests | <source> |
| Styles/theme | <source> |
| Context/providers | <source> |
| Internal primitives | <source> |

## Library-Specific Rules

- Public API extraction: <how to verify props/types/events/defaults>.
- Theme/token mapping: <how source tokens map to shadcn/Tailwind v4>.
- Slot/class/style API: <semantic hooks and override behavior>.
- Internal delegation: <wrapped primitives/hooks/packages to inspect>.
- Deprecated/legacy policy: <default decision>.
- Docs demo parity: <where examples live and how to map them>.

## Common Edge Cases

- <library-specific risk>
