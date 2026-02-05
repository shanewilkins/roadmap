---
id: 579887d7
title: 'docs: add comprehensive documentation for `issue start` command with git-branch
  flags'
headline: ''
priority: medium
status: todo
issue_type: other
milestone: backlog
labels:
- synced:from-github
remote_ids: {}
created: '2026-02-05T15:17:50.618446+00:00'
updated: '2026-02-05T15:17:50.618447+00:00'
assignee: null
estimated_hours: null
due_date: null
depends_on: []
blocks: []
actual_start_date: null
actual_end_date: null
progress_percentage: null
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
comments: []
github_issue: null
---

## Summary

This PR completes the documentation for the auto-branch feature by adding comprehensive documentation for the `roadmap issue start` command's git-branch integration flags in `docs/CLI_REFERENCE.md`.

## Background

The auto-branch feature (issue #1900c289) was already fully implemented in the codebase:
- Git integration with `checkout`, `force`, and template support
- CLI flags on both `issue create` and `issue start` commands
- Configuration model with `auto_branch` and `branch_name_template` settings
- Comprehensive test suite (6 tests, all passing)

However, while the `issue create` command was documented with its git-branch flags, the `issue start` command was missing documentation for its equivalent flags.

## Changes

Added a new section in `docs/CLI_REFERENCE.md` documenting `roadmap issue start` with:

**Command syntax and examples:**
```bash
# Start work and create a Git branch
roadmap issue start abc123 --git-branch

# Start with custom branch name
roadmap issue start abc123 --git-branch --branch-name "feat/custom-auth"

# Force branch creation even with uncommitted changes
roadmap issue start abc123 --git-branch --force
```

**Complete flag documentation:**
- `--date` - Specify start date (defaults to now)
- `--git-branch/--no-git-branch` - Create/skip git branch for the issue
- `--checkout/--no-checkout` - Control whether to checkout the created branch
- `--branch-name` - Override the suggested branch name
- `--force` - Force branch creation even if working tree has tracked modifications

**Behavior notes:**
- Sets issue status to `in-progress`
- Records `actual_start_date` for time tracking
- Respects `defaults.auto_branch` configuration
- Safe by default: won't create branch if working tree has tracked changes (unless `--force` is used)
- Untracked files don't block branch creation

**Example workflow** showing complete usage from issue creation through starting work with automatic branch creation.

## Testing

All existing tests continue to pass:
- ✅ 6 git integration tests (dirty tree, force flag, untracked files, templates, etc.)
- ✅ 41 core and CLI smoke tests
- ✅ Manual end-to-end verification of all documented features

## Related

This documentation complements the existing documentation for:
- `roadmap issue create` command with `--git-branch`, `--branch-name`, and `--force` flags
- Branch template configuration via `defaults.branch_name_template` in `.roadmap/config.yaml`
- Template placeholders (`{id}`, `{slug}`, `{prefix}`)

The auto-branch feature is now fully documented and ready for users to discover and use effectively.

<!-- START COPILOT CODING AGENT SUFFIX -->



<details>

<summary>Original prompt</summary>

> feat(auto-branch): auto-create feature branches for issues, add CLI flags and docs
>
> This PR implements the auto-branch feature and related improvements for v0.2 work.
>
> Summary of changes
>
> - CLI
>   - Added `--git-branch`, `--branch-name`, and `--force` flags to `roadmap issue create` and `roadmap issue start`.
>   - Improved user messages for branch creation outcome (created, checked out, skipped due to dirty tree).
>   - Backwards-compatible helpers to call `create_branch_for_issue` with different signatures.
>
> - Git integration
>   - `GitIntegration` accepts an optional `config` and `suggest_branch_name` uses `defaults.branch_name_template` if present.
>   - `create_branch_for_issue` now treats untracked-only working trees (??) as non-blocking and supports `force=True` to override tracked dirty state.
>   - Re-checks for `.git` directory dynamically in `is_git_repository()`.
>
> - Tests
>   - Added tests under `tests/test_git_integration/` for edge cases (dirty tree, existing branch checkout, branch template, force behavior, and untracked-only case).
>   - Updated existing tests to simulate `.git` where needed.
>
> - Docs
>   - Updated `docs/CLI_REFERENCE.md` with `--branch-name` and `--force` flags and configuration `defaults.branch_name_template`.
>
> - Misc
>   - Small compatibility fixes across CLI modules to ensure tests and older mocks work.
>
> Why
>
> This implements issue #1900c289: automatically create feature branches when creating or starting issues, with safe defaults and explicit CLI/config controls. It adds tests to verify behavior and updates docs for discoverability.
>
> Notes and follow-ups
>
> - Consider adding a `roadmap config set` subcommand to manage `defaults.auto_branch` and `branch_name_template` via CLI.
> - The PR intentionally uses conservative behavior: tracked changes block branch creation unless `--force` is used; untracked-only files do not block creation.
>
> Files changed (high-level)
> - `roadmap/git_integration.py`
> - `roadmap/cli/issue.py`
> - `roadmap/cli/git_integration.py`
> - `roadmap/cli/__init__.py`
> - `roadmap/models.py` (defaults entry)
> - `docs/CLI_REFERENCE.md`
> - `tests/test_git_integration/*` (new and adjusted tests)
>
> Please review and let me know if you'd like a different PR title or more granular commits.


</details>

Created from VS Code via the [GitHub Pull Request](https://marketplace.visualstudio.com/items?itemName=GitHub.vscode-pull-request-github) extension.

<!-- START COPILOT CODING AGENT TIPS -->
---

✨ Let Copilot coding agent [set things up for you](https://github.com/shanewilkins/roadmap/issues/new?title=✨+Set+up+Copilot+instructions&body=Configure%20instructions%20for%20this%20repository%20as%20documented%20in%20%5BBest%20practices%20for%20Copilot%20coding%20agent%20in%20your%20repository%5D%28https://gh.io/copilot-coding-agent-tips%29%2E%0A%0A%3COnboard%20this%20repo%3E&assignees=copilot) — coding agent works faster and does higher quality work when set up for your repo.

---
*Synced from GitHub: #45*
