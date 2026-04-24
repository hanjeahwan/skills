# Learnings and Profile Evolution

Use this reference after verification and before final acceptance. It keeps migration experience reusable across source libraries.

## Migration Learning Format

```markdown
## <Source Library> <Component> - <short issue title>

id: ui-migration-YYYYMMDD-001
date: <YYYY-MM-DD>
source_library: <AntD | MUI | Chakra | ...>
component: <Button | Select | ...>
component_class: <primitive | form-control | overlay | data-display | date-time | infrastructure>
target_stack: <Next.js | Vite | Tailwind v4 | shadcn path | test framework>
edge_gates: <01, 04, 07, 14>
status: <local-learning | promoted-to-profile | promoted-to-core | rejected>
promoted_to: <profile section, SKILL.md section, checklist item, or none>
target_repo: <path or repo name>
source_evidence: <source paths/version/commit/docs>

### Trigger
<error, visual issue, user feedback, failing command, or test failure pattern>

### Symptom
<user-visible or test-visible failure>

### Root cause
<logic-level cause tied to source evidence and target stack>

### Fix
<specific change that resolved the issue>

### Verification
<commands, tests, browser checks, or benchmark assertions>

### Prevention
<future contract row, red test, profile rule, source file to inspect, or non-goal>

### Regression assertion
<objective assertion mapped to test, benchmark, contract, checklist, or source-backed non-goal>

### Backfill scan
<sibling migrated components and shared primitives scanned, matches, fixes, or source-backed non-goals>

### Skill/profile evolution
<new profile rule, core skill rule, or reason not promoted>
```

## Regression Closure

- Every new learning's regression assertion must map to a repo test, benchmark assertion, contract row, acceptance checklist row, or documented source-backed non-goal.
- `Learnings/profile updates captured` cannot pass while new learnings have unmapped assertions.
- Promoted learnings must name the exact profile/core section they update.
- When promoted, scan already migrated sibling components and shared primitives for the same failure class.
- Profile-specific findings belong in `profiles/<library>.md`; cross-library findings belong in `SKILL.md` or references.

## Profile Promotion

Promote a temporary profile into a real profile when:

- Two migrations use the same source library.
- The discovery path is stable and source-backed.
- The profile has deny patterns for source CSS leakage.
- The profile defines API, demo, theme/token, slot/style, internal primitive, and deprecated/legacy policies.

## Benchmark and Viewer Gate

For skill development or migrations claiming full source-library compatibility, create reviewable benchmark/viewer artifacts. For real migrations, record benchmark/viewer scope in the contract.

Benchmark assertions must cover profile decision, profile discovery for unknown libraries, Tailwind-first styling, demo parity, no source CSS leakage, independent verifier evidence, side-branch audit closure, false-pass prevention, and learning/profile backfill.
