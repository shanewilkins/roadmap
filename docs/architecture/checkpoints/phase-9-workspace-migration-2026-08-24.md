# Phase 9 checkpoint — Workspace migration and configuration

- Date: 2026-08-24
- Baseline commit: `7f8667139629592c0ddebb4142071db116ad7c5c`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 10

## Decision

Phase 9 is complete. Existing 0.1.1 workspaces now have one explicit,
idempotent migration into versioned configuration, versioned canonical
documents, flat stable-ID paths, metadata-owned lifecycle state, and a
rebuildable SQLite projection. Normal reads remain non-mutating.

Bootstrap resolves project policy and external user preferences once into an
immutable typed snapshot. Project configuration rejects credentials, provider
state, Git transport policy, machine paths, unknown keys, and user-scoped keys.
The ambient Dynaconf singleton, duplicate configuration loaders/models, and
provider configuration writer were removed rather than retained as parallel
ownership paths.

## Migration contract

`roadmap migrate --dry-run` enumerates and validates the complete write set
without constructing the legacy core or changing workspace, projection, or
user files. `roadmap migrate --yes` verifies the preflight fingerprint before
writing and then:

1. preserves every existing entity ID, supported unknown field, relationship,
   timestamp, lifecycle value, and user-authored Markdown body;
2. writes documents to `.roadmap/<collection>/<complete-id>.md`;
3. reconciles identical duplicates and stops on non-identical duplicates,
   target collisions, invalid documents, permission loss, path escape, invalid
   configuration, or an unsupported future schema;
4. externalizes declared user preferences while existing user values win;
5. commits canonical writes and removals through the journaled unit of work;
6. writes the workspace schema marker as the final canonical replacement; and
7. rebuilds SQLite only after the canonical commit.

The projection may be deleted or corrupt and rebuilt without changing a
canonical digest. A repeated migration reports that no work is required.

## Configuration ownership

`.roadmap/config.yaml` is committed project policy and contains schema markers,
the default project ID, and critical-path policy. User identity, display,
behavior, output, and export preferences live in the platform user
configuration (`~/.config/roadmap/config.yaml` on the checkpoint platform).
Secrets remain in credential facilities or documented invocation environment;
Git owns repository identity and transport.

New workspaces use schema version one immediately. New issue and project IDs use
complete UUID4 values and canonical filenames; legacy IDs are never regenerated
or expanded during migration.

## Focused verification

The final affected-surface regression run passed **192 tests**. It covered
migration, configuration, canonical persistence, initialization, lifecycle,
daily identity resolution, architecture, output, and compatibility inventory.
The complexity extraction was also checked independently by a passing 12-test
migration slice, and the policy slice passed 32 tests.

The complete pytest suite was deliberately not run, following the maintainer's
explicit instruction not to rerun it. No skipped full-suite result is presented
as checkpoint evidence.

Migration-specific tests cover byte-identical dry run, semantic round-trip,
stable IDs and paths, archived retention, identical and non-identical
duplicates, future schemas, permission loss, corrupt projection, ordinary
failure rollback, process interruption, deterministic retry, and idempotency.
The canonical unit-of-work suite covers failure injection at validation,
journal, and replacement stages.

## Installed artifact and journeys

The final wheel was built from the final production tree, installed without
`PYTHONPATH` into a clean Python 3.14.2 environment, and passed import,
metadata/version, help, initialization, issue creation, and issue listing.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `74893fdcb80eec54dcf55ca9f01a7bd522b8754c760d9ee5f8cc2b35d0b74473` | Passed. |

The final cumulative installed journey passed against that wheel. It exercised
the retained fresh-workspace issue, project, milestone, lifecycle, planning,
manual-edit, health-preview, projection-rebuild, and local-Git paths. It then
ran two independent copies of the sanitized 0.1.1 fixture through:

- a machine-readable dry run with byte-identical workspace and user files;
- confirmed migration and flat-path/schema assertions;
- reopened project, milestone, visible/closed/archived issue, relationship, and
  comment journeys;
- deliberately corrupted projection recovery from canonical documents; and
- repeated no-op migration.

Both fixture runs produced the same semantic snapshot. Visible IDs remained
`5898cb1f` and `951f146d`; archived issue `a11ce001`, project `c83ed497`,
milestone `v0-1-1`, and the sanitized comment remained visible with their
original meaning.

## Production CLOC

Fixed command and tool: CLOC 2.10 with Python-only input under `roadmap/` and
`__pycache__` excluded.

| Metric | Phase 8 | Phase 9 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 488 | 487 | -1 |
| Blank lines | 14,465 | 14,303 | -162 |
| Comment lines | 17,732 | 17,376 | -356 |
| Code lines | 52,338 | 52,330 | -8 (-0.02%) |

The CLOC ratchet passes. The Phase 10 ceiling becomes 52,330 production Python
code lines. Phase 9 added the migration/configuration boundary while deleting
the superseded ambient and duplicate implementations rather than carrying both.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `uv lock --check` | Passed; 118 packages resolved. |
| Ruff lint and format | Passed; 1,236 files clean. |
| Pyright | Passed with 0 errors and 0 warnings. |
| Architecture policy | Passed with the exact seven reviewed Phase 11 exceptions and no new baseline entry. |
| Bandit high-severity gate | Passed; 0 high findings (64 low, 5 medium). |
| Radon/Xenon | Passed at absolute C, module C, average A; migration preflight is C (20), with no D-ranked block. |
| `git diff --check` | Passed. |
| Production CLOC ratchet | Passed at 52,330 code lines. |

## Requirements traceability

This phase directly advances UR-015, UR-016, UR-037, UR-045 through UR-048,
and UR-058. It supplies implementation and verification evidence for TR-002,
TR-004, TR-007, TR-008, TR-019, TR-029, TR-030, TR-034, and TR-035.
Requirement lifecycle status remains an explicit maintainer decision.

## Compatibility, recovery, and rollback

Ordinary source rollback remains a source-control revert. A workspace migration
must not be undone by installing old code over new canonical data. Before
execution, users inspect the dry-run and resolve every conflict. During
execution, the durable journal restores ordinary failures or rolls an
interrupted write set forward on retry. After canonical commit, projection
failure is repaired by rerunning `roadmap migrate`; canonical files remain the
authority.

## Known risks and deferred work

- Reporting, health repair, cleanup, recovery presentation, and the final local
  Git boundary remain Phase 10 work. Existing health commands were used only as
  retained journey checks; Phase 9 does not turn them into a migration engine.
- Remote synchronization commands and seven reviewed Application dependency
  exceptions remain until their approved Phase 11 deletion. Canonical-to-SQLite
  projection refresh/rebuild is retained and is not remote synchronization.
- Legacy ownership-zone packages and the compatibility facade remain until
  Phase 12; Bootstrap remains required composition infrastructure.
- The current migration is intentionally concrete: schema zero (0.1.1) to
  schema one. No generalized migration registry or speculative future chain was
  introduced.

## Recommendation

**GO for Phase 10 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin reporting, health, recovery, or local
Git migration automatically.
