# Architecture refactor implementation

- Status: Approved
- Date: 2026-08-10
- Last updated: 2026-08-26
- Implementation status: Phases 0 through 12 complete; the production package
  contains only Domain, Application, inbound/outbound Adapters, and Bootstrap,
  with no architecture exceptions, and execution is stopped before Phase 13
- Governing decisions: ADR-0001 through ADR-0010

## Purpose

This document records the approved implementation shape for the architecture
refactor so the work can resume without reopening settled execution choices. It
is not an ADR and cannot override an accepted ADR. If implementation evidence
requires a different architectural tradeoff, amend or supersede the relevant ADR
before changing this specification.

The refactor is incremental. No step treats the current package layout as the
target architecture, and no broad package move is considered complete until its
dependency rule and behavior contracts pass.

## Target module map

```text
roadmap/
  domain/
    entities/
    policies/
    value_objects/
  application/
    ports/
    use_cases/
  adapters/
    inbound/
      cli/
    outbound/
      documents/
      sqlite/
      git/
      telemetry/
  bootstrap/
```

`roadmap.bootstrap` is the final composition-root namespace. The console entry
point delegates to Bootstrap and does not construct concrete adapters itself.

Feature-level packages may be added within these zones when they improve
cohesion, but they do not create new architectural layers.

### Current-to-target ownership guide

| Current responsibility | Target ownership |
| --- | --- |
| Domain entities and pure rules under `core/domain` or elsewhere | `roadmap.domain` |
| Use-case coordination under `core/services`, `infrastructure`, or CLI helpers | `roadmap.application.use_cases` |
| Inward-facing interfaces | `roadmap.application.ports` |
| Click commands, presenters, and output translation | `roadmap.adapters.inbound.cli` |
| Markdown/YAML parsing and canonical persistence | `roadmap.adapters.outbound.documents` |
| SQLite state and query indexes | `roadmap.adapters.outbound.sqlite` |
| Local repository inspection, branch creation, and explicit issue references | `roadmap.adapters.outbound.git` |
| Roadmap credential-store mechanisms | Remove under ADR-0002; Git owns remote credentials |
| Logging and optional telemetry mechanisms | `roadmap.adapters.outbound.telemetry` |
| Concrete construction currently mixed into coordination | `roadmap.bootstrap` |
| `common` utilities | Domain, Application, or the owning adapter according to meaning |
| Remote/provider synchronization, baselines, reconciliation, and sync metrics | Remove under ADR-0002 |

The guide is an ownership map, not authorization for mechanical directory moves.
Each module is classified by behavior before relocation.

## Port and dependency conventions

- Application owns every port.
- A port describes one capability required by a use case.
- Ports use Domain or Application types and typed failures.
- There is no generic backend, gateway, service locator, or all-purpose CRUD
  repository base class.
- Repository ports are aggregate- or capability-specific.
- Unit-of-work behavior follows ADR-0005 and is exposed through an
  Application-owned transaction boundary.
- Separate adapters do not import one another. Bootstrap supplies collaborators.
- Inbound DTOs and outbound serialization models translate to Domain or
  Application types; they do not become Domain types.
- Domain and Application do not expose filesystem paths, SQLite rows, Click
  contexts, Pydantic boundary models, keyring objects, or provider SDK types.
- Dependency injection uses ordinary constructors and explicit factories in
  Bootstrap. No dependency-injection framework is introduced.
- Application execution remains synchronous unless a later accepted decision
  establishes a concrete need for asynchronous behavior.

## Configuration implementation

Before moving configuration code, inventory every key with:

- canonical name and type;
- project, user, secret, environment, or per-invocation scope;
- default and whether it is overridable;
- current storage locations and aliases;
- public compatibility status;
- redaction requirements; and
- migration or removal behavior.

Bootstrap resolves one immutable typed configuration snapshot per invocation.
No migrated Domain or Application module may read the environment, keyring, or a
global settings singleton directly.

## Canonical storage implementation

The target layout and ID rules are fixed by ADR-0010. Before migration:

1. define the new workspace schema version;
2. inventory every current canonical and derived file;
3. specify round-trip fixtures containing user-authored Markdown, supported
   unknown fields, legacy IDs, relationships, and lifecycle metadata;
4. implement migration preflight and dry-run output;
5. implement duplicate and collision detection without heuristic resolution;
6. implement the ADR-0005 transaction and recovery contract;
7. rebuild projections only after the canonical commit; and
8. verify canonical file digests and semantic entities before and after.

SQLite remains the initial derived projection if it continues to provide value.
The refactor does not redesign or replace it merely to prove adapter
replaceability.

### Projection maintenance is retained

Removing synchronization means removing remote/provider reconciliation between
separately writable sources. It does not remove the one-way pipeline that keeps
SQLite or another approved local index current from canonical documents.

- Canonical Markdown/YAML documents are the only input authority.
- A successful canonical commit is followed by projection refresh.
- Manual edits and Git-authored changes are detected through content identity
  and incorporated by incremental refresh or full rebuild.
- Projection corruption, deletion, or schema incompatibility triggers rebuild
  without changing canonical content.
- Projection failure marks derived state stale and does not undo a successful
  canonical write.
- Target code calls this projection refresh, projection rebuild, or index
  maintenance rather than synchronization.

Existing local file-to-SQLite behavior may be reused after it is separated from
remote sync abstractions and made to satisfy these rules.

## Compatibility inventory

Complete this inventory before changing the first affected behavior. Each item
receives a named owner, evidence fixture, and one disposition: Preserve,
Replace, Remove, or Internal.

### Preserve

- Existing canonical entity IDs.
- User-authored Markdown and supported metadata.
- Valid cross-entity relationships.
- Documented non-sync CLI commands and options unless separately approved.
- Documented exit-code categories.
- Documented JSON, CSV, and other machine-readable schemas.
- Supported project configuration unrelated to removed synchronization.
- Explicit Git hook and local repository features that remain in product scope.

### Replace deliberately

- Mutable title-, milestone-, and lifecycle-based file paths with ADR-0010 paths.
- Physical active/archive moves with ADR-0008 lifecycle metadata.
- Ambient configuration access with ADR-0009 typed injection.
- Framework-shaped domain models with pure Domain types and boundary mappings.
- Best-effort multi-file mutation with ADR-0005 unit-of-work recovery.
- Full-directory parsing for normal filtered queries with rebuildable projections
  where measurements justify indexing.

### Remove deliberately

- Remote/provider sync commands and sync-backend selection.
- GitHub or other provider entity replication.
- The no-op Git synchronization backend.
- Synchronization baselines, checkpoints, merge plans, reconciliation, duplicate
  matching, provider linkage state, and sync-specific metrics.
- Provider credentials and synchronization settings in Roadmap configuration.

External URLs or IDs survive only as ordinary references under ADR-0002 and
ADR-0010.

### Internal and unconstrained

- Current Python import paths not explicitly documented as public.
- The SQLite schema and cache layout.
- Concrete class names and constructor graphs.
- `core`, `common`, `infrastructure`, and `presentation` package boundaries.
- Human-readable colors, spacing, and prose not declared stable.

## Architecture enforcement

Enforcement is installed before production modules move.

### Files

- `architecture.toml` contains machine-readable target dependency rules.
- `architecture-baseline.toml` contains temporary current violations.
- `tests/policy/test_architecture_contract_policy.py` runs the checker through
  normal pytest.
- `tests/policy/fixtures/architecture/valid/` contains permitted examples.
- `tests/policy/fixtures/architecture/invalid/` contains one focused violation
  for every rule.

### Rules

- `roadmap.domain` imports only the standard library and `roadmap.domain`.
- `roadmap.application` imports only the standard library,
  `roadmap.application`, and `roadmap.domain`.
- An adapter may import Application, Domain, and modules inside its own adapter
  boundary.
- Separate inbound or outbound adapter boundaries do not cross-import.
- Only `roadmap.bootstrap` imports concrete adapters across boundaries.
- Production imports must not create a cycle between architectural zones.
- Removed synchronization namespaces are forbidden once their removal stage
  completes.

### Baseline ratchet

Every baseline entry contains the source module, target module, violated rule,
reason, and planned migration stage. Enforcement:

1. fails on a violation absent from the baseline;
2. fails on a malformed or duplicate baseline entry;
3. fails when a baseline entry is no longer exercised;
4. reports exact source, target, and rule; and
5. passes only with an empty baseline when migration is declared complete.

The checker uses Python AST import analysis. It does not infer architecture from
filesystem names alone and does not claim to prove semantic design quality.

## Migration sequence

1. **Install enforcement.** Add the policy, negative fixtures, and exact initial
   baseline without moving production modules.
2. **Establish Bootstrap.** Move concrete construction out of coordination and
   entry points while preserving behavior.
3. **Extract Domain.** Move stable IDs, value objects, aggregate behavior, and
   pure policies without persistence or framework dependencies.
4. **Extract Application vertically.** For one behavior at a time, introduce a
   use case and its narrow ports, then route the existing CLI through it.
5. **Move boundary adapters.** Relocate CLI presentation, document persistence,
   SQLite projections, Git inspection, keyring, and telemetry behind ports.
6. **Implement configuration scopes.** Replace ambient settings with the
   ADR-0009 snapshot and adapter-specific construction.
7. **Migrate canonical storage.** Apply ADR-0010 paths, full IDs for new
   entities, projection rebuild, and ADR-0005 recovery.
8. **Migrate lifecycle behavior.** Replace physical archive moves with ADR-0008
   metadata and explicit query scopes.
9. **Remove remote/provider synchronization.** Delete commands, services,
   adapters, persistence, configuration, metrics, and tests whose only purpose
   is reconciliation with a separately writable remote source. Retain and
   re-home canonical-to-SQLite projection refresh and rebuild behavior.
10. **Dissolve legacy packages.** Assign remaining `common`, `core`,
    `infrastructure`, and `presentation` modules to their owners.
11. **Close enforcement.** Remove the final baseline entries and verify no
    compatibility facade recreates a forbidden dependency.

## Vertical-slice completion rule

A migrated slice is complete only when:

- its use case has an explicit Application API;
- Domain behavior is independent of boundary frameworks;
- required ports are narrow and Application-owned;
- Bootstrap supplies concrete adapters;
- characterization and new contract tests pass;
- no new architecture-baseline entry was added;
- obsolete code for that slice is removed rather than retained as a second path;
  and
- public behavior is either preserved or recorded as an approved replacement or
  removal.

## Deferred decisions

The following decisions are intentionally deferred. Existing code does not make
them implicitly accepted.

| Topic | Default during refactor | Trigger to reconsider |
| --- | --- | --- |
| Plugin architecture | No plugin API or dynamic extension contract | A concrete supported third-party extension use case |
| Asynchronous execution | Synchronous use cases and adapters | Measured blocking work that cannot be bounded adequately |
| Event bus or messaging | Direct use-case calls and explicit collaborators | Multiple real consumers requiring independent delivery semantics |
| Dependency-injection framework | Manual constructor injection in Bootstrap | Demonstrated construction complexity not manageable with ordinary Python |
| GitHub or tracker import/export | No provider integration beyond ordinary stored references | An approved one-shot integration use case and separate ADR |
| Public Python API | Internal modules remain non-public | A supported embedding use case with compatibility ownership |
| Replacing SQLite | Retain it only as a rebuildable projection where useful | Measurement or operational evidence that another projection is needed |
| Telemetry technology | Keep telemetry behind its adapter; no redesign | A concrete operational requirement not met by the current mechanism |
| Filesystem sharding | Flat ID-based entity directories | Measured supported-workspace limits requiring a versioned layout change |
| Web or service interface | CLI remains the only inbound product interface | An approved non-CLI product journey |

Deferred topics must not add speculative ports, generic frameworks, compatibility
promises, or empty extension points during the refactor. Reconsideration begins
from the concrete trigger and, where architectural, a new ADR.

## Refactor completion criteria

The architecture refactor is complete when:

- production dependencies conform to ADR-0001 with an empty exception baseline;
- `roadmap.bootstrap` is the only cross-boundary composition root;
- canonical data and lifecycle behavior conform to ADRs 0003, 0005, 0008, and
  0010;
- configuration conforms to ADR-0009;
- the superseded remote/provider reconciliation mechanism is absent;
- retained local projections refresh or rebuild only from canonical files;
- every retained projection is rebuildable from canonical files;
- compatibility fixtures and migration tests pass on supported platforms; and
- legacy architectural packages no longer exist as catch-all ownership zones.
