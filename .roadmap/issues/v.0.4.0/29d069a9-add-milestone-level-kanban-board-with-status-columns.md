---
id: 29d069a9
title: Add milestone-level kanban board with status columns
headline: '# Add milestone-level kanban board with status columns'
priority: medium
status: closed
issue_type: other
milestone: v.0.4.0
labels:
- priority:high
- status:todo
- kanban
- milestone
- ui
remote_ids:
  github: '39'
created: '2026-01-02T19:20:52.737054+00:00'
updated: '2026-01-10T00:09:37.632254+00:00'
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
github_issue: '39'
---

# Add milestone-level kanban board with status columns

## Description

Implement a kanban board view at the milestone level that displays issues organized in four columns:

## Requirements

- **Overdue**: Issues past their due date that are not completed
- **Blocked**: Issues with status 'blocked' or dependencies that prevent progress
- **In Progress**: Issues currently being worked on (status 'in-progress')
- **Not Started**: Issues that haven't been started yet (status 'not-started')

## Acceptance Criteria

- [ ] Add new CLI command `roadmap milestone kanban <milestone_id>`
- [ ] Display issues in a visual board layout with 4 columns
- [ ] Color-code columns for better visual distinction
- [ ] Show issue titles, IDs, and key metadata in each card
- [ ] Support filtering and sorting within columns
- [ ] Responsive display that works in terminal environments
- [ ] Update existing milestone view to include kanban option

## Technical Notes

- Consider using rich library for enhanced terminal display
- Integrate with existing milestone and issue management
- Ensure performance with large numbers of issues
- Support both detailed and compact view modes
