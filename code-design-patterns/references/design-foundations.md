# Design Foundations

Use this reference when the user asks about OOP design quality, SOLID, object relationships, reuse, extensibility, or when a pattern recommendation needs first-principles grounding before code.

This file distills the foundation chapters of *Dive Into Design Patterns* into enterprise review and implementation checks. Keep explanations practical: user pressure first, mechanism second, code boundary third.

## Table Of Contents

- `Foundation Map`: how reuse pressure flows into pattern decisions.
- `Good Design Pressure`: reuse, extensibility, and complexity cost.
- `OOP Basics And Pillars`: abstraction, encapsulation, inheritance, and polymorphism.
- `Core Design Principles`: encapsulate variation, program to interface, favor composition.
- `SOLID Pressure Tests`: enterprise checks for SRP, OCP, LSP, ISP, and DIP.
- `Object Relationship Vocabulary`: dependency, association, aggregation, composition, inheritance, implementation.
- `Foundation-To-Pattern Bridge`: when principles justify a pattern.
- `Review Output For Foundation Issues`: output shape for principle-level findings.

## Foundation Map

```text
┌──────────────────────┐
│ Reuse and extension   │
│ pressure              │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Variation isolation   │
│ and object relations  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ SOLID pressure test   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Pattern boundary      │
│ only if still needed  │
└──────────────────────┘
```

## Good Design Pressure

| Concern | Enterprise meaning | Design response |
|---|---|---|
| Code reuse | Reusing code is valuable only when the reused unit is not tightly coupled to old context | Extract domain contracts, hide concrete dependencies, keep configuration at composition boundaries |
| Extensibility | New behavior should not repeatedly break stable client code | Isolate variation points and test that new variants plug in through the same boundary |
| Complexity cost | Patterns can increase indirection | Use a pattern only when it lowers repeated change cost more than it raises local reading cost |

## OOP Basics And Pillars

Use OOP vocabulary only when it clarifies an enterprise boundary. A class should represent a cohesive responsibility; an object is a runtime instance with state and behavior; interfaces/contracts describe what clients can rely on.

| Pillar | Practical meaning | Design review question |
|---|---|---|
| Abstraction | Expose the useful capability and hide irrelevant detail | Does the contract describe business capability or leak implementation detail? |
| Encapsulation | Keep state and change-prone rules behind a boundary | Can callers mutate internals or rely on hidden ordering? |
| Inheritance | Reuse and specialize behavior through subtype relationships | Do subtypes preserve the base contract without stronger preconditions? |
| Polymorphism | Callers use one contract while runtime objects provide different behavior | Are implementations substitutable under shared tests? |

OOP is not automatically better than procedural code. Use objects when state, behavior, lifecycle, or collaboration boundaries matter. Use functions/modules when they express the domain more simply.

## Core Design Principles

### Encapsulate What Varies

Use when one part of a workflow changes more often than the rest. Isolate the volatile part behind a method, module, interface, strategy, factory, adapter, or state object depending on the force.

Review questions:

- What specific rule, provider, algorithm, state, format, transport, or policy changes independently?
- Which stable caller should stop knowing about that variation?
- What test proves the stable caller no longer changes when a new variant is added?

Common refactor path:

1. Extract the changing branch into a named method.
2. Move related helper state with it.
3. Promote it to a class/module only when the variation has its own data, lifecycle, or contract.
4. Add a contract test before adding the second or third implementation.

### Program To An Interface, Not An Implementation

Use when high-level code depends on concrete details that are likely to change. The interface should belong to the client/domain side, not to the vendor or low-level provider.

Review questions:

- Does the caller mention concrete class names, SDK DTOs, framework types, or provider-specific errors?
- Is the interface narrow enough that every implementation can honestly satisfy it?
- Does the abstraction encode business capability rather than technical convenience?

Common mistake:

- Extracting an interface that simply mirrors a vendor SDK. That preserves coupling under a new name.

### Favor Composition Over Inheritance

Use when behavior must vary at runtime, when inheritance would multiply subclasses, or when subclass substitution is hard to prove.

Review questions:

- Is the subclass overriding behavior or just selecting a collaborator?
- Do subclasses preserve the same preconditions, postconditions, and errors?
- Could the varying part be injected as a strategy, policy, adapter, renderer, or handler?

Inheritance remains reasonable when:

- The algorithm skeleton is stable and steps vary in controlled hooks.
- The project already has a clear framework extension model.
- Substitution is enforced by tests and narrow contracts.

## SOLID Pressure Tests

| Principle | Enterprise check | Pattern relevance | Failure signal |
|---|---|---|---|
| Single Responsibility | One unit has one reason to change | Extract reporting, formatting, validation, provider integration, or state behavior before applying heavier patterns | A class changes for data, presentation, persistence, and policy reasons |
| Open/Closed | Stable client code stays closed while variants extend through a boundary | Factory, Strategy, State, Command, Visitor, Decorator, Adapter | Adding one provider/format/state edits many unrelated files |
| Liskov Substitution | Implementations preserve caller expectations | Strategy, State, Proxy, Decorator, Template Method | One implementation needs special caller setup or throws unexpected errors |
| Interface Segregation | Contracts are narrow and honest | Adapter, Facade, Abstract Factory, Composite | Implementations fake unused methods or return placeholders |
| Dependency Inversion | High-level policy owns abstractions; low-level details implement them | Adapter, Factory, Bridge, Strategy, Repository-like boundaries | Domain code imports SDKs, framework clients, concrete databases, or transport DTOs |

## Object Relationship Vocabulary

Use this table when explaining diagrams, refactors, or coupling.

| Relationship | Practical meaning | Review pressure |
|---|---|---|
| Dependency | One unit mentions another temporarily, often through a parameter, constructor call, or static access | Can this point at an interface or be moved to a composition boundary? |
| Association | One object can access another over time | Who owns lifecycle, mutation, and nullability? |
| Aggregation | A whole references parts that can exist independently | Are consistency and removal semantics explicit? |
| Composition | A whole owns part lifecycle | Are creation and deletion invariants tested? |
| Inheritance | A subtype specializes a base type | Does every subtype satisfy the base contract without stronger preconditions? |
| Implementation | A concrete type fulfills an interface | Are all implementations substitutable under shared contract tests? |

## Foundation-To-Pattern Bridge

| Foundation pressure | First design move | Pattern only if |
|---|---|---|
| One calculation varies | Extract function/module | Multiple algorithms must be interchangeable through a stable contract: Strategy |
| Concrete construction leaks | Move construction to composition root | Client must delegate product creation: Factory Method or Abstract Factory |
| Vendor API leaks | Define domain interface | Translation/error normalization is needed: Adapter or Facade |
| State branches repeat | Write state/action matrix | State-specific behavior is broad enough: State |
| Optional behavior stacks | Extract wrapper function | Multiple wrappers must compose around same contract: Decorator or Proxy |
| Tree recursion leaks | Define uniform operation | Leaves and containers should be treated alike: Composite |

## Review Output For Foundation Issues

```markdown
## Foundation Finding
Scenario: <real change or maintenance pressure>
Principle: <variation/interface/composition/SOLID relation>
Mechanism: <why current code is costly or fragile>
Smallest correction: <refactor before naming a pattern, or pattern boundary if justified>
Verification: <test proving the stable boundary>
```
