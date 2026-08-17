# Phase 4 checkpoint — Domain and Application contracts

- Date: 2026-08-17
- Baseline commit: `cb8e62e0c88f248f863b764dfd228220ccc173df`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 5

## Decision

Phase 4 establishes the framework-free business kernel and narrow Application
contracts that later persistence and command slices will use. Issue, milestone,
and project identity no longer depends on names, paths, providers, or workflow;
workflow and retention are separate explicit state machines; relationships use
typed complete IDs; time enters through an Application clock; and the inward
packages contain no framework or boundary imports.

The complete checkpoint is green. No CLI route, canonical document, SQLite
schema, configuration, provider behavior, or local projection behavior changed.
Phase 5 may begin only after explicit maintainer approval.

## Implemented target contracts

- `roadmap.domain.types` defines opaque stable IDs, validated title/name values,
  timezone-aware timestamps, priority and workflow enums, retention state, and
  typed issue/milestone/project relationships.
- `roadmap.domain.aggregates` defines immutable Issue, Milestone, and Project
  aggregates with single-aggregate invariants and identity-preserving rename,
  reassignment, workflow, archive, and restore behavior.
- `roadmap.domain.transitions` is the explicit source of truth for every issue,
  milestone, project, and retention transition. Same-state requests are
  idempotent; absent edges are rejected with a typed Domain failure.
- `roadmap.application` defines immutable request/response data, stable failure
  categories, a clock, aggregate-specific load/save capabilities, unit of work,
  projection maintenance, and read-only local Git inspection.
- The complete CAN-001 through CAN-072 mapping records which values enter the
  Domain now, remain losslessly in the canonical document envelope until their
  owning slice, are derived projection values, are adapter-only, or are removed.
  Unknown supported frontmatter remains a document-boundary concern and does
  not become an untyped Domain metadata bag.
- Existing IDs remain unchanged. New IDs are complete lowercase UUID4 values;
  milestone migration introduces a stable ID without turning its retained name
  into identity.

## Removed contract debt

The phase deleted unused, duplicate contracts that had no production caller:

- the three `roadmap.core.domain.ports` ABCs for issue repositories, remote
  backends, and remote baselines;
- duplicate generic repository, backend-factory, sync-service, and sync-state
  interfaces under `roadmap.core.interfaces`;
- three unused generic sync-validation protocols; and
- the filesystem-aware `roadmap.domain.validation` forwarding wrapper.

The legacy GitHub protocol was reduced from an unimplemented ABC hierarchy to
the same structural capability contract. The active remote/provider subsystem
was not removed in this phase, and the local canonical-file-to-SQLite pipeline
was not renamed or deleted. A lazy compatibility re-export plus deterministic
legacy-model initialization removes the accidental import-order dependency that
the deleted state-storage interface had been masking.

Four tests that only proved the deleted ABCs could not be instantiated were
removed. The remote-deduplication fake now implements the exact structural
capability its retained service consumes rather than inheriting an unused ABC.

## Focused evidence

The focused Phase 4 and compatibility run passed **157 tests**. It includes:

- all 63 ordered pairs across the four transition machines, with every allowed,
  idempotent, and rejected result checked;
- legacy-ID preservation and complete lowercase UUID4 generation;
- stable IDs through rename, reassignment, close, archive, and restore;
- timestamp, estimate, progress, self-link, and duplicate-link invariants;
- immutable Application request/response and failure contracts;
- static inward-import and all-72-field mapping policy;
- the exact architecture baseline, retained sync protocol, remote
  deduplication, and SQLite entity-coordinator compatibility tests.

The final focused rerun also passed all 78 targets implicated by an import-order
failure discovered during the first complete-suite attempt. The repair changed
only initialization order; it did not restore the deleted interface or add a
second implementation path.

## Exact architecture baseline

The architecture baseline shrank from eight reviewed exceptions to exactly
seven:

| Rule | Phase 3 | Phase 4 | Owner phase |
| --- | ---: | ---: | ---: |
| `application-dependencies` | 7 | 7 | 11 |
| `domain-dependencies` | 1 | 0 | — |

There are no baselined Domain violations, cycles, adapter-boundary violations,
Bootstrap-wiring violations, or active removed-namespace violations. All seven
remaining entries belong to the legacy remote-deduplication service scheduled
for removal with provider synchronization in Phase 11.

The project still declares 15 runtime dependencies. Remote/provider behavior
remains present by design; this phase pruned only unused contract declarations.
The historical filename-based sync inventory remains too broad to distinguish
that subsystem from the local projection pipeline and is not used as removal
evidence.

## Production CLOC

Fixed command and tool: `cloc` 2.10 with Python-only input under `roadmap/` and
`__pycache__` excluded.

| Metric | Phase 3 | Phase 4 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 505 | 505 | 0 |
| Blank lines | 15,980 | 15,880 | -100 |
| Comment lines | 20,185 | 19,853 | -332 |
| Code lines | 54,205 | 54,202 | -3 (-0.006%) |

The new inward contracts are offset by deleting unused duplicate abstractions,
not by excluding files from measurement. The CLOC ratchet passes, and the Phase
5 ceiling becomes 54,202 production Python code lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed. |
| `uv lock --check` | Passed; 115 packages resolved. |
| Ruff format | Passed; 1,082 production/test files already formatted. |
| Ruff lint | Passed. |
| Architecture policy | Passed; current tree exactly matches 7 reviewed entries and all 72 fields are mapped. |
| Pyright | Passed with 0 errors, 0 warnings, and 188 informational findings. |
| Bandit high-severity gate | Passed; 0 high findings (66 low, 5 medium). |
| Complete pytest suite | Passed; 8,393 tests in 100.09 seconds. |
| Coverage | Passed; 82.10% against the configured 81% minimum. |

There were no failures, skips, or expected failures in the accepted run. The
77-test net increase is 81 new Phase 4 tests minus four obsolete ABC tests. The
suite emitted 1,934 warnings, still dominated by nondeterministically collected
unclosed SQLite connection `ResourceWarning` instances; this known debt remains
visible and is not exempted.

## Distribution boundary

Both artifacts were built from the final tree, installed without `PYTHONPATH`,
and passed isolated import, help, version, initialization, issue creation, and
issue listing on Python 3.14.2.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `781a4a5c03ff103486fdea2883af744b732e5207aefe2285f4df1fb56b7b85d9` | Passed |
| `roadmap_cli-0.1.1.tar.gz` | `4c3170257a50e8f9b0bb5ba0d28f2fdd78953054b4fb5229d7340c408c682176` | Passed |

## Installed application journeys

The cumulative journey ran against the final wheel in a disposable isolated
environment and passed:

1. help and version;
2. initialization and safe reopen;
3. project and milestone creation with a persisted relation;
4. issue create, view, comment, close, archive dry-run, archive, and restore;
5. supported JSON parsing;
6. manual canonical-document edit observation;
7. SQLite deletion and rebuild with unchanged canonical digests;
8. JSON health diagnosis and non-mutating repair preview;
9. offline local Git initialization and status; and
10. two deterministic 0.1.1 compatibility-fixture loads and projection rebuilds.

The compatibility snapshot retained visible issue IDs `5898cb1f` and
`951f146d`, the archived and legacy closed issues, the project and milestone
relations, and the sanitized fixture comment.

## Requirements traceability

This phase directly advances TR-003 (enforced boundaries), TR-005
(framework-independent business kernel), TR-020 (stable identity and typed
relationships), TR-021 (separate transition machines), TR-028 (one-way
projection capability), and TR-031 (ordinary external references stay distinct
from identity/provider synchronization). It creates seams needed by TR-002,
TR-007, and TR-008 but does not claim persistence or route migration complete.
No requirement lifecycle status changed.

## Compatibility and rollback

Phase 4 is additive at the target inward boundary and subtractive only for
unused internal interfaces. Existing command routes continue through the 0.1.1
models. No workspace, canonical field, directory, SQLite schema, configuration,
Git state, or public command changed. The installed 0.1.1 fixture and projection
rebuild demonstrate data compatibility.

Rollback is an ordinary source-control revert. No data migration or recovery
operation is required.

## Known risks and deferred work

- Target contracts are not yet wired to persistence or CLI routes. Phase 5 owns
  document mappings, atomic canonical writes, and disposable SQLite projection
  maintenance.
- Known journey-specific history, comment, planning-date, effort, and ordinary
  external-reference fields remain losslessly owned by the canonical document
  envelope until Phases 7 and 8 give them behavior-specific types.
- Cross-aggregate existence, cycle, and workspace-uniqueness checks belong to
  Application use cases and are deliberately not faked inside one aggregate.
- The broad legacy `RoadmapCore`, provider synchronization subsystem, and seven
  Application violations remain. Phase 11 removes provider synchronization;
  Phase 12 dissolves the remaining legacy ownership zones.
- SQLite connection warnings remain technical debt.
- The supported-platform CI matrix awaits a maintainer-authorized commit and
  push.

## Recommendation

**GO for Phase 5 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin persistence automatically.
