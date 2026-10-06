# Ordered reliability branch pass — 2026-10-06

This follows the [quality review actions](quality-review-actions-2026-10-06.md)
and tackles migration, canonical persistence, planning, domain aggregates and
issue listing in that order. It adds 49 test cases to the previous 1,132-case
candidate. The purpose is behavior under failure and repetition, not a new gate.

## Contracts exercised

- Migration: invalid legacy settings and schema values, non-mapping YAML,
  current-schema/legacy-layout inconsistencies, symlink escapes and case-folded
  target collisions refuse execution without changing source or personal bytes.
  Minimal and missing configurations migrate successfully and repeated previews
  recognize the resulting current workspace.
- Canonical persistence: unknown journal states retain files and recovery
  evidence; recovery refusal releases the writer lock. Unexpected lock errors
  preserve their errno and close the descriptor. ENOSPC before journal creation
  leaves original bytes and no pending transaction, and retry succeeds.
  Read-only commits refuse writes; deleting an absent issue is repeatable.
- Planning: duplicate names and missing assignment targets fail without commit;
  repeated assignment/closure and unchanged updates do not add commits or events.
  Standalone milestones and unique ID prefixes resolve correctly. Archived
  entities require explicit visibility; archive requires a selector. Manually
  authored dependency cycles terminate deterministically in daily recommendations;
  missing dependencies do not break critical-path calculation. Reprojection
  avoids duplicate reciprocal links; milestone purge preserves unrelated projects.
- Domain: inconsistent actual/target dates, invalid effort/progress and duplicate
  or dangling comment IDs fail explicitly. Rejected edits preserve the original
  immutable aggregate; zero progress resets status and repeated branch linking
  does not duplicate the branch.
- Issue listing: actual rich CLI output covers minute/hour/day estimates and
  workload totals/status counts scoped to assignee or current identity. Listing
  preserves canonical bytes; an already-built projection remains unchanged.
  Missing upcoming milestones produce a specific explanation. Empty-list advice
  now includes the required `--title`; executing the suggested command succeeds.

Tests live in:

- [Workspace migration](../../tests/unit/adapters/persistence/test_workspace_migration.py)
- [Transaction recovery](../../tests/unit/adapters/persistence/test_transaction_recovery.py)
- [Planning](../../tests/unit/application/test_planning.py)
- [Domain contracts](../../tests/unit/domain/test_domain_contracts.py)
- [Issue-list CLI](../../tests/integration/cli/test_issue_listing_reliability.py)

## Remaining outcomes in the selected files

| File | Previously missing arcs | Remaining arcs | Executed / total |
| --- | ---: | ---: | ---: |
| Migration | 13 | 1 | 81 / 82 |
| Canonical persistence | 9 | 4 | 104 / 108 |
| Planning | 17 | 2 | 110 / 112 |
| Domain aggregates | 10 | 0 | 28 / 28 |
| Issue listing | 9 | 0 | 18 / 18 |

The seven remaining arcs are retained defensive paths, not seven demonstrated
reliability defects. Migration's duplicate-path guard spans disjoint scan roots.
Canonical's two aggregate-type guards sit behind typed document parsing; another
guard releases an unentered lock, and another handles a deletion whose parent
directory has disappeared. Planning's two archived guards sit after a snapshot
already filtered to visible entities. This pass does not fabricate invalid
repository results or weaken coverage exclusions to execute those guards.
Concurrent external removal of a parent remains an untested race outcome.

The global branch inventory still includes 71 Protocol method-stub arcs. They
are not application decisions. Branch execution also does not prove every
possible input or assert every semantic requirement.

## Validation

- Full configured gate: `uv run --locked pytest --cov=roadmap
  --cov-config=config/.coveragerc --cov-report=term
  --cov-report=json:/tmp/roadmap-reliability-branches-statements.json` —
  **1,181 passed**, 79 existing Click warnings, **97.21% statement coverage**.
  Previous candidate: 96.20%. The enforced floor remains 90%.
- Informational branch command uses a separate
  `COVERAGE_FILE=/tmp/roadmap-reliability-branches-data`, `--cov-branch` and
  `--cov-fail-under=0`; report: `/tmp/roadmap-reliability-branches.json`.
  Sequential full run: **1,181 passed**, 79 existing warnings. Measured
  **88.96%** (1,313 / 1,476), up from 85.50%; missing arcs fall from
  214 to 163, including 51 additional executed outcomes in the selected files.
- Configured Ruff lint, ty, architecture contracts (4 kept) and Xenon B/B/A pass.
  Python formatting is checked with the repository Ruff configuration.

The first full runs exposed unnormalized assertions in the new CLI test and a
performance timing failure while two suites ran concurrently. The assertions
were normalized; suites were rerun sequentially and the configured full gate
passed, including the unchanged performance envelope. No limits, exclusions or
allowlists were relaxed. No commit, push, release or PR change was made.
