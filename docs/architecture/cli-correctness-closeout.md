# CLI correctness closeout

Implemented on 2026-10-06, following the reviewed
[interface contract](cli-interface-contract.md). The checked
[behavior matrix](cli-behavior-matrix.json) records every command and parameter,
its supported/deprecated disposition, choices, defaults, and journey evidence.
Most shared evidence is declared at command level; it does not claim every test
individually exercises every option. The safety-sensitive archive consent/force/
preview and migration/repair parameters now link directly to named assertion
journeys, including consent combined with dry-run. Policy checks require those
parameter references as well as live signatures and
parameter metadata to agree and all evidence IDs to exist. Help is evidence for
namespaces, not for mutation correctness.

## Reliability findings resolved

| Finding | Resolution | Regression journey in `test_cli_correctness_closeout.py` |
|---|---|---|
| S1-01: previews replayed recovery | Read-only units refuse pending transaction work; actual mutations retain automatic recovery. | `test_preview_refuses_pending_recovery_without_any_persistent_write` |
| S1-02: status update bypassed close guards | Project/milestone updates enforce the same open-child guards as close. | `test_status_update_cannot_bypass_close_guard` |
| S1-03: ignored branch-only options | Explicit branch options without branch action refuse before canonical mutation; defaults are exempt. | `test_branch_only_options_refuse_before_canonical_write` |
| S1-04: archive force misclassified | Keep its bounded lifecycle override; add independent consent. Warn on legacy force-as-consent through 0.3. | `test_yes_is_consent_and_does_not_override_archive_lifecycle` |
| S2-01: issue machine streams contained prose | Select representation before banners/workload summaries; empty lists return their schema. | `test_issue_json_is_whole_stream_even_when_empty` |
| S2-02: Rich changed/wrapped serialized values | Write serialized strings directly; plain issue inspection is literal, too. | `test_machine_output_preserves_arbitrary_cell_text`; `test_plain_issue_inspection_preserves_literal_content_and_history` |
| S2-03: mixed sort directions reversed primary groups | Stable sorts from the least significant key; each direction is independent, missing values last. | `test_mixed_direction_sort_preserves_primary_groups` |
| S2-04: parsed filters were silently ignored | Equality is supported; unsupported operators fail before query with replacement syntax. | `test_invalid_output_options_fail_independent_of_result_count` |
| S2-05: empty reports lost schemas/destinations | CSV retains headers; empty critical-path reports honor format, destination and overwrite refusal. | `test_empty_csv_retains_headers`; `test_empty_critical_path_honors_destination_and_overwrite_guard` |
| S2-06: empty results hid invalid options | Parse output options before querying; validate export enum filters in the application. | `test_invalid_output_options_fail_independent_of_result_count`; `test_export_rejects_invalid_enum_filters` |

The mutation tests use real canonical storage and compare persistent file bytes,
including configuration, projection and journals. The lock owner's diagnostic
metadata is intentionally excluded; previews still acquire a writer lock to
protect selection from concurrent writers. Git journeys use real temporary
repositories and inspect HEAD, refs, linked entities and worktree content.
Existing process tests still kill writers at actual journal/replace checkpoints,
retry recovery, refuse post-crash manual-edit overwrite, and test lock contention.

## Supported additions

Explicit selection identifies the workspace directory itself. Without it, normal
commands use the current directory's `.roadmap`; there is no automatic parent
workspace selection. Informational help/version does not require valid workspace
state. Explicit invalid/unreadable paths fail without fallback; preview initialization
creates no destination. Configuration schema/access preflight occurs before init
writes or preview. Custom workspace cache paths are added to its parent's gitignore.

```sh
roadmap --workspace /work/project/planning status --format json
roadmap --workspace /work/project/planning init --skip-project --dry-run
roadmap project create --title Example --owner alice --priority high --print-id
roadmap milestone create --title release-1 --project PROJECT_ID --print-id
roadmap issue create --title 'Ship feature' --due-date 2027-01-15 --print-id
roadmap issue update ISSUE_ID --clear-assignee --clear-estimate --clear-milestone
roadmap issue update ISSUE_ID --add-label ready --remove-label blocked
roadmap milestone update MILESTONE_ID --clear-project --clear-due-date
roadmap project update PROJECT_ID --clear-owner
roadmap issue view ISSUE_ID --format json
roadmap milestone progress MILESTONE_ID --method count_based
roadmap health scan --format json --output health-report.json
roadmap issue archive ISSUE_ID --yes --verbose
```

Omitted update fields stay unchanged. Explicit clear removes a value; setting
and clearing together refuses without writes. Label additions deduplicate while
preserving order; removing an absent label is harmless; add/remove overlap or
empty labels refuse. Clearing a milestone's project removes its reciprocal
project link atomically. Invalid dates/names are errors, including on preview.

Issue/project/milestone inspection JSON declares `schema_version: 1` and
`kind: roadmap.issue|project|milestone`, with `record` containing the application
query record/summary. Issue history is in `record.issue.history`; timestamps are
ISO strings, enums their persisted values, missing values JSON null. Milestone
inspection also returns the selected `issues`; its summary describes the whole
milestone. Use stdout as a complete JSON document.

Verbose explanations on archive/restore, cleanup, migrate and health fix go to
stderr and describe validated selection or completed stages. They do not change
stdout, validation, exit status or side effects. Debug shows unexpected traceback
information without locals. Status no longer hides unexpected failures behind a
concise-error wrapper; its unexpected errors reach the same debug handler.

Archive list mode refuses entity/batch selectors or mutation controls. Health
group options are valid on bare health only; flags before a subcommand refuse
with placement guidance. Neither combination silently ignores user intent.

Health summary-only retains counts and exit status while omitting detailed
findings in every format. Repair requires an explicit `projection` or `recovery`
target. After recovery, a stale projection is a separate bounded repair, not
silently included in a larger repair plan.

## Compatibility boundary

Deprecated spellings warn through the 0.3 series and are removed in 0.4. No version
bump or release is performed by this pass.

- Archive keeps `--force` to allow non-completed records. `--yes` never overrides
  the lifecycle guard. Archive and project close preserve their old force-as-consent
  shortcut temporarily with a warning; use `--force --yes` for both intentions.
- Restore/cleanup force aliases become `--yes`. Init's ineffective force,
  interactive/yes/template controls are deprecated; init is idempotent and does
  not overwrite existing canonical data or bypass schema validation.
- Unsupported verbose switches, health detail/group/show-ID/limit controls,
  cleanup backup/check controls and cosmetic kanban flags warn with guidance.
  Cleanup checks retain their useful read-only diagnosis until the boundary;
  those finding types are available in health scan.
- `critical-path --export` aliases `--format`, rejecting conflicting explicit
  representations. `milestone recalculate` aliases the read-only progress command.
- Health's legacy `--output plain|json|csv` still selects format and warns. Use
  `--format FORMAT --output PATH`; `./json` selects a file literally named json.
  This avoids silently reinterpreting old commands as file destinations.
- Legacy/unbounded health repair selections refuse with supported-target guidance.
  Bare health is the default scan; explicit check and db-integrity warn as aliases.
- Project update's `inactive` retains its documented mapping to persisted `on-hold`.
  Creation title/update name and comment-list text spelling remain supported.

## Verification

- Full suite: **1,094 passed**, with 79 existing Click isolated-filesystem
  deprecation warnings. Added 119 closeout CLI cases and two roster/evidence
  policy checks after the step-one and step-two suites.
- Configured statement coverage: **95.91%** (5,556 of 5,793 statements).
  The coverage floor remains 90%; no exclusions or instrumentation changes.
- All configured pre-commit checks passed: Ruff, ty, Import Linter/architecture
  guards, complexity, syntax and file checks. New untracked Python files were
  also checked explicitly with the exact Ruff configuration.
- Built wheel and clean-environment package smoke passed, including explicit
  workspace selection, project ID-only creation and lossless JSON inspection.
- Full temporary-workspace checkpoint journey passed: explicit migration/retry,
  projection/recovery repair, export, planning, comments, lifecycle and preservation checks.
- Logs: `/tmp/roadmap-step3-full.log`, `/tmp/roadmap-step3-precommit.log`,
  `/tmp/roadmap-step3-package.log`, `/tmp/roadmap-step3-journey.log`.

Coverage supports the reliability evidence above; it is not proof that all
possible unhappy paths have been exhausted. Compatibility retirement is a
scheduled release boundary, not unfinished implementation in this pass.
