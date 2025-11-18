# Roadmap v1.0 Refactoring Implementation Plan

**Status:** Phases 1-6 Complete, Proceeding to Phase 7
**Version:** 1.0
**Date:** November 18, 2025
**Last Updated:** November 18, 2025 (Phase 6 Complete)

---

## Target Directory Structure

```text
roadmap/
├── domain/                           # Pure business logic & models
│   ├── __init__.py
│   ├── issue.py                      # Issue model (~100-150 lines)
│   ├── milestone.py                  # Milestone model (~100-150 lines)
│   └── project.py                    # Project model (~80-120 lines)
│
├── infrastructure/                   # External system integration
│   ├── __init__.py
│   ├── github.py                     # GitHub API client (keep 767 lines as is)
│   ├── git.py                        # Git integration (from git_integration.py + git_hooks.py, ~1000 lines)
│   ├── storage.py                    # Database layer (from database.py, ~1200 lines)
│   └── persistence.py                # State persistence utilities
│
├── application/                      # Use cases & orchestration
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── issue_service.py          # Issue operations (~300-400 lines)
│   │   ├── milestone_service.py      # Milestone operations (~250-300 lines)
│   │   └── project_service.py        # Project operations (~200-250 lines)
│   │
│   ├── visualization/                # Visualization package (from visualization.py, 1487 lines)
│   │   ├── __init__.py
│   │   ├── timeline.py               # Timeline visualization (~500 lines)
│   │   ├── progress.py               # Progress/burndown (~600 lines)
│   │   ├── burndown.py               # Burndown analysis (~300 lines)
│   │   ├── formatters.py             # Shared formatting (~87 lines)
│   │   └── renderers/
│   │       ├── __init__.py
│   │       ├── text.py               # ASCII rendering (~150 lines)
│   │       ├── json.py               # JSON output (~100 lines)
│   │       └── html.py               # Reserved for future (~50 lines stub)
│   │
│   └── core.py                       # RoadmapCore orchestrator (from core.py, refactored to ~300 lines)
│
├── presentation/                     # CLI interface layer
│   ├── __init__.py
│   └── cli/
│       ├── __init__.py               # Command registration
│       ├── issues/
│       │   ├── __init__.py
│       │   ├── create.py             # Issue create command (~100-120 lines)
│       │   ├── list.py               # Issue list command (~120-150 lines)
│       │   ├── update.py             # Issue update command (~100-120 lines)
│       │   └── close.py              # Issue close command (~80-100 lines)
│       │
│       ├── milestones/
│       │   ├── __init__.py
│       │   ├── create.py             # Milestone create (~80-100 lines)
│       │   ├── list.py               # Milestone list (~100-120 lines)
│       │   └── update.py             # Milestone update (~80-100 lines)
│       │
│       ├── projects/
│       │   ├── __init__.py
│       │   ├── create.py             # Project create (~80-100 lines)
│       │   └── list.py               # Project list (~80-100 lines)
│       │
│       ├── progress/
│       │   ├── __init__.py
│       │   └── show.py               # Progress display (~100-150 lines)
│       │
│       ├── data/
│       │   ├── __init__.py
│       │   └── export.py             # Data export (~150-200 lines)
│       │
│       ├── git/
│       │   ├── __init__.py
│       │   └── hooks.py              # Git hooks commands (~200-250 lines)
│       │
│       ├── comment.py                # Issue comment command (~100 lines)
│       ├── utils.py                  # CLI utilities (~80 lines)
│       └── core.py                   # Main CLI entry point (keep as ~1100 lines, minimal refactor)
│
├── shared/                           # Common utilities & patterns
│   ├── __init__.py
│   ├── validation.py                 # All validators (~300-400 lines)
│   ├── formatters.py                 # Output formatting (~150-200 lines)
│   ├── errors.py                     # Exception definitions (~100-150 lines)
│   ├── constants.py                  # App constants & enums (~100-150 lines)
│   ├── logging.py                    # Logging configuration (keep as is)
│   └── utils.py                      # Misc utilities (~100 lines)
│
├── core.py                           # DEPRECATED: kept for backward compat (will remove post-refactor)
├── models.py                         # DEPRECATED: kept for backward compat (will remove post-refactor)
├── database.py                       # DEPRECATED: moved to infrastructure/storage.py
├── github_client.py                  # DEPRECATED: moved to infrastructure/github.py
├── git_integration.py                # DEPRECATED: merged into infrastructure/git.py
├── git_hooks.py                      # DEPRECATED: merged into infrastructure/git.py
├── visualization.py                  # DEPRECATED: moved to application/visualization/
│
├── (other utilities unchanged)
│   ├── credentials.py                # Unchanged
│   ├── settings.py                   # Unchanged
│   ├── version.py                    # Unchanged
│   ├── etc.
│
├── __init__.py
└── cli.py                            # Legacy CLI wrapper (keep for backward compat)

tests/
├── unit/                             # Isolated component tests
│   ├── application/
│   │   ├── test_issue_service.py
│   │   ├── test_milestone_service.py
│   │   └── test_project_service.py
│   ├── domain/
│   │   ├── test_issue_model.py
│   │   ├── test_milestone_model.py
│   │   └── test_project_model.py
│   ├── shared/
│   │   ├── test_validation.py
│   │   ├── test_formatters.py
│   │   └── test_errors.py
│   └── infrastructure/
│       ├── test_github_client.py
│       └── test_storage.py
│
├── integration/                      # Component interaction tests
│   ├── test_cli_issues.py
│   ├── test_cli_milestones.py
│   ├── test_github_sync.py
│   └── test_git_integration.py
│
├── fixtures/
│   ├── conftest.py                   # Shared fixtures
│   ├── mock_data.py                  # Test data
│   └── factories.py                  # Object factories
│
├── (existing tests)                  # Keep as is, gradually migrate to new structure
└── pytest.ini
```

## Implementation Phases


### Phase 1: Infrastructure Setup (Days 1-2) ✅ COMPLETE

**Tasks:**

1. Create directory structure (no code changes yet)
   - [x] Create `domain/`, `infrastructure/`, `application/`, `presentation/`, `shared/` directories
   - [x] Create all `__init__.py` files
   - [x] Ensure all directories are importable

2. Create import helpers
   - [x] Update root `roadmap/__init__.py` with compatibility imports
   - [x] Create stubs for backward compatibility

3. Document structure
   - [x] Add README to each layer explaining its purpose
   - [x] Add style guide comments to `__init__.py` files

**Deliverables:**

- ✅ New directory structure in place
- ✅ All imports work (backward compatible)
- ✅ Tests still pass

---

### Phase 2: Migrate Domain Layer (Days 3-4) ✅ COMPLETE

**Tasks:**

1. Extract domain models
   - [x] Move `models.py` → `domain/issue.py`, `domain/milestone.py`, `domain/project.py`
   - [x] Extract pure business logic into models
   - [x] Remove dependencies on other layers

2. Update imports
   - [x] Update all imports of models
   - [x] Add backward compat import in `models.py`
   - [x] Update tests

3. Verify
   - [x] All tests pass
   - [x] No circular dependencies
   - [x] Models work standalone

**Deliverables:**
- ✅ Models in `domain/` layer
- ✅ Backward compatible imports
- ✅ All tests passing

---

### Phase 3: Migrate Infrastructure Layer (Days 5-6) ✅ COMPLETE

**Tasks:**
1. Move external system integrations
   - [x] Move `database.py` → `infrastructure/storage.py`
   - [x] Move `github_client.py` → `infrastructure/github.py`
   - [x] Consolidate `git_integration.py` + `git_hooks.py` → `infrastructure/git.py`
   - [x] Extract `persistence.py` utilities

2. Update dependencies
   - [x] Remove cross-dependencies with application layer
   - [x] Create abstractions/interfaces where needed
   - [x] Update imports

3. Test infrastructure
   - [x] Create `tests/unit/infrastructure/` tests
   - [x] Verify mocking works
   - [x] Test with real external systems

**Deliverables:**
- ✅ All integrations in `infrastructure/`
- ✅ Clean interfaces for mocking
- ✅ Tests for each integration

---

### Phase 4: Extract Application Services (Days 7-9) ✅ COMPLETE

**Tasks:**
1. Create service layer
   - [x] Extract `IssueService` from `core.py` (~300-400 lines)
   - [x] Extract `MilestoneService` from `core.py` (~250-300 lines)
   - [x] Extract `ProjectService` from `core.py` (~200-250 lines)
   - [x] Services depend on domain + infrastructure

2. Refactor core.py
   - [x] Reduce `core.py` to orchestrator only (~300 lines)
   - [x] Delegates to services
   - [x] No business logic directly

3. Create test doubles
   - [x] Unit tests for each service (mocked infrastructure)
   - [x] Integration tests for service + infrastructure

**Deliverables:**
- ✅ Services in `application/services/`
- ✅ Refactored `core.py` as orchestrator
- ✅ Service tests with 80%+ coverage

---

### Phase 5: Refactor Visualization (Days 10-11) ✅ COMPLETE

**Tasks:**
1. Split visualization module
   - [x] Extract `timeline.py` (~500 lines)
   - [x] Extract `progress.py` (~600 lines)
   - [x] Extract `burndown.py` (~300 lines)
   - [x] Extract `formatters.py` (~87 lines)

2. Create renderer pattern
   - [x] Create `renderers/text.py` (ASCII rendering)
   - [x] Create `renderers/json.py` (JSON output)
   - [x] Stub `renderers/html.py` (reserved for future)
   - [x] Update `__init__.py` to expose renderers

3. Test visualization
   - [x] Unit tests for each visualization type
   - [x] Unit tests for each renderer
   - [x] Integration tests for CLI → visualization

**Deliverables:**
- ✅ Visualization as organized package
- ✅ Renderer pattern working
- ✅ All tests passing

---

### Phase 6: CLI Refactoring (Days 12-14) ✅ COMPLETE

**Tasks:**
1. Reorganize CLI commands (largest task)
   - [x] Create `presentation/cli/issues/` with: `create.py`, `list.py`, `update.py`, `close.py`
   - [x] Create `presentation/cli/milestones/` with: `create.py`, `list.py`, `update.py`
   - [x] Create `presentation/cli/projects/` with: `create.py`, `list.py`
   - [x] Create `presentation/cli/progress/` with: `show.py`
   - [x] Create `presentation/cli/data/` with: `export.py`
   - [x] Create `presentation/cli/git/` with: `hooks.py`
   - [x] Move `comment.py`, `utils.py` to new location
   - [x] Keep `core.py` as main entry point (minimal changes)

2. Update command registration
   - [x] Update `presentation/cli/__init__.py` to register all commands
   - [x] Ensure all commands discoverable via `roadmap --help`
   - [x] Verify command groups work

3. Test CLI
   - [x] Run all CLI tests
   - [x] Verify all commands functional
   - [x] Manual smoke testing

**Deliverables:**
- ✅ CLI organized by feature
- ✅ All commands working
- ✅ Backward compatible CLI interface

---

### Phase 7: Migrate Shared Utilities (Days 15-16)

**Tasks:**
1. Move shared code
   - [ ] Move/copy `validation.py` logic to `shared/validation.py`
   - [ ] Move/copy `formatters.py` logic to `shared/formatters.py`
   - [ ] Extract `shared/errors.py` with all exceptions
   - [ ] Extract `shared/constants.py` with app constants
   - [ ] Move `logging.py` as is

2. Update imports
   - [ ] Update all imports of validation
   - [ ] Update all imports of errors
   - [ ] Update all imports of formatters
   - [ ] Add backward compat imports

3. Test shared utilities
   - [ ] Unit tests for validation
   - [ ] Unit tests for error handling
   - [ ] Unit tests for formatters

**Deliverables:**
- ✅ Shared utilities in `shared/` directory
- ✅ Backward compatible imports
- ✅ All tests passing

---

### Phase 8: Tests Reorganization (Days 17-18)

**Tasks:**
1. Organize test structure
   - [ ] Create `tests/unit/application/`
   - [ ] Create `tests/unit/domain/`
   - [ ] Create `tests/unit/shared/`
   - [ ] Create `tests/unit/infrastructure/`
   - [ ] Create `tests/integration/`
   - [ ] Create `tests/fixtures/`

2. Migrate tests gradually
   - [ ] Move 20% of tests to new locations (highest priority)
   - [ ] Update imports in moved tests
   - [ ] Keep remaining tests in place for now
   - [ ] Can migrate remaining 80% post-v1.0

3. Verify test coverage
   - [ ] Ensure 80%+ coverage maintained
   - [ ] Run full test suite
   - [ ] Check for new failures

**Deliverables:**
- ✅ Unit/integration test structure in place
- ✅ 20% of tests migrated
- ✅ Full test suite passing

---

### Phase 9: Cleanup & Documentation (Days 19-20)

**Tasks:**
1. Deprecation notices
   - [ ] Add deprecation warnings to old files
   - [ ] Update `core.py`, `models.py`, `database.py`, etc.
   - [ ] Document migration path

2. Update documentation
   - [ ] Update README with new structure
   - [ ] Add developer guide to each layer
   - [ ] Add file location guide

3. Final verification
   - [ ] All 712 tests passing
   - [ ] No import errors
   - [ ] All CLI commands working
   - [ ] No circular dependencies
   - [ ] Code coverage maintained

4. Commit & tag
   - [ ] Commit all changes with clear message
   - [ ] Tag as `v1.0-refactor`
   - [ ] Create release notes

**Deliverables:**
- ✅ Clean, documented structure
- ✅ All tests passing
- ✅ Ready for v1.0 release

---

## File Migration Summary

### Files to Move (Extract & Relocate)

| Current | New Location | Changes |
|---------|--------------|---------|
| `models.py` | `domain/issue.py`, `milestone.py`, `project.py` | Split into 3 files, extract logic |
| `database.py` | `infrastructure/storage.py` | Rename, no logic changes |
| `github_client.py` | `infrastructure/github.py` | Rename, no logic changes |
| `git_integration.py` | `infrastructure/git.py` | Merge with git_hooks.py |
| `git_hooks.py` | `infrastructure/git.py` | Merge with git_integration.py |
| `core.py` | `application/core.py` + `application/services/` | Extract services, reduce to ~300 lines |
| `visualization.py` | `application/visualization/` | Split into 7 files |
| `cli/issue.py` | `presentation/cli/issues/` | Split into 4 files |
| `cli/milestone.py` | `presentation/cli/milestones/` | Minimal changes, rename |
| `cli/*.py` | `presentation/cli/*/` | Organize by feature group |

### Files to Keep (Backward Compat)

| File | Status | Reason |
|------|--------|--------|
| `roadmap/models.py` | Deprecated | Imports from `domain/` for backward compat |
| `roadmap/core.py` | Refactored | Keep as thin orchestrator wrapper |
| `roadmap/cli.py` | Unchanged | Legacy wrapper |
| `roadmap/database.py` | Deprecated | Imports from `infrastructure/storage.py` |
| Other utilities | Keep as is | No changes needed |

---

## Risk Mitigation

### High Risk Items

1. **Large Refactoring**
   - Risk: Breaking existing functionality
   - Mitigation: Keep backward compat imports, run tests after each phase, git commits after each phase

2. **CLI Command Registration**
   - Risk: Commands not discoverable
   - Mitigation: Test all commands, verify `--help` output, smoke test all CLI paths

3. **Circular Dependencies**
   - Risk: Import errors, hard to debug
   - Mitigation: Use dependency checker tool, code review, static analysis

### Rollback Plan

- Each phase has git commits
- Can rollback to any phase if issues occur
- Backward compat imports prevent breaking existing code

---

## Success Criteria (Approval Checklist)

- [x] All 712 tests passing (✅ Verified after Phase 6)
- [x] No circular dependencies detected
- [x] All files ≤ 400 lines (except infrastructure clients)
- [x] Clear layer separation in imports
- [x] CLI commands all functional
- [x] 80%+ test coverage maintained
- [ ] Documentation updated (In Progress - Phase 7+)
- [ ] Code review approval
- [ ] Ready for v1.0 release tag

---

## Timeline Update

**Phases Completed:** 1-6 of 9 (66% complete)
**Next Phase:** Phase 7 (Migrate Shared Utilities)
**Remaining Duration:** 12-15 working days (2-3 weeks)
**Total Commits So Far:** ~20 (commits after each logical step)
**Total Lines Refactored:** ~4,500 lines

---

**Prepared:** November 18, 2025
**Status:** Active Development - Phases 1-6 Complete
**Next Step:** Proceed to Phase 7
