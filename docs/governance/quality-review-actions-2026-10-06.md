# Quality review actions — 2026-10-06

The maintainer agreed with four follow-ups to the current B quality assessment.
This record tracks implementation against master `47c25eaa` plus uncommitted
local changes. It does not claim a new release or independent human approval.

| Action | Implementation |
| --- | --- |
| Release and documentation clarity | README/installation distinguish published 0.3.0 from master; package docs URL points to the actual default branch; historical closeout is labeled; a current next-release checklist replaces use of the old 0.2 checklist. |
| Requirement verification | Seven scoped requirements are Verified, four assessed requirements remain Accepted with explicit gaps; lifecycle policy accepts Verified and rejects unsubstantiated evidence. |
| Remaining safety paths | Migration refuses unreadable canonical enumeration and boolean personal schema versions; changed-preview tests protect latest edits; projection failure tests prove rollback/retry; direct parameter evidence links preview/consent/override interactions. |
| Practical continuity | A handover packet and candidate drill specify duties, access, evidence, pause/return and private security handling; no backup maintainer or delegated permissions are invented. |

## Safety findings and proof

Before the fixes, focused regressions produced **3 failures**: personal schema
versions `true`/`false` were accepted and an unreadable canonical directory was
silently skipped. Three other invalid-version cases already passed. Migration
now uses the same fail-closed canonical enumeration as normal document reads,
including the fingerprint scan, and excludes bool from integer schema versions.

New regression cases cover:

- Preview fingerprints invalidated by canonical edits or new/existing personal
  config at both Application and adapter boundaries; refusal preserves the latest
  bytes, and a new preview permits retry without losing those edits.
- ENOSPC/EACCES during projection staging/replacement; old index/canonical bytes
  survive, temporary files are removed, stale state is explicit and retry succeeds.
- SQLite failure after old rows are deleted; the failed refresh rolls back and
  retry reads current canonical data.
- `--dry-run --yes` with format/verbosity on migration and corrupt-index repair;
  consent never converts a preview into writes.
- Archive `--dry-run --yes --force --verbose` across issue/project/milestone;
  preview preserves all persistent state despite consent and lifecycle override.
- CLI migration preview/apply both fail loudly on unreadable nested storage.

The matrix directly links 14 safety-sensitive parameters to named assertions.
Other parameters retain command-level evidence. This is a scoped improvement,
not an exhaustive claim about every combination. Branch coverage is measured
informationally; the enforced 90% gate remains statement coverage.

## Verification and handover drill

The drill used the [handover runbook](HANDOVER.md),
[requirement evidence](../requirements/verification-evidence.json), clean
artifact installations and the cumulative checkpoint journey. Results below
were executed locally on macOS/Python 3.14.2 against the candidate.

| Check | Command / evidence | Result |
| --- | --- | --- |
| Focused evidence and safety | `uv run --locked pytest -n 0 -q` with the three changed/new persistence/CLI files and four requirement/matrix/metadata policy files | **57 passed in 2.87s**. |
| Full configured statement gate | `uv run --locked pytest --cov=roadmap --cov-config=config/.coveragerc --cov-report=term --cov-report=json:/tmp/roadmap-quality-followup-final-statements.json` | **1,132 passed**, 79 existing warnings; **96.20%** statement coverage, 90% floor reached. Baseline 1,094 cases: 38 added cases. |
| Informational branches | Full suite with `--cov-branch`, JSON report and `--cov-fail-under=0`, using separate `COVERAGE_FILE=/tmp/roadmap-quality-followup-branchdata` | **1,132 passed**; branch coverage **85.50%** (1,262/1,476), up from freshly measured baseline **85.09%** (1,256/1,476). Combined line/branch percentage is not the statement gate. |
| Static gates | Locked Ruff lint/format, ty, architecture wrapper, Xenon B/B/A; Bandit with all severities; `uv lock --check` | Passed; Ruff: `196 files already formatted`; architecture: `Contracts: 4 kept, 0 broken.`; Bandit: `No issues identified.` with existing configured/scoped exclusions. |
| Local documentation links | MarkdownIt file/heading audit of README, CONTRIBUTING, SECURITY and docs Markdown | **68 files, 185 links, 0 missing targets/anchors**. External URLs are not an exhaustive crawl. |
| Candidate build | `uv build --out-dir /tmp/roadmap-quality-followup-dist` | Wheel and sdist built successfully; inspected wheel metadata contains the corrected `tree/master/docs` URL. |
| Clean artifact installations | `uv run --locked python scripts/smoke_package.py` with each exact candidate artifact | Both passed: `Installed workspace selection, ID-only creation and JSON inspection passed.` |
| Installed-wheel handover journey | Fresh `/tmp/roadmap-quality-followup-wheel-env`, candidate wheel installed with `uv pip install`; `uv run --locked python scripts/checkpoint_journey.py --roadmap-command /tmp/roadmap-quality-followup-wheel-env/bin/roadmap` | Exit 0; fresh/repeated migration, canonical digest, inspection, projection repair and Git-link checks pass. Final compatibility snapshot preserves both issue IDs/comment and reports project, milestone, closed and archived visibility. |

Candidate wheel SHA-256:
`4088d1c6b06eae35a5ce078c31a40b6acf766c28c9663422ceb88cd1dc3a513c`.
This identifies the tested local artifact, not a published PyPI artifact. Logs
are temporary `/tmp/roadmap-quality-followup-*` files; summaries are retained
here. Branch measurements still leave 214 branch arcs unexecuted overall;
projection missed statements fell from 12 to 2 and migration use-case missed
statements from 2 to 0. Those figures guide further inspection without a new gate.

The scoped drill is complete. Its handover mode is **preparation only, delegate
none**: no repository/PyPI/private-advisory access is delegated, and no alternate
security responder is claimed. Local execution does not establish remote
candidate CI or delegated admin/PyPI/security access. No publication,
service-access change or ownership change was performed.

## Remaining operational decisions

The subsequent [ordered branch reliability pass](branch-reliability-2026-10-06.md)
records tests for the five largest operational coverage gaps and the remaining
defensive arcs separately from Protocol stubs.

- Select/review a new version, run the candidate CI matrix, and approve release
  publication through the [next-release checklist](../releases/NEXT_RELEASE.md).
- The existing PyPI 0.3.0 artifacts are immutable; their old metadata is not
  rewritten by this source fix. Matching GitHub Release announcement belongs to
  publication follow-through, not an unreviewed remote action in this pass.
- A willing backup and explicit service delegation remain unavailable. A
  documented pause is the correct handover mode until someone accepts those duties.
- Keep the four partial requirement assessments open; resolving them needs
  evidence or an explicit requirements decision, not another coverage percentage.
