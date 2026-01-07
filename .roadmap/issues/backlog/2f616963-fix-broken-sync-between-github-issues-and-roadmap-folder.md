---
id: 2f616963
title: Fix broken sync between GitHub issues and roadmap folder
priority: medium
status: closed
issue_type: other
milestone: null
labels:
- priority:high
- status:done
remote_ids:
  github: 3
created: '2026-01-02T19:20:53.427910+00:00'
updated: '2026-01-06T22:07:59.939541+00:00'
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
github_issue: 3
---

# Fix broken sync between GitHub issues and roadmap folder

## Description

The synchronization between GitHub issues and the local `.roadmap/issues/` folder is currently broken. This is a critical feature that allows the roadmap tool to maintain consistency between local project tracking and remote GitHub issue management.

## Problem Details

- **Sync Commands Not Working**: The `roadmap sync` commands may not be properly updating local issues from GitHub
- **GitHub Integration Issues**: Issues created locally may not be properly pushed to GitHub
- **Data Consistency**: Local and remote issue states are becoming out of sync
- **Core Functionality Impact**: This breaks one of the main value propositions of the roadmap tool

## Expected Behavior

- `roadmap sync pull` should fetch GitHub issues and update local `.roadmap/issues/` files
- `roadmap sync push` should create/update GitHub issues from local files
- `roadmap sync` (bidirectional) should keep both sides in sync
- Issue metadata should be properly mapped between GitHub and local formats

## Investigation Areas

1. **GitHub API Integration**: Verify GitHub client authentication and API calls
2. **Sync Manager Logic**: Check the sync algorithms and conflict resolution
3. **Data Mapping**: Ensure proper conversion between GitHub issue format and local YAML frontmatter
4. **Error Handling**: Improve error reporting when sync operations fail

## Acceptance Criteria

- [ ] `roadmap sync pull` successfully fetches and updates local issues from GitHub
- [ ] `roadmap sync push` successfully creates/updates GitHub issues from local files
- [ ] Bidirectional sync maintains data consistency
- [ ] Proper error handling and user feedback for sync operations
- [ ] Documentation updated with current sync behavior and troubleshooting

---
*Created by roadmap CLI*
Assignee: @shanewilkins
