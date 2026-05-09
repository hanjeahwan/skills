# Refactor Playbooks

Use this file when the user asks to refactor existing code toward a pattern or away from pattern misuse. Keep changes behavior-preserving unless the user explicitly asks for behavior change.

## Table Of Contents

- `General Refactor Loop`: shared behavior-preserving migration sequence.
- `Switch Or If/Else Explosion To Strategy`
- `Vendor SDK Spread To Adapter`
- `Global Singleton To Composition Root`
- `God Facade To Focused Facades`
- `State Conditionals To State Objects`
- `Command Extraction For Undo, Queue, Or Audit`
- `Decorator Or Proxy Around Cross-Cutting Behavior`
- `Builder For Unsafe Construction`
- `Pull Request Checklist For Pattern Refactors`

## General Refactor Loop

```text
┌──────────────────────┐
│ Find repeated change  │
│ pressure              │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Lock current behavior │
│ with focused evidence │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Introduce domain      │
│ contract              │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Move one variant      │
│ behind contract       │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Move callers          │
│ incrementally         │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Delete old branches   │
│ after parity          │
└──────────────────────┘
```

## Switch Or If/Else Explosion To Strategy

Use when the same condition appears in multiple methods or files.

1. Identify the domain action hidden inside each branch.
2. Add characterization tests around the current public behavior.
3. Define a narrow interface for the action.
4. Move one branch into one implementation.
5. Add a registry/factory at the composition boundary.
6. Move callers to the interface.
7. Delete the old branch only after focused tests pass.

Keep branch-specific validation inside the implementation, but normalize errors at the boundary.

## Vendor SDK Spread To Adapter

Use when domain code imports vendor classes, error types, request shapes, or response DTOs.

1. List every direct vendor import and the domain behavior it supports.
2. Characterize current success and failure behavior, especially vendor errors.
3. Define a domain-owned interface.
4. Implement an adapter that translates request, response, and error shapes.
5. Move one caller to the domain interface.
6. Replace direct vendor imports incrementally.
7. Add a guardrail test or lint rule if vendor leakage recurs.

Do not let adapter names leak the vendor into domain-facing interfaces.

## Global Singleton To Composition Root

Use when a global context hides configuration, clients, feature flags, or repositories.

1. Inventory every global access and group by capability.
2. Identify lifecycle and tenancy rules for each capability.
3. Add constructor or function parameters at the narrowest consuming boundary.
4. Create dependencies in the application composition root.
5. Move tests to pass fake dependencies explicitly.
6. Leave a temporary compatibility wrapper only when needed for incremental migration.
7. Remove the global after all consumers are moved.

Do not replace one global object with several global objects unless process-wide identity is genuinely required.

## God Facade To Focused Facades

Use when one facade becomes the dumping ground for unrelated workflows.

1. Group methods by user workflow, data ownership, and transaction boundary.
2. Preserve the external API if callers depend on it.
3. Extract focused facades or application services behind the existing facade.
4. Move tests from generic facade behavior to workflow-specific contracts.
5. Deprecate or remove pass-through methods that add no clarity.

A facade should make a workflow simpler, not hide the architecture.

## State Conditionals To State Objects

Use when many methods branch on the same lifecycle state.

1. Write a state/action matrix from current behavior.
2. Test valid actions, invalid actions, and transitions for each state.
3. Define a state interface with only lifecycle-dependent operations.
4. Move one state's behavior into a state object.
5. Keep persistence using stable state identifiers, not class names.
6. Remove duplicated branching after every action is covered.

Keep simple enums when there are only a few stable states and no scattered behavior.

## Command Extraction For Undo, Queue, Or Audit

Use when actions need metadata, durable execution, undo, retry, or permission checks.

1. Identify the receiver, action inputs, side effects, and authorization point.
2. Characterize current execution behavior.
3. Define a command contract with execution result and optional undo.
4. Extract one action into a command.
5. Add command history, queue, or audit only when required by the use case.
6. Define idempotency and serialization before remote execution.

Avoid command objects for simple direct calls that do not need identity.

## Decorator Or Proxy Around Cross-Cutting Behavior

Use when optional behavior wraps a stable contract: caching, authorization, tracing, compression, encryption, lazy loading.

1. Define the subject/component interface from caller expectations.
2. Add contract tests for the base implementation.
3. Add one wrapper and run the same contract tests through it.
4. Centralize wrapper assembly and order.
5. Test cache invalidation, auth denial, error propagation, and wrapper order.

If the wrapper changes the contract, it is not a safe decorator/proxy.

## Builder For Unsafe Construction

Use when constructors have too many optional parameters, invalid combinations, or order-dependent setup.

1. List valid and invalid construction scenarios.
2. Add tests for missing required inputs and invalid combinations.
3. Make the final built value immutable or copy mutable inputs.
4. Keep validation in `build` or in typed steps, not scattered across callers.
5. Remove old constructors only after callers are migrated.

Do not use a builder just to avoid naming a parameter object.

## Pull Request Checklist For Pattern Refactors

- The PR states the behavior boundary and what must not change.
- Current behavior is protected before structural edits.
- The new abstraction has domain naming and one reason to change.
- Old and new paths do not diverge silently during migration.
- Contract tests prove substitutability.
- Pattern assembly happens in one obvious place.
- The refactor removes duplicated change pressure or concrete coupling.
- Remaining temporary compatibility code has an owner and removal condition.
