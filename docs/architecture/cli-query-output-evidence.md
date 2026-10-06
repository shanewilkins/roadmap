# Step two: CLI query and output evidence

> Historical evidence from steps one/two. The open findings below were resolved
> in [step three](cli-correctness-closeout.md); this document preserves their
> original reproductions and verification results.

- Date: 2026-10-06.
- Scope: current query/report options in the
  [accepted CLI interface](cli-interface-contract.md).
- Status: evidence pass; target violations listed below remain open for step
  three. This document does not certify the entire preferred interface.

## Method and evidence boundaries

The [new CLI tests](../../tests/integration/cli/test_cli_query_output_contracts.py)
seed distinguishing canonical records: different lifecycle scopes, assignees,
owners, statuses, priorities, issue types, milestone links, past/future dates,
searchable titles/headlines/bodies, and independent dependency chains. They use
real documents/projections and check exact IDs, ordering, values and totals.
Past/future dates are deliberately far apart to avoid wall-clock boundary flakes.

Query tests compare persistent workspace bytes as in step one. Configuration
scope tests additionally preserve user-configuration bytes outside the workspace.
Destination tests inspect written bytes, stderr acknowledgments, overwrite
refusal and preserved existing content. Byte comparisons use stdout bytes,
avoiding Click's text-result CRLF normalization when comparing CSV.

Issue selection tests parse the table fragment after the current prose prefix.
This proves record selection only: it explicitly does NOT prove whole-stdout
JSON validity. Independent whole-stream probes fail that separate contract.
Project/milestone and export JSON cases parse the entire stream for simple
fixtures. Adversarial values are also probed independently; do not extrapolate
simple-value format successes to all possible values.

No new skipped or expected-failure tests hide broken contracts. Permanent
regressions for the failing target cases belong alongside their step-three fixes.
Existing helper tests are supporting evidence, not substitutes for command wiring.

## Behavior matrix

All new test IDs below are in the linked query/output test module.

| Surface / options | Evidence test IDs | Verified scope / remaining limits |
|---|---|---|
| Issue list lifecycle --scope, --open, --blocked, --status, --priority, --issue-type | `test_issue_query_flags_select_exact_records_without_writes` | Exact visible/all/closed/archived and workflow/type/priority record sets. --scope visible includes visible closed issues; --open narrows them out. |
| Issue list --search, --overdue, --assignee, --my-issues and combinations | Same test | Case-insensitive Unicode title and body/headline search, due-date selection, identity and intersected filters. Selection evidence does not clear stdout pollution. |
| Issue list --backlog, positional backlog, --unassigned, --milestone, --next-milestone | Same test; `test_conflicting_issue_selectors_refuse_without_writes` | Exact milestone/backlog selection and incompatible-selector refusal. Legacy --unassigned is documented as a backlog alias, not an owner-null filter. |
| Project list --owner, --priority, --status, --overdue, --filter | `test_project_query_filters_and_intersections_are_exact` | Single fields, intersections, equality-filter combinations and empty JSON results. Non-equality filter operators remain broken: S2-04. |
| Milestone list --overdue/--filter | `test_milestone_filters_are_exact` | Exact overdue, name equality, date equality and combined selections. |
| Project/milestone --sort-by | `test_single_column_sort_order_is_exact` | Ascending/descending single keys, including sorting alongside column selection. Mixed directions fail: S2-03. |
| --columns and --format json/csv | `test_selected_columns_have_exact_order_and_values` | Exact column order and cell values. JSON retains full column definitions plus metadata.selected_columns; rows use the selected order. CSV readers ignore trailing blank lines. |
| Project/milestone --format rich/plain/json/csv/markdown | `test_list_formats_retain_records_for_simple_values` | All advertised formats retain simple records. JSON/CSV checked structurally; human formats checked for fixture content, not terminal layout. Rich rendering corrupts adversarial machine values: S2-02. |
| --columns/--sort-by/--filter/--format invalid names/directions | `test_bad_output_options_refuse_without_state_changes` | Nonzero errors without persistent changes when records exist. Empty issue results bypass validation: S2-06. |
| Data export --filter and json/csv | `test_export_filters_and_formats_have_exact_record_sets`; `test_invalid_export_filter_refuses_without_writes` | Every supported export filter key and exact scope tested; malformed syntax/unknown keys/invalid retention rejected. Invalid status enum remains silently empty: S2-06. |
| Export quotes/Unicode/labels/newlines | `test_export_preserves_quotes_unicode_and_newlines` | Complete JSON values and CSV title/encoded label values round-trip. CSV intentionally omits the content body. |
| Empty structured results | `test_empty_json_list_retains_schema_and_zero_counts`; `test_empty_export_keeps_versioned_json_schema` | Project/milestone JSON and export JSON retain structure. Issue lists, list CSV and empty analysis have defects: S2-05. |
| Data export/status --output, all existing format choices | `test_file_destination_matches_stdout_and_refuses_overwrite`; `test_invalid_report_destination_preserves_workspace` | Exclusive creation, file/stdout representation consistency, stderr acknowledgment, refusal of existing destinations, missing parents and directories. Rich status files use plain representation. |
| Status --format json | `test_status_counts_match_canonical_lifecycle` | Exact entity, visible workflow, archived and grand totals. |
| Health --filter-entity/--filter-severity, repeated values, --no-dependencies and json/csv | `test_health_filters_repeated_values_and_exit_status_are_exact` | Exact findings, OR within repeated selectors, severity totals, filtered exit status and empty findings. Current format spelling is --output; preferred spelling waits for step three. |
| Milestone view --status/--priority/--only-open | `test_milestone_view_repeated_filters_match_issue_selection` | OR within statuses, narrowing across fields, and explicit open selection. Structured single-record views remain planned. |
| Critical path --milestone/--include-closed/--export json | `test_critical_path_scope_and_closed_inclusion_are_exact` | Exact dependency chain, included IDs and total duration with independent milestone distractor. |
| Critical path --output with plain/json/csv | `test_critical_path_destination_refusal_preserves_existing_file` | Nonempty reports, complete JSON/CSV ID sequences, stderr destination acknowledgment and overwrite preservation. Empty report destination fails: S2-05. |
| Config view --level and explain --format | `test_config_view_levels_select_exact_scope_without_writes`; existing usability config-explanation tests | Exact user/project/merged YAML content and existing value/source JSON evidence; --project shorthand has existing scope evidence. |
| Terminal/color environment and machine output | `test_machine_output_is_stable_across_terminal_environment_flags` | Byte-stable simple project JSON, milestone CSV, status/config/export/health JSON under NO_COLOR, COLUMNS and ROADMAP_OUTPUT overrides. Does not clear long-value corruption. |
| Today current user / next milestone | `test_today_selects_current_identity_and_next_milestone_only` | Exact expected work and exclusion of other assignees/milestones. No new output flags added. |
| Derived milestone progress --method | `test_derived_progress_methods_have_distinguishable_results` | Count-based 50% versus effort-weighted 90% on the same real records, without writes. Preferred command rename pending. |

Other retained evidence:

- [CLI safety journeys](../../tests/integration/cli/test_cli_safety_journeys.py):
  status formats, read-only entity views, comments/replies, daily identity failure,
  critical-path export ordering, health summaries and repair previews.
- [CLI usability](../../tests/integration/cli/test_cli_usability.py):
  exact/ambiguous ID resolution, config defaults/sources, completion and no-workspace
  informational use.
- [Output-option unit tests](../../tests/unit/adapters/cli/test_output_options.py):
  parser validation and formatter selection. Parsed comparison operators alone
  are not evidence that the CLI applies them.
- [Output-model tests](../../tests/unit/adapters/cli/test_output_models.py):
  table column selection, metadata and sorting/filtering primitives.
- [Bootstrap policy tests](../../tests/policy/test_bootstrap_composition_policy.py):
  lazy loading and help/version without workspace construction.
- [Git CLI tests](../../tests/integration/cli/test_cli_data_and_git_commands.py):
  local Git status and branch inspection; no remote operations.

## Open target-contract violations

### S2-01: issue listings mix prose into machine stdout

Priority: machine-interface blocker.

`issue list --format json` succeeds but prints an issue-count banner before the
JSON. Assignee selections also print workload prose. Whole-stream `json.loads`
fails even for simple records. CSV likewise shares the stdout preamble.

Step three: choose representation before emitting prose. Keep machine stdout
exclusively machine-readable; move explanations to stderr or suppress them in
machine modes. Validate both ordinary and assignee-filtered lists.

### S2-02: Rich can reinterpret or wrap serialized data

Priority: output fidelity blocker.

With a project named `[red]Marked[/red]`, JSON listing returns `Marked`, losing
literal stored characters. A 200-character project name yields success but
invalid JSON because terminal wrapping inserts unescaped newlines into a string.
The shared decorator passes serialized JSON/CSV/Markdown through Console.print.

Step three: emit serialized text through a raw text stream, preserving data and
line endings independently of terminal width or markup. Keep Rich rendering
for explicitly human output. Add full round-trip tests for markup, long values,
Unicode, delimiters and embedded newlines in every applicable representation.

### S2-03: mixed-direction sort reverses the wrong groups

Priority: selection/report correctness.

With Alpha owned by bob and Beta/Zulu owned by alice,
`project list --sort-by owner:asc,name:desc --format json` produces
Alpha, Zulu, Beta. Required owner-ascending/name-descending order is
Zulu, Beta, Alpha. The model reverses the entire sorted row list rather than
applying directions independently to their respective keys.

Step three: implement stable multi-key direction handling. Test all four
ascending/descending pairs with ties and deterministic tie behavior.

### S2-04: advertised comparison filters are silently ignored

Priority: selection correctness.

`project list --filter 'owner!=alice' --format json` returns Alpha, Beta and Zulu
instead of only Alpha. The parser accepts comparison operators, but the CLI
decorator applies only equality and silently skips the others.

Step three: implement the advertised operators with documented type semantics,
or reject unsupported ones explicitly. Do not allow ignored filtering to return
success. Test operator behavior at the CLI, not only parser construction.

### S2-05: empty reports lose schemas and destinations

Priority: automation correctness.

- Empty issue JSON listing returns prose instead of a JSON collection.
- Empty project/milestone CSV listing emits no column header.
- Empty critical-path analysis requested as JSON with an output file returns
  prose on stdout, exits 0 and never creates the destination.

Step three: represent empty results in every structured schema, retain CSV
headers, and honor destinations even when no records exist. Destination refusal
must not depend on whether the report has data.

### S2-06: invalid values can succeed depending on results

Priority: validation correctness.

`issue list --search no-match --columns unknown --format json` exits 0 rather
than rejecting the unknown column. Its early empty-result return bypasses
output-option validation. Independently,
`data export --filter status=invalid --format json` exits 0 with zero issues.

Step three: validate output options before querying/rendering and validate
enum-valued export filters against their supported choices. Test the same
invalid options on zero, one and multiple results; no-data must not mask errors.

## Verification

- Added 140 parameterized CLI cases; all 140 passed in final focused verification.
- Full suite: 973 passed; 79 existing Click isolated-filesystem deprecation warnings.
- Configured coverage: 96.10% (5,354 of 5,571 statements); the floor stays 90%.
  No coverage exclusions, instrumentation changes or production changes in this step.
- All configured pre-commit checks passed, including Ruff, ty, architecture and
  complexity gates. Evidence test IDs and document links were verified.
- Logs: `/tmp/roadmap-step2-full.log`, `/tmp/roadmap-step2-focused.log`,
  `/tmp/roadmap-step2-precommit.log`.

Statement coverage does not certify output validity or clear the six findings.
Independent probe results are in `/tmp/roadmap-step2-probes.json`; setup and exact
outcomes are described above so the defects can become regression cases with
their step-three fixes. The date-equality probe passed and was added to the
positive milestone-filter evidence; it is not an open finding.
