---
id: 40e4894a
title: Enhance health command with entity-level diagnostics
headline: '# Enhance health command with entity-level diagnostics'
priority: medium
status: todo
issue_type: feature
milestone: null
labels: []
remote_ids:
  github: '157'
created: '2026-01-09T21:31:15.885610+00:00'
updated: '2026-01-10T00:00:35.217103+00:00'
assignee: null
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
github_issue: '157'
---

Implement comprehensive health scanning to identify problematic entities and their issues.

## Features

### 1. New Command: roadmap health scan
Dedicated command for detailed entity health scanning with multiple output formats and filtering.

Flags:
- --output plain|json|csv (default: plain)
- --filter-entity issues|milestones|projects|comments|dependencies
- --filter-severity degraded|unhealthy
- --group-by entity|error-type (default: entity)

Exit Codes:
- 0 = HEALTHY (no issues found)
- 1 = DEGRADED (warnings, at-risk items)
- 2 = UNHEALTHY (critical failures, data corruption)

### 2. Entity-Level Diagnostics
Report detailed problems for each entity with ID, name, type, status, all validation errors, file path, malformed comments, missing descriptions, dependency problems, and risk factors.

### 3. Dependency Scanning
Checks for circular dependencies, broken references, self-dependencies, orphaned blockers, and deep chains (> 5 levels).

### 4. At-Risk Entity Detection
Issues/milestones past due, unassigned items, stale items, milestones with no issues, high-complexity items.

### 5. Output Formats
Plain text (human-readable), JSON (structured/piping), CSV (analysis/spreadsheet).

### 6. Integration with Recent Features
Report on description and comment issues including missing descriptions, malformed comments, threading errors, circular references.
