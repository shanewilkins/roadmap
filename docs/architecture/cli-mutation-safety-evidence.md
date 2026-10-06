# Step one: CLI mutation-safety evidence

> Historical evidence from steps one/two. The open findings below were resolved
> in [step three](cli-correctness-closeout.md); this document preserves their
> original reproductions and verification results.

- Date: 2026-10-06.
- Scope: current CLI mutations, in support of the accepted
  [target interface](cli-interface-contract.md).
- Status: evidence pass completed; target-contract violations remain open for
  step three. This is not approval to claim all mutations meet the target.

## Test method

New CLI journeys use actual canonical documents and SQLite projections. Refusal,
preview, and declined confirmation cases compare persistent workspace file bytes,
including configuration, projection, backups, and transaction journals. Only
`canonical-write.lock` is excluded: it records ephemeral advisory-lock ownership.
The tests assert entity state and unchanged peers after successful mutations.
Successful retention tests also check the exact set of changed canonical files.

Git cases use real temporary repositories, isolated Git configuration, local
commits, and disabled test-repository hooks/signing. They inspect branch refs,
checkout state, canonical links, and preservation of uncommitted user files.
They do not contact remotes or modify the developer's repository.

No new skips or expected failures hide unmet contracts. Passing characterization
tests of legacy behavior are not proof that that behavior meets the preferred
interface. The targeted probes below explicitly record where it does not.

## Evidence matrix

Test IDs below are function names; parameterization supplies the listed variants.
The matrix distinguishes current CLI evidence from lower-layer evidence and
planned interface changes. It does not count a flag's presence in help as proof.

New mutation tests: [test_cli_mutation_contracts.py](../../tests/integration/cli/test_cli_mutation_contracts.py).
New real-Git tests: [test_cli_git_mutation_contracts.py](../../tests/integration/cli/test_cli_git_mutation_contracts.py).

| Surface / flags | Current behavioral evidence | Target status / limits |
|---|---|---|
| Issue create: title, type, priority, assignee, milestone, repeated labels, estimate, content, depends-on, blocks, print-id | `test_issue_creation_flags_and_reciprocal_dependencies`; `test_invalid_creation_never_leaves_entity_or_partial_reciprocal_link` | Persisted values, reciprocal edges, missing references, negative estimate and cycle refusal verified. New due-date field pending step three. |
| Issue update: title, priority, status, assignee, description, estimate, reason | `test_issue_field_options_persist_without_touching_other_entities`; `test_invalid_issue_update_preserves_all_persistent_state`; `test_update_reason_and_record_time_are_not_just_accepted_options` | Actual field/history writes and refusal verified. Clear fields, label maintenance and due dates pending. |
| Issue update --milestone | `test_issue_milestone_reassignment_changes_only_selected_relationship` | New assignment and old/new derived rollups verified, with unchanged milestone documents and peer issue. |
| Issue start --date; close --date/--record-time/--reason | `test_issue_dates_persist_exact_utc_or_refuse_without_writes`; `test_close_date_requires_time_recording_before_mutation`; `test_update_reason_and_record_time_are_not_just_accepted_options` | Date/date-time UTC values, invalid dates, required combinations, recorded reasons, and default completion time verified. |
| Issue progress PERCENTAGE | `test_progress_range_and_workflow_effects_are_persisted` | Reject out-of-range values; persist 0/35/100. Legacy 100% does not automatically close an issue; step three must document that distinction. |
| Issue block/unblock --reason | `test_block_unblock_reason_is_recorded_and_peer_unchanged` | History and workflow transitions verified; legacy unblock enters in-progress. |
| All entity archive/restore: explicit identity, all-closed/all, dry-run, confirmation | `test_retention_selection_confirmation_and_preview` (36 cases); `test_bad_retention_selectors_never_write` (18 cases) | Clean-workspace selection and persistent-state preservation verified. Prepared-transaction preview violates target: S1-01. New --yes pending. |
| All entity archive --force | `test_legacy_archive_force_overrides_lifecycle_guard_but_does_not_cascade` | Characterizes lifecycle override, not merely confirmation. Roster clarification required: S1-04. |
| Issue archive --orphaned/--list | `test_orphaned_archive_selection_and_list_mode_are_bounded` | Only unlinked issues selected; preview/list read-only in a clean workspace. |
| Issue restore --status | `test_restore_status_flag_selects_real_transition_without_touching_peer` | TODO/in-progress/closed transitions and previews verified. Invalid later-member batch transition covered in real-storage lifecycle tests. |
| All entity delete --yes | `test_delete_consent_does_not_bypass_archive_guard`; `test_delete_yes_preserves_referenced_archived_entity` | Decline, selected purge, visible-entity guard and inbound-reference guard verified through CLI. |
| Project/milestone close --force | `test_close_override_is_bounded_to_selected_parent` | Refusal without override and non-cascading forced completion verified. Separate project --yes pending. |
| Project create: title/description/repository; milestone create: title/description/due-date/project | `test_project_and_milestone_creation_fields_and_exact_parent` | Persisted fields, explicit parent and reciprocal relation verified. Project owner/priority and ID-only creation pending. |
| Project update: name/description/repository/status | `test_project_update_fields_persist_only_on_target` | Field writes and legacy inactive -> on-hold mapping verified. Completed status bypasses close guard: S1-02. Owner/priority/clear-owner pending. |
| Milestone update: name/description/due-date/project/status | `test_milestone_update_fields_and_reassignment_persist_atomically`; `test_invalid_milestone_update_preserves_state` | Dates, reciprocal project reassignment and refusal verified. Closed status bypasses close guard: S1-02. Clear fields pending. |
| Milestone assign ISSUE MILESTONE | Existing `TestCLIMilestoneAssign` cases in milestone CLI tests | Successful relationship assignment and missing issue/milestone refusal; lower-layer rollback evidence remains separate. |
| Issue deps add/remove/update; comments --author/--reply-to | Existing `test_comment_and_dependency_journey_retains_reciprocal_links_and_reply_parent` in CLI safety journeys | Reciprocal edits, cycle refusal, comment authors, reply parent and nonexistent reply refusal. |
| Config set/reset --project/--yes | `test_config_reset_yes_only_changes_selected_scope`; existing scoped config CLI journeys and configuration persistence tests | Scope isolation, declined reset, consent, validation and failed-replacement preservation. User reset removes its file to restore defaults. |
| Git branch --checkout/--no-checkout/--force | `test_git_branch_checkout_and_dirty_override_are_bounded` | Real refs, HEAD, links, dirty refusal and explicit dirty override verified; unrelated files untouched. |
| Issue create/start --git-branch/--branch-name/--force | `test_optional_git_failure_reports_committed_entity_without_retrying`; `test_unsafe_git_branch_name_never_creates_a_branch`; existing branch-notification CLI tests | Duplicate/unsafe branch refusal preserves prior canonical commit. Missing branch-action validation: S1-03. |
| Git link ISSUE | Existing `TestCLIGit.test_git_link_current_branch`; application/local-adapter tests | Real current-branch linking, no-repository refusal, fixed argv, timeout and executable failures. |
| Init name/project-name/description/skip-project/dry-run/force | Existing canonical initialization journeys and initialization application tests | Layout/first project, skip-project fixture, no-write preview and repeated initialization preservation. Reinitialization --force semantics and new --workspace need step-three clarification/implementation. |
| Migrate dry-run/yes | Existing migration CLI/persistence/process-recovery journeys; new `test_declined_migration_preserves_complete_legacy_workspace` | Full legacy-byte preservation on preview/decline, explicit execution, repeated no-op, conflict refusal, rollback and interrupted retry. |
| Cleanup keep/days/dry-run/force | Existing backup cleanup safety journeys | Age/group/tie selection, preview/decline, exact deletion, partial failure, symlink and directory-swap protection. New --yes and retained verbose explanations pending. |
| Health fix fix-type/dry-run/yes | Existing CLI safety journey and process recovery tests | Projection preview/decline/confirmed repair, recovery and unsupported repair refusal. Preferred narrowed choices and verbose explanations pending. |
| Retained --verbose and global --workspace | Approved target only | Not implemented or verified by this step. No ineffective switch is counted as supported behavior. |

Existing evidence sources:

- [CLI safety journeys](../../tests/integration/cli/test_cli_safety_journeys.py)
- [CLI usability and scope tests](../../tests/integration/cli/test_cli_usability.py)
- [Milestone CLI tests](../../tests/integration/cli/test_cli_milestone_commands.py)
- [Git CLI tests](../../tests/integration/cli/test_cli_data_and_git_commands.py)
- [Initialization journeys](../../tests/integration/cli/test_cli_initialization.py)
- [Migration journeys](../../tests/integration/cli/test_cli_migrate_command.py)
- [Backup cleanup safety](../../tests/integration/archive/test_backup_cleanup_safety.py)
- [Real-storage lifecycle and rollback](../../tests/integration/persistence/test_lifecycle_safety.py)
- [Process interruption/recovery](../../tests/integration/persistence/test_process_recovery.py)
- [Transaction validation and rollback](../../tests/unit/adapters/persistence/test_transaction_recovery.py)
- [Migration persistence](../../tests/unit/adapters/persistence/test_workspace_migration.py)
- [Local Git adapter](../../tests/unit/adapters/test_local_git_adapter.py)

## Open target-contract violations

### S1-01: preview can replay a prepared transaction

Priority: data-safety blocker for the dry-run promise.

Reproduction: prepare a valid canonical transaction changing an issue's title;
interrupt after journal preparation using the transaction failure injector and
`SystemExit`, leaving the canonical file unchanged. Run
`issue archive TARGET --dry-run` for that closed issue. Observed exit 0, changed
canonical title and consumed prepared journal. Entering a canonical unit of work
automatically runs recovery before the application checks dry-run.

Required step-three outcome: preview and failed validation must not replay
pending intent. Refuse with explicit recovery guidance or use a genuinely
read-only preview path. Reproduce pending recovery in permanent regression tests
when implementing the fix. Do not weaken crash-recovery guarantees for actual
mutations. Clean-workspace preview tests alone cannot establish this guarantee.

### S1-02: status updates bypass guarded close commands

Priority: governance/integrity blocker.

Reproduced `milestone update TARGET --status closed` with a TODO child issue:
exit 0 and parent closed, even though `milestone close` requires an override.
Independently reproduced a project with an OPEN child milestone: `project close`
declined with exit 1 after confirmation, while
`project update TARGET --status completed` exited 0 and completed the parent.
Children remained unchanged in both probes.

Required step-three outcome: enforce the same completion guards at the
application boundary for every entry point. An update flag must not serve as an
implicit override. Keep explicit close overrides bounded and test both routes.

### S1-03: branch-only flags can be silently ignored

Priority: invalid-request correctness.

Reproduced `issue start TARGET --branch-name ignored` without `--git-branch`:
exit 0, issue became in-progress, requested branch name did nothing.

Required step-three outcome: validate explicitly supplied branch-only flags
before canonical mutation; default checkout values must not trigger false
conflicts. Test create and start, both checkout spellings, branch-name and force.

### S1-04: archive force needs an explicit compatibility decision

Priority: roster/override correctness.

All three archive families use `--force` to allow non-completed entities in
addition to bypassing confirmation. The initial roster called those flags
confirmation-only. Replacing them with confirmation-only `--yes` would remove a
real capability or accidentally let consent bypass a guard.

Step three must explicitly decide whether to retain a separate lifecycle
override. Until then, keep live semantics and do not silently reinterpret the
old flag. The new tests characterize the existing override and its bounded
selection; they do not endorse combining override with consent.

## Verification

- Added 136 parameterized CLI cases: retention, selection, consent, overrides,
  mutation fields, dates, relationships, real Git operations and declined migration.
- Full suite: 833 passed; 79 existing Click isolated-filesystem deprecation warnings.
- Configured statement coverage: 95.21% (5,304 of 5,571 statements), above the
  unchanged 90% floor. No exclusions or instrumentation changes.
- After the fixture typing correction, 139 focused cases passed. Ruff, type,
  architecture, complexity and all configured pre-commit checks passed.
- Logs: `/tmp/roadmap-step1-full.log`, `/tmp/roadmap-step1-precommit.log`.
- Independent probe outcomes: `/tmp/roadmap-step1-probes.json`; reproducible
  setup and observed outcomes recorded above.

Statement coverage supports this evidence; it does not clear the four findings.
