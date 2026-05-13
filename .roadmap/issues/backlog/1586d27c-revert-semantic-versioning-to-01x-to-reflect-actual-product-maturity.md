---
id: 1586d27c
title: Revert semantic versioning to 0.1.x to reflect actual product maturity
headline: ''
priority: high
status: todo
archived: false
issue_type: feature
milestone: null
labels: []
remote_ids: {}
created: '2026-05-13T17:11:31.378852+00:00'
updated: '2026-05-13T17:11:31.378854+00:00'
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

The package is currently versioned as 1.0+, but real-world usage reveals significant bugs and missing features that indicate the product is still in early development.

## Current Issues
- 10+ documented bugs (2 critical, 4 high priority)
- Core functionality broken (health scan, health fix)
- Inconsistent behavior (milestone indexing, ordering algorithms)
- Missing CLI features (dependency management incomplete, pagination controls missing)
- User-facing confusions (terminology, help text accuracy)

## Rationale for 0.1.x
- Signals 'alpha/beta' maturity to users
- Sets correct expectations for breaking changes
- Gives freedom to refactor without guilt (0.1 -> 0.2 breaking changes are acceptable)
- Aligns with the discovery phase we're still in

## Changes needed
1. Update version in pyproject.toml
2. Update CHANGELOG to reflect 0.1.0 release
3. Review and update README if it makes 1.0 stability claims
4. Tag release as pre-release on PyPI/GitHub

## Impact
Better user expectations, clearer communication about product maturity, healthier development velocity.
