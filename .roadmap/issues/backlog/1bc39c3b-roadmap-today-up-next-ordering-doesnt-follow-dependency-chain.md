---
id: 1bc39c3b
title: roadmap today Up Next ordering doesn't follow dependency chain
headline: The daily summary correctly switches milestone priority, but the Up Next
  list doesn't consistently s
priority: medium
status: closed
archived: false
issue_type: bug
milestone: backlog
labels: []
remote_ids: {}
created: '2026-05-13T17:00:28.695742+00:00'
updated: '2026-05-18T16:58:31.690430+00:00'
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

The daily summary correctly switches milestone priority, but the Up Next list doesn't consistently surface the actual critical-path blockers first.

## Steps to reproduce
1. Set up a roadmap with dependency chains
2. Run `roadmap today`
3. The "Up Next" list surfaces standalone items before critical blockers on the dependency path

## Impact
Daily queue can steer work toward non-optimal next tasks.
