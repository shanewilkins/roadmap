# Phase 8 checkpoint — Projects, milestones, and planning views

- Date: 2026-08-24
- Baseline commit: `88a052244a4cd19c2a735747ee7217c892733d37`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 9

## Decision

Phase 8 puts retained project and milestone lifecycle behavior, assignment,
derived progress, boards, daily planning, status, and critical-path analysis on
one Application-owned planning path over canonical Markdown. Bootstrap owns the
composition, inbound commands translate input and failures, and SQLite remains
a disposable projection rather than planning authority.

The accepted planning product now shares stable identities, relationships,
retention semantics, transaction behavior, and progress calculation with the
Phase 6 and 7 issue paths. No Phase 9 schema, configuration, or physical path
migration has begun.

## Planning and lifecycle contract

`Planning` owns project and milestone create, update, assign, close, archive,
restore, purge, lookup, progress, daily summary, and critical-path behavior.
Cross-aggregate project/milestone links are reciprocal and committed in one
canonical unit of work. Issue-to-milestone, milestone-to-project, and
project-to-milestone relations persist complete IDs while CLI views render
human-readable names.

Project and milestone progress is derived from current visible canonical
issues. Recalculation reports derived state and never persists a competing
progress authority. Archive and restore update retention metadata at stable
paths and never cascade silently to linked issues. Purge requires archived,
unreferenced state and removes reciprocal planning links atomically.

The daily summary and critical path use the injected clock. Critical-path
selection is deterministic, effort-aware, rejects cycles, and reports blocking
relationships. The orphaned-milestone health check now reads canonical
relationships with a narrow fallback for legacy isolated callers.

## Production paths removed

The phase deletes the generic CLI CRUD implementation, project and milestone
archive/restore classes, duplicate daily-summary, milestone-list, project-status,
and critical-path services, and their implementation-coupled test suites.
Retained public commands no longer fall back to those paths after cutover.

## Focused evidence

- Eight direct Application tests cover identity, reciprocal relations, derived
  progress, lifecycle, purge guards, injected time, critical-path cycles, and
  interrupted cross-aggregate commits.
- The final post-complexity-refactor planning/lifecycle slice passed 110 tests.
- Earlier focused migration slices passed 53, 31, and 37 tests while repairing
  stable-ID compatibility and the canonical orphan validator.
- Full pytest collection remained clean at 7,929 tests.

## Complete suite evidence

The complete CI-equivalent coverage run passed before the final
behavior-preserving complexity extraction: **7,929 passed** in 123.57 seconds
with **82% coverage**. The extraction split daily-summary selection and
retention batching into smaller private policy helpers; its 110 affected tests,
Ruff, Pyright, Radon, and Xenon checks all passed afterward.

At the maintainer's explicit instruction, the complete pytest suite was not run
a second time after that extraction. There were no failures, skips, or expected
failures in the accepted complete run.

## Exact architecture baseline

The standalone architecture checker passes with exactly the seven previously
reviewed `application-dependencies` exceptions. There are no Domain, cycle,
adapter-boundary, Bootstrap-wiring, or active removed-namespace violations.
Phase 8 adds no baseline exception.

## Production CLOC

Fixed command and tool: `cloc` 2.10 with Python-only input under `roadmap/` and
`__pycache__` excluded.

| Metric | Phase 7 | Phase 8 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 504 | 488 | -16 |
| Blank lines | 15,477 | 14,465 | -1,012 |
| Comment lines | 19,128 | 17,732 | -1,396 |
| Code lines | 54,155 | 52,338 | -1,817 (-3.35%) |

The CLOC ratchet passes. The Phase 9 ceiling becomes 52,338 production Python
code lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed. |
| `uv lock --check` | Passed; 118 packages resolved. |
| Ruff format and lint | Passed; 1,042 files formatted and lint-clean. |
| Architecture policy | Passed; standalone checker and policy tests green. |
| Pyright | Passed with 0 errors, 0 warnings, and 166 informational findings. |
| Bandit high-severity gate | Passed; 0 high findings (66 low, 5 medium). |
| Complexity ratchet | Passed at absolute C, module C, average A; the planning service has no D-ranked block and averages A (4.67). |
| Complete coverage run | Passed; 7,929 tests and 82% coverage, subject to the explicit no-rerun note above. |

## Distribution boundary

Both artifacts were built from the final Phase 8 production tree. Each was
installed without `PYTHONPATH` and passed isolated import, metadata/version,
help, initialization, issue creation, and issue listing on Python 3.14.2.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `e28a43950a05c744edfc88e82172b199ab01e95b9fef5053020504e235f5555c` | Passed. |
| `roadmap_cli-0.1.1.tar.gz` | `b3413694ba9607d05e6c87b4889be19084c0a1ec1cd9aa0aacbb5066faada1c8` | Passed. |

## Installed application journeys

The cumulative journey passed against the isolated final wheel. It covered
help/version, initialization, structured project lookup and update, milestone
creation/view/board/recalculation, issue assignment/view/comment/closure,
metadata-only archive/restore for all three aggregate types, derived daily and
status views, deterministic critical-path JSON, a manual canonical edit,
SQLite deletion and equivalent rebuild, health diagnosis and repair preview,
and local Git status.

Two deterministic 0.1.1 fixture loads retained visible issue IDs `5898cb1f`
and `951f146d`, the archived and legacy closed issues, project and milestone
visibility, the sanitized fixture comment, and unchanged canonical digests
across projection rebuilds.

## Requirements traceability

This phase directly advances UR-003 and UR-025 through UR-028. It supplies
implementation and verification evidence for TR-002, TR-003, TR-004, TR-005,
TR-008, TR-013, TR-020, TR-021, and TR-030. Requirement lifecycle status
remains an explicit maintainer decision.

## Compatibility and rollback

Existing names and unambiguous ID prefixes remain accepted at CLI boundaries;
complete IDs are stored internally. Human output continues to show useful
names, and supported JSON project columns retain the approved `id`, `name`,
`status`, `priority`, and `owner` schema.

This phase performs no workspace schema migration or physical archive move.
Source rollback is an ordinary source-control revert. SQLite can be removed and
rebuilt without changing canonical documents, and journaled multi-document
writes recover or roll back deterministically.

## Known risks and deferred work

- Existing 0.1.1 paths and unversioned workspace configuration remain until
  Phase 9 performs explicit migration and rollback work.
- Reporting, health repair, export, and the final local-Git boundary remain for
  Phase 10; the orphan validator changed only as needed for canonical planning.
- Remote synchronization code and seven reviewed Application dependency
  exceptions remain until Phase 11.
- Legacy ownership-zone packages and the compatibility facade remain until
  Phase 12; Bootstrap is still required composition infrastructure.

## Recommendation

**GO for Phase 9 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin configuration, schema, path, or
migration work automatically.
