---
id: 74865b30
title: Validate assignee is team member
headline: ''
priority: medium
status: todo
issue_type: other
milestone: backlog
labels:
- synced:from-github
remote_ids: {}
created: '2026-02-05T15:17:49.157182+00:00'
updated: '2026-02-05T15:17:49.157183+00:00'
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

# Validate assignee is team member

## Description

When assigning an issue to someone using the `--assignee` flag, we need to validate that the assignee is a valid GitHub user ID who is listed as a team member, collaborator, or contributor in the repository. This should prevent assignment to invalid users and ensure proper access control.

Currently, the system accepts any string as an assignee without validation, which could lead to:
- Issues assigned to non-existent users
- Issues assigned to users without repository access
- Security concerns around unauthorized assignments

## Acceptance Criteria

- [ ] Validate assignee exists as a GitHub user
- [ ] Check if assignee has repository access (collaborator/team member)
- [ ] Provide clear error messages for invalid assignments
- [ ] Cache team member list for performance
- [ ] Support both username and GitHub user ID formats
- [ ] Integration with existing GitHub API client
- [ ] Update CLI help documentation with validation requirements

---
*Synced from GitHub: #38*
