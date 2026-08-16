# Phase 0A checkpoint — baseline lifecycle repair

- Date: 2026-08-16
- Baseline commit: `61595a6e2ac7d014bb75fa43524f5df3851efa0d`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 1

## Decision

The Phase 0 lifecycle blockers are repaired and every required local checkpoint
is green. Phase 1 may begin after explicit maintainer approval.

This phase deliberately repaired released behavior before architectural
restructuring. It did not remove commands or approved user journeys. The
maintainer explicitly exempted Phase 0A from the production-CLOC no-increase
gate because correctness was the controlling objective. The implementation
nevertheless reduced production Python code by 19 lines.

## Behavior repaired

- Issue comments now persist through the coordinator's supported keyword API.
  Invalid bodies, missing reply targets, comment creation failures, and issue
  persistence failures return a nonzero process status.
- Issue archive and restore use atomic same-filesystem moves, honor dry-run
  without mutation, operate only on validated entities, and keep canonical
  lifecycle metadata and the local SQLite projection consistent.
- SQLite initialization and legacy migration independently add required
  `archived` and `archived_at` columns.
- Local projection rebuilds include archived issues. Archived state and its
  timestamp are projected as columns rather than being hidden in metadata.
- Projectless issues remain valid during local projection rebuilds, matching the
  nullable SQLite schema and legacy file behavior.
- Milestone creation persists its `project_id`, updates the project's milestone
  relation, and no longer creates a health-check orphan while claiming success.
- The compatibility fixture and checkpoint runner rejected by Phase 0 now exist
  and pass from an installed wheel.

No behavior was intentionally removed. Provider-to-provider synchronization and
the larger 0.2 architectural migration remain deferred to their planned phases;
local canonical-file-to-SQLite synchronization remains supported.

## Requirements advanced

The repair and evidence directly advance UR-002, UR-003, UR-011, UR-013,
UR-015, UR-022, UR-026, UR-037, UR-045, UR-046, and UR-047, together with
TR-002, TR-004, TR-007, TR-016, TR-020, TR-021, TR-023, TR-024, TR-029,
and TR-034. Requirement statuses remain Draft until Phase 1 contract triage.

## Production CLOC

Fixed command and tool: `cloc` 2.10 against `roadmap/`.

| Metric | Phase 0 | Phase 0A | Delta |
| --- | ---: | ---: | ---: |
| Python files | 504 | 504 | 0 |
| Blank lines | 16,017 | 16,006 | -11 |
| Comment lines | 20,317 | 20,312 | -5 |
| Code lines | 54,225 | 54,206 | -19 (-0.035%) |

The authorized Phase 0A LOC exception was not needed to reach `GO`. The Phase 1
ceiling is 54,206 production Python code lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed. |
| `uv lock --check` | Passed; 115 packages resolved. |
| Ruff format | Passed; 1,059 production/test files already formatted. |
| Ruff lint | Passed. |
| Pyright | Passed with 0 errors, 0 warnings, and 188 informational findings. |
| Bandit high-severity gate | Passed; 0 high findings (66 low, 5 medium). |
| Focused regression set | Passed; 26 tests. |
| Complete pytest suite | Passed; 8,289 tests in 152.42 seconds. |
| Coverage | Passed; 82.05% against the configured 81% minimum. |

The complete suite emitted 1,934 warnings, down from the Phase 0 baseline of
1,974. The remaining visible warnings continue to be dominated by unclosed
SQLite connection `ResourceWarning` instances and are deferred cleanup, not a
new Phase 0A regression.

## Distribution boundary

Both release artifacts were built in a fresh temporary directory, installed
without `PYTHONPATH`, imported from their isolated environments, and passed
help, version, initialization, issue creation, and issue listing smoke tests on
Python 3.14.2.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `f3e1a854c336b13c30bd276489fe3c72bff7900a428dfa9615597547614460a7` | Passed |
| `roadmap_cli-0.1.1.tar.gz` | `44b29ae2195726a040021a830841ac5be29a791213e8186eb213cc207b458e7a` | Passed |

The initial sandboxed build could not resolve Hatchling because network access
was unavailable. The approved network-enabled build passed; this was an
environment restriction rather than a package defect.

## Installed application journeys

The reusable runner operated only in system temporary directories and used the
console script from a clean wheel installation. It passed:

1. help and version;
2. fresh initialization and safe reopen;
3. project and milestone creation with a bidirectional persisted relation;
4. issue creation, view, comment, close, archive dry-run, archive, and restore;
5. supported JSON parsing;
6. manual canonical-document edit observation;
7. SQLite deletion and rebuild without canonical digest changes;
8. JSON health diagnosis and non-mutating health-fix preview;
9. offline local Git initialization and status; and
10. two compatibility-fixture inspections and projection rebuilds with
    identical semantic snapshots.

The final compatibility snapshot contained the expected project and milestone,
visible issue IDs `5898cb1f` and `951f146d`, archived issue visibility, legacy
closed issue visibility, and the sanitized fixture comment. Projection rebuild
included all three issues and retained `archived = 1` for the archived issue.

## Compatibility and rollback evidence

The sanitized fixture under `tests/fixtures/compatibility/v0_1_1/` contains a
project, milestone, active issue, closed dependency, archived issue, comment,
legacy and current external IDs, and user-authored Markdown. Canonical SHA-256
digests are recorded separately from `projection.sql`.

The runner deletes only the disposable SQLite projection, rebuilds it from the
canonical files, and proves the canonical digests are unchanged. Archive and
restore dry-run and round-trip checks demonstrate reversible file behavior.

## Important implementation and evidence files

- `roadmap/adapters/cli/issues/comment.py`
- `roadmap/adapters/cli/crud/base_archive.py`
- `roadmap/adapters/cli/crud/base_restore.py`
- `roadmap/adapters/cli/issues/archive_class.py`
- `roadmap/adapters/cli/issues/restore_class.py`
- `roadmap/adapters/persistence/database_manager.py`
- `roadmap/adapters/persistence/entity_sync_coordinators.py`
- `roadmap/adapters/persistence/sync_orchestrator.py`
- `roadmap/infrastructure/coordination/milestone_coordinator.py`
- `scripts/checkpoint_journey.py`
- `tests/fixtures/compatibility/v0_1_1/`

## Known risks and deferred work

- Phase 0A repairs current 0.1.1 lifecycle semantics; it does not yet implement
  ADR-0008's eventual flat, lifecycle-independent canonical paths.
- Atomic multi-document units of work and failure recovery remain Phase 3 work.
- Existing architecture-policy violations and remote-sync removal are addressed
  in later approved phases.
- SQLite connection warning cleanup remains visible technical debt.
- CI matrix execution awaits a maintainer-authorized commit and push.

## Recommendation

**GO for Phase 1 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin contract triage automatically.
