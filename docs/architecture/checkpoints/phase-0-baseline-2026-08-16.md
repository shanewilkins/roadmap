# Phase 0 checkpoint — unchanged 0.1.1 baseline

- Date: 2026-08-16
- Baseline commit: `61595a6e2ac7d014bb75fa43524f5df3851efa0d`
- Package version: 0.1.1
- Decision: **NO-GO**
- Production changes: none

## Decision

Do not begin Phase 1. The static gates, complete automated suite, coverage gate,
wheel, source distribution, and basic package smoke test pass. Disposable
end-to-end CLI journeys exposed multiple released behaviors that report success
while failing to persist their promised state consistently.

These are baseline reliability defects, not refactor regressions. Phase 0
explicitly forbids repairing them invisibly. They require a separately approved
baseline-remediation step followed by a complete rerun of Phase 0.

## Baseline metrics

| Metric | Result |
| --- | ---: |
| CLOC version | 2.10 |
| Production Python files counted | 504 |
| Production Python code lines | 54,225 |
| Production CLOC phase delta | 0 |
| Python used by pytest | 3.14.2 |
| uv version | 0.12.3 |
| Collected tests | 8,282 |
| Coverage statements | 30,795 |
| Covered percentage | 81.99% |

The verified Phase 0 production CLOC ceiling remains 54,225. No production file
was changed during this checkpoint.

## Passing gates

| Gate | Result |
| --- | --- |
| `uv lock --check` | Passed; 115 packages resolved. |
| Ruff format check | Passed; 1,052 files already formatted. |
| Ruff lint | Passed. |
| Pyright | Passed with 0 errors, 0 warnings, and 188 informational findings. |
| Bandit high-severity gate | Passed; 0 high-severity findings. |
| Complete pytest suite | Passed; 8,282 tests in 109.49 seconds. |
| Coverage gate | Passed; 81.99% against the configured 81% requirement. |
| Wheel build | Passed. |
| Source-distribution build | Passed. |
| Isolated wheel install/smoke | Passed on Python 3.14.2. |
| Isolated source-distribution install/smoke | Passed on Python 3.14.2. |

The artifact smoke tests imported Roadmap from their temporary virtual
environments, reported version 0.1.1, displayed help, initialized a temporary
workspace, created one issue, and listed it successfully.

The complete suite emitted 1,974 warnings. The visible warnings were dominated
by unclosed SQLite connection `ResourceWarning` instances. This count is
recorded as baseline evidence and is not silently accepted as a permanent
target.

The first sandboxed artifact build/install attempts failed because network
access to PyPI was unavailable. Repeating them with approved network access
passed. That initial failure is environmental rather than a package defect.

## Failing application journeys

All journeys ran in a disposable directory under `/private/tmp`; the
repository's live `.roadmap` workspace was not modified.

### 1. Issue comment creation reports false success status

Command:

```text
roadmap issue comment add 951f146d "Sanitized fixture comment." \
  --author fixture-user
```

Observed behavior:

```text
Failed to update issue: IssueCoordinator.update() takes 2 positional
arguments but 3 were given
```

The process exited with status 0. The canonical issue still contained an empty
`comments` list. A mutating command therefore failed, did not persist its
promised change, and reported a successful process status.

### 2. Issue archive moves the file but fails lifecycle persistence

Command:

```text
roadmap issue archive 5898cb1f --force
```

Observed behavior included:

```text
Warning: Failed to mark issue 5898cb1f as archived:
'IssueCoordinator' object has no attribute 'update_issue'
Archived 1 issue
```

The process exited with status 0 and physically moved the file under
`.roadmap/archive/issues/backlog/`, but its canonical frontmatter still said
`archived: false`. The command reported success with contradictory lifecycle
state.

### 3. Issue restore moves the file but fails SQLite lifecycle persistence

Command:

```text
roadmap issue restore 5898cb1f --force
```

Observed behavior included:

```text
Warning: Failed to update restoration status ...:
Failed to update Issue: no such column: archived_at
Restored 1 issue
```

The process exited with status 0. Physical restoration succeeded, but SQLite
update expected an `archived_at` column absent from the current projection
schema. This is a concrete canonical/projection contract mismatch.

### 4. Milestone creation claims project assignment without persisting it

After creating a project, milestone creation printed:

```text
Assigning milestone to project: Fixture Project (c83ed497)
Created milestone: v0-1-1
```

The resulting milestone contained `project_id: null`, the project contained
`milestones: []`, and `roadmap health --format json` classified the milestone as
orphaned. The user-visible success message and persisted planning relationship
disagree.

## Other characterized journeys

The following disposable journeys completed successfully:

- initialization;
- project creation and listing;
- milestone creation, listing, and detail display apart from the failed project
  relationship;
- issue creation, listing, viewing, dependency addition, milestone assignment,
  close, and physical archive/restore moves apart from the lifecycle persistence
  failures above;
- JSON export;
- JSON health summary; and
- JSON health-fix dry-run.

## Blocked Phase 0 deliverables

The sanitized tracked compatibility fixture and reusable expanded journey runner
were not added after the hard-stop defects appeared. A disposable fixture was
created only under `/private/tmp` to gather evidence. Checking a fixture into
the repository while its required creation journey is known to fail would blur
the distinction between characterized valid state and hand-repaired state.

## Recommended baseline remediation

Before Phase 1, authorize a bounded **Phase 0A — baseline lifecycle repair**:

1. fix issue comment persistence and nonzero failure propagation;
2. make archive/restore update canonical lifecycle metadata and the current
   SQLite schema consistently, or fail before moving the file;
3. persist the milestone-to-project relationship atomically or stop claiming it
   was assigned;
4. add installed-CLI regression tests for all three journeys and their exit
   statuses;
5. create the sanitized compatibility fixture and safe checkpoint runner from
   the now-valid journeys; and
6. rerun every Phase 0 static, full-suite, artifact, CLOC, and application gate.

Phase 1 begins only after that rerun is green and the maintainer explicitly
continues.
