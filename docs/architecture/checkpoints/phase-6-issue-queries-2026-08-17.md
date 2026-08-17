# Phase 6 checkpoint — Issue queries

- Date: 2026-08-17
- Baseline commit: `8fd39a0f2143a20f8045cae1b967367972b1f75f`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 7

## Decision

Phase 6 replaces the retained issue list, detail, and lookup read path with one
Application-owned query service. Bootstrap supplies a canonical document
adapter and an optional SQLite projection; the CLI translates user input and
renders results without placing Click, Rich, filesystem, or database types in
Domain or Application.

The complete checkpoint is green. Issue mutations deliberately remain on the
retained path until Phase 7, and no Phase 7 work has begun.

## Query contract and behavior

`IssueQueries` owns complete-ID lookup, detail retrieval, deterministic list
ordering, explicit lifecycle scope, milestone and backlog selection, assignee
selection, status, priority, type, blocked, overdue, and Unicode case-folded
search behavior. Invalid filter combinations and missing records leave the
Application boundary as typed failures. Overdue evaluation receives the
Application-owned `Clock` port from Bootstrap and is deterministic in tests.

The CLI resolves an exact ID first, otherwise accepts only one unambiguous
prefix and passes the complete `EntityId` inward. It exposes `--scope` for
visible, closed, archived, or all retained issues and `--search` for text
queries. Existing plain, Rich, JSON, CSV, Markdown, column-selection, sorting,
and presentation filters remain at the inbound/output boundary.

The Phase 1 compatibility inventory now records the actual retained list
contract. Provider-specific GitHub-ID columns and the duplicate issue-list
export shortcut are removed according to their approved Replace disposition;
file export remains available through `roadmap data export`.

## Canonical-first projection behavior

`DocumentIssueQueries` may ask a healthy SQLite projection for candidate IDs,
but it always loads the returned issues from canonical documents. Missing,
stale, corrupt, or incompatible projection state falls back to a correct
canonical scan. A canonical edit therefore wins immediately over stale indexed
values, while a malformed canonical issue fails explicitly instead of being
hidden by SQLite.

This is local canonical-file-to-SQLite query acceleration. It neither restores
nor expands remote/provider synchronization.

## Removed query debt

The phase deletes the superseded issue filter service and issue DTO presenter,
then removes their assertion-only and duplicate presenter tests. One legacy
filter helper remains because Phase 8 analysis commands still call it; it is no
longer on the `issue list` or `issue view` production path and will be handled
with that owning slice.

The removed test files contained 27 tests. Sixteen focused replacement tests
cover the new Application, persistence, and CLI-prefix boundaries, and one new
governance-consistency test protects checkpoint state. The repository-wide
total therefore falls by ten without losing the retained contract.

## Focused evidence

- 36 focused query, projection, prefix-resolution, and list-command tests pass.
- 25 retained issue integration tests pass after the cutover.
- Healthy, absent, corrupt, and stale projections produce canonical-equivalent
  results; canonical edits win projection disagreement.
- Tests cover empty next-milestone behavior, deterministic ordering, Unicode
  search, lifecycle scopes, malformed documents, invalid filter combinations,
  exact IDs, unique prefixes, ambiguous prefixes, and missing prefixes.
- Existing formatter and full-suite coverage exercise deterministic human and
  structured output, while the installed journey parses JSON from the new
  production path.

## Exact architecture baseline

The architecture checker passes with exactly the seven previously reviewed
`application-dependencies` exceptions. There are no Domain, cycle,
adapter-boundary, Bootstrap-wiring, or active removed-namespace violations.
Phase 6 adds no new baseline exception.

## Production CLOC

Fixed command and tool: `cloc` 2.10 with Python-only input under `roadmap/` and
`__pycache__` excluded.

| Metric | Phase 5 | Phase 6 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 506 | 507 | +1 |
| Blank lines | 15,759 | 15,678 | -81 |
| Comment lines | 19,656 | 19,503 | -153 |
| Code lines | 54,201 | 54,169 | -32 (-0.059%) |

The new query contracts, use case, canonical adapter, and presenter are offset
by removal of duplicate read paths. The CLOC ratchet passes, and the Phase 7
ceiling becomes 54,169 production Python code lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed. |
| `uv lock --check` | Passed; 118 packages resolved. |
| Ruff format | Passed; 1,082 production/test files already formatted. |
| Ruff lint | Passed. |
| Architecture policy | Passed; current tree exactly matches 7 reviewed entries. |
| Pyright | Passed with 0 errors, 0 warnings, and 183 informational findings. |
| Bandit high-severity gate | Passed; 0 high findings (66 low, 5 medium). |
| Repository complexity ratchet | Passed at absolute C, module C, average A; Radon reports 3,752 blocks at average A (3.2934). |
| Complete strict-warning pytest suite | Passed; 8,327 tests in 123.79 seconds. |
| Coverage | Passed; 82.24% against the configured 81% minimum. |
| SQLite/unraisable warning gate | Passed; zero warnings escaped as errors. |

There were no failures, skips, or expected failures in the accepted run. The
full-suite count is ten lower than Phase 5 because 27 superseded tests were
deleted, while 16 focused query tests and one governance test were added.

## Distribution boundary

The wheel and source distribution were built from the Phase 6 production tree,
installed without `PYTHONPATH`, and passed isolated import, help, version,
initialization, issue creation, and issue listing on Python 3.14.2.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `5f399d550d1cc38e46061011b918f3464cf7b582f55426293820c9f2c99b090c` | Passed. |
| `roadmap_cli-0.1.1.tar.gz` | `63b49553d037058d2634f68363c2e96c8b72d25cc20cee323727b159d7aa347d` | Passed. |

## Installed application journeys

The cumulative journey passed against the isolated final wheel. It covered
help/version, initialization, project and milestone creation, issue create and
view, comment, close, archive preview, archive and restore, JSON parsing, a
manual canonical edit, SQLite deletion and rebuild with unchanged canonical
digests, health diagnosis and repair preview, and local Git status.

Two deterministic 0.1.1 fixture loads retained visible issue IDs `5898cb1f`
and `951f146d`, the archived and legacy closed issues, project and milestone
relations, and the sanitized fixture comment.

## Requirements traceability

This phase directly advances UR-002 and satisfies the Phase 6 query slice of
UR-018. It supplies implementation and verification evidence for TR-002
(canonical authority), TR-003 (enforced boundaries), TR-004 (stable CLI),
TR-013 (structured output), and TR-020 (stable identity and prefix handling).
No requirement lifecycle status changes merely because this phase checkpoint
passes; verification remains an explicit maintainer decision.

## Compatibility and rollback

This phase is read-only and performs no canonical migration. Source rollback is
an ordinary source-control revert. SQLite remains disposable and may be deleted
or rebuilt without changing canonical documents. The installed released
fixture and canonical digests provide rollback and compatibility evidence.

The approved CLI changes are explicit in the compatibility inventory. No
unapproved command removal, exit-category change, or persisted-schema change is
introduced.

## Known risks and deferred work

- Issue mutations and relationships still use retained services; Phase 7 owns
  their migration onto the canonical unit of work.
- A malformed unrelated legacy document can make projection selection fall
  back to the slower canonical issue scan; Phase 9 owns final schema migration.
- The Phase 8 analysis commands still consume one legacy issue-filter helper.
- Final flat stable-ID paths remain Phase 9 work.
- Provider synchronization and seven reviewed Application dependency
  exceptions remain until Phase 11.
- The broad legacy `RoadmapCore` remains until migrated slices allow Phase 12
  to dissolve it safely.

## Recommendation

**GO for Phase 7 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin issue-mutation migration
automatically.
