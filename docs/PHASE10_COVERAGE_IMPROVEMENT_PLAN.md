# Phase 10: Test Coverage Expansion Plan (79% → 85%)

## Current Status
- **Current Coverage:** 79% (17,934 lines)
- **Target Coverage:** 85%
- **Gap:** 6 percentage points
- **Lines Missing:** 3,825 uncovered lines
- **Modules Below 85%:** 121 modules

## Key Findings

### 1. Happy Path Bias Confirmed ✓
**Problem:** Most low-coverage files have extensive try/except blocks that aren't tested at all.

Analysis of top 5 low-coverage files shows:
- roadmap/adapters/cli/projects/restore.py: 5 try/except blocks (32% coverage)
- roadmap/version.py: 6 try/except blocks (52% coverage)
- roadmap/adapters/persistence/sync_orchestrator.py: 4 try/except blocks (40% coverage)
- roadmap/adapters/cli/health/scan.py: 2 try/except blocks (26% coverage)
- roadmap/adapters/git/git_hooks_manager.py: 19 try/except blocks (65% coverage)

**Impact:** Error paths represent 20-50% of code in these files but have 0% test coverage.

### 2. High-Impact Coverage Opportunities

#### Tier 1: Maximum Impact (5+ tests each needed)
Files where adding error path tests will yield highest coverage gains:

1. **roadmap/adapters/cli/projects/restore.py** (32% → target 85%)
   - 5 exception handlers untested
   - 75% of file uncovered
   - ~95 lines of error handling code
   - Estimated effort: 8-10 tests

2. **roadmap/version.py** (52% → target 85%)
   - 6 try/except blocks, 1 raise statement
   - Parsing logic with multiple failure modes
   - ~87 lines uncovered
   - Estimated effort: 10-12 tests

3. **roadmap/adapters/persistence/sync_orchestrator.py** (40% → target 85%)
   - 4 exception handlers
   - Core persistence logic
   - ~70 lines uncovered
   - Estimated effort: 8-10 tests

4. **roadmap/adapters/cli/health/scan.py** (26% → target 85%)
   - 2 exception handlers
   - Health check logic
   - ~66 lines uncovered
   - Estimated effort: 6-8 tests

5. **roadmap/adapters/git/git_hooks_manager.py** (65% → target 85%)
   - 19 exception handlers
   - Git operations (high error potential)
   - ~89 lines uncovered
   - Estimated effort: 15-18 tests

#### Tier 2: Good Impact (3+ tests each needed)
15-20 additional modules with 30-70% coverage:
- roadmap/adapters/cli/presentation/cleanup_presenter.py (32%)
- roadmap/common/file_utils.py (51%)
- roadmap/adapters/cli/git/commands.py (60%)
- roadmap/adapters/cli/git/hooks_config.py (30%)
- roadmap/adapters/cli/milestones/archive.py (59%)
- roadmap/adapters/cli/output_manager.py (39%)
- roadmap/adapters/cli/milestones/kanban.py (23%)
- roadmap/common/errors/error_handler.py (24%)
- roadmap/adapters/cli/issues/comment.py (34%)
- roadmap/infrastructure/security/credentials.py (67%)
- roadmap/adapters/cli/issues/close.py (38%)
- roadmap/settings.py (38%)
- roadmap/adapters/cli/crud/crud_helpers.py (29%)
- roadmap/adapters/cli/crud/base_restore.py (21%)
- roadmap/adapters/cli/issues/sync_status.py (64%)

## Phase 10 Action Plan

### Phase 10a: Error Path Testing - Priority Tier 1 (Week 1-2)
**Goal:** Add error/exception path tests for top 5 highest-impact files
**Expected Coverage Gain:** +3-4 percentage points
**Test Count Increase:** 40-60 new error path tests

1. **roadmap/adapters/cli/projects/restore.py**
   - Test invalid file states
   - Test permission errors
   - Test corrupted data scenarios
   - Test file system errors

2. **roadmap/version.py**
   - Test invalid version format parsing
   - Test version comparison edge cases
   - Test version increment failures
   - Test version validation errors

3. **roadmap/adapters/persistence/sync_orchestrator.py**
   - Test database connection failures
   - Test corrupt sync metadata
   - Test file I/O errors
   - Test concurrent sync conflicts

4. **roadmap/adapters/cli/health/scan.py**
   - Test missing project structure
   - Test unreadable files
   - Test invalid configurations
   - Test scan interruptions

5. **roadmap/adapters/git/git_hooks_manager.py**
   - Test git command failures
   - Test hook installation errors
   - Test permission denied scenarios
   - Test invalid git repositories

### Phase 10b: Error Path Testing - Priority Tier 2 (Week 2-3)
**Goal:** Add error/exception path tests for Tier 2 modules
**Expected Coverage Gain:** +2-3 percentage points
**Test Count Increase:** 40-50 new error path tests

Focus on:
- File I/O error handling
- Permission and access control errors
- Invalid input/data validation
- External service failures (GitHub, Git)
- Configuration errors

### Phase 10c: Happy Path Edge Cases (Week 3-4)
**Goal:** Fill remaining gaps with edge case coverage
**Expected Coverage Gain:** +1-2 percentage points
**Test Count Increase:** 20-30 tests

Focus on:
- Boundary conditions
- Empty/null state handling
- Large data set handling
- Timeout scenarios
- Concurrent operations

### Phase 10d: Test Data Consolidation (Ongoing)
**Goal:** Create factory patterns for reusable test data
**Expected Impact:** Improved test maintainability (no coverage change)
**Effort:** Parallel work throughout phase

## Test Organization Strategy

### Error Path Testing Patterns

#### Pattern 1: Exception Handling Tests
```python
def test_restore_handles_file_not_found_error(self):
    """Test graceful handling of missing file."""
    # Setup: file doesn't exist
    # Act: call restore with missing file
    # Assert: returns appropriate error status

def test_restore_handles_permission_denied_error(self):
    """Test handling of permission denied."""
    # Similar pattern for different error
```

#### Pattern 2: Validation Failure Tests
```python
def test_version_parsing_rejects_invalid_format(self):
    """Test version parser with invalid input."""
    # Test various invalid formats
    # Ensure proper error messages

def test_version_parsing_handles_empty_string(self):
    """Test edge case of empty version string."""
```

#### Pattern 3: Resource Constraint Tests
```python
def test_scan_handles_permission_errors(self):
    """Test scanning with restricted permissions."""
    # Mock file system permission denied
    # Verify error handling

def test_git_manager_handles_git_not_installed(self):
    """Test behavior when git isn't available."""
```

## Coverage Goals by Module Type

### CLI Adapters (Currently 40-65%)
- Target: 85%+
- Focus: Error message output, invalid input handling, edge cases
- Effort: HIGH (many exception handlers)

### Core Services (Currently 75-95%)
- Target: 90%+
- Focus: Error paths, edge cases, concurrent access
- Effort: MEDIUM

### Persistence Layer (Currently 40-67%)
- Target: 85%+
- Focus: Corruption recovery, migration errors, concurrency
- Effort: HIGH

### Infrastructure (Currently 68-97%)
- Target: 90%+
- Focus: Initialization errors, validation failures
- Effort: LOW-MEDIUM

## Estimation Summary

### Test Count Estimates
- Phase 10a (Tier 1): 40-60 tests
- Phase 10b (Tier 2): 40-50 tests
- Phase 10c (Edge cases): 20-30 tests
- **Total new tests:** 100-140 tests

### Expected Results
- Coverage increase: 6+ percentage points (79% → 85%+)
- Total tests: 4,070 → 4,170-4,210 tests
- Lines covered: 17,934 → 18,500+ (estimated)

## Success Criteria

✓ Reach 85% overall code coverage
✓ All modules with error handling have 3+ error path tests
✓ Zero untested exception handlers (from top 20 files)
✓ All tests passing with zero regressions
✓ All pre-commit checks passing
✓ Improved test documentation for error scenarios

## Risk Mitigation

1. **Mock Complexity:** Error path testing requires sophisticated mocking
   - Solution: Use existing mock factories, extend as needed

2. **Brittle Tests:** Error condition tests can be fragile
   - Solution: Test error types/messages, not just presence

3. **Unrealistic Scenarios:** Some errors hard to reproduce
   - Solution: Prioritize common/high-impact errors first

4. **Coverage Gaps:** Hard to reach 100% due to untestable code
   - Solution: Target 85% as practical maximum with 80/20 ROI

## Key Decisions for Discussion

1. **Error Message Testing:** Should we test exact error messages or just error types?
   - Recommendation: Test error types/codes, not exact messages (more maintainable)

2. **Mock Depth:** How deep should we mock? (e.g., all git operations vs. just top-level)
   - Recommendation: Mock at natural boundaries (git operations, file I/O, network)

3. **Test Data:** Reuse existing factories or create specialized error fixtures?
   - Recommendation: Extend existing factories with error scenarios

4. **Test Grouping:** Separate error tests into `test_*_errors.py` files or mixed?
   - Recommendation: Mixed within existing files (easier to maintain, see happy path side-by-side)

## Timeline Estimate
- **Phase 10a:** 4-5 days (high-impact tier 1 modules)
- **Phase 10b:** 3-4 days (tier 2 modules)
- **Phase 10c:** 2-3 days (edge cases)
- **Total:** 9-12 days of focused work

---

## Next Steps
1. Approve Phase 10 plan direction
2. Prioritize Tier 1 modules to start with
3. Begin Phase 10a with error path testing
4. Iterate through tiers as coverage improves
