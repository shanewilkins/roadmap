# Self-hosted development observations — 2026-10-08

Workspace: this repository's tracked `.roadmap`; operator: shanewilkins via
Codex. Tool: **published roadmap-cli 0.3.1**, installed from PyPI into an isolated
virtual environment at `/tmp/roadmap-0.4-dogfood-env`. This temporary path is a
session detail; future sessions should install the published version in their
own environment. No candidate source tree was used to execute workspace changes.

The [work-item index](0.4.0-work-item-index.json) names the canonical planning,
health-repair and ongoing dogfooding tasks. The
[accepted plan](0.4.0-plan.md) defines release-review and cutover gates.

## Observation 1: Missing historical backlog blocks projection repair

- Task: recover a trustworthy development workspace before planning 0.4.
- Commands: `roadmap health scan --format json`, then
  `roadmap health fix --fix-type projection --dry-run --format json`.
- Expected: a consistent workspace, or a previewable safe repair.
- Actual: scan exited 2 with 110 `canonical.broken-reference` errors, all naming
  missing milestone `backlog`, and one `projection.not-current` warning. The
  repair preview returned no actions because canonical errors block rebuilding.
  This refusal protected the canonical source; it was not a successful repair.
- Evidence: [initial scan](health-before-2026-10-08.json) and
  [initial repair preview](health-repair-before-2026-10-08.json).
- Workaround: bounded manual recovery of the single missing legacy milestone.
  `git show 4404326a:.roadmap/milestones/backlog.md` recovered its original
  description, timestamps and Markdown. Added current schema version, legacy
  `id: backlog`, visible retention and headline; replaced the obsolete missing
  project reference `8df8c61f` with an initially unassigned relation. Then
  `roadmap milestone update backlog --project 99d80769` established the current
  project relation through the CLI and its reciprocal update. The old project ID
  is retained here as recovery provenance, not claimed to be the current ID.
  No issue assignment, identity, status or body was rewritten for this repair.
- Supported repair: preview then
  `roadmap health fix --fix-type projection --yes --format json`.
  The preview offered exactly `rebuild-projection`; applying it succeeded.
- Verification: [repair preview](health-repair-preview-2026-10-08.json),
  [applied repair](health-repair-applied-2026-10-08.json) and
  [post-repair scan](health-after-repair-2026-10-08.json).
  The final scan exited 0 with zero findings.
- Disposition: workspace repair complete. Retain this as a real-use example of
  the canonical-repair boundary. Health already behaved safely; improved guidance
  for a missing historical target is a candidate usability improvement, not an
  assertion that health should invent missing records automatically.

## Observation 2: Requirements cannot yet govern work as native artifacts

- Task: plan the nine accepted outcomes and GitHub closeout using Roadmap.
- Commands: `roadmap milestone create`, `roadmap issue create`, `issue update`,
  `issue deps add`, `issue comment add`, `issue start` and `issue close`.
- Expected: use existing work planning immediately and retain traceability.
- Actual: 0.3.1 supports canonical issue/milestone operations and dependencies;
  requirements remain CSV governance records, without native lifecycle/linking.
- Workaround: include requirement IDs or maintenance rationale and the plan path
  in each new delivery item; populate CSV `linked_work_items` with actual IDs.
  Preserve source URLs and triage evidence in local GitHub work items. The
  generated [work-item view](0.4.0-work-items.md) is not a second status authority.
- Disposition: accepted native requirements work is planned under UR-049–UR-054,
  UR-062–UR-066 and associated technical requirements. Leave CSV authoritative
  until the verified cutover; do not fabricate native requirement records now.

## Observation 3: Local closure and remote closure have diverged

- Task: reconcile the dated 11-issue GitHub baseline with local work.
- Expected: identify the existing canonical item for each repository-qualified URL.
- Actual: six baseline reports have existing local IDs; two of those are locally
  closed while still open remotely. Five reports have no existing local mapping.
- Workaround: reuse all six matching IDs and reopen the two closed local items for
  evidence-backed triage; create five new triage records. Preserve their history
  and record exact source URLs. Add all 11 as prerequisites of the closeout item.
- Disposition: triage started, remote disposition pending. Do not infer that a
  local closed status fixes the report or closes GitHub. Capture remote failures
  separately and audit before retry, per UR-066/TR-053.

## Ongoing operating practice

Start work through the CLI; record reproduction, requirement/maintenance intent,
acceptance evidence and observations in the canonical issue. After changing
canonical records, run health; use repair previews before supported recovery or
projection actions. A manual repair must record why automation could not safely
infer the answer, its provenance and before/after evidence. Test new candidates
in workspace copies. At release review, account for friction disposition and
execute a complete self-hosted journey; coverage percentages do not replace it.

## Planning-pass verification

On 2026-10-08 the focused policy command passed **43 tests**:

```text
uv run --locked pytest -n 0 tests/policy/test_public_contract_inventory_policy.py tests/policy/test_requirement_verification_policy.py tests/policy/test_documentation_links.py tests/policy/test_architecture_contract_policy.py
```

A separate read-only audit confirmed 11 unique baseline mappings and exact source
URLs, pending remote dispositions, closeout dependencies, valid CSV work-item
links, and preservation of all 116 historical issue IDs, Markdown bodies,
creation timestamps and external identifiers. Only the six reconciled triage
issues changed; the other historical issue documents were unchanged. This is
planning/data verification, not verification of the new 0.4 feature outcomes.
