# Test Organization & Best Practices Recommendations

## Current State Analysis

### Test Directory Structure Issues
Your test structure has grown organically and now has **two competing organizational schemes**:

**Old Structure (Legacy - should be consolidated):**
- `tests/test_cli/` - 29 test files
- `tests/test_core/` - 1 test file
- `tests/test_common/` - 1 test file
- `tests/test_sync_backend/` - Empty dirs with test data
- `tests/test_sync_init/` - Empty dirs with test data
- `tests/test_git_integration/` - Unclear overlap
- `tests/test_roadmap_debug/` - Debug/internal
- `tests/` (loose files) - 3 test files at root

**New Structure (Recommended - current standard):**
- `tests/unit/` (229 test files)
  - `presentation/` - CLI layer tests
  - `infrastructure/` - Integration layer tests
  - `core/services/` - Business logic tests
  - `domain/` - Domain model tests
  - `adapters/` - Adapter pattern tests
  - etc.

### Migration Plan

**Phase 1: Consolidate test_cli/ → unit/presentation/**
```
tests/test_cli/ (29 files) → tests/unit/presentation/
  - Rename files for clarity (already done for some)
  - Update pytest import paths
  - Ensure no duplicate test coverage
```

**Phase 2: Clean up stragglers**
```
tests/test_core/test_*.py → tests/unit/core/
tests/test_common/test_*.py → tests/unit/common/ or tests/unit/shared/
tests/test_*.py (root files) → appropriate unit/ subdirs
```

**Phase 3: Archive/Remove test data dirs**
```
tests/test_sync_backend/ → Extract meaningful tests to unit/adapters/ or unit/infrastructure/
tests/test_sync_init/ → Extract to unit/infrastructure/
tests/test_git_integration/ → Consolidate with integration/
tests/test_roadmap_debug/ → Remove or archive
```

---

## Testing Best Practices Implementation

We've now demonstrated best practices in the new `test_status_change_helpers.py`. Here's how to apply them across your test suite:

### 1. **No Hardcoded Test Data - Use Factories**

✅ **Already Done:**
- `tests/factories/` has data builders
- Example: `IssueTestDataBuilder` in `tests/factories/sync_data`

✅ **New Example:**
Your `test_status_change_helpers.py` tests Status enums directly instead of mocking them.

**Action Items for Existing Tests:**
- Audit `tests/unit/core/services/test_github_sync_*.py` files
- Replace mock factories with real domain factories where possible
- Create GitHub-specific test data builders for issue/milestone sync data

### 2. **Test Actual Behavior, Not Mocks**

✅ **Pattern Used in test_status_change_helpers.py:**
```python
def test_extract_all_valid_issue_statuses(self):
    """Test extraction works for all valid issue statuses."""
    for status in Status:  # Real enum
        result = extract_issue_status_update(f"todo -> {status.value}")
        assert result is not None
        assert result["status_enum"] == status  # Assert real behavior
```

❌ **Current Problem in test_github_sync_orchestrator.py:**
```python
with patch("roadmap.core.services.github_sync_orchestrator.GitHubIssueClient"):
    # Testing through mock instead of behavior
```

**What to Do:**
1. For unit tests: Mock external dependencies (GitHub API, file I/O) but test real business logic
2. For integration tests: Use test fixtures with real objects where safe
3. Create integration tests that actually test sync without network calls (use mock HTTP)

### 3. **Clear, Specific Assertions**

✅ **Good (test_status_change_helpers.py):**
```python
assert result["status_enum"] == Status.CLOSED
assert result["github_state"] == "closed"
assert isinstance(issue_result["status_enum"], Status)
```

❌ **Vague (avoid):**
```python
assert report is not None  # What does report contain?
assert isinstance(report, SyncReport)  # Just type check, no behavior
```

**Principle:** Each test should assert ONE clear behavior. Use multiple small tests instead of mega-tests.

### 4. **Comprehensive Test Coverage at Each Layer**

#### Layer 1: Helpers & Utilities
**Status:** ✅ **EXCELLENT** - test_status_change_helpers.py

33 unit tests covering:
- Valid inputs (all Status/MilestoneStatus enum values)
- Invalid inputs (wrong format, bad values, None)
- Edge cases (whitespace, empty strings)
- Integration between helpers
- Type consistency

**Pattern to replicate for:**
- More helpers in `core/services/helpers/`
- Config validation helpers
- Status mapping logic

#### Layer 2: Service Layer (github_sync_orchestrator.py)
**Status:** ⚠️ **NEEDS IMPROVEMENT**

Current tests use lots of mocks. Should have:
1. **Unit tests** with real domain objects, mocked GitHub client
2. **Integration tests** with real objects and mocked API responses

**New Test Structure Needed:**
```python
class TestGitHubSyncOrchestratorWithRealObjects:
    """Test orchestrator with real domain objects, mocked API."""

    @pytest.fixture
    def sync_data(self):
        """Real test data using factories."""
        return {
            "issues": [IssueTestDataBuilder().with_github_issue(123).build()],
            "milestones": [MilestoneTestDataBuilder().with_github_milestone(1).build()],
        }

    @pytest.fixture
    def github_client_mock(self):
        """Mock GitHub API, not orchestrator internals."""
        return AsyncMock(spec=GitHubIssueClient)

    def test_detect_milestone_changes_with_real_data(self, sync_data, github_client_mock):
        """Test change detection with real milestone objects."""
        milestone = sync_data["milestones"][0]
        github_client_mock.get_milestone.return_value = {"title": "old", "state": "open"}

        orchestrator = GitHubSyncOrchestrator(mock_core, config=GITHUB_CONFIG)
        orchestrator.github_client = github_client_mock

        # Test actual behavior
        changes = orchestrator._detect_milestone_changes(milestone)

        # Assert specific changes detected
        assert changes is not None
        assert "title" in changes.local_changes  # Real field names
        github_client_mock.get_milestone.assert_called_once()
```

#### Layer 3: Backend Adapters (github_sync_backend.py)
**Status:** ⚠️ **NEEDS IMPROVEMENT**

Should test:
1. Backend initialization with/without token
2. Proper error handling from `_safe_init()`
3. Configuration validation
4. Method routing to handlers

**Example:**
```python
class TestGitHubSyncBackendInitialization:
    """Test GitHub backend safe initialization."""

    def test_safe_init_with_valid_token(self, mock_core):
        """Test backend initializes with valid token."""
        config = {"owner": "user", "repo": "repo", "token": "ghp_valid"}

        backend = GitHubSyncBackend(mock_core, config)

        assert backend.github_client is not None
        assert backend.metadata_service is not None

    def test_safe_init_without_token_defers(self, mock_core):
        """Test backend defers initialization without token."""
        config = {"owner": "user", "repo": "repo"}  # No token

        backend = GitHubSyncBackend(mock_core, config)

        # Should still be None until authenticate() called
        assert backend.github_client is None

    def test_safe_init_handles_bad_client_factory(self, mock_core):
        """Test _safe_init gracefully handles initialization failures."""
        config = {"owner": "user", "repo": "repo", "token": "ghp_bad"}

        with patch("roadmap.adapters.sync.backends.github_sync_backend.GitHubIssueClient",
                   side_effect=ValueError("Invalid token")):
            backend = GitHubSyncBackend(mock_core, config)

            # Should log warning and continue
            assert backend.github_client is None
            # Verify logging happened
            assert backend.conflict_detector is None  # Also safe-init'd
```

#### Layer 4: Integration Tests
**Status:** ✅ **GOOD** - tests/integration/ exists

Keep these but ensure they:
1. Test complete workflows (fetch → detect → apply)
2. Use real objects where safe
3. Mock external systems (GitHub API, git commands)
4. Have clear expected outcomes

---

## Recommended Test Writing Checklist

Before writing a test, ask:

- [ ] **What layer is this?** (unit helpers, service, adapter, integration)
- [ ] **Does it use real domain objects?** (factories instead of mocks when possible)
- [ ] **Does it test behavior?** (not just "object created" or "method called")
- [ ] **Are assertions specific?** (not just `assert result` or `assert not None`)
- [ ] **Does it cover edge cases?** (None, empty, invalid values)
- [ ] **Is it isolated?** (one behavior per test, max 1-2 assertions per test concept)
- [ ] **Would someone understand what broke from the test name?** (descriptive names)
- [ ] **Does it follow existing patterns in this layer?** (consistency)

---

## Sync Testing Improvements (Immediate Actions)

Based on your recent refactoring, you should now add these test suites:

### 1. Test the `_get_owner_repo()` helper
```python
class TestGitHubSyncOrchestratorConfigHelper:
    def test_get_owner_repo_valid_config(self, orchestrator):
        result = orchestrator._get_owner_repo()
        assert result == ("user", "repo")

    def test_get_owner_repo_missing_owner(self, orchestrator):
        orchestrator.config["owner"] = None
        result = orchestrator._get_owner_repo()
        assert result is None
```

### 2. Test the 6 refactored methods with real milestone/issue objects
```python
class TestGitHubSyncOrchestratorRefactoredMethods:
    def test_create_milestone_on_github(self, orchestrator, real_milestone):
        orchestrator.github_client = mock_handler
        orchestrator._create_milestone_on_github(real_milestone.name)
        # Assert milestone linked properly
```

### 3. Test status change helpers in orchestrator context
```python
class TestGitHubSyncOrchestratorStatusMapping:
    def test_milestone_status_update_with_helpers(self):
        # Use extract_milestone_status_update directly
        # Verify orchestrator uses it correctly
```

---

## Summary

**Action Priority:**

1. **HIGH:** Create comprehensive sync integration tests (demonstrating the refactoring benefits)
2. **HIGH:** Add layer-2 service tests for orchestrator with real objects
3. **MEDIUM:** Migrate `test_cli/` → `unit/presentation/` (no breaking changes)
4. **MEDIUM:** Create test data builders for sync-specific objects
5. **LOW:** Clean up old test directories (`test_sync_*`, `test_roadmap_debug`)

**Your test suite is now ready for this work** - the status_change_helpers tests demonstrate best practices you can replicate across all layers.
