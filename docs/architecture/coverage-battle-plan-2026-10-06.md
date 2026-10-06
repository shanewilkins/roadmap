# Coverage battle plan: 2026-10-06

This is a prioritization report, not an implementation pass. No new tests or
production changes were made for these coverage targets.

## Baseline and interpretation

The latest full reliability run passed **541 tests**. Coverage.py 7.16.2 reports
**85.90% statement coverage**: 4,708 of 5,481 executable statements covered,
773 missing. The sweep uses that run's `.coverage` data, exported with:

```sh
uv run --locked --extra dev coverage json --rcfile=config/.coveragerc \
  -o /tmp/roadmap-coverage-sweep.json
```

Branch coverage is not enabled, so these numbers do not measure every decision
outcome. Child Python processes are not instrumented by the current coverage
configuration. A reported 0% means no execution was observed in the instrumented
run; it does not prove a function has never been exercised. In particular, the
installed-package checkpoint journey exercises project archive and restore.
Before adding tests, reconcile each gap with existing subprocess scenarios.

Priorities below weigh irreversible operations, consistency across related
entities, corrupted user-authored input, and truthful failure reporting. File
percentages establish scope; each proposal targets a concrete safety contract.

## Five priorities

| Order | Target | File coverage | Missing statements | Main risk |
| --- | --- | --- | --- | --- |
| 1 | `application/use_cases/planning.py` | 85.93% | 56 | Deleting referenced projects or selecting the wrong retention batch |
| 2 | `adapters/inbound/cli/cleanup.py` | 64.77% | 31 | Removing the wrong backups or claiming partial deletion succeeded |
| 3 | `application/use_cases/issue_mutations.py` | 89.20% | 35 | Inconsistent reciprocal dependencies and unsafe bulk lifecycle changes |
| 4 | `adapters/outbound/persistence/documents.py` | 86.00% | 28 | Misinterpreting damaged or manually edited canonical documents |
| 5 | `adapters/outbound/persistence/diagnostics.py` | 84.51% | 22 | Reporting health or offering repairs when storage cannot be inspected safely |

Paths in the table are relative to `roadmap/`.

### 1. Planning deletion and retention

`Planning.purge_project` (line 627) is entirely unobserved: 10 missing statements.
`_retention_selection` has 57.1% coverage; project archive and restore wrappers
are also unobserved in pytest, though covered by the separate package journey.

Start with project purge: reject a visible project, reject an archived project
referenced by a milestone, and delete an archived unreferenced project. Verify
canonical documents and projection contents after each outcome, including that
rejected operations change nothing. Then cover mixed visible/archived and
complete/incomplete batches, dry runs, forced archive, ambiguous names, and
project closure with open milestones. Exercise commit failure on a deletion
through the existing real persistence fixtures rather than only mock assertions.

### 2. Backup selection and deletion

`_stale_paths` (line 29) and `_remove_backups` (line 77) both report 0%. Existing
cleanup integration tests mostly use workspaces without backup files, leaving
the actual selection and removal paths unobserved.

Use populated backup groups with controlled modification times. Check keep
limits, age boundaries, combined options, equal-time ordering, and invalid
negative values. Assert dry runs and declined confirmation preserve every byte;
confirmed cleanup removes exactly the listed files and leaves canonical files
and transaction journals intact. Inject an unlink failure after one successful
removal and require a nonzero exit with truthful partial-failure details.

### 3. Issue lifecycle and dependency integrity

`_archive_selection` (line 650) has 28.6% coverage; `_reciprocate_new` has 66.7%.
`replace_dependency` has 82.6%, with unobserved invalid-link, no-op, and domain
failure handling. Successful dependency replacement already has a unit test.

Cover mixed bulk archive selections, orphan selection, force versus closed-only
guards, and dry-run immutability. For dependency edits, test missing old links,
same-ID replacement, duplicate new links, cycles, and creation with outgoing
`blocks` relationships. Assert both sides of each relationship in canonical
files and projections. A rejected edit or commit failure must leave all related
issues unchanged. Verify restore with a status change, already-visible entries,
and invalid transitions without partial batch updates.

### 4. Canonical document validation

Validation helpers have substantial uncovered error handling: `_enum` 50%,
`_ids` 62.5%, `_timestamp` 71.4%, and `_base` 72.7%. These are input boundaries
for files users can edit or merge directly.

Build representative malformed fixtures: wrong container types, invalid enums,
timestamps and IDs, malformed comments/history, unsupported schema, and invalid
frontmatter. Assert actionable parse failures and byte-for-byte preservation
through rejected commands and health scans. Pair valid legacy/current fixtures
with round trips that preserve unknown frontmatter and body content. Parameterize
shared validation cases, while retaining entity-specific relation cases.

### 5. Diagnostics and repair refusal

`_pending_transactions` (line 314) has 55.6% coverage; `apply` has 70% and
`_process_document` 73.9%. The recent reliability tests already cover common
interrupted transactions and missing/corrupt/truncated projections.

Focus next on inaccessible journal directories, unreadable canonical files,
duplicate IDs, unresolved merge markers, noncanonical paths, and projection
inspection exceptions. Assert critical/error findings and refusal of unsafe
repair. Inject repair I/O failures and require a storage-unavailable failure,
nonzero CLI exit, and recoverable remaining state. Keep an explicit distinction
between a damaged rebuildable projection and inaccessible canonical storage.

## Iteration and the 90% goal

Start with priorities 1 and 2, then relationship integrity, input validation,
and diagnostic refusal. For each slice, run focused tests with real temporary
workspaces, assert both successful state and failed-operation immutability, then
run the full suite and regenerate this ranking. Reuse the existing fault and
process recovery fixtures where they test the relevant contract.

At a fixed denominator, reaching 90% needs **225 additional covered statements**.
These five files contain 172 missing statements in total; even covering all of
them would reach only about **89.03%**. This is a first reliability tranche, not
a promise to reach the threshold. The next sweep should assess configuration
validation and workspace discovery before selecting further work. Production
changes can also change the denominator.

The raw lowest-coverage files include the analysis presenter (21.4%), daily
summary (26.9%), project view (39.1%), milestone view (40.0%), and analysis CLI
commands (42.6%). Those percentages alone do not justify taking priority over
deletion safety and data integrity. Their useful follow-up tests should assert
correct results on realistic planning graphs, rather than merely rendering lines
to improve the metric.
