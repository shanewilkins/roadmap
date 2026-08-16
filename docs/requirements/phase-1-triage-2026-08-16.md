# Phase 1 requirements triage

- Decision date: 2026-08-16
- Target release: 0.2.0
- User requirements: 46 Accepted, 13 Deferred
- Technical requirements: 34 Accepted, 10 Deferred
- Draft, TBD, Rejected, and unowned rows: 0

Every `Must` requirement is Accepted and assigned to a 0.2 implementation
phase. Accepted `Should` and `Could` rows are likewise scheduled. Dependencies
and requirement references are checked by the public-contract policy test.

## Deferred product directions

`UR-006`, `UR-030`, and `UR-031`, with `TR-026` and `TR-027`, defer automatic
Git-hook installation and commit-message-driven mutation until after 0.2. The
0.2 product still supports ordinary Git collaboration, explicit branch and
issue references, and local Git inspection. Provider synchronization is not a
deferred 0.2 feature: ADR-0002 rejects it in favor of ordinary Git.

`UR-049` through `UR-057` and `UR-059`, with `TR-037` through `TR-044`, defer
requirements as first-class Roadmap entities. The CSV registers remain the
authoritative governance inputs. A later product decision can adopt the
requirements-as-artifacts proposal without burdening the core 0.2 refactor.

## Scheduling rationale

- Phases 2–5 establish dependency rules, errors, identity, and repositories.
- Phases 6–8 migrate queries and the issue/project/milestone vertical slices.
- Phase 9 owns typed configuration and workspace migration.
- Phase 10 owns reports, structured output, health, repair, and retained Git
  conveniences.
- Phase 11 removes retired remote-sync, provider, hook, placeholder, and
  duplicate command surfaces.
- Phases 12–14 consolidate migrations, packaging, tests, and documentation.

No production behavior changes in Phase 1. The accepted requirements and
[public contract](../architecture/public-contract-0.2.md) constrain the later
implementation phases.
