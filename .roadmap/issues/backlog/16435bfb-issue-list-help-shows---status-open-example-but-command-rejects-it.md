---
id: 16435bfb
title: issue list help shows --status open example but command rejects it
headline: ''
priority: medium
status: todo
archived: false
issue_type: bug
milestone: null
labels: []
remote_ids: {}
created: '2026-05-13T17:00:43.246260+00:00'
updated: '2026-05-13T17:00:43.246263+00:00'
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
github_issue: null
---

The help text shows conflicting filter options for issue state.

## Steps to reproduce
1. Run `roadmap issue list --help` - shows `--open` option and generic `--status` example
2. Run `roadmap issue list --status open`
3. Fails with: Error: Invalid value for '--status': 'open' is not one of 'todo', 'in-progress', 'blocked', 'review', 'closed'

The valid statuses are workflow states (todo, in-progress, blocked, review, closed), but "open" is not one of them.

## Impact
Confusing help surface makes CLI harder to use.
