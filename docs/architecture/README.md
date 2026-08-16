# Architecture decisions

This directory contains the authoritative architectural decisions for Roadmap.
When an older design note, generated Sphinx page, or implementation detail
conflicts with an accepted ADR here, the accepted ADR takes precedence.

The ADRs describe the intended architecture. The current package layout is in
transition and is not evidence that a conflicting dependency is permitted.
Implementation changes require separate, explicitly scoped work.

## Accepted decisions

- [ADR-0001: Adopt pragmatic hexagonal architecture](adr/0001-pragmatic-hexagonal-architecture.md)
- [ADR-0002: Use Git as the sole synchronization mechanism](adr/0002-git-owned-synchronization.md)
- [ADR-0003: Use canonical files with rebuildable projections](adr/0003-canonical-files-and-rebuildable-projections.md)
- [ADR-0004: Define domain boundaries and stable identity](adr/0004-domain-boundaries-and-stable-identity.md)
- [ADR-0005: Make writes consistent under concurrency and failure](adr/0005-write-consistency-and-concurrency.md)
- [ADR-0006: Assign validation and error ownership by boundary](adr/0006-validation-and-error-ownership.md)
- [ADR-0007: Define the compatibility and evolution contract](adr/0007-compatibility-and-evolution.md)
- [ADR-0008: Separate entity lifecycle from physical storage](adr/0008-lifecycle-independent-of-storage.md)
- [ADR-0009: Assign configuration ownership and scope](adr/0009-configuration-ownership-and-scope.md)
- [ADR-0010: Use stable ID-based canonical paths](adr/0010-stable-id-based-canonical-paths.md)

## Approved implementation specification

- [Refactor implementation](refactor-implementation.md)

## Delivery plans

- [Roadmap 0.2 architecture simplification plan](roadmap-0.2.md)
- [Roadmap 0.2 refactor execution plan](refactor-execution-plan.md)

## Execution checkpoints

- [Phase 0 unchanged baseline — 2026-08-16](checkpoints/phase-0-baseline-2026-08-16.md)
- [Phase 0A lifecycle repair — 2026-08-16](checkpoints/phase-0a-lifecycle-repair-2026-08-16.md)
