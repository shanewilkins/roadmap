---
id: a3af7f22
title: Implement semantic versioning enforcement and PyPI publication
priority: high
status: done
issue_type: other
milestone: v.0.4.0
labels: []
github_issue: 22
created: '2025-10-14T15:46:41.872165+00:00'
updated: '2025-11-16T13:41:23.289950'
assignee: shanewilkins
estimated_hours: 16.0
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

# Implement semantic versioning enforcement and PyPI publication

## Description

Implement a robust semantic versioning system with automated enforcement and prepare the roadmap CLI tool for PyPI publication. This includes version validation, automated release workflows, and proper package configuration.

## Acceptance Criteria

- [ ] **Version Validation**: Implement semantic version validation (MAJOR.MINOR.PATCH format)
- [ ] **Version Consistency**: Ensure version is consistent across pyproject.toml, __init__.py, and changelog
- [ ] **Release Command**: Add `roadmap release` command for automated version bumping and changelog updates
- [ ] **PyPI Configuration**: Complete pyproject.toml with all required metadata for PyPI publication
- [ ] **Build Validation**: Ensure `poetry build` creates valid distribution packages
- [ ] **Pre-release Checks**: Validate tests pass, documentation is complete, and no uncommitted changes
- [ ] **Changelog Integration**: Automatic changelog generation for releases with issue summaries
- [ ] **Version Bump Logic**: Support patch, minor, major version increments with dependency impact analysis

## Technical Implementation

### Phase 1: Version Management System
1. Create `roadmap/version.py` module for centralized version handling
2. Add version validation functions (semantic version format checking)
3. Implement version consistency checker across files
4. Add version bump utilities (patch, minor, major)

### Phase 2: Release Command
1. Add `roadmap release` CLI command with options: `--patch`, `--minor`, `--major`
2. Pre-flight checks: tests, git status, documentation completeness
3. Automated changelog generation from completed milestones/issues
4. Git tagging and commit automation

### Phase 3: PyPI Publication Setup
1. Complete pyproject.toml metadata (description, keywords, classifiers, URLs)
2. Validate package build process (`poetry build`)
3. Test installation from built packages
4. Document publication workflow for maintainers

### Phase 4: Documentation and Validation
1. Create release documentation in docs/PYPI_PUBLICATION.md
2. Add version management to CLI reference
3. Test complete release workflow in development
4. Validate package functionality after installation

---
*Created by roadmap CLI*
Assignee: @shanewilkins
