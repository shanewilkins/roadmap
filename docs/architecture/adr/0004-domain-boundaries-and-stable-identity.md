# ADR-0004: Define domain boundaries and stable identity

- Status: Accepted
- Date: 2026-08-10
- Scope: Domain aggregates, identity, relationships, and model ownership

## Context

Current models mix business meaning with serialization, filesystem location,
provider linkage, framework behavior, and coordination across entities. A
package refactor cannot produce a clean architecture unless the domain boundary
and identity rules are explicit first.

Loading an entire project as one mutable object would also make ordinary issue
operations unnecessarily broad and make multi-file consistency harder than the
business behavior requires.

## Decision

A Roadmap workspace is the repository-level context in which independently
addressable planning entities live. It is not a single aggregate that must be
loaded and rewritten for every operation.

Issues, milestones, and project metadata are separate aggregates:

- Each aggregate has a stable, opaque, globally unique Roadmap ID.
- Identity does not change when a title, status, milestone assignment, file
  location, or external reference changes.
- References between aggregates use stable Roadmap IDs rather than direct
  mutable object graphs, filenames, titles, or provider IDs.
- An aggregate enforces the invariants and state transitions wholly contained
  within itself.
- Application use cases enforce rules that require multiple aggregates, such as
  uniqueness in a workspace, relationship validation, assignment to an existing
  milestone, or deletion of a referenced entity.

Domain models own business state and behavior. They do not contain:

- filesystem paths or filenames;
- parser or serialization behavior;
- SQLite identifiers or cache state;
- CLI presentation concerns;
- provider clients or synchronization metadata; or
- framework-specific base classes required only for validation or transport.

Domain types use Python language and standard-library facilities. Boundary
models may use libraries such as Pydantic, but they translate to and from domain
types rather than becoming the domain by convenience.

External URLs and identifiers may be retained as ordinary references when they
provide user value. They never replace Roadmap identity and do not imply that an
external record is a synchronized replica.

Time-dependent domain operations receive the relevant time or a clock-owned
value from Application. Domain behavior does not read global process time as a
hidden dependency.

## Relationship rules

- Relationships are typed and use stable IDs.
- Missing, self-referential, duplicate, and prohibited cyclic relationships are
  rejected at the appropriate Domain or Application boundary.
- Archived and closed targets remain addressable so historical relationships do
  not become corrupt merely because visibility changed.
- Aggregate projections such as milestone completion are calculated from
  canonical linked entities under one Application-owned policy; they are not
  independently authoritative counters.

## Consequences

### Positive

- Entity operations have bounded read and write sets.
- Domain tests do not require parsers, files, databases, provider SDKs, or a CLI
  context.
- Renames and lifecycle transitions do not break identity or references.
- Provider-specific models cannot distort core business concepts.

### Costs and constraints

- Current framework models will need mapping at boundaries.
- Cross-aggregate operations require explicit Application use cases.
- Convenience fields derived from other aggregates cannot silently become
  independently persisted truth.
- Existing filename-, title-, or provider-based lookup assumptions must be
  migrated deliberately.

## Alternatives considered

### Treat the whole workspace as one aggregate

Rejected because it gives routine changes unnecessarily large consistency and
I/O boundaries.

### Use serialization models as domain models

Rejected because storage and validation-framework concerns would continue to
shape business behavior.

### Use external tracker IDs as identity

Rejected because Roadmap remains usable without a provider and external IDs are
not portable across repositories or integrations.

## Related decisions

- ADR-0001 defines the Domain and Application dependency boundary.
- ADR-0003 defines canonical entity documents.
- ADR-0008 defines lifecycle state without identity or path changes.

## Migration boundary

This ADR does not finalize every field or workflow transition. A target domain
model and mapping inventory must precede production module movement.

