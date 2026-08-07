---
id: 3c47370c
title: roadmap health scan fails with AttributeError - missing repositories
headline: 'The `roadmap health scan` command raises AttributeErrors instead of scanning
  entities:'
priority: high
status: closed
archived: false
issue_type: bug
milestone: backlog
labels: []
remote_ids: {}
created: '2026-05-13T16:59:59.818671+00:00'
updated: '2026-05-17T13:59:29.129852+00:00'
assignee: shanewilkins
estimated_hours: null
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
completed_date: null
comments: []
github_issue: null
---

The `roadmap health scan` command raises AttributeErrors instead of scanning entities:
- 'RoadmapCore' object has no attribute 'issue_repository'
- 'RoadmapCore' object has no attribute 'milestone_repository'
- 'RoadmapCore' object has no attribute 'project_repository'

After logging these errors, the command reports "No entities to report." - a success-like message despite internal failures.

## Steps to reproduce
1. Run `roadmap health scan`
2. Observe AttributeErrors in output

## Impact
Health scan cannot be trusted to detect roadmap inconsistencies.
