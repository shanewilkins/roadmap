---
id: 122f1222
title: CLI emits unnecessary OpenTelemetry warning on basic commands
headline: ''
priority: low
status: todo
archived: false
issue_type: bug
milestone: backlog
labels: []
remote_ids: {}
created: '2026-05-13T17:00:36.120315+00:00'
updated: '2026-05-13T17:00:36.120318+00:00'
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

Routine commands emit an unrelated warning about missing OpenTelemetry dependencies.

## Example
On `roadmap issue list --help`:
```
[ WARNING] roadmap.common.observability.otel_init: opentelemetry_not_available |
detail=Tracing features will be disabled. Install with: pip install opentelemetry-exporter-jaeger
error=No module named 'opentelemetry.exporter.otlp'
```

This warning appears for commands that don't use tracing and adds noise to normal output.

## Impact
Noise/UX issue, but doesn't break functionality.
