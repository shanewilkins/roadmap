# B+ review follow-up — 2026-10-08

Baseline: `c246bfb962d8fa0f126d46ff3a072178d1877c39` on `master`, plus the
local changes listed below. This closes implementation follow-ups from the
October 6 B assessment; it does not confer an independent B+ grade, publish a
release, or establish a backup maintainer.

## Disposition

| Review concern | Current disposition |
| --- | --- |
| Release/source ambiguity | Published 0.3.0 and unpublished 0.3.1 candidate are distinguished in README, installation guidance and metadata. The maintainer selected 0.3.1 on October 8. Delivered changes moved into a dated candidate changelog section. Publication remains subject to approval. |
| Requirement traceability | Existing scoped evidence remains linked. Exact baseline CI was checked; obsolete platform-pending language was narrowed to the new local candidate. Four partial records remain Accepted with their specific unmet criteria. |
| Safety paths and flag interactions | The October 6 safety/matrix and ordered branch passes already supply the implementation evidence. This pass reran migration, transaction, projection and real-process recovery tests. It does not imply exhaustive combinations or hardware power-loss proof. |
| Continuity | The executable handover drill and explicit single-maintainer limitation remain in force. Recruiting a willing delegate and granting service access require real human acceptance; no delegate is invented. |
| Deprecated test isolation | All Click `isolated_filesystem` calls replaced with a shared pytest temporary-workspace context. It restores cwd before cleanup, including nested scopes and exceptions. Affected CLI journeys pass with deprecations as errors. |
| Coverage configuration | Removed all obsolete omit patterns. The statement floor remains 90%; branch coverage remains informational. |
| Broad security suppression | Removed the global B110 exemption. All-severity Bandit passes with only the existing two scoped local-Git subprocess exceptions and configured B101 exclusion. |
| Missing dead-code/documentation automation | Added stock Vulture at 100% confidence and a local Markdown file/heading link gate to CI and contributor commands. Negative fixtures prove both reject representative defects. Markdown parser and Vulture are explicit locked dev dependencies. |

Vulture's five-name analysis-only whitelist covers Click's debug parameter,
two retained no-op board compatibility options, and two context-manager protocol
arguments. It excludes no production modules. It is name-based, so reviewers
must inspect future uses of those names; low-confidence dead code is not proved
absent. The documentation gate checks active repository Markdown, not external
URLs or every possible GitHub anchor extension.

## Verification performed

| Check | Result |
| --- | --- |
| Baseline CI | [CI run 37531418989](https://github.com/shanewilkins/roadmap/actions/runs/37531418989): all 12 jobs passed at exact baseline SHA, including Python 3.12–3.14 tests and six Ubuntu/macOS package jobs. This is baseline evidence, not CI for local edits. |
| Affected CLI and documentation tests | 118 passed with `-W error::DeprecationWarning`. |
| Policy, migration, transaction, projection and process-recovery tests | 149 passed with `-W error::DeprecationWarning` after correcting a new negative fixture. |
| Gate-negative fixtures | 7 passed: missing documentation targets/headings, reference/Unicode/duplicate-heading handling, unused arguments and unreachable code. |
| Ruff lint/format and ty | Passed. |
| Architecture | Four contracts kept, zero broken. |
| Complexity | Xenon B/B/A passed. |
| All-severity Bandit | No issues identified with B110 enabled. |
| Lockfile and hashed dependency audit | Lock resolved; pinned pip-audit reported `No known vulnerabilities found`, including Vulture. |
| Initial clean artifact check | Wheel and sdist built and clean-installed successfully before the version bump; both reported installed-workflow success. Final 0.3.1 artifact checks follow below. |
| Final 0.3.1 artifacts | Wheel and sdist built; each clean-installed and passed help/version/import-origin and workspace/ID/JSON checks. The separate installed-wheel cumulative migration/recovery journey passed and preserved fixture IDs `5898cb1f` and `951f146d`, comment content, archived/closed visibility, project and milestone. |
| Final full configured coverage gate | `uv run --locked --extra dev pytest -n 0 --cov=roadmap --cov-config=config/.coveragerc --cov-report=term --cov-report=json:/tmp/roadmap-bplus-0.3.1-coverage.json -W error::DeprecationWarning`: **1,188 passed in 84.35s**, no warnings; **97.21%** statement coverage (5,673 / 5,836), 90% floor reached. Includes the unchanged performance envelope. |

Final artifact SHA-256 values:

- Wheel: `541f92b6ed22a5d73019394d09604d2e5e1a358fa08e31cacc116227b1530752`.
- Source distribution: `91b33ec4853c1783e5d5c16c2c7af80659141ba977e3311c67f1c934930e686f`.

Artifacts are local candidates under `/tmp/roadmap-bplus-0.3.1-dist`; these are
not PyPI publication hashes. Their embedded README/changelog describe the
candidate as unpublished.

The first scoped run found a faulty new negative fixture: an unused local
assignment is below Vulture's 100% threshold. The fixture now exercises an unused
argument at that threshold. The corrected scoped run passes; no gate was relaxed.

The first full run used eight workers while artifact work also ran: 1,187 tests
passed, but the benchmark's filtered lookup took 4.134 seconds against its
3-second ceiling. The full sequential rerun after artifact work finished passed
all 1,188 tests. No timing ceiling, test skip or failure allowance was changed;
the only coverage configuration change removed obsolete omit patterns.

PyPI was freshly checked on October 8 and still reports 0.3.0. `gh release view`
reports latest GitHub announcement v0.2.0. The prepared
[0.3.1 announcement](../releases/0.3.1-announcement.md) supplies publication copy;
the discovery mismatch remains unresolved until a reviewed release is published.

## Remaining decisions and acceptance

- Full configured suite and final 0.3.1 artifacts: complete locally, as recorded
  above; full-suite approval received October 8.
- Exact final candidate SHA and green candidate CI need a reviewed commit/push.
- Tagging, PyPI publication, index installation and matching GitHub Release
  announcement follow the [release checklist](../releases/NEXT_RELEASE.md).
- TR-008 still needs complete interruption-stage/platform evidence; TR-011
  needs candidate CI and broader negative-gate proof; TR-014 needs its broader
  correlation/redaction/audit-context assessment; TR-035 needs final candidate
  OS-matrix evidence. None is promoted solely because aggregate coverage is high.
- The B+ roadmap checkbox remains open until a fresh quality assessment accepts
  the final evidence and release/capacity limits. Historical grades are preserved.

See [October 6 follow-ups](quality-review-actions-2026-10-06.md),
[branch reliability](branch-reliability-2026-10-06.md), the
[verification ledger](../requirements/verification-evidence.json), and the
[handover runbook](HANDOVER.md).

## Release authorization

On October 8 the maintainer authorized committing/pushing the candidate, creating
the version tag and building the PyPI release. The release commit finalizes the
changelog and version-matched installation links before tagging. The candidate
hashes above describe the earlier local build; final release artifact hashes
and workflow evidence are recorded separately after publication.
