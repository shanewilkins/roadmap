# Phase 1 checkpoint — public contract and requirements triage

- Date: 2026-08-16
- Baseline commit: `fc47aba7c9e604cf54827c4301970499afd9e0e4`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 2

## Decision

Phase 1 fixed the 0.2 product contract without changing production behavior.
Every current CLI command and option, configuration key, canonical model field,
machine-output contract, exit category, storage boundary, Git behavior, and
migration obligation is inventoried with an explicit disposition. Requirements
are fully triaged, public documentation reflects the accepted direction, and
the complete checkpoint is green.

Phase 2 may begin after explicit maintainer approval.

## Requirements triage

| Register | Accepted for 0.2 | Deferred post-0.2 | Other |
| --- | ---: | ---: | ---: |
| User requirements | 46 | 13 | 0 |
| Technical requirements | 34 | 10 | 0 |

All `Must` requirements are Accepted and assigned to a 0.2 phase. There are no
Draft, TBD, Rejected, unowned, duplicate-ID, broken-reference, or
Accepted-to-Deferred dependency rows.

Automatic Git-hook and commit-message mutation requirements are Deferred.
Requirements as first-class Roadmap application entities are also Deferred;
the CSV files remain governance artifacts. Provider synchronization is not a
deferred 0.2 feature: it is an explicitly retired product direction under
ADR-0002.

## Compatibility inventory

The inventory contains 209 reviewed surfaces:

| Category | Rows |
| --- | ---: |
| CLI commands and groups | 82 |
| Configuration keys | 29 |
| Canonical model fields | 72 |
| Output contracts | 9 |
| Exit categories | 3 |
| Storage/layout contracts | 5 |
| Git behavior contracts | 5 |
| Migration contracts | 2 |
| Requirements-boundary contracts | 2 |

Disposition totals are 126 Preserve, 31 Replace, 37 Remove, and 15 Internal.
Every removal has replacement or retirement guidance, evidence, ownership,
requirement traceability, and an implementation phase.

The principal product decisions are:

- preserve local canonical-file-to-SQLite projection and rebuild behavior;
- preserve ordinary Git collaboration and explicit local branch/work links;
- preserve issue comment add/list as the supported discussion journey;
- replace configuration, lifecycle storage, broad cleanup, and machine schemas;
- remove remote/provider sync, provider credentials and mapping, automatic Git
  mutation, the fake top-level comment family, and the placeholder report
  command; and
- keep requirements CSVs as governance inputs without adding them to the 0.2
  application model.

## Documentation

The README, quick start, workflows, FAQ, Git sharing guidance, and future
direction now describe the accepted file-first local product. Stale instructions
to create provider tokens, invoke remote sync, rely on commit prose, or install
automatic hooks were replaced with migration guidance. The exact phrase
previously requested for removal no longer appears in repository documentation.

The authoritative documents are:

- `docs/architecture/public-contract-0.2.md`;
- `docs/architecture/compatibility-inventory-0.2.csv`; and
- `docs/requirements/phase-1-triage-2026-08-16.md`.

## Policy evidence

`tests/policy/test_public_contract_inventory_policy.py` adds five passing policy
tests. They enforce register schemas and triage, requirement references and
status-compatible dependencies, inventory ownership/evidence/guidance, and
exact current coverage for all CLI, configuration, and canonical-field
surfaces. Negative proofs demonstrate that an unreviewed command or
configuration key fails the gate.

Focused result: **5 passed**.

## Production CLOC

Fixed command and tool: `cloc` 2.10 against `roadmap/`.

| Metric | Phase 0A | Phase 1 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 504 | 504 | 0 |
| Blank lines | 16,006 | 16,006 | 0 |
| Comment lines | 20,312 | 20,312 | 0 |
| Code lines | 54,206 | 54,206 | 0 (0.000%) |

No production file changed. The CLOC ratchet passes and the Phase 2 ceiling
remains 54,206 production Python code lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed. |
| `uv lock --check` | Passed; 115 packages resolved. |
| Ruff format | Passed; 1,060 production/test files already formatted. |
| Ruff lint | Passed. |
| Pyright | Passed with 0 errors, 0 warnings, and 188 informational findings. |
| Bandit high-severity gate | Passed; 0 high findings (66 low, 5 medium). |
| Complete pytest suite | Passed; 8,294 tests in 118.47 seconds. |
| Coverage | Passed; 82.05% against the configured 81% minimum. |

The five-test increase over Phase 0A is exactly the new contract-policy file.
The suite emitted 1,938 warnings, four more than the Phase 0A run. The visible
warnings remain dominated by nondeterministically collected unclosed SQLite
connection `ResourceWarning` instances; no production code changed in this
phase. Connection cleanup remains visible debt rather than a relaxed gate.

## Distribution boundary

Both artifacts were built from the final Phase 1 README in a fresh directory,
installed without `PYTHONPATH`, imported from isolated virtual environments,
and passed help, version, initialization, issue creation, and issue listing on
Python 3.14.2.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `467d39f798e3e51f020eb7d07bbe02807c2faf2bc9b68d1332d33740908ec1c1` | Passed |
| `roadmap_cli-0.1.1.tar.gz` | `a0f1a8e39f9a901e3a3e1a05be1b3e49e809feb3beffed675199a32ed7431861` | Passed |

The initial sandboxed build and wheel smoke could not reach the package index.
Their approved network-enabled reruns passed; this was an environment
restriction rather than a package failure.

## Installed application journeys

The retained journey runner used the final wheel hash above in a disposable
workspace and passed:

1. help and version;
2. initialization and safe reopen;
3. project and milestone creation with a persisted relation;
4. issue create, view, comment, close, archive dry-run, archive, and restore;
5. supported JSON parsing;
6. manual canonical-document edit observation;
7. SQLite deletion and rebuild with unchanged canonical digests;
8. JSON health diagnosis and non-mutating repair preview;
9. offline local Git initialization and status; and
10. two deterministic 0.1.1 compatibility-fixture loads and projection
    rebuilds.

The compatibility snapshot retained visible issue IDs `5898cb1f` and
`951f146d`, the archived and legacy closed issues, project and milestone
relations, and the sanitized fixture comment.

## Architecture and removal baseline

Architecture enforcement begins in Phase 2, so no violation was silently
accepted or removed in Phase 1. A filename-based baseline currently counts 111
Python files and 17,380 code lines under sync/GitHub-named paths; this includes
both the local projection behavior that must survive and the remote/provider
subsystem scheduled for Phase 11 removal. Later phases must classify by behavior
rather than deleting every file matched by that crude name filter.

## Compatibility and rollback

Phase 1 modifies only documentation, CSV registers, and policy tests. It does
not migrate or mutate a workspace, canonical file, SQLite schema, configuration,
or Git state. Rollback is therefore an ordinary source-control revert. The
installed compatibility journey separately proves the Phase 0A data and
projection guarantees remain intact.

## Known risks and deferred work

- The 0.1.1 implementation still exposes commands now approved for removal;
  Phase 11 owns their code deletion and intentional-absence tests.
- Configuration and structured-output target schemas are specified at contract
  level but finalized with migration fixtures in Phases 9 and 10.
- Architecture violations are not yet mechanically ratcheted; Phase 2 owns the
  enforcement baseline.
- SQLite connection warnings remain technical debt.
- CI matrix execution awaits a maintainer-authorized commit and push.

## Recommendation

**GO for Phase 2 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin architecture enforcement
automatically.
