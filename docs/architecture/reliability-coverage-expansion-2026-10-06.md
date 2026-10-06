# Reliability coverage expansion: 2026-10-06

This is the first implemented tranche of the
[coverage battle plan](coverage-battle-plan-2026-10-06.md). It strengthens
evidence for data safety and predictable failure handling; it does not assign
a new quality-review score or claim the 90% coverage goal has been reached.

## Results

The full local suite passed **624 tests** on macOS ARM64 / Python 3.14.2.
Statement coverage increased from **85.90% to 88.06%**: 4,829 of 5,484
statements covered. The enforced coverage floor is raised from 85% to 87%.

The original tranche added 48 reliability cases and three type-gate rejection
cases; this follow-up adds 32 more reliability cases plus import-gate proofs.
Existing successful-path, process-death, and installed-package tests remain.
An isolated Python invocation also passed 120 lifecycle, cleanup, document, and
diagnostics cases against the newly built non-editable wheel, after asserting
that `roadmap` imports from the isolated environment's site-packages.

The table below records the original tranche; follow-up regressions are described
separately below.

| Reliability target | Before | After | Evidence |
| --- | --- | --- | --- |
| Planning lifecycle | 85.93% | 90.95% | Visible/referenced/missing project purge refusal; successful purge; mixed retention batches; dry runs; force/non-cascade boundaries; failed deletion restoration |
| Backup cleanup | 64.77% | 98.86% | Populated groups; age cutoff and timestamp ties; exact confirmed selection; preview/decline/invalid options preserve files; truthful partial unlink failure |
| Issue mutations | 89.20% | 92.28% | Invalid links, no-op replacements, cycles, deduplication, reciprocal relationships, partial-write rollback, closed/orphan archive boundaries |
| Canonical documents | 86.00% | 98.50% | Invalid timestamps, enums, IDs, relations, comments/history and YAML rejected without rewrite; legacy archive/type compatibility and unknown-field round trip |
| Diagnostics | 84.51% | 95.10% | Duplicate identities, wrong paths, malformed documents, unreadable journals/projections, repair refusal, and storage failure translation |

The lifecycle tests use real canonical storage and SQLite projections. Rejected
operations assert unchanged document bytes and projection rows. Write failures
are injected at the actual transaction boundary, including after deletion or
after one reciprocal document has been replaced, rather than only mocking a
successful commit response.

## Defect found and fixed

An unreadable transaction directory was reported as critical by health scanning,
but recovery preview silently treated it as having no pending transactions.
Preview now raises a storage-unavailable application failure when journals
cannot be inspected. Projection repair is also blocked by that critical finding.
This is additional evidence for TR-008 and TR-033/TR-034; passing tests does not
automatically change requirement-governance status.

## Toolchain decisions

- ty is the sole type checker; remove Pyright's dependency, config, and CI step.
  Explicit correctness rules and executable bad-code probes retain a meaningful
  gate at the Python 3.12 support floor.
- Remove unused pytest async/HTTP, benchmark, and mocking plugins and duplicate
  development declarations. The initial cleanup shrank the lockfile from 53 to 38 packages; adding
  Import Linter and its graph dependencies brings it to 41.
- Keep Ruff, Bandit, dependency auditing, architecture enforcement, Xenon,
  actionlint, distribution checks, and the existing compatibility matrix.
- Replace the descriptive pre-commit Radon report with architecture enforcement;
  retain Radon reporting in CI and Xenon's enforcing gate in both surfaces.
- Save JSON/XML coverage evidence in CI for 14 days, including on failure.
- Release tags call the same full CI workflow before release build/publication.
  Build with uv/Hatchling; no additional build tool is introduced.

Actionlint 1.7.12 locally validated the reusable CI and release definitions.
Ruff, ty, architecture enforcement, Bandit, Xenon, lock integrity, and dependency
audit passed locally. The first PR head passed all 12 CI jobs and CodeQL, with 87.72% Linux
coverage. The production follow-up at `5bf9ffba` also passed all 12 CI jobs and
CodeQL. Consult PR #3774 checks for the final deletion-race regression head.

## Follow-up architecture and reliability fixes

Stock Import Linter 2.15 / Grimp 3.17 now enforces layers, independent adapter
features, and protected bootstrap wiring. The old 649-line graph/exception
engine is replaced by narrow guards for retired namespaces, unzoned internal
imports, and the blanket external-library ban in core layers. All seven
original negative fixtures still fail; relative imports, aliases, and imports
inside `TYPE_CHECKING` have additional bypass regressions. The completed
migration baseline remains strictly empty.

Post-commit transaction cleanup errors now preserve successful acknowledgement,
clear pending writes, refresh the projection, and retain journals for retry on
reopen. Tests inject completed-directory rename, removal, and sync errors and
verify reopen preserves bytes. A simultaneous projection-refresh and stale-marker
failure also preserves canonical success; content comparison repairs the cache
on the next read. Warnings expose maintenance failures without encouraging a
retry of a committed mutation.

Backup cleanup refuses symlinked directories/files (including dangling links),
revalidates every selected path after confirmation, and unlinks through a
directory descriptor opened with `O_NOFOLLOW`. External backup bytes and all
unselected workspace files survive refusal. Canonical enumeration now uses an
error-reporting walk: root and nested directory denials fail scans and block
projection repair instead of producing an apparently empty inventory.

Additional real-storage tests cover issue creation with outgoing blocking links,
cycle/missing-target refusal, partial-write rollback, restore status transitions
and dry runs, batch restore refusal after a later invalid transition, milestone
reassignment across two projects, and concurrent opposing dependency additions.
The latter permits exactly one valid commit and rejects the cycle-producing edit.

The coverage floor is 87%, leaving matrix headroom below the observed result;
90% remains an incremental goal. No exclusions or synthetic execution were added
to reach that floor.

## Remaining reliability work

Prioritize ambiguous planning-name resolution, configuration validation, and
workspace discovery next. Broaden cross-process relationship contention and
filesystem fault coverage where the failure could violate a documented promise. Prefer asserted
postconditions and failed-operation immutability over incidental execution.

Coverage remains statement-only; subprocess execution is not instrumented by
the current configuration. Reported percentages describe observed pytest
execution, not every CLI/process scenario or every decision outcome. The 79
existing warnings concern deprecated Click isolated-filesystem fixtures; migrate
those incrementally when touching their tests rather than hiding the warnings.
