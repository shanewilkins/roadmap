---
remote_ids: {}
handoff_notes: null
previous_assignee: null
handoff_date: null
git_commits: []
completed_date: null
github_issue: null
schema_version: 1
id: ee3aba55
created: '2026-05-13T16:59:51.025304+00:00'
updated: '2026-05-17T13:59:28.296231+00:00'
retention: visible
title: 'roadmap health fix crashes with TypeError: unexpected ''force'' keyword argument'
headline: The `roadmap health fix` command fails with a TypeError instead of applying
  fixes.
priority: critical
status: closed
issue_type: bug
milestone: backlog
depends_on: []
blocks: []
labels: []
assignee: shanewilkins
estimated_hours: null
due_date: null
progress_percentage: 100.0
actual_start_date: null
actual_end_date: null
git_branches: []
comments: []
history: []
---

The `roadmap health fix` command fails with a TypeError instead of applying fixes.

## Error
```
TypeError: OldBackupsFixer.apply() got an unexpected keyword argument 'force'
```

This occurs when running `roadmap health fix` (or with --yes flag).

## Steps to reproduce
1. Run `roadmap health fix`
2. Observe crash with TypeError about unexpected 'force' keyword

## Impact
Automatic health fixes are completely unavailable through the CLI.
