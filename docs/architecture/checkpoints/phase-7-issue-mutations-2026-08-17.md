# Phase 7 checkpoint — Issue mutations and relationships

- Date: 2026-08-17
- Baseline commit: `20d9265a1f2fc1a637ae4661616c0c0ec2d28bef`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 8

## Decision

Phase 7 moves retained issue creation, editing, workflow transitions, progress,
comments, dependencies, retention, and purge behavior behind one
Application-owned mutation service and a canonical unit of work. Bootstrap
wires the use case; Click commands resolve user input and translate typed
failures without owning business or persistence rules.

The complete checkpoint is green. No Phase 8 project, milestone, or planning
view migration has begun.

## Mutation and transaction contract

`IssueMutations` owns create, update, start, progress, transition, close,
comment, dependency, archive, restore, and purge operations. Domain owns
single-issue invariants and lifecycle events. Application owns cross-issue
existence, reciprocal dependency updates, self-link and cycle rejection,
assignee validation, retention prerequisites, inbound-reference protection,
and idempotency.

`CanonicalIssueUnitOfWork` stages complete write sets, commits canonical
documents before refreshing SQLite, journals multi-document changes, rolls
back interrupted commits, and performs recovery on entry. Invalid operations
leave both canonical documents and the projection unchanged.

Archive and restore now change lifecycle metadata at a stable canonical path;
they do not move files. Purge requires an archived issue, explicit CLI
confirmation, and no inbound dependency references.

## Relationships, history, and compatibility

Comments and lifecycle events now round-trip stable IDs, authors, targets,
timestamps, ordering, and reply relationships. Legacy naïve timestamps are
normalized at the canonical adapter boundary, and malformed relationship
collections fail explicitly rather than silently corrupting an aggregate.

Dependency mutations update both sides in one transaction and reject missing
targets, self-links, duplicates, and cycles. Existing 0.1.1 UUID document names
remain addressable until the Phase 9 path migration. Canonical data remains the
authority when SQLite is absent, stale, or rebuilt.

All retained `roadmap issue` mutation commands now use the target Application
path. The old issue archive/restore classes, status helpers, start service,
update service, unused CLI parameter records, and their implementation-specific
tests are removed. The narrow issue-to-Git branch bridge remains deliberately
until Phase 10 moves local Git awareness behind its final port.

## Focused evidence

- 41 focused Application mutation and canonical persistence tests pass.
- 11 focused `IssueMutations` tests cover transactional lifecycle,
  relationships, invalid operations, and recovery behavior.
- Retained create, workflow, archive/restore, comment, prefix-resolution,
  milestone-assignment interoperability, Git-branch, and auto-assignee slices
  pass.
- Archive integration verifies metadata-only retention and stable canonical
  paths.
- The installed lifecycle journey and two deterministic 0.1.1 compatibility
  fixture inspections pass.

## Exact architecture baseline

The architecture checker and its 20 policy tests pass with exactly the seven
previously reviewed `application-dependencies` exceptions. There are no Domain,
cycle, adapter-boundary, Bootstrap-wiring, or active removed-namespace
violations. Phase 7 adds no baseline exception.

## Production CLOC

Fixed command and tool: `cloc` 2.10 with Python-only input under `roadmap/` and
`__pycache__` excluded.

| Metric | Phase 6 | Phase 7 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 507 | 504 | -3 |
| Blank lines | 15,678 | 15,477 | -201 |
| Comment lines | 19,503 | 19,128 | -375 |
| Code lines | 54,169 | 54,155 | -14 (-0.026%) |

The new mutation contracts, domain behavior, unit of work, adapters, and CLI
translation are offset by deleting superseded issue implementations. The CLOC
ratchet passes, and the Phase 8 ceiling becomes 54,155 production Python code
lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed. |
| `uv lock --check` | Passed; 118 packages resolved. |
| Ruff format | Passed; 1,265 files already formatted. |
| Ruff lint | Passed. |
| Architecture policy | Passed; 20 tests and the standalone checker are green. |
| Pyright | Passed with 0 errors, 0 warnings, and 180 informational findings. |
| Bandit high-severity gate | Passed; 0 high findings (66 low, 5 medium). |
| Repository complexity ratchet | Passed at absolute C, module C, average A; Radon reports 3,783 blocks at average A (3.2831). |
| Complete strict-warning pytest suite | Passed; 8,182 tests in 148.08 seconds. |
| CI-equivalent coverage run | Passed; 8,182 tests in 120.69 seconds and 81.89% coverage against the configured 81% minimum. |

There were no failures, skips, or expected failures in either accepted full
run. The suite is 145 tests smaller than Phase 6 because the phase deletes
large mock-heavy suites for superseded CLI helpers and services, while retaining
public integration journeys and adding tests at the Domain, Application,
canonical persistence, recovery, and CLI-resolution boundaries.

## Distribution boundary

The wheel and source distribution were built from the Phase 7 production tree.
The wheel was installed without `PYTHONPATH` and passed isolated import, help,
version, initialization, issue creation, and issue listing on Python 3.14.2.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `ff7cfc10cdac6f267c7f8052b4545e0c29a9ad1f7dd84d3b54f4a7f4f196d893` | Passed. |
| `roadmap_cli-0.1.1.tar.gz` | `6513afa69834180142392f1499352e7d0a2d35257540e154181e31e48d3585fc` | Passed. |

## Installed application journeys

The cumulative journey passed against the isolated final wheel. It covered
help/version, initialization, project and milestone creation, issue create and
view, comment, close, archive preview, metadata-only archive and restore, JSON
parsing, a manual canonical edit, SQLite deletion and rebuild with unchanged
canonical digests, health diagnosis and repair preview, and local Git status.

Two deterministic 0.1.1 fixture loads retained visible issue IDs `5898cb1f`
and `951f146d`, the archived and legacy closed issues, project and milestone
relations, and the sanitized fixture comment.

## Requirements traceability

This phase directly advances UR-017, UR-019, UR-020, UR-022, UR-028, and UR-038.
It supplies implementation and verification evidence for TR-002 (canonical
authority), TR-003 (enforced boundaries), TR-004 (stable CLI), TR-005 (atomic
writes), TR-020 (stable identity), TR-021 (separate workflow and retention),
TR-023 (durable comments/history), and TR-031 (ordinary external references).
Requirement lifecycle status remains an explicit maintainer decision.

## Compatibility and rollback

This phase performs no workspace schema migration or physical archive move.
Source rollback is an ordinary source-control revert. SQLite remains disposable
and rebuildable without changing canonical documents. Multi-document writes
have journaled rollback and recovery, and invalid mutations are non-destructive.

The retained CLI command paths and options remain compatible with the Phase 1
inventory. Incidental human-readable success prose may differ as permitted;
structured output and stable entity IDs remain the supported automation
boundary.

## Known risks and deferred work

- Project and milestone mutations, assignment, progress reconciliation, and
  planning views still use retained services; Phase 8 owns their migration.
- The legacy issue service remains reachable only from planning and remote-sync
  paths owned by Phases 8 and 11; retained issue CLI mutations no longer call
  it.
- The temporary issue-to-Git branch bridge remains until Phase 10.
- Flat complete-ID canonical paths and final schema migration remain Phase 9
  work.
- Provider synchronization and seven reviewed Application dependency
  exceptions remain until Phase 11.
- Legacy ownership-zone packages remain until Phase 12.

## Recommendation

**GO for Phase 8 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin project, milestone, or planning-view
migration automatically.
