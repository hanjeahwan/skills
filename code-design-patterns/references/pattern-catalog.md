# Pattern Catalog

This catalog is intentionally concise. Use it to check pattern fit after the forces are known. For selection from symptoms, read `selection-guide.md` first.

## Creational Patterns

| Pattern | Enterprise use | Fit signals | Cautions | Verification clue |
|---|---|---|---|---|
| Factory Method | Delegate one product creation decision to subclasses, configuration, or a composition boundary | Product type varies; clients should depend on a product interface | Can create inheritance ceremony when DI or a simple factory function is enough | Add a product implementation without changing client orchestration |
| Abstract Factory | Create families of compatible products | Provider/platform/tenant variants must stay internally consistent | Too much nesting when only one product varies | A full product family swaps through one factory contract |
| Builder | Construct complex objects step by step | Many optional steps, invalid constructor combinations, multiple representations | Fluent builders can hide validation or produce half-built objects | Tests cover required steps, defaults, invalid combinations, and final immutable output |
| Prototype | Clone configured objects without coupling to concrete classes | Runtime templates, expensive setup, or user-defined configurations need copying | Deep copy semantics, identity, and shared mutable state can break correctness | Mutating a clone does not corrupt the source; type-specific cloning stays encapsulated |
| Singleton | Ensure one controlled instance and global access point | Process-wide identity is inherent, such as a registry or clock source in a narrow runtime | Often damages tests, multi-tenancy, dependency injection, and lifecycle control | Concurrent access and reset/lifecycle behavior are explicit and tested |

## Structural Patterns

| Pattern | Enterprise use | Fit signals | Cautions | Verification clue |
|---|---|---|---|---|
| Adapter | Translate an incompatible interface into the client-owned contract | Legacy or third-party dependency cannot be changed but is valuable | Adapter should not leak vendor types into domain code | Domain tests run against the adapter contract; vendor quirks are isolated |
| Bridge | Separate abstraction from implementation so both can vary | Two independent dimensions would otherwise multiply subclasses | Premature bridge layers are hard to understand | Add one abstraction variant and one implementation variant independently |
| Composite | Treat individual objects and object groups uniformly | Tree/graph-like part-whole structures, nested containers, recursive operations | Uniform interface can become too broad for leaves | Same operation works for leaf and nested composite fixtures |
| Decorator | Add stackable responsibilities around a component | Optional behaviors combine dynamically around the same interface | Wrapper order, error propagation, and observability can become unclear | Tests cover wrapper order and composition around the same component contract |
| Facade | Provide a simpler stable API over a complex subsystem | Client workflows currently know too many subsystem classes or steps | Facade can turn into a god service or hide important failures | Client uses one narrow facade method while subsystem tests still cover detailed behavior |
| Flyweight | Share immutable intrinsic state across many objects | High object counts repeat the same heavy data | Shared mutable state and cache eviction are correctness risks | Memory/performance measurement plus behavior parity for shared instances |
| Proxy | Control access to another object through the same contract | Need lazy loading, caching, auth, rate limiting, remote transport, logging, or audit | Proxy must preserve subject contract and failure semantics | Contract tests pass against both real subject and proxy |

## Behavioral Patterns

| Pattern | Enterprise use | Fit signals | Cautions | Verification clue |
|---|---|---|---|---|
| Chain of Responsibility | Let ordered handlers process or pass a request | Validation, middleware, support routing, policy checks, fallback chains | Ordering, short-circuiting, and error semantics must be explicit | Tests prove handled, passed, unhandled, and failure cases |
| Command | Represent an action as an object | Need queueing, retry, audit, undo, scheduling, transport, or permission checks | Commands need clear idempotency and serialization rules | Command can be persisted/replayed or undone according to its contract |
| Iterator | Traverse a collection without exposing representation | Trees, pages, cursors, remote APIs, or filtered views need uniform traversal | Native iteration may already be enough | Client consumes the iterator without knowing storage shape |
| Mediator | Centralize coordination between many components | Components are tightly coupled through direct calls for one workflow | Mediator can become an opaque god object | Components depend on mediator contract, and workflow rules are tested in one place |
| Memento | Save and restore private state | Undo, draft restore, editor snapshots, workflow rollback | Snapshot size, privacy, and versioning need control | Restore returns the object to prior observable behavior without exposing internals |
| Observer | Notify many subscribers about publisher events | Subscribers are independent and may change without publisher changes | Delivery order, backpressure, retries, and duplicate handling matter in distributed systems | Publisher tests assert notification contract; subscriber tests stay independent |
| State | Move state-specific behavior into state objects | Many methods branch on the same state; transitions change valid behavior | A small stable enum may be clearer | Tests cover allowed actions and transitions per state |
| Strategy | Swap algorithms behind one task | Algorithm varies by request, tenant, feature flag, or configuration | Strategies must be substitutable under the same contract | Each strategy passes the same contract tests plus specific edge cases |
| Template Method | Keep an algorithm skeleton stable while subclasses override steps | Inheritance is already the extension model and step order is fixed | Harder to change at runtime; subclass hooks can be fragile | Base algorithm tests prove step order; subclass tests cover overridden steps |
| Visitor | Add operations to stable object structures | Many operations over a stable tree or AST-like model | New element types require changing all visitors | New operation is added without modifying element behavior |

## Relationship Notes

- Factory Method often appears first, then evolves into Abstract Factory, Builder, or Prototype when product families or construction complexity grow.
- Strategy and State both delegate behavior, but Strategy selects interchangeable algorithms while State models lifecycle-dependent behavior and transitions.
- Decorator and Proxy both wrap an object, but Decorator adds optional behavior while Proxy controls access to the original object.
- Adapter changes an interface for compatibility; Facade simplifies a subsystem for clients.
- Composite pairs naturally with Iterator for traversal and Visitor for external operations on stable structures.
- Command pairs with Memento when undo requires private state snapshots.

## SOLID And Pattern Fit

| Principle | Pattern relevance |
|---|---|
| Single Responsibility | A pattern should isolate one reason to change, not create a class per noun |
| Open/Closed | New variants should extend through a stable boundary without editing client orchestration |
| Liskov Substitution | Subclasses and strategies must preserve preconditions, postconditions, and error semantics |
| Interface Segregation | Pattern interfaces should be narrow enough that implementers do not fake unused behavior |
| Dependency Inversion | High-level policy should depend on domain-owned abstractions, not concrete vendor or framework classes |

## Object Relation Vocabulary

Use these terms when explaining design mechanics:

| Relation | Meaning in design reviews |
|---|---|
| Dependency | One class/function mentions or uses another; weaken it through interfaces or injected collaborators when it creates change pressure |
| Association | One object knows about another over time; review lifecycle and ownership |
| Aggregation | A container references parts that can live independently; review mutation and consistency |
| Composition | The whole owns part lifecycle; review creation, deletion, and invariants |
| Inheritance | A subtype reuses and specializes a base type; review substitution and whether composition is simpler |
| Implementation | A concrete type fulfills an interface; review contract completeness and substitutability |
