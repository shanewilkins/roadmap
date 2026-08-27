# Architecture decisions

This directory contains the authoritative architectural decisions for Roadmap.
When an older design note, generated Sphinx page, or implementation detail
conflicts with an accepted ADR here, the accepted ADR takes precedence.

The ADRs describe the intended architecture. The current package layout is in
transition and is not evidence that a conflicting dependency is permitted.
Implementation changes require separate, explicitly scoped work.

## Current execution state

- Accepted checkpoint: Phase 13, hardening and 0.2.0 release preparation.
- Next work requires separate maintainer authorization: version bump, clean
  release commit, tag, trusted publication, and post-publication verification.
- Final planned implementation phase: Phase 13, 0.2.0 release preparation.
- The production-CLOC phase ratchet retired after Phase 13. Historical
  measurements remain in the execution plan and checkpoints; architecture,
  complexity, test, typing, security, and artifact gates now prevent regression.
- The first complete post-refactor suite established a 78.42% statement-
  coverage baseline; CI enforces a rounded 78% floor alongside installed
  end-to-end journeys.
- All implementation phases are complete; package version remains 0.1.1.

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
- [Roadmap 0.2 public contract](public-contract-0.2.md)
- [Roadmap 0.2 compatibility inventory](compatibility-inventory-0.2.csv)
- [Canonical persistence and projection contract](canonical-persistence-contract-0.2.md)
- [Runtime dependency boundaries](dependency-boundaries.md)
- [Measured 0.2 performance envelope](performance-envelope-0.2.md)
- [Portfolio case study](portfolio-case-study.md)

## Delivery plans

- [Roadmap 0.2 architecture simplification plan](roadmap-0.2.md)
- [Roadmap 0.2 refactor execution plan](refactor-execution-plan.md)
- [Roadmap 0.2.0 release checklist](../releases/0.2.0-checklist.md)
- [Roadmap 0.2.0 rollback plan](../releases/0.2.0-rollback.md)
- [Roadmap 0.1.1 to 0.2 migration guide](../user_guide/MIGRATING_TO_0_2.md)

## Execution checkpoints

- [Phase 0 unchanged baseline — 2026-08-16](checkpoints/phase-0-baseline-2026-08-16.md)
- [Phase 0A lifecycle repair — 2026-08-16](checkpoints/phase-0a-lifecycle-repair-2026-08-16.md)
- [Phase 1 public contract — 2026-08-16](checkpoints/phase-1-public-contract-2026-08-16.md)
- [Phase 2 architecture enforcement — 2026-08-16](checkpoints/phase-2-architecture-enforcement-2026-08-16.md)
- [Phase 3 Bootstrap composition root — 2026-08-16](checkpoints/phase-3-bootstrap-composition-root-2026-08-16.md)
- [Phase 4 Domain and Application contracts — 2026-08-17](checkpoints/phase-4-domain-application-contracts-2026-08-17.md)
- [Phase 5 canonical persistence and SQLite projection — 2026-08-17](checkpoints/phase-5-canonical-persistence-projection-2026-08-17.md)
- [Phase 6 issue queries — 2026-08-17](checkpoints/phase-6-issue-queries-2026-08-17.md)
- [Phase 7 issue mutations — 2026-08-17](checkpoints/phase-7-issue-mutations-2026-08-17.md)
- [Phase 8 planning path — 2026-08-24](checkpoints/phase-8-planning-2026-08-24.md)
- [Phase 9 workspace migration — 2026-08-24](checkpoints/phase-9-workspace-migration-2026-08-24.md)
- [Phase 10 operational boundaries — 2026-08-24](checkpoints/phase-10-operational-boundaries-2026-08-24.md)
- [Phase 11 remote sync removal — 2026-08-24](checkpoints/phase-11-remote-sync-removal-2026-08-24.md)
- [Phase 12 legacy-zone dissolution — 2026-08-26](checkpoints/phase-12-legacy-zone-dissolution-2026-08-26.md)
- [Phase 13 release candidate — 2026-08-26](checkpoints/phase-13-release-candidate-2026-08-26.md)
