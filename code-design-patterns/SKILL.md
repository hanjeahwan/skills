---
name: code-design-patterns
description: Guides design pattern selection, application, refactoring, review, documentation, and explanation for SOLID, OOP design principles, object collaboration, and pattern names such as Factory, Builder, Adapter, Strategy, Observer, Command, Proxy, Facade, Decorator, State, Visitor, and Singleton. Use when production services, SDKs, domain models, plugins, workflows, UI architecture, integrations, or legacy refactors need context-first pattern decisions, implementation boundaries, code sketches, contract tests, or pattern-misuse review.
argument-hint: "[code path, design problem, pattern candidate, review target, or architecture decision]"
user-invocable: true
---

# Enterprise Design Patterns

Use this skill to turn design pattern knowledge into production-quality architecture decisions and implementation boundaries. The goal is not to name a pattern; the goal is to stabilize a real variation point, reduce coupling, and leave code easier to test and evolve.

This skill distills the user's local copy of *Dive Into Design Patterns* by Alexander Shvets together with enterprise maintainability practice. Do not reproduce long passages from the source material. Use pattern names and paraphrased concepts, then ground every recommendation in the current codebase or the user's stated scenario.

## Consistent Terminology

Use these terms consistently throughout outputs:

| Term | Meaning |
|---|---|
| `contract` | The caller-facing promise: inputs, outputs, errors, side effects, and invariants |
| `interface` | A language-level or framework-level construct that expresses all or part of a contract |
| `boundary` | The module/class/service edge where a contract is owned and concrete details are hidden |
| `variant` | One interchangeable implementation behind a boundary, such as a provider, format, algorithm, state, or handler |
| `composition root` | The place where concrete variants are wired together |
| `verification` | Tests, type checks, browser checks, scripts, or runtime probes that prove the contract |

Do not use `URL`, `API route`, `endpoint`, and `path` interchangeably. If the topic is not HTTP, prefer `boundary`, `code path`, or `migration path` according to the meaning above.

## Operating Model

```text
┌──────────────────────┐
│ Real user pressure    │
│ or code smell         │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Forces and variation  │
│ axes                  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Smallest useful       │
│ pattern boundary      │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Tests, contracts,     │
│ and migration plan    │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Decision record or    │
│ implementation patch  │
└──────────────────────┘
```

## When You Trigger

Classify the request first:

| Request shape | Primary output |
|---|---|
| "Which pattern should we use?" | Recommendation memo with forces, chosen pattern, rejected alternatives, and tests |
| "Refactor this code" | Behavior-preserving refactor plan or patch, with characterization evidence before edits |
| "Review this design/PR" | Findings first, ordered by risk, with pattern fit and maintainability concerns |
| "Explain this pattern" | Reality-based explanation: user scenario first, mechanism second, implementation cautions third |
| "Write an ADR/design doc" | Decision record focused on context, forces, consequences, migration, and verification |

Ask a clarifying question only when the missing answer changes the correct design: ownership boundary, runtime variability, compatibility requirements, concurrency model, persistence semantics, or whether behavior may change.

## Workflow

### 1. Anchor In A Real Scenario

State the concrete pressure before naming any pattern. Examples:

- A payments team needs to add providers without touching checkout orchestration.
- A reporting API needs different export algorithms selected per tenant.
- A legacy SDK has a useful class but exposes the wrong interface for current clients.
- A UI command history needs undo, queueing, and auditability.

If working in a repo, inspect callers, tests, interfaces, and existing conventions before recommending a pattern.

### 2. Extract The Forces

Build a short force map:

| Force | Questions to answer |
|---|---|
| Variation axis | What changes independently: product family, algorithm, state, transport, persistence, UI action, traversal, notification, authorization? |
| Creation ownership | Who should know concrete classes, defaults, caches, object lifetime, and dependency wiring? |
| Collaboration shape | Is the problem one-to-one wrapping, one-to-many notification, chain traversal, tree composition, or centralized coordination? |
| Runtime behavior | Must behavior switch at runtime, per tenant, per request, per feature flag, or only at compile/config time? |
| Compatibility | Which public API, database contract, event schema, or UI behavior must stay stable? |
| Operational risk | What are the performance, concurrency, observability, security, rollout, and rollback constraints? |
| Testability | What focused test proves the pattern boundary works without coupling to internals? |

### 3. Choose The Smallest Pattern Boundary

Use the decision guide in `references/selection-guide.md`. Prefer the simplest design that isolates the real variation point:

- Use a plain function, module, map, or dependency injection when that solves the problem cleanly.
- Use one primary pattern unless the forces are genuinely independent.
- Prefer composition over inheritance for runtime variability, testability, and gradual rollout.
- Keep domain names ahead of pattern names. `PaymentProvider`, `ExportStrategy`, or `AuditCommand` is usually clearer than exposing generic pattern vocabulary.
- Treat Singleton as a last resort for identity or process-wide coordination, not as a shortcut for dependency access.

When the request is about design principles, SOLID, object relations, or whether a pattern is justified at all, read `references/design-foundations.md` before selecting a pattern.

When the request is about a specific pattern or pattern comparison, read `references/pattern-anatomy.md` so the answer covers problem, solution, structure, applicability, implementation, costs, related patterns, and verification.

### 4. Move From Pattern To Code Shape

When the user asks for implementation guidance or code, read `references/code-reference.md` before writing code. Choose the closest skeleton, then adapt it to the repository's language, dependency injection style, error model, and test framework.

When the user asks for refactoring, read `references/refactor-playbooks.md` before proposing or editing. Refactors should move one variant or caller at a time and keep old behavior protected until the obsolete path is deleted.

Code output should include:

- the domain-owned interface or contract
- one concrete implementation or wrapper
- the composition/registry boundary where concrete classes are wired
- the focused test or contract-test shape that proves substitutability, with concrete scenarios or test names
- migration notes for moving existing callers safely

When the user asks for tests, code references, or implementation sketches, include a `Verification` or `Contract Tests` section with concrete test cases. Do not stop at "add tests" or a vague test category.

### 5. Make The Design Testable

For code changes, establish evidence before implementation:

- New behavior: write or identify an acceptance/contract test that fails before the change.
- Refactor: find or add characterization tests that pass before and after.
- Integration pattern: use an integration test around the boundary, not just a unit test of private helpers.
- UI behavior: use component or browser evidence for user-visible states.

The pattern is not accepted until the test proves the intended decoupling or behavior.

### 6. Document Consequences

Every enterprise pattern recommendation should include:

- `Context`: the user/business pressure and current code shape.
- `Forces`: what varies, what must stay stable, and what operational constraints matter.
- `Recommended pattern`: one primary pattern, named with the domain boundary it protects.
- `Why this pattern`: mechanism and concrete benefits.
- `Rejected alternatives`: only serious alternatives that someone on the team might reasonably choose.
- `Implementation boundary`: interfaces, classes/modules, ownership, lifecycle, and migration sequence.
- `Verification`: tests, type checks, browser checks, or runtime probes.
- `Consequences`: complexity added, team conventions, rollout and rollback notes.

## Reference Routing

Read only the file needed for the current task:

- `references/selection-guide.md`: choosing a pattern from forces, symptoms, and constraints.
- `references/design-foundations.md`: OOP relations, reuse/extensibility, encapsulate variation, program to interface, composition over inheritance, and SOLID pressure tests.
- `references/pattern-catalog.md`: concise catalog of GoF patterns with enterprise fit, cautions, and verification clues.
- `references/pattern-anatomy.md`: pattern-specific cards and source-book-style explanation structure for all 22 GoF patterns.
- `references/code-reference.md`: implementation skeletons, contract boundaries, and test shapes for common enterprise pattern applications.
- `references/pattern-code-sketches.md`: compact code sketches and code coverage map for all 22 GoF patterns, especially patterns not expanded in `code-reference.md`.
- `references/refactor-playbooks.md`: incremental behavior-preserving migrations from concrete smells to pattern boundaries.
- `references/enterprise-review-checklist.md`: reviewing code, plans, PRs, or ADRs for pattern misuse and maintainability risk.
- `references/source-alignment.md`: PDF-to-skill coverage map and re-audit checklist for future skill maintenance.
- `scripts/verify_skill.py`: deterministic coverage checker; run it after editing this skill, with `--pdf` when the source PDF is available.

Use reference files as internal working material. Do not cite skill reference file paths in normal user-facing answers unless the user explicitly asks to audit, maintain, or inspect this skill.

For audit or verification requests about this skill, run `scripts/verify_skill.py` when the local filesystem and Python are available. Report the command and result. If the source PDF is available, include `--pdf`; otherwise run the local structure check and say the PDF-specific outline check was skipped.

If the user or harness forbids reading `evals/evals.json`, run `scripts/verify_skill.py --skip-evals` and clearly report that eval coverage was skipped. Do not replace the script with an ad hoc inline verifier unless the script itself cannot run.

## Output Templates

### Recommendation Memo

```markdown
## Scenario
<real user or business pressure>

## Forces
| Force | Evidence |
|---|---|

## Recommendation
Use <pattern> at <boundary>.

## Why
<mechanism tied to the forces>

## Rejected Alternatives
| Alternative | Why not |
|---|---|

## Implementation Boundary
<interfaces/modules/classes and migration order>

## Verification
- `<command or test>`: <expected proof>

## Consequences
<complexity, rollout, ownership, residual risk>
```

### Implementation Sketch

```markdown
## Target Boundary
<domain-owned interface and concrete ownership>

## Code Shape
<minimal skeleton adapted to the repo's language and conventions>

## Wiring
<composition root, registry, factory, or module boundary>

## Contract Tests
<shared tests or focused verification proving implementations are substitutable>

## Migration
<small caller-by-caller sequence with rollback point>
```

### Refactor Plan

```markdown
## Behavior Boundary
<observable behavior that must stay stable>

## Current Evidence
<tests, callers, logs, screenshots, or fixtures>

## Pattern Boundary
<where the pattern starts and ends>

## Migration Steps
1. <small behavior-preserving step>
2. <small behavior-preserving step>
3. <remove old path after parity>

## Verification
<focused then wider checks>
```

### Code Review Findings

Lead with issues, not praise. For each finding include:

```markdown
- [Severity] <problem>
  File/line: <path:line>
  Scenario: <real failure or maintenance pressure>
  Mechanism: <why the pattern choice or absence causes the problem>
  Recommendation: <smallest safe correction>
  Verification: <test or check that would catch it>
```

## Quality Bar

Before finishing, verify:

- The recommendation is anchored in a concrete force, not a pattern preference.
- Foundation principles are checked before adding pattern ceremony.
- The chosen pattern has a narrow ownership boundary.
- Code guidance includes a concrete interface, implementation, wiring boundary, and verification shape when the user asks for implementation.
- Pattern-specific explanations distinguish problem, solution, structure, applicability, implementation, pros/costs, related patterns, and verification.
- Public contracts and behavior compatibility are explicit.
- Tests or equivalent evidence prove the intended behavior.
- The design reduces coupling or repeated change cost more than it adds indirection.
- Remaining risks are named instead of hidden behind pattern terminology.
