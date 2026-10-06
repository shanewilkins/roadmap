# Reliability coverage expansion: 2026-10-06

This is the first implemented tranche of the
[coverage battle plan](coverage-battle-plan-2026-10-06.md). It strengthens
evidence for data safety and predictable failure handling; it does not assign
a new quality-review score or claim the 90% coverage goal has been reached.

## Results

The full local suite passed **592 tests** on macOS ARM64 / Python 3.14.2.
Statement coverage increased from **85.90% to 87.76%**: 4,811 of 5,482
statements covered. The enforced coverage floor remains 85%.

There are 48 added reliability cases and three type-gate rejection cases.
Existing successful-path, process-death, and installed-package tests remain.
An isolated Python invocation also passed 88 lifecycle, cleanup, document, and
diagnostics cases against the newly built non-editable wheel, after asserting
that `roadmap` imports from the isolated environment's site-packages.

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
  development declarations. The lockfile shrinks from 53 to 38 packages.
- Keep Ruff, Bandit, dependency auditing, architecture enforcement, Xenon,
  actionlint, distribution checks, and the existing compatibility matrix.
- Replace the descriptive pre-commit Radon report with architecture enforcement;
  retain Radon reporting in CI and Xenon's enforcing gate in both surfaces.
- Save JSON/XML coverage evidence in CI for 14 days, including on failure.
- Release tags call the same full CI workflow before release build/publication.
  Build with uv/Hatchling; no additional build tool is introduced.

Actionlint 1.7.12 locally validated the reusable CI and release definitions.
Ruff, ty, architecture enforcement, Bandit, Xenon, lock integrity, and dependency
audit passed locally. Remote checks for this change still need to run.

## Remaining reliability work

Prioritize issue creation with outgoing blocking relationships and restore
status changes, planning edits that reassign linked entities, ambiguous name
resolution, and inaccessible canonical directory enumeration. These remain
meaningful safety gaps even though these five files now mostly exceed 90%.
Then assess configuration validation and workspace discovery. Prefer asserted
postconditions and failed-operation immutability over incidental execution.

Coverage remains statement-only; subprocess execution is not instrumented by
the current configuration. Reported percentages describe observed pytest
execution, not every CLI/process scenario or every decision outcome. The 79
existing warnings concern deprecated Click isolated-filesystem fixtures; migrate
those incrementally when touching their tests rather than hiding the warnings.
