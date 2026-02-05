---
id: e3104cef
title: Add GitHub issue ID cross-referencing and manual sync
headline: ''
priority: medium
status: todo
issue_type: other
milestone: backlog
labels:
- synced:from-github
remote_ids: {}
created: '2026-02-05T15:17:51.717929+00:00'
updated: '2026-02-05T15:17:51.717929+00:00'
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

Implement GitHub issue ID cross-referencing with manual sync capability

## Overview
Enable tracking and linking of GitHub issue IDs with internal roadmap issues. Store GitHub issue ID as metadata and provide commands for cross-referencing.

## Phase 1: Manual Sync (this issue)
No automatic syncing - user-driven, explicit linking only.

## Features to Implement

### 1. Issue Model Enhancement
- github_issue field already exists (int | None)
- Update YAML serialization to include github_issue in metadata
- Add validation for github_issue (positive integer)

### 2. CLI Commands

#### Link GitHub ID to Issue
```bash
roadmap issue link <internal-id> --github-id <number>
```
- Update issue with GitHub ID
- Store in both DB and YAML file
- Validation: ID must be positive integer

#### Lookup Issue by GitHub ID
```bash
roadmap issue lookup-github <github-id>
```
- Find internal issue by GitHub ID
- Return: ID, title, status, priority, milestone
- Error if not found

#### Manual Sync from GitHub
```bash
roadmap issue sync-github <internal-id>
```
- Fetch GitHub issue details via API
- Update: title, description, labels, state
- Show diff of changes (don't auto-apply)
- User confirms before updating

### 3. Display Enhancements
- Add `--show-github-ids` flag to `roadmap list`
- Add `--show-github-ids` flag to `roadmap issue view`
- Show GitHub ID in issue detail view by default

### 4. Issue Creation
- Add optional `--github-id <number>` to `roadmap issue create`
- Link GitHub ID during creation

## Implementation Details

### GitHub API Integration
- Use PyGithub or similar library (check dependencies)
- Require GitHub token (env var: GITHUB_TOKEN)
- Handle missing token gracefully (just skip GitHub features)
- API calls only on-demand (no background polling)

### Data to Sync (Phase 1)
- Title
- Description/body
- Labels
- State (open/closed)
- Assignees

### Error Handling
- GitHub ID already linked to different issue → error
- GitHub ID doesn't exist → warning
- API errors → clear message
- Missing GitHub token → skip gracefully

### Testing Requirements
- Unit tests for GitHub API integration
- Integration tests for link/lookup commands
- Mock GitHub API responses
- Test bidirectional lookup
- Test validation (invalid IDs, duplicates)

## Future Work (Phase 2)
- Automatic bi-directional sync
- Sync on specific triggers (scheduled job, webhook)
- Conflict resolution (changes in both systems)
- Sync milestones and projects to GitHub labels/projects

## Success Criteria
✅ Can link GitHub ID to issue and persist it
✅ Can look up issue by GitHub ID
✅ Can manually sync GitHub issue details
✅ GitHub ID shown in list/view with flag
✅ All existing tests pass
✅ 100% test coverage for new code
