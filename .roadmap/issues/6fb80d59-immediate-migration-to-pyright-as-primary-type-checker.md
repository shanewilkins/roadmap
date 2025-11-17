---
id: 6fb80d59
title: Immediate Migration to Pyright as Primary Type Checker
priority: high
status: todo
issue_type: feature
milestone: 0.4.0
labels: []
github_issue: null
created: '2025-11-17T03:04:27.550602+00:00'
updated: '2025-11-17T03:04:27.550933+00:00'
assignee: shane
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

### Phase 1: Core Infrastructure Setup

- [ ] Update pyproject.toml to make Pyright primary type checker
- [ ] Remove MyPy from CI/CD pipeline
- [ ] Configure Pyright strict mode gradually by module
- [ ] Update pre-commit hooks to use Pyright instead of MyPy

### Phase 2: Core Module Type Safety

- [ ] Fix type errors in roadmap/core.py (highest priority)
- [ ] Address type issues in roadmap/models.py
- [ ] Clean up roadmap/cli/core.py type annotations
- [ ] Resolve roadmap/persistence.py type problems

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
