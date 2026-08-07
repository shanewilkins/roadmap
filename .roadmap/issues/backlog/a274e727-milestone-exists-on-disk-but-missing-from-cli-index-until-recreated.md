---
id: a274e727
title: Milestone exists on disk but missing from CLI index until recreated
headline: The `sppm-semantic-completeness` milestone existed on disk (.roadmap/milestones/)
  and issues were qu
priority: high
status: closed
archived: false
issue_type: bug
milestone: backlog
labels: []
remote_ids: {}
created: '2026-05-13T17:00:09.347131+00:00'
updated: '2026-05-17T14:12:37.131688+00:00'
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

The `sppm-semantic-completeness` milestone existed on disk (.roadmap/milestones/) and issues were queryable, but was initially missing from normal CLI views.

## Steps to reproduce
1. `.roadmap/milestones/sppm-semantic-completeness.md` exists
2. `roadmap milestone list` does NOT show it
3. `roadmap milestone view sppm-semantic-completeness` returns "not found"
4. `roadmap issue list -m sppm-semantic-completeness` DOES return the milestone's issues

## Expected
All three commands should be consistent

## Workaround
Re-create the milestone via `roadmap milestone create` to make it appear in CLI views

## Impact
CLI can present inconsistent roadmap data vs file source of truth.
