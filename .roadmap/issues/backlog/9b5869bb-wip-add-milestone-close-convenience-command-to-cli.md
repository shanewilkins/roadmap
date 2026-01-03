---
id: 9b5869bb
title: '[WIP] Add milestone close convenience command to CLI'
priority: medium
status: closed
issue_type: other
milestone: null
labels: []
github_issue: 49
created: '2026-01-02T19:20:53.618250+00:00'
updated: '2026-01-03T17:47:02.199326+00:00'
assignee: shanewilkins
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
---

Implementation of `roadmap milestone close` convenience command and test:

- [x] Verify existing code in `roadmap/cli/milestone.py` - `close` subcommand exists (lines 180-208)
- [x] Verify test in `tests/test_cli/test_milestone_close.py` - test exists and passes
- [x] Verify `milestone update --status open|closed` option - implemented on line 215
- [x] Run existing tests to ensure all milestone tests pass (14/14 passed)
- [x] Manually verify `milestone update --status closed` works correctly
- [x] Identify bug with `--name` option in update command (causes "got multiple values for argument 'name'" error)
- [ ] Fix the `--name` bug in milestone update command
- [ ] Run linting to ensure code quality
- [ ] Final verification of all changes

Current Status:
The core functionality requested (milestone close command and --status option) is already fully implemented and working. Tests pass. However, there's an unrelated bug with the --name option in the update command that should be fixed.

<!-- START COPILOT CODING AGENT SUFFIX -->



<details>

<summary>Original prompt</summary>

> cli: add 'milestone close' convenience command and test
>
> This PR adds a convenience `roadmap milestone close <NAME>` command to quickly mark a milestone closed from the CLI. It includes:
>
> - `roadmap/cli/milestone.py` - new `close` subcommand with confirmation and `--force` to skip prompt. It uses `core.update_milestone(..., status=MilestoneStatus.CLOSED)` and prints success/failure.
> - `tests/test_cli/test_milestone_close.py` - a unit/CLI test that creates a milestone and then closes it with `--force`, verifying the milestone is listed as closed.
>
> Notes:
> - The PR includes a small fix to the existing `milestone update` command to accept `--status open|closed`.
>
> Please review and let me know if you'd like an alias `roadmap milestone done` or an interactive option.


</details>

Created from VS Code via the [GitHub Pull Request](https://marketplace.visualstudio.com/items?itemName=GitHub.vscode-pull-request-github) extension.

<!-- START COPILOT CODING AGENT TIPS -->
---

💡 You can make Copilot smarter by setting up custom instructions, customizing its development environment and configuring Model Context Protocol (MCP) servers. Learn more [Copilot coding agent tips](https://gh.io/copilot-coding-agent-tips) in the docs.
