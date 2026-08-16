# Roadmap 0.2 architecture simplification plan

- Status: Approved
- Date: 2026-08-11
- Release target: 0.2.0
- Governing decisions: ADR-0001 through ADR-0010
- Implementation specification: [refactor-implementation.md](refactor-implementation.md)
- Detailed execution and checkpoint protocol:
  [refactor-execution-plan.md](refactor-execution-plan.md)

## Decision

Salvage Roadmap in Python. Do not restart it in Rust.

The package now installs and releases correctly. The remaining problem is not
the language: it is excessive product scope, duplicate architectural ownership,
multiple state models, and too many implementations of the same boundary. A
rewrite would discard useful behavior and test evidence while recreating the
same product and storage decisions in a new language.

Version 0.2 is therefore a controlled product contraction and architecture
replacement inside the existing repository. It is not a feature release and it
is not a mechanical package shuffle.

## Baseline

As of 2026-08-11, the repository contains approximately:

- 90,567 physical lines across 512 production Python modules;
- 54,225 Python code lines across 504 files according to CLOC 2.10 on
  2026-08-16;
- 134,927 lines across 540 test modules;
- 45,098 production lines under `roadmap.adapters`;
- 23,764 production lines under `roadmap.core`;
- 14,458 production lines under the catch-all `roadmap.common` package; and
- 16,303 lines in the direct remote-sync packages, rising to roughly 22,754
  lines when remote-sync-specific CLI, persistence, and metrics code is
  included.

The current architecture policy described in the approved implementation
specification has not yet been installed. The existing `.roadmap` data also
contains a closed legacy milestone named `v0-2-0`; it is historical data, not
this release plan.

These counts are diagnostic, not productivity targets. The release succeeds by
removing duplicate responsibilities and enforcing one path for each retained
behavior. A smaller codebase should be the consequence.

Production CLOC is nevertheless an execution ratchet for this refactor. Phase 0
verifies the exact baseline using the command in the detailed execution plan.
Every later accepted phase must have the same or fewer Python code lines under
`roadmap/` than the preceding accepted phase. Tests and documentation are
reported separately and cannot offset an increase in production code.

## 0.2 product boundary

### Retain and make trustworthy

- installed CLI, workspace discovery, initialization, configuration, and
  explicit migration;
- issues, projects, and milestones with stable IDs and a small, documented
  lifecycle;
- list, detail, planning, and basic daily views derived from canonical data;
- deterministic human, plain, JSON, and CSV output where already declared;
- canonical Markdown/YAML documents with SQLite used only as a disposable,
  rebuildable projection;
- one-way projection refresh and rebuild from canonical documents into SQLite,
  including detection of manual and Git-authored file changes;
- validation, health diagnosis, projection rebuild, and transaction recovery;
- local Git awareness needed for repository context, ordinary diffs, and
  explicit references; and
- clean installation and artifact testing on every supported runtime and OS.

### Remove

- `roadmap sync` and provider-backed bidirectional synchronization;
- GitHub entity replication, provider baselines, checkpoints, three-way merge,
  reconciliation, linkage repair, remote reconciliation databases, and sync
  metrics;
- Roadmap-owned remote credentials and sync-backend configuration;
- no-op backends, generic gateways, service locators, and compatibility layers
  that exist only to preserve the rejected sync model;
- generated or speculative APIs with no retained 0.2 user journey; and
- the legacy `core`, `common`, `infrastructure`, and `presentation` ownership
  zones after their retained behavior has moved.

### Defer until after 0.2

- requirements as first-class application entities;
- automatic mutation from Git hooks and commit messages;
- third-party import, export, or publishing adapters;
- predictive analytics, an event bus, plugins, a web interface, and async use
  cases;
- replacement of SQLite without measured evidence; and
- a documentation framework migration or broad Sphinx rebuild.

The CSV requirement registers remain governance and planning artifacts during
0.2. This lets the project use requirement IDs immediately without forcing a
new requirements domain into an unstable core. The optional application feature
can be reconsidered for 0.3 after the storage, lifecycle, and traceability
boundaries are proven.

### Synchronization terminology

Throughout this plan, **remove synchronization** means remove remote/provider
reconciliation between separately writable sources. It does not mean remove
local projection maintenance.

The retained local flow is deliberately one-way:

```text
canonical Markdown/YAML -> validate -> refresh or rebuild SQLite projection
```

Canonical files always win. Projection records never write back as authority.
After a canonical commit, Roadmap refreshes the affected projection records.
After manual edits or Git changes, Roadmap detects stale content and performs an
incremental refresh or full rebuild. If projection maintenance fails, canonical
state remains committed and the projection is marked stale. Target code names
this behavior projection refresh, projection rebuild, or index maintenance—not
sync.

## Delivery rules

1. Freeze feature development for 0.2. Critical 0.1.x defects may be fixed, but
   they do not expand the refactor scope.
2. Migrate one complete user behavior at a time. Do not move whole directories
   to make the tree look architectural.
3. Characterize the public behavior before changing it, then test the target
   contract through an installed CLI.
4. Route a migrated behavior through exactly one Application use case and
   delete its obsolete implementation in the same change.
5. Add no generic repository, backend, gateway, manager, service locator,
   compatibility facade, or utility package without a concrete retained use
   case and an approved decision.
6. Domain and Application remain synchronous and framework-free. Bootstrap uses
   ordinary constructor injection.
7. Canonical files commit before projections. Projection refresh is one-way
   from canonical files; failure can mark an index stale but cannot invalidate a
   successful canonical write or make SQLite authoritative.
8. Every breaking public change receives requirement disposition, migration or
   replacement guidance, and an Unreleased changelog entry.
9. A passing test count is not enough: tests that protect removed behavior are
   deleted, and retained tests must identify the contract or risk they cover.
10. No phase may increase the architecture violation baseline.

## Execution roadmap

### Phase 0 — approve scope and compatibility

**Purpose:** decide what 0.2 promises before moving code.

Deliverables:

- triage the requirement registers, accepting the 0.2 Must journeys and
  deferring or rejecting removed and post-0.2 behavior;
- replace every `TBD` roadmap target used by 0.2 with a phase identifier;
- inventory documented commands, options, exit categories, structured output,
  configuration keys, canonical fixtures, and stable IDs;
- classify each surface as Preserve, Replace, Remove, or Internal; and
- correct README and user-guide claims so 0.1.1 and the planned 0.2 boundary are
  truthful.

Primary requirements: TR-004, TR-015; UR-013, UR-048.

Exit gate: every retained or removed public behavior has an explicit
disposition, evidence fixture, and owner. No Draft requirement is treated as
committed scope merely because code exists for it.

### Phase 1 — install enforceable guardrails

**Purpose:** make architecture drift mechanically impossible.

Deliverables:

- add `architecture.toml`, an exact `architecture-baseline.toml`, the AST policy
  test, and positive and negative fixtures from the approved specification;
- make new violations, stale baseline entries, package cycles, and malformed
  exceptions fail locally and in CI;
- repair Pyright configuration and establish a realistic ratcheting policy;
- provide one fast local check and one documented CI-equivalent check; and
- add repository link and documentation-source checks without rebuilding the
  generated Sphinx tree.

Primary requirements: TR-003, TR-011, TR-015.

Exit gate: a deliberately injected forbidden dependency fails with an exact
diagnostic, current violations are fully enumerated, and no wrapper converts
architecture failures to success.

### Phase 2 — establish Bootstrap and the domain kernel

**Purpose:** create the only target construction path and a framework-free
business model.

Deliverables:

- create `roadmap.bootstrap` as the sole composition root;
- define stable IDs, workflow state, retention state, and typed failures under
  `roadmap.domain`;
- define narrow Application-owned ports and the unit-of-work boundary;
- resolve one immutable configuration snapshot per invocation; and
- make the console entry point delegate to Bootstrap without importing concrete
  collaborators in command modules.

Primary requirements: TR-005, TR-008, TR-017, TR-019, TR-020, TR-021.

Exit gate: Domain imports only the standard library and Domain; Application
imports only Domain and Application; one installed smoke command is constructed
entirely through Bootstrap.

### Phase 3 — migrate the issue journey vertically

**Purpose:** prove the target architecture on the central product behavior.

Deliverables:

- implement create, list, view, update, start, block, close, archive, and restore
  as explicit Application use cases;
- add the inbound Click adapter, document adapter, SQLite projection adapter,
  and Bootstrap wiring required by those use cases;
- refresh affected SQLite records after canonical commits and detect manual or
  Git-authored changes for incremental refresh or full rebuild;
- enforce stable-ID lookup, explicit lifecycle query scope, typed validation,
  atomic writes, and deterministic structured output;
- preserve supported legacy IDs and user-authored Markdown; and
- delete the superseded issue services, coordinators, gateways, repositories,
  CLI helpers, and duplicate tests for each migrated operation.

Primary requirements: UR-002, UR-017 through UR-020, UR-037, UR-040, UR-046;
TR-002, TR-005, TR-008, TR-013, TR-017, TR-020, TR-021, TR-029, TR-030.

Exit gate: the complete issue lifecycle passes against canonical fixtures and a
clean installed artifact; interruption and projection-corruption tests recover
without canonical data loss; there is one production path per operation.

### Phase 4 — migrate planning and reporting slices

**Purpose:** complete the smallest coherent planning product.

Deliverables:

- migrate project and milestone create, list, view, update, assignment, close,
  archive, restore, and derived progress behaviors;
- migrate basic daily, board, export, and report queries only where they use the
  same Application-owned calculation policy;
- validate cross-aggregate references and dependency graphs; and
- remove duplicate presenters, CRUD base classes, coordinators, storage
  managers, and calculation paths as their slices move.

Primary requirements: UR-003, UR-004, UR-021, UR-024 through UR-028, UR-040,
UR-041; TR-017, TR-020, TR-021, TR-022, TR-024, TR-032.

Exit gate: project and milestone progress reconciles from linked canonical
issues after mutation, manual edit, archive, restore, and projection rebuild.

### Phase 5 — migrate workspace storage and configuration

**Purpose:** make existing repositories safely consumable by the target model.

Deliverables:

- inventory and version every canonical schema and configuration key;
- implement migration preflight, dry-run, collision detection, transaction
  journal, recovery, and unsupported-future-version rejection;
- migrate entities to flat, complete-ID paths without changing existing IDs;
- replace physical archive moves with lifecycle metadata;
- make SQLite disposable and rebuildable from canonical documents; and
- remove ambient settings, Dynaconf access, and adapter-crossing configuration.

Primary requirements: UR-011, UR-015, UR-016, UR-037, UR-045 through UR-048,
UR-058; TR-002, TR-007, TR-008, TR-019, TR-029, TR-030, TR-034, TR-035.

Exit gate: representative 0.1.1 repositories migrate idempotently; an injected
failure at every commit stage recovers to a complete old or new state; deleting
SQLite changes no canonical digest and rebuilds equivalent query results.

### Phase 6 — narrow Git and operational boundaries

**Purpose:** retain useful local integration without recreating synchronization.

Deliverables:

- keep only explicit repository inspection and ordinary external references
  behind narrow Application ports;
- ensure Roadmap never owns remote transport, authentication, fetch, pull,
  merge, rebase, push, or provider reconciliation;
- migrate health detection, targeted repair, cleanup, logging, and telemetry to
  their owning adapters; and
- remove credentials and network dependencies that have no retained boundary.

Primary requirements: UR-005, UR-007, UR-009, UR-029, UR-033 through UR-039,
UR-042 through UR-045; TR-006, TR-009, TR-010, TR-014, TR-025, TR-028, TR-031,
TR-033.

Exit gate: core journeys pass with network access blocked; Git failures are
bounded and non-mutating; no Roadmap configuration or canonical document stores
provider credentials or synchronization state.

### Phase 7 — delete remote synchronization and dissolve legacy zones

**Purpose:** collect the simplification dividend instead of leaving two systems.

Deliverables:

- delete remote sync commands, provider backends, merge engines, baselines,
  checkpoints, remote reconciliation, provider mappings, remote sync
  persistence, sync metrics, and their tests and documentation;
- retain and re-home useful canonical-to-SQLite refresh and rebuild behavior
  under the outbound projection adapter, without a generic sync abstraction;
- delete the no-op Git sync abstraction;
- remove empty compatibility packages and all remaining legacy construction
  paths;
- move each surviving `common`, `core`, `infrastructure`, and `presentation`
  module to its semantic owner or delete it; and
- remove unused runtime dependencies and duplicate documentation systems.

Primary requirements: UR-007, UR-033 through UR-036; TR-003, TR-009, TR-028.

Exit gate: no removed remote-sync namespace, command, setting, database, metric,
provider dependency, or documentation claim remains; the retained projection
pipeline rebuilds SQLite solely from canonical files; the architecture baseline
is empty; legacy ownership-zone packages no longer exist.

### Phase 8 — harden and release 0.2.0

**Purpose:** prove the contracted product from a user's installation boundary.

Deliverables:

- run migration and user-journey tests across supported Python and OS targets;
- build wheel and sdist once, inspect them, and smoke-test both outside the
  source tree;
- test interruption, concurrency, invalid files, projection corruption,
  structured output, offline operation, and clean uninstall/reinstall paths;
- publish migration guidance, removed-feature guidance, architecture metrics,
  and a truthful portfolio-oriented case study; and
- publish 0.2.0 through the existing trusted publishing workflow.

Primary requirements: TR-001, TR-004, TR-011, TR-012, TR-015, TR-016, TR-036.

Exit gate: all retained public journeys pass from installed artifacts; CI is
green; the version, changelog, docs, requirements, package metadata, and tag
agree; rollback guidance has been exercised on fixtures.

## Release checkpoints

- **0.2.0-alpha.1:** Phases 0–3 complete. Bootstrap and the issue journey use the
  target architecture, but migration is explicitly experimental.
- **0.2.0-beta.1:** Phases 4–7 complete. All retained commands use the target
  architecture, sync is absent, storage migration is feature-complete, and the
  architecture baseline is empty.
- **0.2.0:** Phase 8 complete. The installed package and supported workspace
  migrations meet the declared compatibility contract.

No alpha or beta is published merely because a date arrives.

## Progress measures

Record these at the end of every phase:

- architecture-baseline violations by rule;
- production modules and lines by architectural zone;
- production Python CLOC before, after, and phase delta;
- retained behaviors with more than one production implementation;
- remote-sync-specific modules and lines remaining;
- canonical-to-projection refresh and rebuild contract tests passing;
- legacy-package imports remaining;
- runtime dependencies with a named retained boundary;
- public commands covered through installed-artifact contract tests;
- canonical migration fixtures passing; and
- Must requirements accepted, implemented, and verified.

The final required values are zero architecture exceptions, zero
remote-sync-specific code, zero legacy ownership zones, one composition root,
one canonical-to-projection pipeline, and one implementation path for every
retained behavior. Production Python CLOC may not increase between accepted
phases. That ratchet complements rather than replaces correctness, data safety,
architecture, performance, and meaningful test evidence.

## Pull-request shape

Each implementation pull request should contain:

- the requirement IDs and roadmap phase it advances;
- the preserved, replaced, or removed public behavior;
- characterization evidence before the change;
- target Domain/Application contracts and boundary tests;
- the obsolete production and test paths deleted by the change;
- architecture-baseline entries removed;
- data migration, rollback, or “no data impact” notes; and
- documentation and Unreleased changelog updates when behavior changes.

Avoid long-running branches and package-wide rewrites. Merge small vertical
slices only when their old path has been removed and the phase gate remains
green.

## Reconsideration triggers

Reconsider a scoped rewrite only if a target vertical slice demonstrates, with
fixtures, that the current canonical data cannot be preserved safely or that the
released CLI contract cannot be characterized. Even then, rewrite the affected
adapter or slice behind the approved boundaries; changing languages requires a
new decision with measured operational benefit.

Reconsider SQLite only if projection benchmarks or operational failures show it
cannot meet the documented small-team envelope. A document database would still
be derived state and would not replace canonical files.

Reconsider requirements as an application feature after 0.2 when the same
artifact, lifecycle, transaction, migration, and traceability primitives can be
added without a second implementation path.

## Immediate next change

Follow the detailed execution plan and begin only Phase 0: prove the unchanged
baseline, create the compatibility fixture and checkpoint harness, run the full
suite and installed-artifact journeys, report the evidence, and stop. Phase 1
does not begin until the maintainer reviews that checkpoint and explicitly
continues.
