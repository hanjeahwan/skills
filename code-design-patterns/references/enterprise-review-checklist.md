# Enterprise Review Checklist

Use this checklist when reviewing a proposed pattern, existing code, a PR, or an ADR.

## Table Of Contents

- `Review Flow`: review sequence from behavior to operational risks.
- `Correctness And Contracts`: contract and substitution checks.
- `Maintainability`: abstraction and naming checks.
- `Testability`: required verification by pattern type.
- `Enterprise Operations`: observability, security, performance, rollout, and rollback.
- `Red Flags`: common pattern misuse signals.
- `Review Output Shape`: findings-first format.
- `ADR Quality Bar`: decision-record readiness checks.

## Review Flow

```text
┌──────────────────────┐
│ Observable behavior   │
│ and contracts         │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Variation axes and    │
│ ownership boundaries  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Pattern fit and       │
│ simpler alternatives  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Verification and      │
│ operational risks     │
└──────────────────────┘
```

Lead with concrete findings. Do not give a pattern lecture unless the user asked for teaching.

## Correctness And Contracts

- The pattern preserves public API, event schema, persistence semantics, and UI behavior unless a change is explicit.
- Interfaces encode real capabilities, not convenient buckets of methods.
- Subtypes, strategies, handlers, and proxies preserve preconditions, postconditions, exceptions, and idempotency.
- Creation logic does not bypass validation, authorization, tenant isolation, or lifecycle rules.
- Error propagation remains visible; facades and proxies do not flatten important failures into vague errors.

## Maintainability

- The abstraction has one clear reason to change.
- Domain names explain the business concept; pattern names stay internal.
- The pattern removes repeated conditional logic, duplicate construction, or direct vendor coupling.
- The implementation does not introduce subclass matrices, god mediators, oversized facades, or catch-all base classes.
- New variants can be added in a predictable place with focused tests.
- The team can understand and operate the abstraction without specialized pattern knowledge.

## Testability

- There is a contract test for interchangeable implementations.
- Refactors have characterization tests before behavior-preserving edits.
- Integration boundaries are tested where frameworks, databases, queues, network clients, or auth are involved.
- Caches, proxies, decorators, and chains have order, invalidation, fallback, and error tests.
- State machines cover allowed transitions, blocked actions, and persistence/recovery if relevant.
- Event or observer flows cover duplicate, missing, delayed, and failed subscriber behavior when those cases matter.

## Enterprise Operations

- Observability names the pattern boundary in logs/metrics/traces through domain terms.
- Security checks stay close to the boundary that enforces access, not hidden inside optional wrappers.
- Performance assumptions are measured when using Flyweight, Proxy caching, lazy loading, or deep decorators.
- Concurrency and lifecycle are explicit for Singleton, caches, shared factories, and mutable builders.
- Rollout can happen incrementally behind a stable contract or feature flag when the blast radius is large.
- Rollback does not require data loss or breaking persisted command/event/snapshot formats.

## Red Flags

| Red flag | Why it matters | Better direction |
|---|---|---|
| Pattern chosen before forces are named | Adds ceremony without solving a change pressure | Write the force map first |
| `Manager`, `Helper`, or `Service` owns unrelated pattern roles | Hides responsibilities and makes tests vague | Split by domain boundary or workflow |
| Singleton used to reach configuration or clients | Creates hidden dependencies and test coupling | Inject dependencies from the composition root |
| Strategy implementations require different caller setup | Violates substitutability | Normalize contract or use separate workflows |
| Facade hides transaction, auth, or retry behavior | Makes failures hard to reason about | Make operational semantics explicit in the facade contract |
| Decorators mutate shared state unpredictably | Wrapper stacks become order-sensitive bugs | Define order and immutability rules |
| Observer used for critical durable workflows without delivery semantics | Lost or duplicated events become production incidents | Use a queue/event bus contract with retry and idempotency |
| Visitor added while element types are still changing | Every new type creates broad churn | Keep operations on elements or use pattern matching until stable |

## Review Output Shape

Use this structure for review tasks:

```markdown
## Findings

- [P1] <behavioral, contract, or maintenance risk>
  File/line: <path:line>
  Scenario: <real user or operator pressure>
  Mechanism: <why the current pattern choice fails>
  Recommendation: <smallest correction>
  Verification: <test/check>

## Open Questions
<only blockers that change the recommendation>

## Residual Risk
<unverified area or none known>
```

Severity guide:

| Severity | Meaning |
|---|---|
| P0 | Data loss, security issue, production outage, or broken critical path |
| P1 | Likely correctness regression, contract break, or high-cost maintainability problem |
| P2 | Moderate maintainability, testability, or operational risk |
| P3 | Minor clarity or convention issue |

## ADR Quality Bar

An ADR or design doc is ready when it answers:

- What real change pressure caused this decision?
- What code or system boundary owns the abstraction?
- Which behavior and contracts stay stable?
- Which serious alternatives were rejected and why?
- What tests prove the chosen boundary?
- What migration and rollback path exists?
- What new operational responsibility appears?
