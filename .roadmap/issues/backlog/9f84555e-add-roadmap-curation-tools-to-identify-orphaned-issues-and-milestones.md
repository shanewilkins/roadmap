---
id: 9f84555e
title: Add roadmap curation tools to identify orphaned issues and milestones
headline: ''
priority: medium
status: todo
issue_type: other
milestone: backlog
labels:
- data-management
- curation
- orphaned
- synced:from-github
remote_ids: {}
created: '2026-02-05T15:17:51.868061+00:00'
updated: '2026-02-05T15:17:51.868061+00:00'
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

# Add roadmap curation tools to identify orphaned issues and milestones

## Description

Implement comprehensive curation tools to help maintain roadmap data integrity by identifying and managing orphaned issues and milestones that lack proper organizational structure.

## Requirements

### Orphaned Issues Detection

- **Unassigned Issues**: Issues not assigned to any milestone or backlog
- **Categorization**: Group orphaned issues by type, priority, age, and assignee
- **Reporting**: Generate reports showing orphaned items with actionable recommendations

### Orphaned Milestones Detection

- **Unlinked Milestones**: Milestones not assigned to any roadmap
- **Analysis**: Identify patterns in orphaned milestones (completion status, dates, etc.)
- **Suggestions**: Recommend which roadmaps might be appropriate for orphaned milestones

## Acceptance Criteria

- [x] Add new CLI command `roadmap curate orphaned` to scan for orphaned items
- [x] Implement `roadmap curate issues` to show issues without milestone assignment
- [x] Implement `roadmap curate milestones` to show milestones without roadmap assignment
- [x] Display orphaned items with metadata (creation date, assignee, priority, etc.)
- [x] Provide batch operations to assign orphaned items to appropriate parents
- [x] Generate curation reports with statistics and recommendations
- [x] Add filtering options (by date, assignee, priority, type)
- [x] Include interactive mode for guided curation workflow

## Technical Notes

- Scan all `.roadmap/issues/`, `.roadmap/milestones/`, and `.roadmap/roadmaps/` directories
- Parse YAML frontmatter to determine parent-child relationships
- Consider "Backlog" as a valid milestone assignment (not orphaned)
- Performance optimization for large datasets
- Export curation results to various formats (JSON, CSV, Markdown)

## Future Enhancement (AI Integration)

- **TODO**: Intelligent categorization using AI to suggest appropriate milestone/roadmap assignments based on issue content, title, and context
- **TODO**: Automated tagging and priority suggestions for orphaned items
- **TODO**: Similarity analysis to group related orphaned items
