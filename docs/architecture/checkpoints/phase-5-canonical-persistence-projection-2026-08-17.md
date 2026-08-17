# Phase 5 checkpoint — Canonical persistence and SQLite projection

- Date: 2026-08-17
- Baseline commit: `6d7046b8468fdaba0d22d25aa606b868843ebda5`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 6

## Decision

Phase 5 establishes the target persistence boundary: Markdown documents with
YAML frontmatter are authoritative, and SQLite is a disposable one-way
projection. The new outbound adapters implement lossless document mapping,
atomic and recoverable canonical writes, concurrent-edit detection, and
incremental or complete projection refresh. They do not make SQLite a second
source of truth and cannot write canonical documents from database state.

The complete checkpoint is green. Most importantly, the full suite now passes
with every `ResourceWarning` and Pytest unraisable-exception warning promoted to
an error. The previous flood of unclosed SQLite connection warnings is gone;
no warning filter or exemption was added.

Existing CLI routes still use the retained 0.1.1 persistence path. Phase 6 may
begin only after explicit maintainer approval.

## Canonical document boundary

- `roadmap.adapters.outbound.persistence.documents` maps issue, milestone, and
  project documents to the Phase 4 aggregates through a boundary-owned
  envelope.
- Supported unknown frontmatter and user-authored Markdown survive a semantic
  read/change/write round trip. Unicode, complete IDs, typed owned values, and
  deferred known fields remain intact.
- The retained 0.1.1 active and archive layouts are readable. Missing schema
  versions are legacy version zero; new writes declare schema version one.
  Invalid or future versions, malformed YAML, invalid required fields, and
  duplicate identities fail without mutation.
- Reads do not normalize or rewrite source files. Phase 9 still owns migration
  to the final flat, stable-ID path layout from ADR-0010.

## Atomic and recoverable writes

`CanonicalUnitOfWork` acquires one workspace advisory lock and records the
content digest observed for every document in its write set. A manual or Git
edit after the read is treated as an optimistic-concurrency conflict and is not
overwritten.

Before replacement, the adapter durably journals complete before/after state
under `.roadmap/db/transactions`. Each document is written to a same-filesystem
temporary file, flushed, atomically replaced, and followed by a directory
flush. An ordinary failure restores a complete old state. A simulated process
death leaves durable intent, and the next locked unit of work rolls the complete
new state forward. Recovery paths are resolved and constrained to the workspace,
including through symlinks.

Canonical commit occurs before projection refresh. If projection maintenance
fails, canonical success remains committed and the projection is marked stale
for later rebuild.

## Disposable SQLite projection

`roadmap.adapters.outbound.persistence.projection` implements projection schema
version one and has no canonical-document write operation. Missing, corrupt,
truncated, incompatible, or explicitly stale state rebuilds from canonical
documents into a temporary database that is then replaced. Manual document
edits and deletions are detected by digests and can be refreshed incrementally.

Contract tests compare canonical bytes before and after rebuild, including the
released 0.1.1 compatibility fixture. Repeated rebuilds produce equivalent
query state without changing the documents from which they were derived.

## SQLite lifetime repair

The retained database manager now owns every SQLite connection it creates,
including worker-thread connections. Explicit `close()` closes the complete
registry and is idempotent; a weak finalizer closes the same registry when an
embedding host abandons the manager, including through reference cycles. A
connection that fails during PRAGMA/configuration is closed before the error
escapes.

Direct retained SQLite call sites now use closing scopes. A test fixture that
owned a real SQLite connection was also corrected. The strict full-suite gate
proves there are zero unclosed SQLite connection warnings.

## Removed persistence debt

The phase deleted four unused production experiments with no production
callers: the duplicate persistence facade, focused-manager wrappers, a second
conflict resolver, and the old file-locking module. Their assertion-only tests
were deleted with them. Dead parser helper chains and unused persistence package
re-exports were also removed.

The active local canonical-file-to-SQLite refresh and `StateManager` remain.
Remote/provider synchronization remains present until Phase 11; this phase does
not confuse its future removal with removal of the useful local projection.

## Contract and failure evidence

The Phase 5 contract suite covers:

- unknown-field, body, Unicode, legacy-version, and released-fixture round trips;
- invalid and future versions, malformed documents, and duplicate identities;
- optimistic concurrency and bounded concurrent-writer lock failure;
- failures before validation, after journaling, and during replacement;
- process-death recovery to a complete new state and ordinary rollback to a
  complete old state;
- path and symlink escape refusal;
- missing, corrupt, truncated, incompatible, stale, manually edited, and
  partially refreshed projection state; and
- canonical-first behavior when projection refresh itself fails.

## Exact architecture baseline

The architecture checker passes with exactly the seven previously reviewed
`application-dependencies` exceptions. There are still no Domain violations,
cycles, adapter-boundary violations, Bootstrap-wiring violations, or active
removed-namespace violations. Phase 5 adds its target implementation only under
the enforced outbound adapter zone.

## Production CLOC

Fixed command and tool: `cloc` 2.10 with Python-only input under `roadmap/` and
`__pycache__` excluded.

| Metric | Phase 4 | Phase 5 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 505 | 506 | +1 |
| Blank lines | 15,880 | 15,759 | -121 |
| Comment lines | 19,853 | 19,656 | -197 |
| Code lines | 54,202 | 54,201 | -1 (-0.002%) |

The target persistence implementation and its connection-lifetime repairs are
offset by deleting dead alternatives. The CLOC ratchet passes, and the Phase 6
ceiling becomes 54,201 production Python code lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed. |
| `uv lock --check` | Passed; 115 packages resolved. |
| Ruff format | Passed; 1,080 production/test files already formatted. |
| Ruff lint | Passed. |
| Architecture policy | Passed; current tree exactly matches 7 reviewed entries. |
| Pyright | Passed with 0 errors, 0 warnings, and 183 informational findings. |
| Bandit high-severity gate | Passed; 0 high findings (66 low, 5 medium). |
| Repository complexity ratchet | Passed at absolute C, module C, average A; Radon reports 3,745 blocks at average A (3.292). |
| Phase 5 complexity gate | Passed at the stricter absolute B, module B, average A. |
| Complete strict-warning pytest suite | Passed; 8,337 tests in 103.24 seconds. |
| Coverage | Passed; 82.07% against the configured 81% minimum. |
| SQLite/unraisable warning gate | Passed; zero warnings escaped as errors. |

There were no failures, skips, or expected failures in the accepted run. The
global legacy codebase does not yet meet an absolute-B Xenon ceiling. The locked
pre-commit and CI ratchet therefore rejects D-grade blocks or modules and an
average worse than A, while the Phase 5 gate applies the stricter ceiling to the
new outbound persistence boundary and repaired database manager. Broader legacy
complexity is reduced slice by slice in its owning phases rather than
represented as newly clean.

## Distribution boundary

Both artifacts were built from the Phase 5 tree, installed without
`PYTHONPATH`, and passed isolated import, help, version, initialization, issue
creation, and issue listing on Python 3.14.2.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `761e14d119714a5e4d06d4c6e4fdf50ac9149baaa5b4aa9507a4753f7290539f` | Passed. |
| `roadmap_cli-0.1.1.tar.gz` | `d6af006ae3da74ca6d310b36734dc9a00fb15e41dd5f070ac97175e37fee3e7f` | Passed. |

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

This phase directly advances TR-002 (canonical documents as authority), TR-007
(repository boundary), TR-008 (atomic and recoverable mutation), TR-029
(rebuildable projections), TR-034 (recovery integrity), and TR-035 (versioned
canonical compatibility). It also supplies evidence for UR-005, UR-011,
UR-037, and UR-045. No requirement lifecycle status changed.

TR-012's evidence path now names the target canonical adapter rather than the
deleted file-locking experiment. The register policy now validates ISO dates
and rejects future timestamps without requiring unrelated requirements to share
one hard-coded update date.

## Compatibility and rollback

The target boundary is additive and not yet wired to public commands. Existing
commands and workspaces continue through the retained 0.1.1 path, as confirmed
by both built-artifact smoke tests and the cumulative installed journey. The
new adapter reads the released fixture without changing its canonical bytes.

Source rollback is an ordinary source-control revert. Target-adapter journals
and projections are local derived state; incomplete journal state is recovered
under the workspace lock, and a projection can always be deleted and rebuilt
from canonical documents.

## Known risks and deferred work

- Target persistence is not yet the command query path. Phase 6 owns issue
  query use cases and route migration onto the new ports.
- The final flat stable-ID storage migration remains Phase 9 work.
- Cross-platform locking and crash guarantees still require the supported OS CI
  matrix in Phase 13; the current lock implementation has contract tests on the
  development platform.
- Provider synchronization, remote baselines, and seven Application dependency
  exceptions remain until Phase 11.
- The broad legacy `RoadmapCore` composition root remains until its slices are
  migrated and Phase 12 can dissolve it safely.

## Recommendation

**GO for Phase 6 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin issue-query migration automatically.
