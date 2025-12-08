# Phase 2a: Deprecation Strategy

**Date:** December 8, 2025
**Phase:** 2a (Test Infrastructure Refactoring)
**Document Type:** Deprecation & Removal Plan

---

## Overview

This document outlines the strategy for deprecating and removing the 24 shim files during Phase 2b-2c of the roadmap refactoring.

**Timeline:**
- **Phase 2a (Complete):** Planning & Audits
- **Phase 2b (1-2 weeks):** Test refactoring using new imports
- **Phase 2c (3-5 days):** Shim file deletion and cleanup

**Safety Approach:** Keep all shim files in place during Phase 2b. Only delete in Phase 2c after tests pass.

---

## Deprecation Tiers

### Tier 1: Safe to Remove Immediately (Low Risk)

These shims are pure re-exports with no active code depending on them.

**Files:**
1. `roadmap/adapters/cli/init_workflow.py`
2. `roadmap/adapters/cli/init_validator.py`
3. `roadmap/adapters/cli/github_setup.py`

**Characteristics:**
- Pure re-exports (no logic)
- Used only in tests
- No circular dependencies
- No external consumers expected

**Deprecation Approach:**
- No warnings needed (they're internal)
- Delete in Phase 2c immediately
- Update all imports in Phase 2b

**Validation:**
```bash
# Step 1: Verify no external imports
grep -r "from roadmap.adapters.cli.init_workflow" /Users/shane/roadmap --exclude-dir=.git

# Step 2: Update all imports
# Step 3: Delete file
# Step 4: Verify tests pass
```

---

### Tier 2: Safe to Remove After Update (Medium Risk)

These shims have clear new locations but are used in multiple places.

**Files:**
4. `roadmap/adapters/cli/logging_decorators.py` - Modern equivalent: `roadmap.infrastructure.logging`
5. `roadmap/adapters/cli/issue_filters.py` - Modern equivalent: `roadmap.core.services.filtering`
6. `roadmap/adapters/persistence/storage.py` - Modern equivalent: `roadmap.adapters.persistence.storage` package
7. `roadmap/common/errors.py` - Modern equivalent: `roadmap.common.errors` package
8. `roadmap/common/security.py` - Modern equivalent: `roadmap.common.security` package
9. `roadmap/adapters/persistence/parser.py` - Modern equivalent: Direct parsers

**Deprecation Approach:**

**Phase 2b (Test Refactoring):**
```python
# Add deprecation warnings to facades
import warnings

warnings.warn(
    "The 'roadmap.adapters.cli.logging_decorators' module is deprecated. "
    "Use 'roadmap.infrastructure.logging' instead.",
    DeprecationWarning,
    stacklevel=2
)
```

**Phase 2c (Deletion):**
- After all imports updated and tests pass, delete files
- Verify no imports reference the deleted files
- Commit with detailed message

**Validation:**
```bash
# Before deletion, search for any remaining imports
grep -r "from roadmap.adapters.cli.logging_decorators" . --exclude-dir=.git
```

---

### Tier 3: Requires Code Changes (Higher Risk)

These are helper modules that need functional refactoring, not just import updates.

**Files:**
10. `roadmap/adapters/cli/init_utils.py`
11. `roadmap/adapters/cli/cleanup.py`
12. `roadmap/adapters/cli/audit_logging.py`
13. `roadmap/adapters/cli/error_logging.py`
14. `roadmap/adapters/cli/kanban_helpers.py`
15. `roadmap/adapters/cli/performance_tracking.py`

**Deprecation Approach:**

**Phase 2b:**
1. Identify all call-sites of functions in these modules
2. Replace with modern service layer calls
3. Keep facade files but add deprecation warnings:

```python
# roadmap/adapters/cli/cleanup.py
import warnings

warnings.warn(
    "The 'roadmap.adapters.cli.cleanup' module is deprecated. "
    "Use 'roadmap.infrastructure.lifecycle.WorkspaceLifecycleService' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Continue re-exporting for now
from roadmap.infrastructure.lifecycle import cleanup_workspace
```

4. Update test fixtures to use services
5. Ensure all tests pass with new patterns

**Phase 2c:**
- Delete facade files only after all call-sites refactored
- Run full test suite
- Commit cleanup

**Validation:**
```bash
# Find all direct function calls
grep -r "from roadmap.adapters.cli.init_utils import" . --exclude-dir=.git
grep -r "cleanup_workspace(" . --exclude-dir=.git

# After refactoring, verify none exist
```

---

### Tier 4: Convenience Functions (Inline or Deprecate)

These are module-level convenience functions that can be inlined or converted to service methods.

**Files:**
16. `roadmap/common/datetime_parser.py` (convenience functions only)
17. `roadmap/common/logging.py` (backwards-compatible logger)
18. `roadmap/common/timezone_utils.py` (helper functions)
19. `roadmap/common/validation/validators.py` (legacy methods)

**Deprecation Approach:**

**Option A - Inline (Recommended for v1.0.0):**
```python
# Before deletion in Phase 2b:
# 1. Find all call-sites
# 2. Replace function calls with service calls
# 3. Delete convenience function
# 4. Update tests

grep -r "parse_datetime(" . --exclude-dir=.git
# Replace all with: DateTimeParser().parse()
```

**Option B - Add Deprecation Warnings:**
```python
# In Phase 2b, add warnings:
def parse_datetime(date_str: str):
    import warnings
    warnings.warn(
        "parse_datetime() is deprecated. Use DateTimeParser().parse() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return DateTimeParser().parse(date_str)

# In Phase 2c, delete function entirely
```

**Recommendation:** Use Option A for v1.0.0 (no deprecation warnings for internal functions).

---

### Tier 5: Test-Specific Shims (Fixture Updates)

These are test fixtures that need replacement with real services.

**Files:**
20. `tests/fixtures/conftest.py` - `patch_github_integration` fixture
21. `tests/conftest.py` - Similar fixtures

**Deprecation Approach:**

**Phase 2b:**
1. Create new fixtures using real services:
```python
@pytest.fixture
def github_integration_service(temp_workspace):
    """Real GitHub integration service for testing."""
    from roadmap.core.services.github_integration import GitHubService
    config = TestConfig(workspace=temp_workspace)
    return GitHubService(config)
```

2. Update all tests to use new fixtures instead of mocks
3. Delete old mock fixtures

**Phase 2c:**
- Clean up any remaining test-specific shims
- Verify full test suite passes

---

## Package-Level Facades (No Deprecation Needed)

These facades are useful for package users and should remain in place:

- `roadmap/common/validation/__init__.py`
- `roadmap/common/security/__init__.py`

**Recommendation:** Keep these facades. They provide a good API surface for package users.

---

## Detailed Removal Timeline

### Phase 2b Timeline (1-2 weeks)

**Week 1:**
- **Day 1:** Add deprecation warnings to Tier 2-3 files
- **Day 1-2:** Update all imports from Tier 1 files
- **Day 2-3:** Update all imports from Tier 2 files
- **Day 3-4:** Update test fixtures for Tier 3 files
- **Day 4-5:** Refactor code to use services instead of helper modules

**Week 2:**
- **Day 6:** Inline convenience functions (Tier 4)
- **Day 7:** Run full test suite, fix any issues
- **Day 8-10:** Final testing and validation

### Phase 2c Timeline (3-5 days)

**Day 1 (Monday):**
```bash
# Delete Tier 1 files (safest)
git rm roadmap/adapters/cli/init_workflow.py
git rm roadmap/adapters/cli/init_validator.py
git rm roadmap/adapters/cli/github_setup.py

# Run tests
poetry run pytest -x
```

**Day 2 (Tuesday):**
```bash
# Delete Tier 2 files
git rm roadmap/adapters/cli/logging_decorators.py
git rm roadmap/adapters/cli/issue_filters.py
git rm roadmap/adapters/persistence/storage.py
git rm roadmap/common/errors.py
git rm roadmap/common/security.py
git rm roadmap/adapters/persistence/parser.py

# Run tests
poetry run pytest -x
```

**Day 3 (Wednesday):**
```bash
# Delete Tier 3 helper modules
git rm roadmap/adapters/cli/init_utils.py
git rm roadmap/adapters/cli/cleanup.py
git rm roadmap/adapters/cli/audit_logging.py
git rm roadmap/adapters/cli/error_logging.py
git rm roadmap/adapters/cli/kanban_helpers.py
git rm roadmap/adapters/cli/performance_tracking.py

# Run tests
poetry run pytest -x
```

**Day 4 (Thursday):**
```bash
# Clean up convenience functions
# This is done in Phase 2b, but verify in Phase 2c
poetry run pytest -x

# Commit the cleanup
git add -A
git commit -m "Phase 2c: Remove all 24 backwards-compatibility shims

- Deleted 14 re-export facades (Tier 1-2)
- Deleted 6 helper module facades (Tier 3)
- Inlined 4 convenience functions (Tier 4)
- Updated 2 test fixture sets (Tier 5)
- Updated all imports across codebase
- All 1730+ tests still passing
- Removes ~1000 lines of compatibility code"
```

**Day 5 (Friday):**
- Final verification
- Ensure no broken imports remain
- Push to repository

---

## Risk Mitigation

### What Could Go Wrong?

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Missed import in test file | Medium | Test fails | Pre-commit grep for old imports |
| Circular dependency broken | Low | Tests fail | Import discovery in Phase 2b |
| External consumer depends on shim | Low | Breaking change | Check if published as library |
| Type hints break with new imports | Low | Type checking fails | Run pyright after updates |
| Test fixture incompatibility | Medium | Tests fail | Update fixtures in Phase 2b |

### Rollback Strategy

If Phase 2c deletion causes test failures:

1. **Stop immediately.** Commit should not complete.
2. **Revert the deletion commit:**
   ```bash
   git reset --hard HEAD~1
   ```
3. **Identify the blocker:** Run tests to see what broke
4. **Fix in Phase 2b:** Go back and refactor the failing area
5. **Retry Phase 2c after fix confirmed**

---

## Communication Plan

### Internal (Team)

- **Before Phase 2b:** Share migration map with team
- **During Phase 2b:** Daily standup on migration progress
- **End of Phase 2b:** Report that shims are unused and safe to delete
- **Before Phase 2c:** Announce deletion timeline
- **After Phase 2c:** Celebrate the cleanup!

### External (Changelog)

In `CHANGELOG.md`:
```markdown
## [1.0.0] - TBD

### Removed
- **BREAKING:** Removed 24 backwards-compatibility shim modules
  - See Migration Guide for import updates
  - All public APIs remain unchanged
  - Only import paths have changed

### Changed
- Updated test suite to use modern service layer
- Improved test fixture patterns
```

---

## Success Criteria

### Phase 2b Success:
- ✅ All imports updated to new locations
- ✅ All test fixtures use real services, not mocks
- ✅ All helper function calls replaced with service layer
- ✅ All convenience functions inlined
- ✅ 1,730+ tests pass with new patterns
- ✅ No deprecation warnings in test output

### Phase 2c Success:
- ✅ All 24 shim files deleted
- ✅ No broken imports remain
- ✅ 1,730+ tests still pass
- ✅ Git history shows clean removal
- ✅ No references to deleted files in codebase

---

## Dependency Map for Deletion Order

```
Delete Order:
1. Init workflow (no dependencies on others)
2. Init validator (depends on workflow)
3. GitHub setup (depends on validator)
4. Logging decorators (widely used, last in Tier 1)
5. Error/Security (widely used, last in Tier 2)
6. Helper modules (Tier 3 - last because tests might use them)
7. Convenience functions (inlined, no file deletion)
```

**Key:** Only delete a shim if nothing depends on it.

---

## Post-Phase 2c Tasks

1. **Update Documentation**
   - Update migration guide
   - Update API documentation
   - Update developer guide

2. **Update CI/CD**
   - Verify pipeline passes with new structure
   - Update any linting rules

3. **Release Notes**
   - Document migration for users
   - Provide examples of new import paths
   - Link to migration guide

4. **Archive Old Documentation**
   - Save old API docs if needed
   - Mark Phase 1 docs as completed

---

## Approval Checklist

Before starting Phase 2b:
- [ ] Shim inventory reviewed and approved
- [ ] Migration map reviewed and approved
- [ ] This deprecation strategy reviewed and approved
- [ ] Test fixtures updated and tested locally
- [ ] Team informed of migration plan
- [ ] Rollback plan understood

Before starting Phase 2c:
- [ ] All Phase 2b refactoring complete
- [ ] All tests passing with new imports
- [ ] Import validation script run
- [ ] Team ready for deletion

---

## Files in This Phase

**Deliverables:**
1. ✅ PHASE_2A_SHIM_INVENTORY.md - Complete shim catalog
2. ✅ PHASE_2A_MIGRATION_MAP.md - Exact import changes
3. ✅ PHASE_2A_DEPRECATION_STRATEGY.md - This file
4. ⏳ PHASE_2B_REFACTORING_CHECKLIST.md - Will be created in Phase 2b
