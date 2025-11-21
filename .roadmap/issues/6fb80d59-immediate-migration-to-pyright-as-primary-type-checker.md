---
id: 6fb80d59
title: Immediate Migration to Pyright as Primary Type Checker
priority: high
status: in-progress
issue_type: feature
milestone: v.0.5.0
labels: []
github_issue: null
created: '2025-11-17T03:04:27.550602+00:00'
updated: '2025-11-21T12:14:00.000000+00:00'
assignee: shane
estimated_hours: null
due_date: null
depends_on: []
blocks: []
actual_start_date: '2025-11-16T21:10:08.453716'
actual_end_date: null
progress_percentage: 40.0
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
---

# Immediate Migration to Pyright as Primary Type Checker

## Description

Replace MyPy with Pyright as the primary type checker for the roadmap project, implementing immediate migration rather than gradual adoption.

## Background

- Current MyPy configuration has 460 type errors across the codebase
- Pyright demonstrates superior error specificity (8 vs 24 errors on core.py)
- Modern VSCode integration with Pylance provides better developer experience
- Performance benefits and more accurate type inference

## Migration Phases

### Phase 1: Core Infrastructure Setup ✅

- [x] Update pyproject.toml to make Pyright primary type checker
- [x] Remove MyPy from CI/CD pipeline
- [x] Configure Pyright strict mode gradually by module
- [x] Update pre-commit hooks to use Pyright instead of MyPy

### Phase 2: Core Module Type Safety ✅

- [x] Fix type errors in roadmap/core.py (highest priority) - 8 errors fixed
- [x] Address type issues in roadmap/models.py - 3 errors fixed
- [x] Clean up roadmap/cli/core.py type annotations - 14 errors fixed
- [x] Resolve roadmap/persistence.py type problems - 3 errors fixed

### Phase 3: Extended Module Coverage

- [ ] Fix roadmap/analytics.py type errors
- [ ] Address roadmap/github_client.py type issues
- [ ] Clean up roadmap/git_integration.py annotations
- [ ] Resolve remaining CLI module type problems

### Phase 4: Full Codebase Compliance

- [ ] Address all remaining roadmap/ module type errors
- [ ] Update test files for type compatibility
- [ ] Configure strictest Pyright settings
- [ ] Document type checking standards

## Success Criteria

- [ ] Zero Pyright type errors across entire codebase
- [ ] CI/CD pipeline uses Pyright exclusively
- [ ] Developer tooling configured for optimal Pyright experience
- [ ] Performance maintained or improved over MyPy
- [ ] All pre-commit hooks updated to use Pyright

## Timeline

Target completion: End of v0.4.0 milestone

## Dependencies

- Pyright already installed and configured
- VSCode settings configured for Pylance
- Pre-commit infrastructure in place
