---
id: eac05773
title: Implement team onboarding architecture - project detection on init
priority: high
status: completed
issue_type: other
milestone: v0.7.0
labels: []
github_issue: null
created: '2025-12-05T00:03:01.538842+00:00'
updated: '2025-12-05T00:03:01.538848+00:00'
assignee: shanewilkins
estimated_hours: null
due_date: null
depends_on: []
blocks: []
actual_start_date: null
actual_end_date: null
progress_percentage: 100
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits:
  - "24c5b47"
completed_date: null
---

# Implement team onboarding architecture - project detection on init

## Problem
Currently, when team members clone an existing repository and run `roadmap init`, they create a NEW project instead of joining the EXISTING shared project. This breaks collaboration because different team members have different project files in `.roadmap/projects/`.

## Solution: Option A - Projects as Committed Team Artifacts
Projects should be committed to git and detected during init, not generated locally.

## Implementation Plan

### Phase 1: Project Detection in Init
- [x] Add detection logic to check if `.roadmap/projects/` already contains `.md` files
- [x] If projects exist, load them instead of generating new ones
- [x] Update `init()` in `roadmap/cli/core.py` to skip project creation if projects already exist
- [x] Add comprehensive tests (12 integration tests covering all scenarios)

### Phase 2: Config Refactoring
- [x] Split config model into shared (`config.yaml`) and local (`config.yaml.local`)
- [x] Update `ConfigManager` to handle `.local` pattern
- [x] Modify `.gitignore` to commit `config.yaml` but exclude `*.local` files
- [x] User-specific settings (GitHub tokens, UI preferences) go in `.local`
- [x] Add test: `test_config_local_overrides_shared()` (14 comprehensive config tests added)

### Phase 3: Init Messaging & UX
- [x] Detect 'new project creation' vs 'joining existing project'
- [x] Update CLI output: show 'Joined existing project' or 'Created new project'
- [x] Show which projects are available when joining
- [x] Add helpful messaging about `config.local` for new team members
- [x] Add tests: 17 comprehensive UX messaging tests

### Phase 4: End-to-End Testing
- [x] Test scenario: Alice creates repo, Bob clones and joins
- [x] Test config inheritance and overrides
- [x] Test backward compatibility with existing single-project setups
- [x] Add integration tests for full onboarding workflow (7 E2E tests)

## Technical Details

### Current Behavior
- `roadmap init` always creates new project with UUID-based ID
- Each developer generates own project file
- Projects aren't committed to git (or if they are, duplicates exist)

### New Behavior
- If `.roadmap/projects/*.md` exists, load and use existing projects
- If `.roadmap/projects/` is empty, create new project
- `config.yaml` committed as team artifact
- `config.yaml.local` (gitignored) for user overrides

### Files to Modify
- `roadmap/cli/core.py` (init command)
- `roadmap/cli/init_workflow.py` (initialization logic)
- `roadmap/shared/config_manager.py` (config splitting)
- `roadmap/application/core.py` (project detection)
- `.gitignore` (update pattern)

### Files to Add
- Tests in `tests/integration/` for onboarding scenarios
- Config merge logic for `.local` overrides

## Acceptance Criteria

- [x] Issue created and assigned in v0.7.0 milestone
- [x] Alice creates repo and runs init → creates project, commits to git
- [x] Bob clones repo and runs init → joins Alice's project (no new project created)
- [x] Bob's local config (`config.yaml.local`) doesn't affect Alice's setup
- [x] All existing tests pass (1,449 total tests)
- [x] New tests cover all onboarding scenarios:
  - [x] Phase 1: Project detection (12 tests)
  - [x] Phase 2: Config refactoring (14 tests)
  - [x] Phase 3: UX messaging (17 tests)
  - [x] Phase 4: End-to-end workflows (7 tests)
  - **Total: 50 new tests**
- [x] Documentation patterns established for team onboarding

## Implementation Summary

**Architecture:** Option A - Projects as Committed Team Artifacts

- Projects (`.roadmap/projects/*.md`) committed to git
- Config split: team (`config.yaml`) vs user (`config.yaml.local`)
- Projects detected on init, not generated
- Config merging supports nested overrides

**Core Components:**

1. `_detect_existing_projects()` - Checks for existing project files
2. `ConfigManager` with deep merge - Handles shared + local configs
3. Enhanced init messaging - Shows "Joined" vs "Created" workflows
4. E2E test patterns - Validates Alice/Bob team scenarios

**Files Modified:**

- `roadmap/cli/core.py` - Project detection in init
- `roadmap/shared/config_manager.py` - Config splitting and merging
- `.gitignore` - Config file patterns (shared committed, local ignored)

**Test Coverage:**

- 1,449 total tests passing (1,399 baseline + 50 new)
- All phases of implementation validated
- No regressions from architectural changes
- E2E workflows demonstrate team use cases
