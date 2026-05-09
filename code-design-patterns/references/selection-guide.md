# Pattern Selection Guide

Use this guide when choosing a pattern, rejecting a proposed pattern, or turning a code smell into a refactor direction.

## Table Of Contents

- `Force-First Selection`: decision flow before naming a pattern.
- `Quick Selection Table`: pattern selection by force.
- `Symptom To Pattern`: code smells mapped to likely forces.
- `Enterprise Decision Questions`: questions before recommending a pattern.
- `Combination Rules`: safe pattern combinations and risks.
- `Anti-Pattern Checks`: when not to use a pattern.
- `Verification Patterns`: proof required by pattern family.

## Force-First Selection

```text
┌──────────────────────┐
│ What changes often?   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Who should be unaware │
│ of that change?       │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ What boundary can     │
│ absorb the change?    │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Which pattern makes   │
│ that boundary explicit│
│ with least ceremony?  │
└──────────────────────┘
```

Do not start from "we need a pattern." Start from repeated change pressure or a concrete dependency problem.

## Quick Selection Table

| Problem force | First pattern to consider | Use when | Prefer not when |
|---|---|---|---|
| Client should not know concrete product classes | Factory Method | One product varies and subclasses/configuration choose the concrete type | A simple constructor or DI container binding is enough |
| Need families of compatible products | Abstract Factory | Products must be created in matched sets, such as platform widgets or provider-specific clients | Only one product type varies |
| Complex construction has optional steps or representations | Builder | Construction is multi-step, order-sensitive, or overloaded constructors are spreading | The object has a few stable parameters |
| Need copies without coupling to concrete classes | Prototype | Runtime-configured objects should be cloned or templated | Copying is simple data copying with clear types |
| One process-wide identity is truly required | Singleton | There is one conceptual instance and lifecycle is controlled | It is only being used to avoid passing dependencies |
| Existing interface does not match client needs | Adapter | A legacy or third-party dependency is useful but incompatible | You can change the source interface cleanly |
| Abstraction and implementation vary independently | Bridge | Two dimensions of variation would otherwise create subclass explosion | There is only one dimension of variation |
| Part-whole hierarchy should be treated uniformly | Composite | Leaves and containers need the same operations | The hierarchy is shallow and explicit branching is clearer |
| Add responsibilities around an object dynamically | Decorator | Behavior stacks independently, such as compression, encryption, logging, or validation | The behavior is mandatory and belongs in the core object |
| Hide subsystem complexity behind a stable entry point | Facade | Clients need a simpler API over many classes/services | The facade would become a dumping ground for unrelated operations |
| Many similar objects duplicate large immutable state | Flyweight | Memory pressure is proven or likely at scale | Object count is low or shared state risks correctness |
| Control access to another object | Proxy | Need lazy loading, caching, remote access, authorization, rate limits, or audit around a subject | The wrapper changes the subject contract unexpectedly |
| Request should pass through ordered handlers | Chain of Responsibility | Multiple handlers may process or decline a request | Ordering and failure semantics cannot be made explicit |
| Request should become a durable object | Command | Need queueing, retry, undo, audit, scheduling, or transport | A direct function call is sufficient and no metadata is needed |
| Collection traversal should hide representation | Iterator | Clients should traverse trees, pages, cursors, or remote collections uniformly | Native language iteration already exposes the right abstraction |
| Many components communicate chaotically | Mediator | Coordination rules are centralized and direct dependencies are growing | The mediator would become an opaque god object |
| Object state must be snapshotted privately | Memento | Need undo/restore without exposing internals | State can be represented as a simple explicit DTO |
| Many subscribers react to publisher events | Observer | One publisher event fans out to independent listeners | Ordering, delivery, and retry need stronger event infrastructure |
| Behavior depends on internal state | State | State transitions change which operations are valid | A small enum and switch are clearer and stable |
| Algorithm varies behind one task | Strategy | Different algorithms are interchangeable per request, tenant, or configuration | The algorithms are not actually substitutable |
| Algorithm skeleton is stable but steps vary | Template Method | Inheritance is already the right extension mechanism | Runtime composition or dependency injection is needed |
| Add operations across stable object types | Visitor | Object structure is stable but operations grow | Element types change frequently |

## Symptom To Pattern

| Symptom in code | Likely force | Candidate |
|---|---|---|
| `if provider == ...` repeated across call sites | Product or algorithm selection leaks into clients | Factory Method, Abstract Factory, Strategy |
| Constructor has many optional parameters or invalid combinations | Construction complexity | Builder |
| Subclass matrix grows as `PlatformXFeatureY` | Two variation axes are coupled | Bridge |
| Third-party SDK contaminates domain code | Interface mismatch and ownership leak | Adapter or Facade |
| Business logic branches on state in many methods | State-dependent behavior is scattered | State |
| UI/menu/job operations need undo, retry, or audit | Action needs identity and metadata | Command |
| Nested data structures require recursive branching in clients | Part-whole hierarchy leaks | Composite |
| Notification fan-out is hard-coded | Publisher depends on subscribers | Observer |
| Many services call each other directly for one workflow | Coordination logic is scattered | Mediator |
| Cross-cutting behavior stacks around core work | Optional wrappers | Decorator or Proxy |

## Enterprise Decision Questions

Answer these before recommending a pattern:

1. What exact change becomes cheaper after this pattern exists?
2. Which callers stop knowing about concrete classes, state branches, provider APIs, or traversal details?
3. What public contract remains stable during migration?
4. What new abstraction becomes owned by the domain rather than by a generic pattern name?
5. What test proves a new implementation can be added without editing client orchestration?
6. What operational concern is affected: latency, memory, concurrency, auth, retries, logging, observability, or rollout?
7. What future change would make this pattern the wrong choice?

## Combination Rules

Combining patterns is acceptable only when each pattern protects a different force:

| Combination | Works when | Risk |
|---|---|---|
| Abstract Factory + Strategy | Product family creation and algorithm choice are separate axes | Over-configured provider layers |
| Command + Memento | Commands need undo snapshots | Snapshot size and privacy leaks |
| Composite + Visitor | Stable tree needs many external operations | Visitor churn when node types change |
| Decorator + Factory | Wrappers are assembled from configuration | Hidden wrapper order bugs |
| Proxy + Facade | External subsystem needs both access control and simpler API | Too much behavior in one gateway |

Use an explicit assembly boundary when combining patterns. Do not let clients build arbitrary pattern stacks.

## Anti-Pattern Checks

- A pattern is not justified by "future flexibility" unless the future variation is named and likely.
- A base class is not an interface just because it has one method.
- A strategy is unsafe if algorithms do not share the same preconditions and postconditions.
- A factory is unnecessary if callers already receive dependencies from a composition root.
- A facade is harmful if it hides errors, authorization, or transaction boundaries.
- A singleton is usually a dependency management smell in tests and multi-tenant systems.
- A visitor is brittle if new element types are expected soon.
- A mediator is risky when it owns too much domain state or hides critical dependencies.

## Verification Patterns

| Pattern family | Verification clue |
|---|---|
| Creational | A new product or representation can be added with no client orchestration change |
| Structural | Client code depends on a stable interface while wrappers/adapters/subsystems vary |
| Behavioral | A behavior, command, handler, state, visitor, or subscriber can change independently with clear tests |

The best pattern proof is a focused test that adds a realistic new variant and shows the old client path still works.
