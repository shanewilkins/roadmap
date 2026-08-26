# Phase 13 checkpoint — Hardened 0.2 release candidate

- Date: 2026-08-26
- Phase 12 accepted commit: `5a03b3a1`
- Package version: 0.1.1
- Target version: 0.2.0
- Decision: **GO**
- Next action: stop before changing the version, committing a release, tagging,
  pushing, or publishing

## Decision

Phase 13 is complete. The contracted 0.2 product is a release candidate with
one architecture, one canonical data authority, a disposable SQLite projection,
an explicit 0.1.1 migration, an offline core, deterministic machine output,
and no provider synchronization or Roadmap-owned authentication.

Separate authorization is required for the 0.2.0 version bump, release commit,
tag, push, trusted PyPI publication, and post-publication verification. This
checkpoint performs none of those actions; package metadata remains 0.1.1.

## Hardening and test-quality audit

Existing focused suites already inject write failures at every canonical commit
stage, lock contention, interrupted recovery, SQLite corruption/missing/old
schema states, external canonical edits, permissions failures, migration
collisions and rollback, structured stdout/stderr boundaries, Unicode/null
exports, output collisions, and blocked network access.

Phase 13 removed a 351-line disabled test module that imported deleted
production namespaces, moved ANSI helpers out of a fake unit-test module, and
replaced conditional skips and tautological CLI assertions with persisted-state
checks. Executable policy now forbids silent skip/xfail calls, disabled test
files, duplicate test-module names, removed imports, and assertions that accept
both a condition and its negation. The audit found one deliberate assertion-free
resource-warning test: its `ResourceWarning` filter is the failure oracle.

The selected hardening checkpoint passed **220 tests** covering canonical
persistence, configuration, queries/mutations/planning, workspace diagnosis and
migration, archive/restore, CLI issue/milestone/data/Git/migration journeys, the
performance envelope, and every executable policy. The complete pytest suite
was deliberately not run, following the maintainer's explicit instruction.

## Performance envelope

The new automated small-team envelope creates 500 dependency-linked issues in
one milestone: 400 active, 50 closed, and 50 archived. Projection rebuild,
filtered lookup, daily/board calculation, critical-path analysis, read-only
health scan, and deterministic JSON export all passed their documented shared-CI
ceilings. The complete contract and thresholds are in
[performance-envelope-0.2.md](../performance-envelope-0.2.md).

## Distribution and installed journeys

The unchanged-version candidate built as a wheel and source distribution. Each
artifact installed without `PYTHONPATH` into an isolated Python 3.14.2
environment and passed metadata/version, import-origin, help, initialization,
issue creation, and list smoke tests. The wheel contains 111 entries and the
source distribution contains no tests, `.roadmap` state, cache, or build output.

| Artifact | SHA-256 | Result |
|---|---|---|
| `roadmap_cli-0.1.1-py3-none-any.whl` | `d5775540d392b2018401737b5e34938fb723c47882245a6b86915537c5bf3be4` | Passed. |
| `roadmap_cli-0.1.1.tar.gz` | `305a0ce142708ed92c3112c4bcd6603cc7fdd16cf2fe75dfc13605fbf2461cd6` | Passed. |

The installed wheel completed the cumulative fresh-workspace journey and two
independent copies of the sanitized 0.1.1 migration fixture. Both migration
copies preserved visible issue IDs `5898cb1f` and `951f146d`, archived issue
`a11ce001`, project `c83ed497`, milestone `v0-1-1`, and the sanitized comment.
Dry-run remained non-mutating, projection corruption rebuilt without changing
canonical meaning, and repeated migration was idempotent.

CI and the tag-triggered release workflow now run artifact smoke/cumulative
journeys. Package compatibility uses the Cartesian matrix of Python 3.13 and
3.14 on Ubuntu and macOS. That remote matrix remains a release checklist gate
after this work is committed; it is not claimed as locally executed evidence.

## Measured simplification

| Metric | Initial baseline | Phase 13 | Change |
|---|---:|---:|---:|
| Production Python code lines | 54,225 | 9,200 | -45,025 (-83.03%) |
| Production Python files | 504 | 106 | -398 (-78.97%) |
| Test modules | 540 | 52 | -488 (-90.37%) |
| Architecture exceptions | not enforced | 0 | enforceable empty baseline |
| Direct runtime dependencies | mixed/sprawling | 3 | Click, Rich, PyYAML |
| Average cyclomatic complexity | not governed | A (3.47) | CI-enforced |

Production CLOC is unchanged from Phase 12, so the 9,200-line ratchet passes.
The retained suite contains 4,892 Python code lines, 52 files, and 212 source
test functions. Tests and documentation increased only where they add Phase 13
evidence.

## Documentation and release controls

- Package author, keywords, classifiers, Python/platform support, runtime
  dependencies, repository URLs, and installed metadata were inspected.
- The changelog now describes only verified behavior and identifies the
  premature pre-reset 1.x claims as unsupported history.
- The README, public contract, requirements, migration guide, removed-sync
  guide, CLI help, performance envelope, release checklist, and rollback plan
  agree on scope and data authority.
- The portfolio case study records the rewrite decision, architecture,
  migration strategy, evidence, and measured contraction.
- Pre-commit passes, including the EOF hook. Canonical `.roadmap/` runtime data
  is excluded from whitespace/EOF rewriting so hooks do not fight Roadmap's
  serializer or mutate lock state.
- Trusted publishing is scoped to GitHub's tag-triggered release workflow, the
  PyPI `pypi` environment, and OIDC `id-token: write`; no API token is stored.

## Automated and static gates

| Gate | Result |
|---|---|
| Selected Phase 13 pytest checkpoint | Passed: 220 tests. |
| Pre-commit all files | Passed. |
| Ruff lint and format | Passed. |
| Pyright | Passed after test-policy typing repair. |
| Architecture/test-quality/public-contract policies | Passed. |
| Bandit high-severity gate | Passed. |
| Radon/Xenon | Passed; average A (3.47), absolute C, module C, average A. |
| Wheel/source smoke and artifact audit | Passed. |
| Installed cumulative fresh/migration journey | Passed. |
| Production CLOC ratchet | Passed at 9,200 code lines. |

## Requirements traceability

Phase 13 provides direct evidence for UR-001, UR-005, UR-008, UR-010, UR-016,
UR-024, UR-027, UR-033, UR-037, UR-040 through UR-048, and TR-001 through
TR-006, TR-008 through TR-013, TR-015, TR-020, TR-021, TR-024, TR-025,
TR-028 through TR-036.

Authentication remains a conditional post-0.2 decision gate. Requirements as
application entities, a documentation framework, provider adapters, and broader
performance targets remain deferred pending concrete evidence.

## Recommendation

**GO for a separately authorized 0.2.0 release operation.** Stop here. Do not
change the version, commit, tag, push, or publish as part of Phase 13.
