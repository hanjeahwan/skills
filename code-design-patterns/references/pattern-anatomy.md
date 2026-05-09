# Pattern Anatomy

Use this reference when the user asks about a specific pattern, asks for a comparison between patterns, or wants an explanation that should follow the source book's pattern structure without copying the book.

Each pattern answer should separate:

1. Problem pressure.
2. Solution mechanism.
3. Structure and roles.
4. Applicability.
5. Implementation steps.
6. Pros, costs, and enterprise risks.
7. Relations to nearby patterns.
8. Verification evidence.

## Table Of Contents

- `Explanation Template`: required answer structure for pattern-specific requests.
- `Pattern Cards`: concise cards for all 22 GoF patterns.
- `Factory Method`
- `Abstract Factory`
- `Builder`
- `Prototype`
- `Singleton`
- `Adapter`
- `Bridge`
- `Composite`
- `Decorator`
- `Facade`
- `Flyweight`
- `Proxy`
- `Chain Of Responsibility`
- `Command`
- `Iterator`
- `Mediator`
- `Memento`
- `Observer`
- `State`
- `Strategy`
- `Template Method`
- `Visitor`
- `Coverage Check For Specific Pattern Answers`

## Explanation Template

```markdown
## Pattern
<pattern name and domain boundary>

## Problem Pressure
<real scenario where current code changes too often, leaks coupling, or duplicates behavior>

## Solution Mechanism
<how the pattern moves responsibility and what becomes stable>

## Structure
| Role | Domain name | Responsibility |
|---|---|---|

## Applicability
- Use when <force>
- Avoid when <simpler design is enough>

## Implementation Steps
1. <find stable client contract>
2. <extract role/interface>
3. <move one implementation>
4. <wire at composition boundary>
5. <add contract/parity tests>

## Pros And Costs
| Benefit | Cost / risk |
|---|---|

## Related Patterns
<neighboring patterns and why they differ>

## Verification
<focused tests or checks>
```

## Pattern Cards

### Factory Method

- Problem pressure: clients construct concrete products and must change when product type changes.
- Structure: Creator, Concrete Creator, Product, Concrete Product.
- Applicability: one product family varies; subclasses or configuration choose products.
- Implementation: move `new ConcreteProduct` behind a creation method; make clients depend on the product contract; register concrete creators at the composition boundary.
- Cost: inheritance ceremony or hidden construction logic if a simple factory function would do.
- Related: evolves toward Abstract Factory for product families, Builder for complex construction, Prototype for cloning.

### Abstract Factory

- Problem pressure: related products must be created in compatible families.
- Structure: Abstract Factory, Concrete Factory, Abstract Products, Concrete Products.
- Applicability: provider/platform/tenant variants include multiple matched collaborators.
- Implementation: define one factory interface for the family; make each concrete factory produce all compatible products; keep family selection in one place.
- Cost: adding a new product kind touches every factory.
- Related: often composed from Factory Methods; competes with Prototype when product family is cloneable templates.

### Builder

- Problem pressure: construction has many optional steps, invalid combinations, or representations.
- Structure: Builder, Concrete Builder, Product, optional Director.
- Applicability: object creation needs sequencing, validation, or multiple representations.
- Implementation: expose meaningful build steps; validate before `build`; keep built result immutable or copied.
- Cost: verbose when a parameter object is enough.
- Related: Abstract Factory creates families; Builder constructs one complex product step by step.

### Prototype

- Problem pressure: new objects should be copied from configured examples without depending on concrete classes.
- Structure: Prototype interface, Concrete Prototype, Client.
- Applicability: runtime templates, expensive setup, user-defined configurations.
- Implementation: define clone/copy semantics; protect identity and mutable nested state; test deep/shallow copy behavior.
- Cost: copy semantics become subtle with references, resources, and persistence identity.
- Related: can support Abstract Factory by cloning product prototypes.

### Singleton

- Problem pressure: one process-wide identity must be controlled.
- Structure: Singleton class with controlled construction and access.
- Applicability: rare; use for inherent single identity, not convenience dependency lookup.
- Implementation: make lifecycle, concurrency, reset, and test seams explicit.
- Cost: hidden dependencies, global mutable state, multi-tenant bugs, hard tests.
- Related: many Singleton uses should become dependency injection or a composition root.

### Adapter

- Problem pressure: a useful class or SDK has the wrong interface for current clients.
- Structure: Client, Target interface, Adapter, Adaptee.
- Applicability: legacy or third-party dependency cannot be changed.
- Implementation: define client-owned target interface; translate request/response/error shapes in the adapter.
- Cost: adapter can become a leaky mirror of the vendor API.
- Related: Facade simplifies a subsystem; Adapter changes an interface.

### Bridge

- Problem pressure: two independent variation axes create subclass multiplication.
- Structure: Abstraction, Refined Abstraction, Implementation, Concrete Implementation.
- Applicability: abstraction and implementation should evolve independently.
- Implementation: move implementation axis behind an interface and have abstraction delegate.
- Cost: premature bridge layers obscure simple code.
- Related: Strategy swaps algorithms; Bridge separates two hierarchies.

### Composite

- Problem pressure: clients branch on leaf/container objects in a tree.
- Structure: Component, Leaf, Composite, Client.
- Applicability: part-whole hierarchy should support uniform operations.
- Implementation: define shared component operations; make composites delegate to children recursively.
- Cost: shared interface may force leaves to expose meaningless operations.
- Related: often pairs with Iterator for traversal and Visitor for operations over stable trees.

### Decorator

- Problem pressure: optional behaviors should stack without subclass explosion.
- Structure: Component, Concrete Component, Base Decorator, Concrete Decorators.
- Applicability: compression, encryption, logging, validation, formatting, or tracing layers.
- Implementation: wrappers implement the same contract and delegate to an inner component.
- Cost: wrapper order and error propagation can be hard to see.
- Related: Proxy controls access; Decorator adds behavior.

### Facade

- Problem pressure: clients know too many subsystem classes and ordering rules.
- Structure: Facade, Subsystem classes, Client.
- Applicability: simplify a complex subsystem behind a stable workflow entry point.
- Implementation: expose a narrow domain operation; keep detailed subsystem behavior testable underneath.
- Cost: god facade, hidden transaction/auth/retry semantics.
- Related: Adapter changes interface compatibility; Facade reduces surface area.

### Flyweight

- Problem pressure: many objects duplicate large immutable state.
- Structure: Flyweight, Flyweight Factory, Context, Client.
- Applicability: proven memory pressure or large object counts with shareable intrinsic state.
- Implementation: separate intrinsic shared state from extrinsic context; centralize cache/factory.
- Cost: correctness bugs if mutable state is accidentally shared.
- Related: often uses Factory for flyweight reuse.

### Proxy

- Problem pressure: access to a subject needs control before/after delegation.
- Structure: Subject, Real Subject, Proxy, Client.
- Applicability: lazy loading, remote access, caching, authorization, rate limiting, audit.
- Implementation: preserve subject contract; add access behavior in proxy; test real and proxy with contract tests.
- Cost: hidden latency, stale cache, changed error semantics.
- Related: Decorator adds optional behavior; Proxy controls access.

### Chain Of Responsibility

- Problem pressure: several handlers may process a request and caller should not choose the exact handler.
- Structure: Handler, Concrete Handlers, Client.
- Applicability: middleware, validation, support routing, policy checks.
- Implementation: define ordered handlers; decide pass/handle/fail semantics; provide safe fallback.
- Cost: debugging order and unhandled requests.
- Related: Command object can travel through a chain.

### Command

- Problem pressure: a request needs identity, metadata, queueing, retry, undo, or audit.
- Structure: Command, Concrete Command, Invoker, Receiver, optional History.
- Applicability: UI actions, jobs, remote operations, workflow steps.
- Implementation: capture receiver/action inputs; define execute result; add undo or serialization only when needed.
- Cost: many small classes/objects and unclear idempotency if not designed.
- Related: pairs with Memento for undo snapshots.

### Iterator

- Problem pressure: clients should traverse a collection without knowing internal representation.
- Structure: Iterator, Concrete Iterator, Collection, Concrete Collection.
- Applicability: trees, pages, cursors, remote collections, filtered views.
- Implementation: expose next/current/done or native iteration protocol; hide storage traversal.
- Cost: native language iteration may already be enough.
- Related: Composite trees often expose iterators.

### Mediator

- Problem pressure: components communicate through too many direct dependencies.
- Structure: Mediator, Concrete Mediator, Components.
- Applicability: one workflow has centralized coordination rules.
- Implementation: components notify mediator; mediator orchestrates collaborators through explicit workflow methods.
- Cost: mediator becomes a god object if it owns unrelated workflows.
- Related: Observer broadcasts events; Mediator coordinates directed collaboration.

### Memento

- Problem pressure: state must be restored without exposing object internals.
- Structure: Originator, Memento, Caretaker.
- Applicability: undo, draft restore, editor snapshots, workflow rollback.
- Implementation: originator creates/restores snapshots; caretaker stores snapshots without inspecting internals.
- Cost: snapshot size, versioning, privacy, and persistence compatibility.
- Related: Command uses Memento for undoable commands.

### Observer

- Problem pressure: a publisher event should notify many independent subscribers.
- Structure: Publisher, Subscriber, Concrete Subscribers.
- Applicability: in-process event fan-out where subscribers are independent.
- Implementation: publisher owns subscription list or event dispatcher; subscribers implement a narrow handler.
- Cost: delivery order, backpressure, retry, duplicate handling, and durability in distributed systems.
- Related: use queues/event buses for critical cross-service delivery.

### State

- Problem pressure: behavior changes with internal lifecycle state and branches repeat.
- Structure: Context, State interface, Concrete States.
- Applicability: actions and valid transitions differ by state.
- Implementation: write state/action matrix; move state-specific behavior into state objects; persist stable state identifiers.
- Cost: overkill for small stable enums.
- Related: Strategy swaps algorithms; State models lifecycle and transitions.

### Strategy

- Problem pressure: several algorithms solve the same task and must be interchangeable.
- Structure: Context, Strategy, Concrete Strategies.
- Applicability: algorithm varies by request, tenant, feature flag, or configuration.
- Implementation: define a common algorithm contract; inject/select strategy at boundary; run shared contract tests.
- Cost: unsafe if strategies require different caller setup.
- Related: State is Strategy with lifecycle awareness.

### Template Method

- Problem pressure: algorithm skeleton is stable but some steps vary.
- Structure: Abstract Class, Template Method, Primitive Operations, Concrete Classes.
- Applicability: inheritance is the intended extension mechanism and step order is fixed.
- Implementation: keep skeleton final/stable where possible; define narrow hooks; test step order.
- Cost: static inheritance, fragile hooks, limited runtime selection.
- Related: Strategy uses composition and supports runtime swapping.

### Visitor

- Problem pressure: many operations must run over a stable object structure.
- Structure: Visitor, Concrete Visitor, Element, Concrete Elements.
- Applicability: object types are stable; operations grow.
- Implementation: add accept/visit dispatch; keep operations in visitors; test every element-operation pair.
- Cost: adding new element types changes every visitor.
- Related: Composite trees often use Visitor for external operations.

## Coverage Check For Specific Pattern Answers

Before finishing a pattern-specific answer, verify:

- The problem pressure is real and concrete.
- Roles are mapped to domain names, not left as generic pattern words.
- Applicability includes a "do not use when" condition.
- Implementation steps include where concrete classes are wired.
- Tests prove the stable client does not change when a variant is added.
- Nearby patterns are distinguished if a team could reasonably confuse them.
