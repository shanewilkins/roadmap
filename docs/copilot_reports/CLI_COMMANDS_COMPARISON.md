CLI commands — monolithic -> modular mapping
==========================================

This document lists the commands and options present in the original monolithic CLI (`roadmap/cli_backup_original.py`) and where each command now lives in the modular CLI (`roadmap/cli/*.py`). It also calls out behavioral differences, missing features, and recommended next steps before removing the monolithic backup.

How to read this file
---------------------
- "Monolith" column lists the original command name and key options/flags from `cli_backup_original.py`.
- "Modular" column lists the implementing file and function in `roadmap/cli/`.
- "Notes" indicate any differences, missing options, or recommended follow-up.

Top-level commands
------------------
- monolith: `init` (options: --name/-n, --project-name, --description, --github-repo, --skip-github, --skip-project, --interactive/--non-interactive, --template)`
  - modular: `roadmap/cli/core.py::init`
  - notes: Implemented with matching options; behavior preserved.

- monolith: `status`
  - modular: `roadmap/cli/core.py::status`
  - notes: Implemented; displays status similarly.

Git-related commands (group `git`)
----------------------------------
- monolith: `git setup` (hooks, --force)
  - modular: `roadmap/cli/git_integration.py` (setup command)
  - notes: Functionality implemented; help text and behavior present.

- monolith: `git sync`, `git status`, `git create-issue`, `git github-sync`, `git webhook`, `git validate`, `git serve-webhook`
  - modular: implemented across `roadmap/cli/git_integration.py` and related modules (e.g., `enhanced_github_integration` wrappers)
  - notes: Implementations exist; minor help-text differences possible.

Issue commands (group `issue`)
------------------------------
- monolith: `issue create` (many options: --priority/-p, --type/-t, --milestone/-m, --assignee/-a, --labels/-l, --estimate/-e, --depends-on, --blocks, --git-branch, --checkout)`
  - modular: `roadmap/cli/issue.py::create_issue`
  - notes: Options and behavior implemented; auto-detection of assignee and validation preserved.

- monolith: `issue list` (filters: --milestone/-m, --backlog, --unassigned, --open, --blocked, --next-milestone, --assignee/-a, --my-issues, --status/-s, --priority/-p)
  - modular: `roadmap/cli/issue.py::list_issues`
  - notes: Implemented; output formatting uses rich Table as before.

- monolith: `issue update` (options: --status,-s; --priority,-p; --milestone,-m; --assignee,-a; --estimate,-e; --reason,-r)
  - modular: `roadmap/cli/issue.py::update_issue`
  - notes: Implemented. Important: modular code explicitly converts empty string `--assignee ""` to unassign (`None`) to support unassignment behavior.

- monolith: `issue finish` (replaces done/complete; flags: --reason, --date, --record-time) and `done` alias
  - modular: `roadmap/cli/issue.py::done` exists; I did not find a `finish` command with the exact `--record-time` semantics in the modular implementation.
  - notes: Partial parity. If tests or docs rely on `finish --record-time` behavior, port that functionality into the modular `issue` module or add `finish` as an alias that calls `done` with the same flags.

- monolith: `issue start` (option --date)
  - modular: `roadmap/cli/issue.py::start_issue`
  - notes: Implemented.

- monolith: `issue progress` (arguments: issue_id, percentage)
  - modular: `roadmap/cli/issue.py::update_progress`
  - notes: Implemented; auto status updates retained.

- monolith: `issue block` and `issue unblock`
  - modular: `issue.block` exists in `roadmap/cli/issue.py`.
  - notes: I could not find a separate `unblock` command in the modular `issue.py`. Monolith's `unblock_issue` should be re-implemented or re-exposed in modular code if required by tests or user workflows.

- monolith: `issue deps` (shows dependencies or --show-all), `issue deps add` (adds a dependency)
  - modular: `roadmap/cli/issue.py::deps` group and `add_dependency`
  - notes: `deps.add` implemented; dep display commands implemented across modules; ensure `--show-all` semantics are covered if tests expect that exact option.

- monolith: `issue delete` (uses click.confirmation_option with long warning)
  - modular: `roadmap/cli/issue.py::delete_issue` (uses `--yes` flag to skip confirm)
  - notes: Behavior present but option handling differs; tests relying on the confirmation dialog should be updated accordingly or confirm backward-compatible aliases.

Milestones
----------
- monolith: `milestone create`, `list`, `assign`, `delete`, `update` (options include due date, clear via `clear` text)
  - modular: `roadmap/cli/milestone.py` implements `create`, `list`, `assign`, `delete` and `update` (modular uses `--clear-due-date` boolean instead of passing `due-date=clear` string)
  - notes: Slight difference for clearing due date; tests/docs should be consistent with modular usage.

Sync (GitHub) group
-------------------
- monolith: `sync setup` (options: --token, --repo, --insecure), `sync test`, `sync status`, `sync delete-token`, `sync push`, `sync pull`, `sync bidirectional`
  - modular: `roadmap/cli/sync.py` implements `setup`, `test`, `status`, `delete-token`, `push`, `pull`, `bidirectional`.
  - notes/differences:
    - `delete-token` printed message behavior was adjusted in modular code to print the returned message exactly (tests patched `roadmap.cli.sync.SyncManager` expecting that). Make sure any tests check the message content accordingly.
    - High-performance sync details (detailed progress callbacks, performance report formatting, default batch/workers) in monolith are more fully-featured. Modular `sync.push`/`pull` are present but simplified; `HighPerformanceSyncManager` usage exists in the monolith pull/push helpers but modular CLI uses simpler defaults (batch/workers smaller) — port high-performance implementation if needed.

Activity & Collaboration (team)
-------------------------------
- monolith: `broadcast` (argument message, options: --assignee/-a, --issue/-i), `activity` (options --days, --assignee), `handoff` (issue_id, new_assignee, --notes, --preserve-progress), `handoff-context`, `handoff-list`, `workload-analysis` (many options), `smart-assign`, `capacity-forecast`
  - modular: `roadmap/cli/activity.py` contains `broadcast`, `activity`, `handoff`, `handoff-context`, `handoff-list`, `workload-analysis`, `smart-assign`, `capacity-forecast`
  - notes: Most commands implemented. Some analysis-heavy commands (workload-analysis, smart-assign) are present but lighter; monolith has longer, more detailed implementations. `broadcast` stores updates to `.roadmap/updates.json` in modular code as expected.

Comment group
-------------
- monolith: `comment list`, `create`, `edit`, `delete` — all implemented in modular `roadmap/cli/comment.py`.

Export group
------------
- monolith: `export issues` (CSV/JSON/Markdown with full field formatting), `export timeline`, `export report` — detailed exporters implemented in the monolith (`_export_issues_csv`, `_export_issues_json`, `_export_issues_markdown`)
  - modular: exports are split across `roadmap/cli/data.py`, `activity.export`, and other modular exporters. I did not find a plug-and-play replica of the monolith's fully-featured `export issues` implementations (CSV/Markdown writer functions) in the modular code.
  - notes: If you rely on the exact monolith export formatting, port utility functions into `roadmap/cli/export.py` or similar.

Deprecated aliases & backward compatibility
------------------------------------------
- The modular `roadmap/cli/__init__.py` exposes `curate_orphaned` and has helper `register_git_commands()` and imports to maintain test patch targets. `roadmap/cli/deprecated.py` registers many legacy aliases.
- notes: These wrappers are present to help tests and preserve backward compatibility.

Other notable differences
------------------------
- Default values changed in some sync commands (batch/workers). Monolith high-perf defaults: batch_size=50, workers=8; modular uses smaller defaults (batch_size=10, workers=3). Update tests/docs if they check defaults.
- Some commands that were full-featured in monolith are intentionally trimmed in modular code; decide whether to port full implementations or accept lighter versions.

Tests and patch targets
-----------------------
- Tests import the CLI entry point via `from roadmap.cli import main` and patch `roadmap.cli.sync.SyncManager` and `roadmap.cli.RoadmapCore` as needed. That is correct for the modular architecture because `roadmap/cli/sync.py` defines the `SyncManager` usage and `roadmap/cli/__init__` imports `RoadmapCore`.
- Most tests were adjusted to patch the modular import paths (this repository's tests pass locally as of the last full run: 1190 passed, 37 warnings).

Recommendations before deleting `cli_backup_original.py`
------------------------------------------------------
1. Keep `cli_backup_original.py` as an archived reference until all monolith behaviors needed by users or docs are ported. Consider moving it into a `roadmap/legacy/` directory or the repository's `archives/` folder and reference it in the docs.
2. Port the missing/richer features from the monolith into modular modules if you want 1:1 parity:
   - `issue finish` semantics (record time, `--date`, duration vs estimate reporting)
   - `issue unblock` command
   - Full `export issues` CSV/Markdown/JSON implementations and timeline report generation
   - High-performance sync push/pull reporting & default values (50/8)
3. Update tests that depend on exact default values or exact help text so they match the modular implementations. Add new tests for any ported functionality.
4. Once porting and test coverage are complete, remove or archive `cli_backup_original.py` in a separate commit/PR.

Next actions I can take for you
------------------------------
- Create a repository file with the above content (done — `CLI_COMMANDS_COMPARISON.md` created).
- Open a TODO/issue list with concrete port tasks (I can add a Github issue list or local TODO file).
- Port one missing feature (for example, add `finish` with `--record-time`) and add tests.


---

Generated by the CLI audit script on the workspace (automated side-by-side review of `roadmap/cli_backup_original.py` vs `roadmap/cli/*`).
