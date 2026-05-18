---
id: bd90cb26
title: Refactor close vs archive semantics
headline: '# Refactor close vs archive semantics'
priority: medium
status: closed
archived: false
issue_type: other
milestone: v1-0-2
labels: []
remote_ids:
  github: 3752
created: '2026-02-10T21:25:38.676310+00:00'
updated: '2026-05-18T17:14:13.359417+00:00'
assignee: shanewilkins
estimated_hours: null
due_date: null
depends_on: []
blocks: []
actual_start_date: '2026-05-18T17:02:10.727794+00:00'
actual_end_date: '2026-05-18T17:14:13.311720+00:00'
progress_percentage: 100.0
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
comments: []
github_issue: 3752
---

# Refactor close vs archive semantics

## Description

`roadmap issue close` and `roadmap issue archive` are intended to mean different things, but the current implementation still leaks active-issue persistence rules into the archive path. Closing an issue should only update workflow state on the active issue file. Archiving should be the separate cleanup operation that moves the issue markdown under `.roadmap/archive/issues/...`, marks the issue as archived for sync purposes, and keeps the issue out of active listings without recreating a second active copy.

Refactor the issue persistence and CLI archive flow so the close/archive split is explicit, stable, and covered by tests. The fix should preserve milestone-based folder structure for both active and archived issues and avoid regressions in restore behavior.

## Acceptance Criteria

- [x] `roadmap issue close <id>` only changes issue workflow state and completion metadata; it does not move the issue file into `.roadmap/archive/issues/` or mark the issue as archived.
- [x] `roadmap issue archive <id>` moves the issue markdown into the matching archive folder, marks the issue as archived, and does not recreate an active copy under `.roadmap/issues/`.
- [x] Archived issues continue to preserve milestone/backlog folder placement, and `roadmap issue restore` moves them back to the correct active folder while clearing the archived flag.
- [x] Regression tests cover the close/archive split and the no-duplicate-file behavior for archived issues.
