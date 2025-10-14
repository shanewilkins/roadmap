---
id: fcad6a99
title: Validate assignee is team member
priority: high
status: done
issue_type: feature
milestone: v.0.5.0
labels:
- security,validation,github-integration
github_issue: null
created: '2025-10-12T11:41:15.911050'
updated: '2025-10-14T14:16:47.394392'
assignee: shanewilkins
estimated_hours: 4.0
depends_on: []
blocks: []
actual_start_date: '2025-10-13T09:52:51.660500'
actual_end_date: null
progress_percentage: 0.0
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
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