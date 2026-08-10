# ADR-0001: Adopt pragmatic hexagonal architecture

- Status: Accepted
- Date: 2026-08-10
- Scope: Target application architecture and dependency policy

## Context

Roadmap is a file-first, Git-native command-line application. Its implementation
has grown across packages named `core`, `common`, `infrastructure`, `adapters`,
`application`, `domain`, and `presentation`.

The existing six-layer description does not establish a usable dependency
direction. It permits, among other relationships, Core to depend on
Infrastructure while Infrastructure also depends on Core. Similar cycles exist
between Infrastructure and Adapters. `common` has consequently become another
architectural layer rather than a set of values with clear owners, and concrete
dependency construction is mixed with application coordination.

We need one architecture that:

- has a dependency direction that can be stated and mechanically checked;
- keeps domain and application behavior independent of frameworks and I/O;
- makes external systems replaceable at explicit boundaries;
- gives dependency construction one unambiguous home; and
- supports an incremental migration without treating existing violations as the
  desired design.

## Decision

Roadmap will use a pragmatic form of hexagonal architecture, also known as
ports and adapters. The target architecture has four zones: Domain,
Application, Adapters, and Composition.

```text
                         Composition root
                         /              \
                  inbound adapters   outbound adapters
                          \             /
                           Application
                                |
                              Domain

                  Compile-time imports point inward.
```

Runtime calls may cross a port in either direction. Compile-time dependencies
still point inward because the port is owned by the Application zone and the
outbound adapter implements it.

### Domain

The Domain zone owns entities, value objects, invariants, and pure business
policies.

- It may depend on the Python standard library and other Domain modules.
- It must not depend on Application, Adapters, Composition, CLI frameworks,
  persistence, configuration, logging, telemetry, or network libraries.
- Domain types must not be shaped around a particular storage format or remote
  provider.

The target namespace is `roadmap.domain`.

### Application

The Application zone owns use cases, orchestration, application DTOs, and ports
for capabilities supplied at the boundary.

- It may depend on Domain and other Application modules.
- It must not import concrete adapters, Composition, CLI frameworks, persistence
  implementations, or provider SDKs.
- Ports are narrow and capability-oriented. They must not be service locators or
  generic gateways that conceal concrete imports.
- Transaction and use-case boundaries belong here; concrete transaction
  mechanisms do not.

The target namespace is `roadmap.application`.

### Adapters

Adapters translate between an external boundary and Application or Domain
types.

Inbound adapters include the CLI and output presentation. Outbound adapters
include roadmap document persistence, derived indexes, Git inspection, keyring,
telemetry, and any deliberately approved external integration.

- Adapters may depend on Application and Domain.
- An adapter may depend on libraries required to implement its boundary.
- Application and Domain never import an adapter.
- Separate adapters must not import one another to obtain collaborators.
  Collaborators are supplied by Composition through Application-owned ports.
- Code shared by one adapter remains inside that adapter. Code shared across
  boundaries must first be assigned to Domain or Application based on its
  meaning; it must not default to a generic utilities layer.

The target namespaces are `roadmap.adapters.inbound` and
`roadmap.adapters.outbound`. Exact feature-level package names will be decided
as part of migration planning.

### Composition

Composition is the only zone that selects concrete implementations and wires
the application graph.

- It may import every zone for construction purposes.
- It contains no business rules.
- It does not become a runtime service locator.
- An executable entry point asks Composition for a fully constructed inbound
  adapter or use case rather than constructing dependencies itself.

The composition-root namespace is `roadmap.bootstrap`. This is the final target
name. There will be one composition root and its responsibility will not change
during migration.

### No `common` or `infrastructure` layer

`common` is not an architectural zone in the target design. Existing contents
will eventually move according to ownership:

- business meaning to Domain;
- use-case meaning and ports to Application;
- I/O, configuration, logging, security mechanisms, and provider code to the
  adapter that implements that boundary; and
- concrete construction to Composition.

Likewise, `infrastructure` is not a dependency layer. Infrastructure is a kind
of outbound adapter. Coordination that is actually a use case belongs in
Application, while dependency construction belongs in Composition.

This decision does not require an all-purpose shared package. If a genuinely
generic support package is later justified, it requires its own decision and a
strict dependency policy; it must not become a new name for `common`.

## Enforcement contract

Architectural conformance will be enforced by a first-party policy test that
examines Python imports. It will run under the normal pytest suite rather than
as a separate linting system.

The enforcement mechanism must:

1. encode the allowed dependency direction as data rather than prose alone;
2. report the source module, imported module, and violated rule;
3. include valid and invalid fixtures proving that every rule is detected;
4. reject architectural package cycles;
5. maintain an explicit, reviewed baseline for pre-existing violations during
   migration;
6. fail on any violation not present in that baseline; and
7. fail when a baseline exception is no longer exercised, so the exception set
   can only shrink.

The baseline is a temporary migration mechanism, not an alternate set of
allowed dependencies. Once migration is complete, it must be empty.

Enforcement should remain narrow and objective. Import rules can prove
dependency direction; they should not pretend to prove semantic qualities such
as good abstraction design. Those remain review concerns.

## Consequences

### Positive

- Business behavior can be tested without filesystem, CLI, database, Git, or
  network dependencies.
- External mechanisms become replaceable implementations of explicit ports.
- Dependency cycles and accidental boundary crossings become mechanically
  detectable.
- Dependency construction has one discoverable location.
- The architecture can be adopted incrementally through a ratcheted exception
  baseline.

### Costs and constraints

- The current layout does not conform and will require a staged migration.
- Some abstractions currently called interfaces or gateways will need to be
  narrowed, moved, or removed.
- Features cannot bypass Application merely because importing another adapter
  is convenient.
- `common` and `infrastructure` cannot be preserved as catch-all layers.

## Alternatives considered

### Preserve the documented six-layer model

Rejected because its allowed dependency rules are circular and therefore do
not define an enforceable architecture.

### Conventional top-down layering

Rejected because placing persistence beneath Domain encourages Domain or
Application to import concrete storage mechanisms. Ports and adapters express
the required inversion directly.

### Unconstrained feature packages

Rejected because feature locality alone does not prevent framework, storage,
and provider concerns from entering business behavior.

## Migration boundary

This ADR selects the destination and its enforcement rules. It does not move,
rename, or delete production modules. A package map, initial violation baseline,
and sequence of vertical migrations are defined in the approved
`../refactor-implementation.md` specification.
