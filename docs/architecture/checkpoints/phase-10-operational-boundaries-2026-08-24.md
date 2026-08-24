# Phase 10 checkpoint — Reporting, health, recovery, and local Git

- Date: 2026-08-24
- Baseline commit: `ba86b2f5472e536561a7616ae3287146466d7a9b`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 11

## Decision

Phase 10 is complete. Retained reporting, workspace diagnosis, bounded
recovery, backup retention, and local Git behavior now cross explicit
Application-owned contracts. Canonical documents remain authoritative; SQLite
is only a rebuildable projection; and no retained Git path performs network,
remote, credential, provider, or automatic-hook operations.

The old exporter, overlapping status/health implementations, heuristic repair
stack, cleanup presenter, infrastructure validators, Git authentication/setup
handlers, connectivity handlers, hook configuration, and their
implementation-coupled tests were deleted instead of carried as parallel
paths.

## Reporting and output contract

`roadmap data export` reads canonical issue records through Application,
orders them by stable ID, and emits schema-version-one JSON, CSV, or Markdown.
JSON preserves complete canonical issue meaning, including Unicode, explicit
nulls, comments, history, relations, lifecycle, and ordinary local branch
references, while excluding paths, caches, credentials, and provider
projection internals. Empty exports remain valid and versioned.

Status and critical-path structured output are deterministic and versioned.
Every file output uses exclusive creation and refuses to overwrite an existing
target. Successful machine payloads use stdout alone; logging, diagnostics,
and file confirmations use stderr. Ordinary failures are nonzero without a
traceback or partial machine payload.

## Diagnosis and recovery contract

Health detection is non-mutating. It diagnoses invalid or unreadable canonical
documents, unresolved Git conflict markers, duplicate IDs, noncanonical paths,
broken typed relationships, missing/stale/corrupt/outdated projection state,
and interrupted canonical transactions. Findings have stable IDs, severities,
scopes, messages, and safe-action metadata in the versioned health schema.

Repair accepts only projection rebuild, interrupted-transaction recovery, or
the combined data-integrity operation. Every action is previewable, confirmed
before application, and followed by a fresh health scan. Repair never writes
from SQLite into canonical files. Legacy heuristic fix names return explicit
guidance to inspect and edit canonical data rather than guessing.

`roadmap cleanup` is now separate retention maintenance. It enumerates only
exact `*.backup.md` candidates, applies deterministic keep/age rules, previews
the exact paths, requires confirmation unless forced, and reports partial
filesystem failures. Its legacy check flags are read-only views over stable
health findings.

## Local Git and identity contract

Application owns the local Git port. The subprocess adapter uses fixed argument
arrays, an explicit repository path, no shell, a bounded timeout, disabled
terminal prompts, and stable error translation. It inspects only the local
branch, HEAD, and dirty paths; creates safe local issue branches; and persists
explicit branch references through the canonical issue mutation path.

The retained `roadmap git` commands are `status`, `branch`, and `link`.
Roadmap-owned authentication, connectivity checks, setup, sync, and automatic
hook commands are absent from that command group. Descriptive current-user
identity is resolved once from typed user configuration or local `Git
user.name`; it is not authentication or authorization.

Authentication remains a conditional road-to-1.0 decision gate, not planned
scope. A future proposal requires a concrete hosted or multi-user trust
boundary, threat model, credential and recovery ownership, offline semantics,
data migration, requirements, and a separate ADR.

## Focused verification

The final affected-surface run passed **120 tests** covering architecture and
public-inventory policy, CLI stdout/stderr policy, canonical exports, status,
health diagnosis and repair, permission denial, interrupted and repeated
recovery, backup retention, local Git subprocess safety, branch/link
persistence, and daily identity resolution.

The complete pytest suite was deliberately not run, following the maintainer's
explicit instruction. No skipped full-suite result is presented as checkpoint
evidence.

## Installed artifact and journeys

The final wheel was built from the final production tree, installed without
`PYTHONPATH` into a clean Python 3.14.2 environment, and passed import,
metadata/version, help, initialization, issue creation, and issue listing.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `aacbaff5c15dd204b1f7e254a0347055feb862d32df97da980e8f142c8d0e51c` | Passed. |

The cumulative installed journey passed against the wheel. In addition to the
retained issue, planning, lifecycle, manual-edit, and migration paths, it
verified versioned canonical export, non-mutating health preview, confirmed
projection rebuild, clean post-check evidence, unchanged canonical digests,
local Git status, safe issue-branch creation, and canonical branch linking.

Two independent copies of the sanitized 0.1.1 fixture again produced the same
semantic snapshot after dry-run, migration, reopen, corruption recovery, and
idempotent rerun. Visible IDs remained `5898cb1f` and `951f146d`; archived issue
`a11ce001`, project `c83ed497`, milestone `v0-1-1`, and the sanitized comment
retained their meaning.

## Production CLOC

Fixed command and tool: CLOC 2.10 with Python-only input under `roadmap/` and
`__pycache__` excluded.

| Metric | Phase 9 | Phase 10 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 487 | 453 | -34 |
| Blank lines | 14,303 | 12,905 | -1,398 |
| Comment lines | 17,376 | 15,800 | -1,576 |
| Code lines | 52,330 | 47,998 | -4,332 (-8.28%) |

The CLOC ratchet passes. The Phase 11 ceiling becomes 47,998 production Python
code lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `uv lock --check` | Passed; 118 packages resolved. |
| Ruff lint and format | Passed; 1,174 files clean. |
| Pyright | Passed with 0 errors and 0 warnings. |
| Architecture policy | Passed with the reviewed Phase 11 exceptions and no new baseline entry. |
| Public compatibility inventory | Passed; removed CLI surfaces may disappear early while every retained surface remains mandatory. |
| Bandit high-severity gate | Passed; 0 high findings (63 low, 5 medium). |
| Radon/Xenon | Passed at absolute C, module C, average A. |
| `git diff --check` | Passed. |
| Production CLOC ratchet | Passed at 47,998 code lines. |

## Requirements traceability

This phase directly advances UR-007, UR-008, UR-010, UR-011, UR-021,
UR-040 through UR-043, and UR-047. It supplies implementation and verification
evidence for TR-004, TR-008, TR-013, TR-017, TR-028, TR-032, and TR-033.
Requirement lifecycle status remains an explicit maintainer decision.

## Known risks and deferred work

- The top-level remote/provider synchronization subsystem, provider
  replication, credential storage, validation, metrics, configuration, and
  their runtime dependencies remain until the approved Phase 11 deletion.
- Some legacy local Git/hook implementations remain reachable only through the
  old sync/core graph. Phase 11 must classify and delete them without removing
  the new `roadmap.adapters.outbound.git` boundary.
- Legacy ownership-zone packages and the compatibility facade remain until
  Phase 12. Bootstrap remains the intended permanent composition root.
- The placeholder hidden `data generate-report` path remains scheduled for
  final command-tree removal in Phase 11; the supported replacement is
  `roadmap data export` plus versioned status/analysis output.

## Recommendation

**GO for Phase 11 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin remote/provider synchronization
deletion automatically.
