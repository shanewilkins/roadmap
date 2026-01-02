# Implementation Plan: Test Improvements for Sync Layer

## Overview
This plan systematizes the test improvements identified in TEST_IMPROVEMENTS.md. We'll progressively improve test coverage and quality across the sync layer and test organization.

---

## Phase 1: Directory Consolidation (Priority: MEDIUM, Effort: 4-6 hours)

### 1.1 Migrate test_cli/ → unit/presentation/

**Current State:**
- 29 test files in `tests/test_cli/`
- Already have some test files in `tests/unit/presentation/`
- Potential duplicate coverage

**Tasks:**
```
1. Audit all 29 files in tests/test_cli/
   - Identify duplicate coverage with unit/presentation/
   - Group by functionality
   - Create mapping document

2. Rename files for clarity (using patterns like completed work):
   - test_conflicts_errors.py → test_conflict_handling_errors.py
   - test_git_integration_commit_ops.py → test_git_operations_and_integration.py
   - test_health_scan_errors.py → test_health_check_and_scanning.py
   - etc.

3. Move files one category at a time:
   - Git operation tests → unit/presentation/
   - Conflict handling tests → unit/presentation/
   - Query/milestone tests → unit/presentation/
   - Health/scan tests → unit/presentation/

4. Update all import paths in moved files

5. Verify test discovery still works: pytest --collect-only
```

**Success Criteria:**
- All 29 tests pass in new location
- No duplicate test coverage
- Clear naming indicates what's being tested

### 1.2 Migrate test_core/ and test_common/

**Current State:**
- 1 test file in `tests/test_core/`
- 1 test file in `tests/test_common/`

**Tasks:**
```
1. Identify correct destination:
   - test_core/* → tests/unit/core/services/ or tests/unit/domain/
   - test_common/* → tests/unit/common/ or tests/unit/shared/

2. Move files and update imports

3. Consolidate with existing tests if duplicates exist
```

### 1.3 Consolidate test_sync_* directories

**Current State:**
- `tests/test_sync_backend/` - empty except test data dirs
- `tests/test_sync_init/` - empty except test data dirs
- `tests/test_git_integration/` - unclear purpose

**Tasks:**
```
1. Archive or remove test_sync_backend/ and test_sync_init/
   (they appear to be test data containers, not test files)

2. Consolidate test_git_integration/ with integration/ tests

3. Verify no test files are lost:
   find tests/test_sync* -name "test_*.py" | wc -l
```

### 1.4 Move loose test files

**Current State:**
- 3 test files at `tests/` root level

**Tasks:**
```
1. Move to appropriate unit/ subdirectories
2. Update imports
3. Verify they run from new location
```

---

## Phase 2: Sync Layer Testing (Priority: HIGH, Effort: 8-12 hours)

### 2.1 Create GitHub Sync Test Data Builders

**Purpose:** Replace hardcoded test data with factories (following best practices)

**Files to Create:**
```
tests/factories/github_sync_data.py
  - IssueChangeTestBuilder
  - SyncReportTestBuilder
  - GitHubIssueTestBuilder
  - GitHubMilestoneTestBuilder
```

**Example Pattern (from sync_data.py):**
```python
class IssueChangeTestBuilder:
    """Build IssueChange objects for testing."""

    def __init__(self):
        self.issue_id = "test-issue"
        self.local_changes = None
        self.github_changes = None

    def with_local_changes(self, changes: dict):
        self.local_changes = changes
        return self

    def with_github_changes(self, changes: dict):
        self.github_changes = changes
        return self

    def build(self) -> IssueChange:
        return IssueChange(
            issue_id=self.issue_id,
            local_changes=self.local_changes,
            github_changes=self.github_changes,
            # ... other fields
        )
```

**Success Criteria:**
- All sync-related test data uses builders
- No hardcoded dictionaries in tests
- Builders reusable across test files

### 2.2 Add tests for `_get_owner_repo()` helper (tests/unit/core/services/)

**File:** `test_github_sync_orchestrator_config_helpers.py`

**Tests to Add:**
```python
class TestGitHubSyncOrchestratorConfigHelper:
    """Test config extraction helper method."""

    def test_get_owner_repo_with_valid_config(self, orchestrator):
        """Test extracting owner/repo from valid config."""
        result = orchestrator._get_owner_repo()
        assert result == ("user", "repo")

    def test_get_owner_repo_missing_owner(self, orchestrator):
        """Test returns None when owner missing."""
        orchestrator.config["owner"] = None
        assert orchestrator._get_owner_repo() is None

    def test_get_owner_repo_missing_repo(self, orchestrator):
        """Test returns None when repo missing."""
        orchestrator.config["repo"] = None
        assert orchestrator._get_owner_repo() is None

    def test_get_owner_repo_empty_config(self):
        """Test returns None with empty config."""
        orch = GitHubSyncOrchestrator(mock_core, config={})
        assert orch._get_owner_repo() is None
```

**Success Criteria:**
- Helper method fully tested with real domain objects
- All edge cases covered
- Tests demonstrate the refactoring benefit

### 2.3 Add integration tests for 6 refactored methods

**File:** `test_github_sync_orchestrator_refactored_methods.py`

**Tests to Add (one per method):**
```python
class TestGitHubSyncOrchestratorRefactoredMethods:
    """Test the 6 refactored methods that now use _get_owner_repo()."""

    @pytest.fixture
    def real_milestone(self):
        """Create real milestone using builder."""
        return MilestoneTestDataBuilder().with_github_milestone(123).build()

    @pytest.fixture
    def real_issue(self):
        """Create real issue using builder."""
        return IssueTestDataBuilder().with_github_issue(456).build()

    @pytest.fixture
    def mock_github_client(self):
        """Mock GitHub client (not orchestrator internals)."""
        return AsyncMock(spec=GitHubIssueClient)

    # 1. test_detect_milestone_changes
    def test_detect_milestone_changes_with_real_milestone(self, orchestrator, real_milestone, mock_github_client):
        """Test change detection uses _get_owner_repo() and handlers."""
        orchestrator.github_client = mock_github_client
        mock_github_client.get_milestone.return_value = {"title": "old", "state": "open"}

        changes = orchestrator._detect_milestone_changes(real_milestone)

        assert changes is not None
        # Verify it called the handler with correct owner/repo
        mock_github_client.get_milestone.assert_called_once()

    # 2. test_create_milestone_on_github
    def test_create_milestone_on_github(self, orchestrator, real_milestone, mock_github_client):
        """Test milestone creation via handler."""
        orchestrator.github_client = mock_github_client
        mock_github_client.create_milestone.return_value = {"number": 123}

        orchestrator._create_milestone_on_github(real_milestone.name)

        mock_github_client.create_milestone.assert_called_once()

    # 3. test_apply_archived_issue_to_github
    # 4. test_apply_restored_issue_to_github
    # 5. test_apply_archived_milestone_to_github
    # 6. test_apply_restored_milestone_to_github
```

**Success Criteria:**
- Each refactored method tested with real domain objects
- Handler calls verified (not orchestrator internals)
- Demonstrates _get_owner_repo() reduces duplicate code
- All tests pass

### 2.4 Add status mapping tests in orchestrator context

**File:** `test_github_sync_orchestrator_status_helpers.py`

**Tests to Add:**
```python
class TestGitHubSyncOrchestratorStatusHelpers:
    """Test status change helpers integration with orchestrator."""

    def test_extract_issue_status_update_via_orchestrator(self):
        """Test orchestrator uses extract_issue_status_update correctly."""
        orch = GitHubSyncOrchestrator(mock_core, config=GITHUB_CONFIG)

        # Test through orchestrator method
        result = orch._extract_status_update("todo -> closed")

        assert result is not None
        assert result["status_enum"] == Status.CLOSED
        assert result["github_state"] == "closed"

    def test_extract_milestone_status_update_via_orchestrator(self):
        """Test orchestrator uses extract_milestone_status_update correctly."""
        orch = GitHubSyncOrchestrator(mock_core, config=GITHUB_CONFIG)

        result = orch._extract_milestone_status_update("open -> closed")

        assert result is not None
        assert result["status_enum"] == MilestoneStatus.CLOSED
        assert result["github_state"] == "closed"
```

**Success Criteria:**
- Orchestrator properly delegates to helpers
- Status values correctly mapped to GitHub state
- All status enum values tested

---

## Phase 3: GitHub Backend Testing (Priority: HIGH, Effort: 6-8 hours)

### 3.1 Add GitHub backend initialization tests

**File:** `tests/unit/adapters/test_github_sync_backend_initialization.py`

**Tests to Add:**
```python
class TestGitHubSyncBackendInitialization:
    """Test safe initialization of GitHub backend."""

    def test_backend_safe_init_with_valid_token(self):
        """Test backend initializes successfully with token."""
        config = {"owner": "user", "repo": "repo", "token": "ghp_valid"}

        backend = GitHubSyncBackend(mock_core, config)

        assert backend.github_client is not None
        assert backend.metadata_service is not None

    def test_backend_safe_init_without_token(self):
        """Test backend defers initialization without token."""
        config = {"owner": "user", "repo": "repo"}  # No token

        backend = GitHubSyncBackend(mock_core, config)

        assert backend.github_client is None  # Deferred until authenticate()

    def test_backend_safe_init_graceful_failure(self):
        """Test _safe_init handles factory failures gracefully."""
        config = {"owner": "user", "repo": "repo", "token": "invalid"}

        with patch("roadmap.adapters.sync.backends.github_sync_backend.GitHubIssueClient",
                   side_effect=ValueError("Invalid token")):
            backend = GitHubSyncBackend(mock_core, config)

            # Should still initialize but with None client
            assert backend.github_client is None
            # Verify metadata service also safe-init'd
            # (can be None or real, depends on implementation)
```

**Success Criteria:**
- Backend initialization tested with real and invalid configs
- _safe_init() error handling verified
- Token handling correctly implemented

### 3.2 Add backend handler creation tests

**File:** `tests/unit/adapters/test_github_sync_backend_handlers.py`

**Tests to Add:**
```python
class TestGitHubSyncBackendHandlerCreation:
    """Test handler creation in backend."""

    def test_authenticate_creates_github_client(self):
        """Test authenticate() properly initializes client."""
        config = {"owner": "user", "repo": "repo", "token": "ghp_valid"}
        backend = GitHubSyncBackend(mock_core, config)

        # Should create client on demand
        result = backend.authenticate()

        # Verify client was created and authenticate succeeded
        assert backend.github_client is not None
```

---

## Phase 4: Service Layer Testing Improvements (Priority: MEDIUM, Effort: 8-10 hours)

### 4.1 Improve test_github_sync_orchestrator.py

**Current Issues:**
- Lots of patches of internal methods
- Not testing actual behavior with real objects

**Improvements:**
```python
class TestGitHubSyncOrchestratorWithRealObjects:
    """Test orchestrator with real domain objects."""

    @pytest.fixture
    def sync_data(self):
        """Real test data using factories."""
        return {
            "issues": [
                IssueTestDataBuilder().with_github_issue(123).build(),
                IssueTestDataBuilder().with_status(Status.CLOSED).build(),
            ],
            "milestones": [
                MilestoneTestDataBuilder().with_github_milestone(1).build(),
            ],
        }

    @pytest.fixture
    def github_client_mock(self):
        """Mock GitHub API, not orchestrator internals."""
        return AsyncMock(spec=GitHubIssueClient)

    def test_sync_all_linked_issues_with_real_data(self, orchestrator, sync_data, github_client_mock):
        """Test syncing actual domain objects."""
        # Setup
        orchestrator.github_client = github_client_mock
        for issue in sync_data["issues"]:
            orchestrator.core.issues.add(issue)

        # Execute
        report = orchestrator.sync_all_linked_issues(dry_run=False)

        # Assert
        assert isinstance(report, SyncReport)
        assert report.total_synced > 0
        github_client_mock.get_issue.assert_called()
```

**Success Criteria:**
- Tests use real domain objects
- Mock only external dependencies (GitHub API)
- Behavior-focused assertions
- Better coverage of actual sync logic

### 4.2 Create sync integration test suite

**File:** `tests/integration/test_github_sync_complete_workflow.py`

**Tests to Add:**
```python
class TestGitHubSyncCompleteWorkflow:
    """Test complete sync workflows with realistic data."""

    @pytest.fixture
    def github_api_mock(self):
        """Mock GitHub API responses."""
        return {
            "issues": [
                {"number": 1, "title": "Issue 1", "state": "open"},
                {"number": 2, "title": "Issue 2", "state": "closed"},
            ],
            "milestones": [
                {"number": 1, "title": "v1.0", "state": "open"},
            ]
        }

    def test_sync_fetch_detect_apply_workflow(self, orchestrator, github_api_mock):
        """Test complete workflow: fetch → detect → apply."""
        # Setup
        with patch.object(orchestrator, 'github_client') as mock_client:
            mock_client.get_issues.return_value = github_api_mock["issues"]
            mock_client.get_milestones.return_value = github_api_mock["milestones"]

            # Execute full workflow
            report = orchestrator.sync_all_linked_issues(dry_run=False)

            # Assert
            assert report.issues_synced >= 0
            assert report.milestones_synced >= 0
            assert report.total_synced >= 0
```

---

## Phase 5: Continuous Integration Tests (Priority: LOW, Effort: 4-6 hours)

### 5.1 Add missing assertion audit

**Purpose:** Ensure all tests have meaningful assertions

**Process:**
```
1. Find tests with only isinstance/is None assertions:
   grep -r "assert isinstance\|assert.*is None" tests/unit/

2. For each, ask:
   - Does it test actual behavior?
   - Is the assertion specific enough?
   - Could it be more meaningful?

3. Improve assertions to test business logic, not just types
```

### 5.2 Add vague assertion audit

**Purpose:** Eliminate empty or meaningless assertions

**Process:**
```
1. Find tests with vague assertions:
   grep -r "assert result\|assert report" tests/unit/ | grep -v "\["

2. Improve with specific field checks:
   Before: assert report
   After:  assert report.status == "success" and report.count > 0
```

---

## Implementation Checklist

### Phase 1: Directory Consolidation
- [ ] Audit all 29 test_cli/ files
- [ ] Create file mapping document
- [ ] Rename files for clarity
- [ ] Move to unit/presentation/ with updated imports
- [ ] Run `pytest --collect-only` to verify
- [ ] Run full test suite - all pass
- [ ] Migrate test_core/ and test_common/
- [ ] Archive/remove test_sync_* dirs
- [ ] Move loose test files

### Phase 2: Sync Layer Testing
- [ ] Create github_sync_data.py builders
- [ ] Add _get_owner_repo() tests
- [ ] Add tests for 6 refactored methods
- [ ] Add status helper integration tests
- [ ] Verify all sync tests use real objects
- [ ] Ensure handler calls mocked, not orchestrator internals

### Phase 3: GitHub Backend Testing
- [ ] Add initialization tests
- [ ] Add handler creation tests
- [ ] Test _safe_init() error handling
- [ ] Verify token handling

### Phase 4: Service Layer Improvements
- [ ] Refactor test_github_sync_orchestrator.py
- [ ] Create integration test suite
- [ ] Test complete workflows (fetch → detect → apply)
- [ ] All service tests using factories

### Phase 5: QA
- [ ] Audit for vague assertions
- [ ] Audit for missing assertions
- [ ] Verify 100% of sync-related tests have meaningful assertions
- [ ] Final full test run - all 6000+ tests pass

---

## Success Metrics

1. **Test Organization:**
   - 0 files in `test_cli/`, `test_core/`, `test_common/`, `test_sync_*`
   - All tests under `tests/unit/` or `tests/integration/`
   - Clear naming that indicates what's tested

2. **Test Quality:**
   - 100% of sync tests use factories, not hardcoded data
   - 0 tests with only `isinstance` or `is None` assertions
   - Every test has specific, behavior-focused assertions
   - Real domain objects used where safe

3. **Coverage:**
   - All 6 refactored methods have dedicated tests
   - Config helper (_get_owner_repo) fully tested
   - Status helpers tested in orchestrator context
   - GitHub backend initialization/handlers tested
   - Complete workflow tests

4. **Test Suite Health:**
   - All 6000+ tests passing
   - 0 flaky tests (no mocking of orchestrator internals)
   - Clear test names that describe business behavior
   - Documentation in TEST_IMPROVEMENTS.md accurate

---

## Estimated Timeline

- **Phase 1:** 1-2 sessions (4-6 hours)
- **Phase 2:** 2-3 sessions (8-12 hours)
- **Phase 3:** 1-2 sessions (6-8 hours)
- **Phase 4:** 2-3 sessions (8-10 hours)
- **Phase 5:** 1-2 sessions (4-6 hours)

**Total:** ~4-6 weeks at 2-3 sessions/week, or 2-3 weeks at 4-5 sessions/week

---

## Notes

- Start with Phase 2 if directory consolidation seems too large
- Phases can be parallelized (different team members on different phases)
- Test suite should remain passing throughout implementation
- Each phase adds value independently - can stop after any phase
- Documentation in TEST_IMPROVEMENTS.md should be updated as phases complete
