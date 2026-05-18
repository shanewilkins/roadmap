---
id: 23bd7845
title: milestone view shows pagination indicator but provides no way to navigate pages
headline: ''
priority: low
status: todo
archived: false
issue_type: bug
milestone: backlog
labels: []
remote_ids: {}
created: '2026-05-13T17:00:56.483920+00:00'
updated: '2026-05-13T17:00:56.483924+00:00'
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

When viewing a milestone with > 10 items, the CLI shows pagination but offers no way to view subsequent pages.

## Steps to reproduce
1. Run `roadmap milestone view <id>` where milestone has > 10 items
2. Output shows pagination indicator
3. No `--page` option or pagination controls available

## Current Workaround
Filter with `roadmap issue list -m <id>`

## Impact
Low - Workaround is available but pagination feature is incomplete.
