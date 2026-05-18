---
id: 610bbc26
title: roadmap health --details option not accepted by subcommands
headline: ''
priority: medium
status: todo
archived: false
issue_type: bug
milestone: backlog
labels: []
remote_ids: {}
created: '2026-05-13T17:00:16.180547+00:00'
updated: '2026-05-13T17:00:16.180550+00:00'
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

The top-level `roadmap health` help advertises a `--details` option, but subcommands don't accept it.

## Steps to reproduce
1. Run `roadmap health --help` - shows `--details` option
2. Run `roadmap health db-integrity --details`
3. Fails with: Error: No such option: --details

## Impact
Misleading help surface makes it harder to discover correct invocation patterns.
