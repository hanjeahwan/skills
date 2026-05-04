---
name: parity-test-first
description: "Use this skill whenever a coding task might change observable behavior, including refactors, bug fixes, new features, migrations, rewrites, dependency upgrades, performance changes, API changes, test-failure repairs, and behavior-preserving cleanup. It enforces a parity-test-first workflow: define the behavior boundary, capture current or expected behavior with focused tests or equivalent evidence before implementation, verify the pre-change red/green state that matches the task type, implement the smallest safe change, and prove parity before reporting completion."
argument-hint: "[task description, affected files, or behavior boundary]"
user-invocable: true
---

# Parity Test First

Use this skill to make behavior evidence lead the implementation. The goal is not "write tests because tests are good"; the goal is to prevent accidental behavior drift while changing code.

## Operating Model

```text
┌──────────────────────┐
│ Behavior boundary     │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Existing evidence     │
│ and project patterns  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Parity matrix         │
│ preserve/change/new   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ First verification    │
│ red or green by mode  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Minimal implementation│
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Focused verification  │
│ then wider checks     │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Final evidence report │
└──────────────────────┘
```

## Task Modes

Classify the task before editing code. The first verification state depends on the mode.

| Mode | First evidence | Expected pre-change result | Proceed when |
|---|---|---|---|
| Refactor / cleanup | Characterization or existing tests for current public behavior | Green before the refactor | The invariant is protected and scoped |
| Bug fix | Minimal reproducer, failing test, or failing command for the reported bug | Red for the exact failure | The failure is observed and tied to the suspected code path |
| New feature | Acceptance test or executable contract for the new expected behavior | Red because behavior does not exist yet | The expected behavior is explicit and reviewed against project conventions |
| Migration / rewrite | Source behavior fixtures plus target parity tests | Source passes; target is red until implemented | Every source behavior has a target landing site or is blocked |
| Dependency / performance change | Before/after contract, snapshot, benchmark, or integration test | Green on old behavior | The intended non-functional change does not alter public behavior unless approved |
| Test-failure repair | Deterministic reproduction of the failing test or flaky condition | Red under controlled conditions | The failure mode is isolated enough to avoid weakening the test |

For bug investigations, capture the failure first. If active project or user instructions require human confirmation before fixing, stop after presenting the failure evidence and root cause.

## Characterization Tests

Characterization tests capture the current observable behavior of existing code. Use them when the task promises behavior preservation, especially when the implementation is hard to understand, under-tested, legacy, or about to be refactored.

Do not treat characterization tests as the default for every task. They answer "what does this already do?" not "what should the new behavior be?"

```text
┌──────────────────────┐
│ Existing behavior     │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Characterization test │
│ green before change   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Refactor / migrate    │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Same behavior proven  │
│ green after change    │
└──────────────────────┘
```

Use characterization tests this way:

- **Refactor / cleanup:** make characterization tests the default first evidence when existing tests do not already protect the behavior boundary. They must be green before edits and green again after.
- **Migration / rewrite:** characterize the source implementation with fixtures, golden outputs, or source-path tests; then write target parity tests. Source evidence should be green while target tests are red until implementation.
- **Bug fix:** start with a minimal failing reproducer for the bug, not a characterization test for the broken behavior. Add characterization tests for adjacent behavior that must stay unchanged.
- **New feature:** start with acceptance or contract tests for the new behavior. Characterize existing behavior only where the feature must integrate with or preserve an existing flow.
- **Visual-only change:** prefer screenshot, browser, Figma, and accessibility/interaction checks. Do not force characterization tests unless the visual change touches behavior.

Good characterization tests:

- Assert public outputs, state transitions, side effects, errors, serialization, or user-visible UI behavior.
- Use realistic fixtures from current callers, factories, production-shaped data, or source examples.
- Preserve current behavior without blessing it as correct. If behavior looks suspicious, label it `current behavior` and ask before changing it.
- Avoid coupling to private helper structure, branch shape, or incidental implementation details.

## Pressure Handling

Users often ask for the exact shortcut that would make a parity-first workflow unsafe: "skip tests", "no reproducer", "just patch it", "relax the assertion", "fix the legacy bug during the port", or "make it like the old page" without naming the old contract.

When that happens, explicitly call out the conflict before continuing:

```markdown
Pressure conflict: <quote or summarize the shortcut request>
Evidence path: <the first test, reproducer, source fixture, screenshot, or blocked question required before implementation>
Proceed only after: <green/red pre-change condition appropriate to the task mode>
```

Use the exact labels below when they apply; they make the safety decision easy to audit in reviews and agent transcripts:

- `Pressure conflict:` for any shortcut pressure.
- `Do not invent:` when source behavior, API shape, CSV columns, filters, routes, side effects, or old-system contracts are missing.
- `Do not weaken:` when the user asks to relax, skip, delete, downgrade, or content-strip a test/assertion.

Use these patterns:

- **Skip tests / skip verification pressure:** state that behavior-preserving work cannot skip tests or equivalent executable evidence. For refactors, require green characterization or existing tests before implementation.
- **No reproducer / quick patch pressure:** state that bug fixes require a minimal failing reproducer, failing test, or failing command for the exact reported behavior before implementation.
- **Ambiguous old-system parity:** state `Do not invent:` for the missing contract. If old columns, filters, routes, side effects, or source behavior cannot be discovered from code/tests/docs, mark the row `BLOCKED` and ask for the missing decision.
- **Migration plus cleanup pressure:** separate `PRESERVE` rows from explicit `CHANGE` rows. A legacy behavior can change only when the user request is specific enough to test the new behavior, and source parity still protects the rest.
- **Relax / skip flaky test pressure:** state `Do not weaken:` for the protected assertion. Fix waits, clocks, schedulers, selectors, test isolation, or the product race while preserving the user-visible assertion. Skipping, broad sleeps, generic "any toast" checks, and content-free smoke assertions are not parity evidence.
- **Visual-only pressure:** use screenshot, browser, design comparison, and accessibility/interaction checks as the primary evidence. Do not force unit tests when the requested change is purely visual and behavior remains unchanged.

## Workflow

### 1. Define the Behavior Boundary

Identify exactly what may change from a user's point of view:

- Inputs and outputs.
- Error states and exception types.
- Persistence, network requests, emitted events, logs, queues, and other side effects.
- UI states, accessibility behavior, routing, and form validation.
- Timing, caching, ordering, retries, and idempotency.
- Public API contracts, database writes, serialization, and authorization decisions.

Exclude implementation details unless they are part of the observable contract.

### 2. Read Existing Evidence First

Before creating tests or editing code, inspect:

- Existing tests near the affected module.
- Fixtures, factories, mocks, snapshots, and test helpers.
- The implementation and its public callers.
- Project instructions such as `AGENTS.md`, `CLAUDE.md`, `README.md`, testing docs, and package scripts.
- Library or framework documentation when an API, type signature, or tool behavior is not certain.

Prefer the project's existing test style over a new harness.

### 3. Build a Parity Matrix

For non-trivial changes, create a short working matrix in the plan, commit message draft, PR notes, or a temporary scratch file. Keep it only if the project benefits from the artifact.

```markdown
| ID | Scenario | Current/source evidence | Expected invariant or intended delta | Verification | Pre-change result | Post-change result | Status |
|---|---|---|---|---|---|---|---|
| P1 | <user-visible case> | <file:test/log/source path> | PRESERVE / CHANGE / NEW | <test command> | red/green/not run | red/green/not run | open/pass/blocked |
```

Use these status meanings:

- `PRESERVE`: behavior must stay the same.
- `CHANGE`: behavior intentionally changes because the user requested it or the bug fix requires it.
- `NEW`: behavior did not exist before.
- `BLOCKED`: expected behavior, source evidence, or verification path is unclear.

Do not implement rows marked `BLOCKED`. Resolve them by reading more evidence or asking the user.

### 4. Choose the Lowest Reliable Verification Level

Use the narrowest test that proves the behavior without coupling to irrelevant internals.

| Behavior | Preferred verification |
|---|---|
| Pure calculation, parser, mapper, validator | Unit test |
| Service orchestration, database, API calls, auth, queues | Integration test |
| UI state, form behavior, component events | Component test |
| Critical user journey or routing flow | E2E test |
| Migration / rewrite parity | Source fixture plus target contract test |
| Performance or caching | Benchmark plus behavioral regression test |
| Visual-only style change | Screenshot or browser check, with tests only for behavior |

### 5. Establish First Verification

Run or create the focused verification before implementation.

- For refactors, the parity test should usually pass before edits. It proves the existing behavior is now locked.
- For bug fixes and new features, the test should fail before edits. It proves the test can catch the missing or broken behavior.
- For migrations, source behavior should be executable or cited, and target parity tests should fail until target code exists.
- For flaky tests, reproduce the failure under a controlled seed, clock, network mock, or scheduler before changing code.

If the test result does not match the mode, fix the test or the scope before continuing.

### 6. Implement the Smallest Safe Change

Make the narrowest implementation that satisfies the parity matrix.

- Do not broaden scope while making the test pass.
- Do not weaken assertions, skip tests, delete coverage, or alter fixtures to hide the problem.
- Do not use `any`, `@ts-ignore`, disabled lint rules, non-null assertions, or TypeScript type assertions to force a pass.
- Do not invent external library APIs. Verify with Context7, official docs, installed type definitions, or source.
- Prefer explicit control flow, type guards, precise types, and project-owned helpers.

### 7. Verify in Rings

Run checks in this order:

1. The focused parity test or reproducer.
2. Adjacent tests for the same module or feature.
3. Typecheck, lint, build, or package-specific verification when the change touches shared contracts.
4. Browser, E2E, database, migration, or integration checks when user-visible workflows or side effects are involved.

Stop on the first failure that is causally related to the change. Diagnose it before expanding verification.

## Test Design Rules

- Name tests after behavior, not implementation details.
- Use realistic fixtures from existing factories, source data, API contracts, or production-shaped examples.
- Assert public outputs, state transitions, side effects, and error behavior.
- Avoid snapshots for broad objects unless the project already uses reviewed golden files for that contract.
- For refactors, prefer characterization tests that lock current behavior before changing internals.
- For bug fixes, the test name should describe the user-visible failure and the corrected behavior.
- For new features, encode the acceptance rule, not every implementation branch.
- For migrations, every source behavior either maps to a target test, a source-backed non-goal, or a blocker.

## Stop Conditions

Stop and ask for alignment when:

- The expected behavior is ambiguous and cannot be inferred from code, docs, tests, or user request.
- The project has no reliable way to verify the behavior and creating one would be a larger design decision.
- Existing tests contradict the requested change.
- A parity-preserving change conflicts with architecture, security, or data integrity constraints.
- The only way to pass is to weaken tests, lie to the type system, or bypass validation.
- A migration or rewrite has source behavior that cannot be mapped to the target architecture.

## Final Report

When work is complete, report:

```markdown
Changed files:
- <path>: <what changed>

Parity evidence:
- <behavior ID or scenario>: <pre-change result> -> <post-change result>

Verification:
- `<command>`: pass/fail and important output

Residual risk:
- <unverified area, or "none known">
```

Do not say the work is complete until the relevant parity evidence and focused verification have passed, or until you clearly report what could not be verified.
