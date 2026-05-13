---
id: 824e8932
title: issue deps only supports add operation, no remove or update
headline: ''
priority: medium
status: todo
archived: false
issue_type: bug
milestone: null
labels: []
remote_ids: {}
created: '2026-05-13T17:00:49.855210+00:00'
updated: '2026-05-13T17:00:49.855212+00:00'
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

The dependency management surface is incomplete - only exposes `add`, not `remove` or `update`.

## Steps to reproduce
1. Run `roadmap issue deps --help`
2. Only one subcommand: `add`
3. No way to remove or correct an incorrect dependency edge through the CLI

## Current Workaround
Manually edit `.roadmap/issues/*.md` files

## Impact
Roadmap maintenance becomes brittle when edge correction requires file edits.
