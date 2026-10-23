# Requirement lifecycle verification — 2026-10-20

Work item: `4c04e9cb-2b7d-4732-a09b-f6a5974a5138`. Candidate is the local
working tree based on `69c7a5ffee2b4f8eda4ebc61b4d23db7aed43261`.
This report records local verification; no candidate commit, push, remote CI or
release is claimed. Package metadata remains 0.3.1 for unreleased 0.4 development.

## Delivered behavior

The [lifecycle contract](requirements-lifecycle-contract-0.4.md) records the
transition table, acceptance/evidence schema and worked examples. Draft, Accepted,
In Progress, Verified, Deferred and Rejected have explicit guarded transitions.
Acceptances and criterion results retain UUIDs, intent revisions, actor/date,
reasons or notes and commit/artifact references. Current acceptance and intent
must both match the actor's reviewed values when adding evidence. Reacceptance
at an unchanged digest starts a fresh cycle; results for old cycles cannot be
silently attached to the replacement cycle.

Verification requires latest passing evidence for every criterion. Failed,
incomplete and missing results block it. Negative results demote Verified to In
Progress; subsequent passes require explicit verification again. Issue completion
does not mutate requirement governance. Metadata and rekey preserve acceptance;
semantic edits withdraw it while preserving prior definitions and evidence.
Manual edits produce effective Draft and missing current results on reads without
canonical writes. An observed edit cannot regain acceptance merely by reverting
through update. Unobserved byte-for-byte manual reversion is inherently undetectable.

Parsing validates historical definitions, acceptance references, criterion
membership, record identities and verification prerequisites. Old capture-only
Draft documents remain readable with empty governance histories. Unknown fields,
prior content and history survive writes. SQLite rebuilds and CLI filters use
effective lifecycle state. All writes reuse existing canonical transactions,
locks, optimistic conflict validation and recovery.

## Local evidence

- Complete normal parallel suite: **1,352 passed**, 93.01 seconds, **97.04%**
  statement coverage (6,896 statements; 204 uncovered), with the unchanged 90%
  floor. Command: `uv run --locked pytest -n auto --cov=roadmap
  --cov-config=config/.coveragerc --cov-report=term-missing`.
- Real-storage journeys in
  `tests/integration/cli/test_cli_requirement_governance.py` prove complete,
  failed, incomplete, stale and renewed evidence; no-write refusals; stale cycle
  rejection; manual edit/reversion; external-write preservation; issue-close
  independence; malformed records; transaction interruption and recovery.
- Pure examples in `tests/unit/domain/test_requirement_governance.py` prove
  transition prerequisites, latest-result semantics and historical invariants.
  The new immutable governance value module has 100% statement coverage.
- Ruff formatting/lint, ty, Vulture, Xenon and high-severity Bandit checks pass.
  Radon reports no D-or-higher block; average complexity A (3.25).
- Architecture: four import contracts kept, zero broken; 153 files and 610
  dependencies. No new runtime dependency, architecture zone or exception.
- CLI signature/parameter inventory, behavioral evidence matrix and documentation
  policies pass in the full suite. `uv lock --check` and `git diff --check` pass.
- Built wheel and source distribution. Installed the exact wheel in a clean
  temporary Python 3.14.2 environment with runtime dependencies and ran
  `scripts/requirements_journey.py` and `scripts/checkpoint_journey.py` successfully.
  The governance journey covers explicit verification, failure demotion, manual
  staleness, renewed acceptance/fresh results, unchanged issue data, stable UUID/path
  and projection rebuild. Reads wrote zero canonical files.
- Clean wheel and source-distribution smoke installations both pass, including
  retained-user workflows, workspace selection and JSON inspection.
- Permanent requirements package-matrix journey now exercises this governance
  behavior alongside capture/adoption. The existing six CI package jobs call it;
  their remote result for this working tree remains pending.

Artifacts built locally:

| Artifact | SHA-256 |
| --- | --- |
| `roadmap_cli-0.3.1-py3-none-any.whl` | `c06dc064ca28186221a4388e09b3c647de68c2d149611d6b89aa1c4b8c6b474f` |
| `roadmap_cli-0.3.1.tar.gz` | `bc736f0a64b4dcbc1c88af900111ab268d25845d165886c35e4142baf462beb9` |

The [installed result](requirement-lifecycle-verification-2026-10-20.json)
records the candidate journey. This pass did not rerun actual published-0.3.1
refusal; the [capture verification](requirement-capture-verification-2026-10-12.md)
retains that earlier evidence. It did exercise retained issue-only initialization
and explicit adoption using the installed candidate.

## Remaining boundaries

Typed relations, reverse queries, gap reports, recommendation/schedule work and
project register cutover remain separate. The project workspace was not adopted;
CSV remains authoritative. Do not promote CSV requirement statuses from this issue
or count local success as remote supported-platform verification. References and
local actor attribution are recorded offline, not authenticated or remotely checked.
