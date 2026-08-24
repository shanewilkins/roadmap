# Phase 11 checkpoint — Remote/provider synchronization removal

- Date: 2026-08-24
- Baseline commit: `f19cb25662ba8d7d5ae16580c39f2378cee85814`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 12

## Decision

Phase 11 is complete. Roadmap no longer implements a second distributed-state
protocol. Provider replication, remote reconciliation, synchronization
baselines and checkpoints, automatic Git hooks, provider credentials and
configuration, sync metrics, retry machinery, remote linkage storage, generic
sync backends, and their implementation-coupled tests are deleted.

Canonical Markdown and YAML remain the durable state. The canonical-to-SQLite
refresh/rebuild pipeline and bounded local Git inspection remain supported.
Manual or Git-authored canonical changes are detected by projection maintenance;
Roadmap performs no provider request, hidden fetch, pull, merge, rebase, push,
or remote authentication.

## Removed product surface

The root `roadmap sync` and `roadmap validate-links` commands are absent. The
`roadmap git` group contains only `status`, `branch`, and `link`; initialization
has no provider, token, repository, or backend options; and the issue group has
no provider link, lookup, unlink, or sync-status commands. Removed invocations
return Click's standard exit-2 `No such command` response without a lazy command
registration warning.

The old GitHub/provider adapters, generic sync backend and factory, baseline and
three-way merge engines, remote state repositories, Git hook automation,
credential/keyring boundary, provider validation, metrics, retries, templates,
gateways, and remote-deduplication service were deleted. Obsolete tests were
deleted with them; retained tests were rewritten around local assignment,
generic external references, local conflict inspection, and local
configuration.

Direct runtime dependencies on `asyncclick`, `dynaconf`, `keyring`, `requests`,
`tabulate`, and `urllib3` were removed. `requests` and `urllib3` may still appear
transitively beneath the retained OpenTelemetry exporter; no Roadmap provider
feature imports or owns them.

## Persistence and migration contract

The disposable SQLite projection remains. The unchanged Phase 5 tests prove
rebuild, stale-state detection, and incremental refresh after a manual
canonical-file edit without changing canonical bytes.

Opening a legacy local state database drops only the obsolete provider-protocol
tables: `issue_remote_links`, `sync_metrics`, `sync_base_state`,
`sync_metadata`, and `file_sync_state`. These tables were derived state, not
canonical user data. The bounded 0.1.1 migration preserves supported entities,
stable IDs, relationships, timestamps, user-authored bodies, and ordinary
external URLs; it does not migrate credentials, transport policy, provider
baselines, or reconciliation state.

The removal and migration instructions are documented in
`docs/user_guide/REMOTE_SYNC_REMOVAL_0_2.md`. Current Markdown and Sphinx user
guides no longer instruct users to configure provider tokens or invoke deleted
sync commands.

## Focused verification

Two disjoint focused runs passed **399 tests**. The 194-test Phase 11 core set
covered absence policy, architecture and Bootstrap policy, unchanged Phase 5
canonical persistence and projection behavior, issue-query projection
behavior, local assignment filters, local configuration, local Git-conflict
inspection, provider-neutral domain parsing/serialization, and retained
merge/archive behavior. A further 205-test residue audit covered the retained
generic validator and local Git branch-manager suites after obsolete
provider-number validation and mock support were removed.

The complete pytest suite was deliberately not run, following the maintainer's
explicit instruction. No skipped full-suite result or coverage number is
presented as checkpoint evidence.

The cumulative journey passed in a disposable workspace. It exercised help and
version, initialization, project/milestone/issue creation and mutation,
lifecycle transitions, structured export, projection preview and confirmed
rebuild, clean health output, local Git status/branch/link, and deterministic
0.1.1 dry-run/migration/reopen/rebuild/idempotency. Two fixture copies retained
visible IDs `5898cb1f` and `951f146d`, archived issue `a11ce001`, project
`c83ed497`, milestone `v0-1-1`, and the sanitized comment semantics.

## Distribution boundary

Wheel and source distribution were built from the Phase 11 tree. Each was
installed without `PYTHONPATH` into a clean Python 3.14.2 environment and passed
metadata/version, help, initialization, issue creation, and issue listing.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `04299db751e00f61fb550cd9363093c8686fb842bcbc50ceac0c8d1ee4c803a4` | Passed. |
| `roadmap_cli-0.1.1.tar.gz` | `a1e176709b1643e95705a368281139ba6520d9cc85c79f55db3dbb8f06b3d28c` | Passed. |

## Production CLOC

Fixed command and tool: CLOC 2.10 with Python-only input under `roadmap/` and
`__pycache__` excluded.

| Metric | Phase 10 | Phase 11 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 453 | 307 | -146 |
| Blank lines | 12,905 | 7,010 | -5,895 |
| Comment lines | 15,800 | 8,660 | -7,140 |
| Code lines | 47,998 | 24,545 | -23,453 (-48.86%) |

The CLOC ratchet passes. The Phase 12 ceiling becomes 24,545 production Python
code lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `uv lock --check` | Passed; 104 packages resolved. |
| Ruff lint and format | Passed; 646 Python files clean. |
| Pyright | Passed with 0 errors and 0 warnings. |
| Architecture policy | Passed with 0 production violations and an empty baseline. |
| Phase 11 absence policy | Passed across source namespaces, CLI, configuration, schema, and direct dependencies. |
| Bandit high-severity gate | Passed. |
| Radon/Xenon | Passed; average complexity A (2.99), absolute C, module C, average A. |
| `git diff --check` | Passed. |
| Production CLOC ratchet | Passed at 24,545 code lines. |

## Requirements traceability

This phase supplies implementation and verification evidence for UR-005,
UR-007, UR-009, UR-029, UR-033 through UR-037, UR-039, UR-045, and UR-046. It
directly advances TR-002, TR-006, TR-009, TR-028, TR-029, TR-031, and TR-035.
Requirement lifecycle status remains an explicit maintainer decision.

## Known risks and deferred work

- Legacy ownership-zone packages and compatibility imports remain. Phase 12
  classifies them under Domain, Application, inbound/outbound Adapters, or
  Bootstrap, then deletes duplicate ownership and empty scaffolding.
- Bootstrap remains the intended permanent composition root, while the legacy
  coordination facade remains temporary migration scaffolding for Phase 12.
- The retained OpenTelemetry exporter brings transitive HTTP libraries even
  though Roadmap's removed provider surface has no direct network dependency.
  Phase 12 must justify every remaining runtime dependency by boundary.
- Documentation still has multiple sources. Phase 12 consolidates them without
  changing documentation frameworks merely for appearance.
- Supported-platform CI remains pending until the maintainer authorizes a
  checkpoint commit and push.

## Recommendation

**GO for Phase 12 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin legacy ownership-zone dissolution
automatically.
