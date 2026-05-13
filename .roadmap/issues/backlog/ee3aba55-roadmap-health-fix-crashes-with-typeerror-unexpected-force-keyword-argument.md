---
id: ee3aba55
title: 'roadmap health fix crashes with TypeError: unexpected ''force'' keyword argument'
headline: ''
priority: critical
status: todo
archived: false
issue_type: bug
milestone: null
labels: []
remote_ids: {}
created: '2026-05-13T16:59:51.025304+00:00'
updated: '2026-05-13T16:59:51.025313+00:00'
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
