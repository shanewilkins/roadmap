---
id: c0850c90
title: Fix broken sync between GitHub issues and roadmap folder
priority: high
status: done
issue_type: bug
milestone: ''
labels: []
github_issue: 3
created: '2025-10-11T19:48:01.356056+00:00'
updated: '2025-11-16T13:41:23.259381'
assignee: ''
estimated_hours: 8.0
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
