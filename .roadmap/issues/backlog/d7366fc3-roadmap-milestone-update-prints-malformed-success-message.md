---
id: d7366fc3
title: roadmap milestone update prints malformed success message
headline: Updating a milestone succeeds, but prints a malformed success message.
priority: low
status: closed
archived: false
issue_type: bug
milestone: backlog
labels: []
remote_ids: {}
created: '2026-05-13T17:00:22.230958+00:00'
updated: '2026-05-18T15:23:00.038159+00:00'
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

Updating a milestone succeeds, but prints a malformed success message.

## Steps to reproduce
1. Run `roadmap milestone update <id>`
2. Update applies correctly
3. But CLI prints: "Updated bool: Untitled" (or similar malformed output)

## Expected
"Updated milestone: <name>"

## Impact
Output is misleading but functionality works.
