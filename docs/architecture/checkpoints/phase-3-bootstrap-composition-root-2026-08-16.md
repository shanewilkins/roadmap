# Phase 3 checkpoint — Bootstrap composition root

- Date: 2026-08-16
- Baseline commit: `5809350548020fb094fe0ee37e3968cbb00eb7c4`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 4

## Decision

Phase 3 makes `roadmap.bootstrap` the installed application's composition root
without changing the retained 0.1.1 command, workspace, or data behavior. The
entry point now delegates to Bootstrap; concrete collaborator selection lives
there; the CLI receives factories and the retained core through Click context;
and command modules no longer import or construct `RoadmapCore`.

The complete checkpoint is green. Phase 4 may begin only after explicit
maintainer approval.

## Implemented construction boundary

- `roadmap.bootstrap` owns working-directory resolution, core construction,
  existing-workspace discovery, console creation, logging, and tracing
  factories.
- `roadmap.bootstrap.core` owns construction of the retained concrete
  collaborator graph. `RoadmapCore` is now a compatibility facade whose graph
  is supplied by Bootstrap rather than selected in the facade.
- The packaged `roadmap` entry point targets `roadmap.bootstrap:main`.
- The root Click adapter accepts an explicit runtime, loads feature commands on
  demand, and supplies core and factory dependencies through context.
- Root help is rendered from static command metadata. Importing Bootstrap or
  the CLI, invoking `--help`, and invoking `--version` do not inspect or mutate
  a workspace, initialize telemetry, access keyring, use the network, or import
  feature/core/profiling modules.
- Logging and tracing initialization is idempotent for the CLI runtime. An
  already configured host logging environment is preserved.
- The import-time logging setup and broad `roadmap.infrastructure` and
  `roadmap` compatibility re-exports were removed.
- The redundant CLI project-initialization facade was deleted; callers use the
  existing core service directly.

No dependency-injection framework or service locator was introduced. No
Domain, persistence, or feature package was moved, and no workspace schema or
canonical document changed.

## Focused policy evidence

`tests/policy/test_bootstrap_composition_policy.py` adds five executable
contracts. They prove:

1. imports and root help perform no boundary initialization;
2. help and version remain independent of workspace/runtime factories;
3. explicit Bootstrap inputs deterministically control construction and
   process initialization runs only once;
4. the retained facade accepts a Bootstrap-supplied component builder and does
   not import concrete adapters; and
5. CLI modules do not import or construct `RoadmapCore`.

The public-contract and packaging policies were adapted to enumerate the lazy
Click registry through Click's command API. All Phase 3 policy tests and the
existing architecture policy pass.

## Exact architecture and removal baseline

The architecture baseline remains exactly eight reviewed exceptions:

| Rule | Count | Owner phase |
| --- | ---: | ---: |
| `application-dependencies` | 7 | 11 |
| `domain-dependencies` | 1 | 4 |

There are still no baselined cycles, adapter-boundary violations,
Bootstrap-wiring violations, or active removed-namespace violations. The
filename-based remote-sync inventory remains 111 Python files and 17,380 code
lines. It deliberately includes the local canonical-file-to-SQLite projection
behavior that must survive; Phase 11 owns behavioral classification and remote
provider-sync removal.

The project still declares 15 runtime dependencies.

## Production CLOC

Fixed command and tool: `cloc` 2.10 against `roadmap/`.

| Metric | Phase 2 | Phase 3 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 504 | 505 | +1 |
| Blank lines | 16,006 | 15,980 | -26 |
| Comment lines | 20,312 | 20,185 | -127 |
| Code lines | 54,206 | 54,205 | -1 (-0.002%) |

The additional file count is the net result of adding the two-file Bootstrap
package and deleting one redundant compatibility module. The CLOC ratchet
passes, and the Phase 4 ceiling becomes 54,205 production Python code lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed. |
| `uv lock --check` | Passed; 115 packages resolved. |
| Ruff format | Passed; 1,080 production/test files already formatted. |
| Ruff lint | Passed. |
| Architecture policy | Passed; the current tree exactly matches 8 reviewed entries. |
| Pyright | Passed with 0 errors, 0 warnings, and 188 informational findings. |
| Bandit high-severity gate | Passed; 0 high findings (66 low, 5 medium). |
| Complete pytest suite | Passed; 8,316 tests in 114.18 seconds. |
| Coverage | Passed; 82.07% against the configured 81% minimum. |

There were no failures, skips, or expected failures. The suite emitted 1,914
warnings, dominated by nondeterministically collected unclosed SQLite
connection `ResourceWarning` instances. The warning debt remains visible and
was not converted into an exemption.

The three-test increase over Phase 2 is the net of five new Bootstrap-policy
tests and removal of two obsolete tests for private CLI initialization helpers
that no longer exist.

## Distribution boundary

Both final artifacts were freshly built, installed without `PYTHONPATH`, and
passed isolated import, help, version, initialization, issue creation, and
issue listing on Python 3.14.2.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `42c3538e33d17537e36436d7a39dd2aafd19b00a574ede924bad0c4cfbdb8b23` | Passed |
| `roadmap_cli-0.1.1.tar.gz` | `f4904a163d566b3dc00a62645ca16a7095022365472addd46e209186c6dbea72` | Passed |

An additional empty-directory check proved that installed root help creates no
files or directories and preserves the accepted help text.

## Installed application journeys

The retained journey runner used the final wheel in a disposable isolated
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
10. two deterministic 0.1.1 compatibility-fixture loads and projection
    rebuilds.

The compatibility snapshot retained visible issue IDs `5898cb1f` and
`951f146d`, archived and legacy closed issues, project and milestone relations,
and the sanitized fixture comment.

## Requirements traceability

This phase directly advances TR-003 (enforced boundaries), TR-004 (stable CLI
contract), TR-016 (isolated distributable package), and TR-017 (consistent
command construction and error translation). It establishes the Bootstrap
injection seam required by TR-019 but does not claim the Phase 9 scoped,
versioned configuration work is complete. No requirement status changed.

## Compatibility and rollback

All installed commands and command metadata remain present, and the complete
contract inventory and application journeys pass. Internal imports of
`roadmap.adapters.cli.main`, the broad `roadmap.infrastructure` re-exports, and
the redundant project-initialization facade are not approved public surfaces.

Rollback is an ordinary source-control revert. No migration is needed because
Phase 3 does not alter canonical files, SQLite schema, configuration schema, or
Git state.

## Known risks and deferred work

- `RoadmapCore` remains a broad, dynamically wired compatibility facade. Later
  feature slices must replace it with narrow Application ports and use cases.
- The Bootstrap graph still constructs retained legacy gateways, coordinators,
  and remote-sync collaborators. Centralizing that debt does not make it target
  architecture; Phases 4 through 11 remove it slice by slice.
- Configuration discovery used by retained assignee validation still occurs
  during core construction. Phase 9 owns the immutable typed configuration
  snapshot and scope migration.
- Many feature command modules retain their current internal helper and adapter
  coupling. This phase changed construction ownership, not business modules.
- SQLite resource warnings remain technical debt.
- CI matrix execution awaits a maintainer-authorized commit and push.

## Recommendation

**GO for Phase 4 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not begin Domain extraction automatically.
