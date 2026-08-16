# Phase 2 checkpoint — architecture enforcement

- Date: 2026-08-16
- Baseline commit: `795770dcca6c602d9f7eb7a32d22e5a1fe7aa306`
- Package version: 0.1.1
- Decision: **GO**
- Next action: stop and obtain maintainer approval before Phase 3

## Decision

Phase 2 installed a mechanical architecture ratchet without moving or changing
any production module. The target Domain, Application, inbound adapter,
outbound adapter, and Bootstrap dependency directions are machine-readable,
checked with Python AST import analysis, and enforced in both local checks and
CI. Deliberate violations fail, current migration debt passes only through
eight exact reviewed exceptions, and the complete application checkpoint is
green.

Phase 3 may begin after explicit maintainer approval.

## Behavior and requirements

No user-facing behavior was added, replaced, or removed. Existing 0.1.1
behavior, storage, data compatibility, and installed journeys were preserved.

This phase completes the Phase 2 obligation of **TR-003, Enforced architecture
boundaries**, and advances the architecture portion of **TR-011, Automated
quality gate**. No user requirement changed status.

## Enforcement delivered

`architecture.toml` declares five target zones and seven exact rules:

1. Domain imports only the standard library and Domain.
2. Application imports only the standard library, Application, and Domain.
3. Inbound adapters may use Application, Domain, external packages, the
   standard library, and their own inbound-adapter boundary.
4. Outbound adapters have the equivalent isolation rule.
5. Only Bootstrap may wire concrete adapters across boundaries.
6. Architectural-zone cycles are forbidden.
7. Retired remote-sync namespaces become forbidden in Phase 11.

The checker rejects unknown policy fields, malformed rule identities, malformed
or duplicate baseline entries, nonfuture removal phases, unbaselined
violations, and stale exceptions. It returns a failing process status for a
real violation; no wrapper converts failure to success.

The positive fixture exercises permitted dependency directions. Focused
negative fixtures cover all seven rules, including a two-edge zone cycle and a
Phase 11 removed namespace. The policy suite also proves new-violation and
stale-exception behavior, strict policy and baseline parsing, scheduled-rule
activation, exact current-tree matching, and meaningful Pyright settings.

Focused result: **19 passed in 1.80 seconds**.

## Exact architecture baseline

The reviewed baseline contains eight source/target/rule exceptions, each with a
human reason, accountable owner, and exact removal phase:

| Rule | Count | Owner phase | Description |
| --- | ---: | ---: | --- |
| `application-dependencies` | 7 | 11 | The legacy remote-deduplication service still imports concrete logging, telemetry, repository, model, and sync machinery. |
| `domain-dependencies` | 1 | 4 | The transitional Domain validation wrapper delegates to legacy validators. |

There are no baselined cycles, adapter-boundary violations, Bootstrap-wiring
violations, or active removed-namespace violations. The baseline has no
wildcards. New and stale entries both fail the gate, so the count can only
remain exact or shrink.

The previously recorded filename-based remote-sync inventory remains 111 Python
files and 17,380 code lines. It is deliberately broader than the eight actual
target-zone import exceptions and still includes local projection behavior that
must survive. Phase 11 owns behavioral classification and removal.

## Pyright repair

Pyright now resolves the checked-in `.venv` directly and no longer uses a
hard-coded Python 3.14 site-packages path or treats `roadmap/` itself as an
extra import root. Only the deliberately invalid architecture-fixture directory
is excluded. Core import, undefined-variable, general-type, optional-member,
and optional-subscript diagnostics remain errors.

The final result is **0 errors, 0 warnings, and 188 informational findings**.
No type-error baseline was necessary.

## Important files

- `architecture.toml`
- `architecture-baseline.toml`
- `tests/policy/architecture_checker.py`
- `tests/policy/test_architecture_contract_policy.py`
- `tests/policy/fixtures/architecture/`
- `pyrightconfig.json`
- `.github/workflows/tests.yml`
- `CONTRIBUTING.md`

No file below `roadmap/` changed and no production file was deleted or moved.
The project retains 15 declared runtime dependencies.

## Production CLOC

Fixed command and tool: `cloc` 2.10 against `roadmap/`.

| Metric | Phase 1 | Phase 2 | Delta |
| --- | ---: | ---: | ---: |
| Python files | 504 | 504 | 0 |
| Blank lines | 16,006 | 16,006 | 0 |
| Comment lines | 20,312 | 20,312 | 0 |
| Code lines | 54,206 | 54,206 | 0 (0.000%) |

The CLOC ratchet passes and the Phase 3 ceiling remains 54,206 production
Python code lines.

## Automated and static gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed. |
| `uv lock --check` | Passed; 115 packages resolved. |
| Ruff format | Passed; 1,078 production/test files already formatted. |
| Ruff lint | Passed. |
| Architecture policy | Passed; the current tree exactly matches 8 reviewed entries. |
| Pyright | Passed with 0 errors, 0 warnings, and 188 informational findings. |
| Bandit high-severity gate | Passed; 0 high findings (66 low, 5 medium). |
| Complete pytest suite | Passed; 8,313 tests in 102.19 seconds. |
| Coverage | Passed; 82.00% against the configured 81% minimum. |

The 19-test increase over Phase 1 is exactly the new architecture-policy suite.
There were no failures, skips, or expected failures. The suite emitted 1,854
warnings, 84 fewer than the Phase 1 run. They remain dominated by
nondeterministically collected unclosed SQLite connection `ResourceWarning`
instances; no production lifecycle code changed in this phase.

## Distribution boundary

Both artifacts were freshly built, installed without `PYTHONPATH`, imported
from isolated virtual environments, and passed help, version, initialization,
issue creation, and issue listing on Python 3.14.2.

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `roadmap_cli-0.1.1-py3-none-any.whl` | `467d39f798e3e51f020eb7d07bbe02807c2faf2bc9b68d1332d33740908ec1c1` | Passed |
| `roadmap_cli-0.1.1.tar.gz` | `a0f1a8e39f9a901e3a3e1a05be1b3e49e809feb3beffed675199a32ed7431861` | Passed |

The hashes are unchanged from Phase 1 because Phase 2 did not alter packaged
production or README content. Initial sandboxed smoke attempts could not reach
PyPI; the approved network-enabled reruns passed. This was an environment
restriction, not an artifact defect.

## Installed application journeys

The retained journey runner used the final wheel above in a disposable
workspace and passed:

1. Help and version.
2. Initialization and safe reopen.
3. Project and milestone creation with a persisted relation.
4. Issue create, view, comment, close, archive dry-run, archive, and restore.
5. Supported JSON parsing.
6. Manual canonical-document edit observation.
7. SQLite deletion and rebuild with unchanged canonical digests.
8. JSON health diagnosis and non-mutating repair preview.
9. Offline local Git initialization and status.
10. Two deterministic 0.1.1 compatibility-fixture loads and projection
    rebuilds.

The compatibility snapshot retained visible issue IDs `5898cb1f` and
`951f146d`, archived and legacy closed issues, project and milestone relations,
and the sanitized fixture comment.

## Compatibility and rollback

Phase 2 adds repository policy, tests, CI configuration, and documentation
only. It does not mutate a workspace, canonical document, SQLite schema,
configuration, or Git state. Rollback is an ordinary source-control revert.
The installed compatibility journey separately proves that the accepted 0.1.1
canonical-file and projection guarantees remain intact.

## Known risks and deferred work

- The target zones are intentionally sparse. The ratchet governs modules as
  they enter those namespaces; Phase 3 begins the production migration by
  establishing one composition root.
- Eight exact architecture exceptions remain: one is due in Phase 4 and seven
  are due in Phase 11.
- The 0.1.1 implementation still exposes remote/provider sync slated for
  intentional removal in Phase 11; local canonical-file-to-SQLite projection
  remains retained behavior.
- SQLite connection warnings remain visible lifecycle debt.
- CI matrix execution awaits a maintainer-authorized commit and push.

## Recommendation

**GO for Phase 3 after explicit maintainer approval.** Stop here in accordance
with the execution contract; do not create Bootstrap automatically.
