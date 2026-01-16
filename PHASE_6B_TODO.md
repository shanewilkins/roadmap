# Phase 6B: Code Consolidation & Reorganization TODO

## Overview
Phase 6B focuses on fixing structural code smells discovered during Phase 6A layer violation analysis. Two major consolidations have been adopted:
1. **Logging consolidation** - merge infrastructure/logging into common/logging
2. **GitHub reorganization** - move github setup/config to proper layers

---

## Task Breakdown

### ✅ COMPLETED
- [x] 6b.0.1 - Fix flaky test (test_milestone_list_shows_estimates)
- [x] 6b.0.2 - Consolidate common/ and shared/ layers
- [x] 6b.0.3 - Identify code smells (logging duplication, github fragmentation)

---

### 🔄 IN PROGRESS / QUEUED

#### Task 6b.1: Consolidate Logging Modules
**Status**: NOT STARTED | **Effort**: 2-3 hours | **Priority**: HIGH

**Objective**: Merge `infrastructure/logging/` into `common/logging/` to eliminate duplication

**Steps**:
- [ ] 6b.1.1 - Move infrastructure/logging/decorators.py → common/logging/
- [ ] 6b.1.2 - Move infrastructure/logging/error_logging.py → common/logging/
- [ ] 6b.1.3 - Move infrastructure/logging/audit_logging.py → common/logging/
- [ ] 6b.1.4 - Move infrastructure/logging/performance_tracking.py → common/logging/
- [ ] 6b.1.5 - Update common/logging/__init__.py to export all moved items
- [ ] 6b.1.6 - Search and update 52 imports from infrastructure.logging → common.logging
- [ ] 6b.1.7 - Delete infrastructure/logging/ directory
- [ ] 6b.1.8 - Run test suite to verify no regressions
- [ ] 6b.1.9 - Commit with message: "refactor: consolidate logging into common/logging"

**Files Affected**: 52 files importing from infrastructure.logging

**Validation**:
- All tests pass
- No remaining imports from infrastructure.logging
- Pre-commit hooks pass

---

#### Task 6b.2: Reorganize GitHub Modules
**Status**: NOT STARTED | **Effort**: 4-5 hours | **Priority**: MEDIUM

**Objective**: Move GitHub setup/config management from infrastructure/github to proper layers

**Option Selected**: Clean Separation with Better Layering

**Structure Changes**:
```
adapters/github/              (Pure API client - no changes)
  ├── github.py (GitHubClient)
  └── handlers/

core/services/github/         (Business logic - no changes)
  ├── integration_service.py
  ├── change_detector.py
  ├── conflict_detector.py
  └── entity_classifier.py

[NEW] common/configuration/github/
  ├── __init__.py
  ├── token_resolver.py        (moved from infrastructure/github/setup.py)
  └── config_manager.py        (moved from infrastructure/github/setup.py)

[NEW] common/initialization/github/
  ├── __init__.py
  ├── setup_service.py         (moved from infrastructure/github/setup.py)
  └── setup_validator.py       (moved from infrastructure/github/setup.py)
```

**Steps**:
- [ ] 6b.2.1 - Create common/configuration/github/ directory
- [ ] 6b.2.2 - Create common/initialization/github/ directory
- [ ] 6b.2.3 - Extract GitHubTokenResolver from infrastructure/github/setup.py → common/configuration/github/token_resolver.py
- [ ] 6b.2.4 - Extract GitHubConfigManager from infrastructure/github/setup.py → common/configuration/github/config_manager.py
- [ ] 6b.2.5 - Extract GitHubSetupValidator from infrastructure/github/setup.py → common/initialization/github/setup_validator.py
- [ ] 6b.2.6 - Extract GitHubInitializationService from infrastructure/github/setup.py → common/initialization/github/setup_service.py
- [ ] 6b.2.7 - Create common/configuration/github/__init__.py (export token_resolver, config_manager)
- [ ] 6b.2.8 - Create common/initialization/github/__init__.py (export setup_validator, setup_service)
- [ ] 6b.2.9 - Update core/services/github to import from new locations
- [ ] 6b.2.10 - Search and update ~30 imports across codebase
- [ ] 6b.2.11 - Delete infrastructure/github/ directory
- [ ] 6b.2.12 - Run test suite to verify no regressions
- [ ] 6b.2.13 - Commit with message: "refactor: reorganize github modules by concern"

**Files Affected**: ~30 files importing from infrastructure.github or importing in core/services/github

**Validation**:
- All tests pass
- No remaining imports from infrastructure.github
- Pre-commit hooks pass
- GitHub integration tests still work

---

### 📋 REMAINING TASKS (After 6b.1 & 6b.2)

#### Task 6b.3: Simplify Interface Methods
**Status**: QUEUED | **Effort**: 1-2 hours | **Priority**: MEDIUM

**Objective**: Consolidate duplicate interface methods (push_issue/push_issues, pull_issue/pull_issues)

---

#### Task 6b.4: Split Infrastructure Layer by Concern
**Status**: QUEUED | **Effort**: 3-4 hours | **Priority**: LOW

**Objective**: Reorganize infrastructure/ to separate concerns (persistence, github, observability, security)

---

## Execution Plan

### Recommended Sequence
1. **Task 6b.1 (Logging)** - Start here (simpler, fewer files)
   - Straightforward consolidation
   - Well-contained changes
   - 52 import updates

2. **Task 6b.2 (GitHub)** - Follow with this (more complex)
   - Requires careful refactoring
   - More testing needed
   - ~30 import updates

3. **Task 6b.3 & 6b.4** - Only after 6b.1 & 6b.2 complete
   - Depends on stable foundation from first two tasks
   - Lower priority improvements

---

## Success Criteria

After completing 6b.1 & 6b.2:
- ✅ All 6,556+ tests pass
- ✅ No imports remain from old locations (infrastructure/logging, infrastructure/github)
- ✅ Pre-commit hooks pass (ruff, pylint, vulture, pyright, etc.)
- ✅ Architecture checker validates clean layer separation
- ✅ Code smells eliminated
- ✅ Developer experience improved (clearer module organization)

---

## Rollback Plan

If issues arise during execution:
1. Commit frequently (after each subtask if possible)
2. Can revert individual commits if a task causes problems
3. After 6b.1.7 or 6b.2.11, full cleanup is done - can't easily revert

---

## Notes

- **Test Suite**: Currently takes ~100 seconds with xdist. Document this as known issue for future optimization.
- **Pre-commit**: All hooks must pass before commits are accepted
- **Import Updates**: Use grep-search + replace_string_in_file for efficiency
