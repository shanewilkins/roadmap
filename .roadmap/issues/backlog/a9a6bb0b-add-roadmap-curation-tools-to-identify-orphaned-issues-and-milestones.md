---
id: a9a6bb0b
title: Add roadmap curation tools to identify orphaned issues and milestones
priority: high
status: closed
issue_type: feature
milestone: ''
labels:
- curation
- data-management
- orphaned
remote_ids:
  github: 165
created: '2025-10-13T08:47:02.916590+00:00'
updated: '2025-10-14T10:58:00+00:00'
assignee: shanewilkins
estimated_hours: 6.0
due_date: null
depends_on: []
blocks: []
actual_start_date: null
actual_end_date: null
progress_percentage: 100.0
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: '2025-10-14T10:58:00.000000'
comments: []
github_issue: 165
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
