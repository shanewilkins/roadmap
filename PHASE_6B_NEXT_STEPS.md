# Phase 6B Status & Next Steps

## Completed Work

✅ **6b.0.1**: Fixed flaky test (test_milestone_list_shows_estimates)
- Changed from CLI output parsing to core API usage
- Now fully independent for xdist parallelization

✅ **6b.0.2**: Consolidate common/ and shared/ layers
- Merged formatting and observability into common/
- Updated 68 files with new imports
- All 6,556 tests passing

✅ **6b.0.3**: Identified code smells
- Logging duplication analysis complete
- GitHub fragmentation analysis complete

---

## Phase 6B Tasks - Comprehensive Overview

### Current Queue (In Priority Order)

| Task | Priority | Effort | Status |
|------|----------|--------|--------|
| **6b.1: Consolidate Logging** | HIGH | 2-3h | NOT STARTED |
| **6b.2: Reorganize GitHub** | MEDIUM | 4-5h | NOT STARTED |
| 6b.3: Simplify Interface Methods | MEDIUM | 1-2h | QUEUED |
| 6b.4: Split Infrastructure Layer | LOW | 3-4h | QUEUED |

---

## TASK 6B.1: CONSOLIDATE LOGGING MODULES (2-3 hours)

### What Needs to Happen
Merge `infrastructure/logging/` into `common/logging/` to eliminate duplication and create single source of truth.

### Files to Move
```
infrastructure/logging/decorators.py           → common/logging/decorators.py
infrastructure/logging/error_logging.py        → common/logging/error_logging.py
infrastructure/logging/audit_logging.py        → common/logging/audit_logging.py
infrastructure/logging/performance_tracking.py → common/logging/performance_tracking.py
infrastructure/logging/__init__.py             → DELETE (merge exports)
```

### Import Updates Required
- 52 files currently import from `infrastructure.logging`
- Must change all to `from roadmap.common.logging import ...`

### Sub-Tasks
1. Copy 4 modules from infrastructure/logging to common/logging
2. Update common/logging/__init__.py exports (add decorators, error_logging, audit_logging, performance_tracking)
3. Update 52 imports across codebase
4. Delete infrastructure/logging/
5. Run tests to verify
6. Commit

---

## TASK 6B.2: REORGANIZE GITHUB MODULES (4-5 hours)

### What Needs to Happen
Move GitHub setup/config management from `infrastructure/github/` to proper architectural layers.

### Directory Structure Changes

**Create**:
- `common/configuration/github/` → token management, config management
- `common/initialization/github/` → setup workflows, validation

**Keep Unchanged**:
- `adapters/github/` - pure API client
- `core/services/github/` - business logic

**Delete**:
- `infrastructure/github/`

### Classes to Move
From `infrastructure/github/setup.py`:

```python
GitHubTokenResolver          → common/configuration/github/token_resolver.py
GitHubConfigManager          → common/configuration/github/config_manager.py
GitHubSetupValidator         → common/initialization/github/setup_validator.py
GitHubInitializationService  → common/initialization/github/setup_service.py
```

### Import Updates Required
- ~30 files need import updates
- Mostly in core/services/github and adapter CLI files

### Sub-Tasks
1. Create common/configuration/github/ directory
2. Create common/initialization/github/ directory
3. Extract 4 classes from infrastructure/github/setup.py into 4 new files
4. Update exports in new __init__.py files
5. Update ~30 imports across codebase
6. Delete infrastructure/github/
7. Run tests to verify
8. Commit

---

## Implementation Approach

### Sequencing
**Start with 6b.1 (Logging)** because:
- Simpler, more straightforward consolidation
- Fewer files to update (52 vs ~30)
- Less risky (pure consolidation, no restructuring)
- Quick win to build momentum

**Then move to 6b.2 (GitHub)** because:
- More complex refactoring
- More testing needed
- Builds on confidence from 6b.1

**Defer 6b.3 & 6b.4** until after 6b.1 & 6b.2 complete

### Execution Strategy
1. Work on one task at a time
2. Commit after completing each task
3. Run tests frequently to catch issues early
4. Use grep to find all imports that need updating
5. Use multi_replace_string_in_file for efficiency

---

## Success Criteria (After Completing 6b.1 & 6b.2)

✅ All 6,556+ tests pass
✅ No remaining imports from infrastructure.logging
✅ No remaining imports from infrastructure.github
✅ Pre-commit hooks pass (all linters, formatters, type checkers)
✅ Architecture checker validates clean layer separation
✅ Developer experience improved (clearer module organization)

---

## Next Action

**Ready to start Task 6b.1 (Consolidate Logging)?**

This will:
1. Move 4 files from infrastructure/logging to common/logging
2. Update 52 imports
3. Delete infrastructure/logging/
4. Take ~2-3 hours
5. Resolve HIGH priority code smell

Confirm to proceed, and I'll begin the consolidation!
