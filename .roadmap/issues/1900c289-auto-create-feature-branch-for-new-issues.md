---
id: 1900c289
title: Auto-create feature branch for new issues
priority: medium
status: done
issue_type: feature
milestone: v.0.2.0
labels:
- automation
- git-integration
- workflow
github_issue: 40
created: '2025-10-12T11:42:46.274786+00:00'
updated: '2025-11-16T13:41:23.308644'
assignee: shanewilkins
estimated_hours: 3.0
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
---

# Auto-create feature branch for new issues

## Description

Evaluate whether the roadmap CLI should automatically create a new feature branch in Git when starting work on a new issue. This would streamline the development workflow by ensuring each issue has its own dedicated branch for isolated development.

Currently, developers must manually create branches for issues. An automatic branch creation feature could:

- Enforce consistent branch naming conventions
- Ensure feature isolation and cleaner Git history
- Reduce setup overhead when starting new work
- Integrate with existing `roadmap issue start` command

However, there are considerations around:

- Branch naming strategies (feature/issue-id vs feature/issue-title)
- Handling of existing branches
- Developer preferences for branch management
- Integration with team workflows

## Acceptance Criteria

- [ ] Research existing branch creation patterns in the codebase
- [ ] Design configurable branch naming strategies
- [ ] Implement `--git-branch` flag for `roadmap issue start` command
- [ ] Add configuration option to enable/disable auto-branch creation
- [ ] Handle edge cases (existing branches, dirty working tree)
- [ ] Provide option to checkout the new branch automatically
- [ ] Update documentation with new workflow options
- [ ] Consider integration with GitHub flow vs Git flow patterns