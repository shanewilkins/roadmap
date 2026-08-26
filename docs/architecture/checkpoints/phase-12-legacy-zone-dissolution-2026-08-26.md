# Phase 12 checkpoint — Legacy-zone dissolution and dependency pruning

- Date: 2026-08-26
- Phase 11 accepted commit: `5cb58e1c`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 13

## Decision

Phase 12 is complete. The production package now has one ownership model:
Domain, Application, inbound Adapters, outbound Adapters, and Bootstrap. The
legacy `core`, `common`, `infrastructure`, `presentation`, old adapter, and
application-service zones are physically absent and forbidden by executable
architecture policy. The architecture baseline remains empty.

Bootstrap is the permanent composition root. The temporary facade was replaced
by a narrow `WorkspaceServices` capability bundle; Bootstrap constructs target
use cases and adapters directly. Inbound adapters depend only on Application
and Domain. Outbound adapters depend on Application ports and Domain rather
than on sibling adapters. Package version information is injected into the CLI
by Bootstrap.

No-op command instrumentation, ambient logging/tracing initialization,
duplicate presenters, error systems, validators, persistence stacks, service
locators, compatibility imports, generated documentation, and empty package
scaffolding were removed. Initialization is a target Application use case with
a filesystem adapter. The retained one-time 0.1.1 migration remains isolated
at its explicit boundary.

## Dependency boundary

Roadmap has exactly three direct runtime dependencies:

| Dependency | Owner | Purpose |
| --- | --- | --- |
| Click | inbound CLI adapter | Command parsing, dispatch, confirmation, and exit behavior. |
| Rich | inbound CLI adapter | Interactive terminal presentation. |
| PyYAML | outbound persistence and configuration CLI adapters | Versioned canonical/configuration YAML. |

Domain and Application import no third-party packages. SQLite remains a
standard-library, rebuildable outbound projection. The complete justification
is recorded in [Runtime dependency boundaries](../dependency-boundaries.md).
The lock resolves 52 packages, down from Phase 11's 104.

## Behavior repairs found by the checkpoint

The focused checkpoint exposed and repaired three concrete integration defects:

- `ApplicationFailure` could not accept Python's traceback assignment because
  the exception dataclass was frozen;
- a projection-repair test did not actually establish stale projection state;
  the fixture now creates the correct `projection.db.stale` marker; and
- explicit local branch creation rejected a dirty worktree without exposing
  its supported force path; `roadmap git branch --force` now makes that risk
  decision visible.

The installed cumulative journey now explicitly sets its user identity before
running the identity-scoped daily view. This proves the documented
configuration boundary instead of relying on the developer machine's Git
configuration.

## Focused verification

The retained Phase 12 suite passed **335 tests** across target Application and
Domain contracts, outbound adapters, CLI journeys, archive/restore behavior,
and executable policy. The complete pytest suite was deliberately not run,
following the maintainer's explicit instruction.

The cumulative installed-artifact journey passed from a fresh workspace and
twice from the tracked 0.1.1 compatibility fixture. It exercised initialization,
scoped identity configuration, project/milestone/issue workflows, comments,
lifecycle transitions, structured output, manual canonical edits, projection
preview/rebuild, health, local Git branch linking, migration dry-run and
execution, projection-corruption recovery, and idempotent migration reruns.
The compatibility snapshots retained visible IDs `5898cb1f` and `951f146d`,
archived issue `a11ce001`, project `c83ed497`, milestone `v0-1-1`, and the
sanitized comment semantics.

## Distribution boundary

The wheel contains 111 entries: only the five intended production ownership
areas plus distribution metadata. The source distribution contains only the
production package and declared release files. Neither artifact contains a
legacy ownership zone. Both artifacts installed without `PYTHONPATH` into clean
Python 3.14.2 environments and passed metadata/version, help, initialization,
issue creation, and issue listing smoke tests.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `475a7e5497040521109651653c83cb9608a41a4d5b51900012b58901cdd44c92` | Passed. |
| `roadmap_cli-0.1.1.tar.gz` | `ac7174c93e7d5655d4da168ef7adcce0ad1d3d7f39e54280faffd1de1521e78b` | Passed. |

## Production CLOC

Fixed command and tool: CLOC 2.10 with Python-only input under `roadmap/` and
`__pycache__` excluded.

| Metric | Phase 11 | Phase 12 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 307 | 106 | -201 |
| Blank lines | 7,010 | 1,532 | -5,478 |
| Comment lines | 8,660 | 1,043 | -7,617 |
| Code lines | 24,545 | 9,200 | -15,345 (-62.52%) |

The CLOC ratchet passes. The Phase 13 ceiling becomes 9,200 production Python
code lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `uv lock --check` | Passed; 52 packages resolved. |
| Ruff lint and format | Passed. |
| Pyright | Passed with 0 errors and 0 warnings. |
| Architecture and legacy-zone policies | Passed with 0 production violations and an empty baseline. |
| Bandit high-severity gate | Passed. |
| Radon/Xenon | Passed; average complexity A (3.47), absolute C, module C, average A. |
| Wheel/source artifact audit and smoke | Passed. |
| Cumulative fresh/migration journey | Passed from the installed wheel. |
| `git diff --check` | Passed. |
| Production CLOC ratchet | Passed at 9,200 code lines. |

## Requirements traceability

This phase supplies implementation and verification evidence for UR-001,
UR-005, UR-013, UR-016, UR-024, UR-032, UR-037, UR-045, and UR-048. It directly
advances TR-001 through TR-005, TR-009 through TR-013, TR-015 through TR-020,
TR-025, TR-029, TR-030, TR-033, and TR-035.

## Known risks and deferred work

- Phase 13 still owns failure injection, concurrency and corruption envelopes,
  test-quality audit, supported CI matrix, package metadata and release-doc
  consistency, before/after case-study evidence, and release/rollback planning.
- The CLI presentation layer remains the largest concentration of mechanical
  output code. Phase 13 may harden or simplify it only when retained behavior
  and measured evidence justify the change; no feature expansion is approved.
- The one-time 0.1.1 migration remains until the supported compatibility window
  is explicitly closed. It is not a general migration framework.
- Authentication remains a conditional post-0.2 decision gate, not a 0.2
  feature.

## Recommendation

**GO for Phase 13 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin release hardening automatically.
