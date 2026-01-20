# DRY Violations Remediation Plan

Strategic approach to addressing 784 code duplication patterns identified across the Roadmap codebase.

---

## Executive Summary

**Current State**: 784 total pattern occurrences across 6 duplication types
- Mock Setup: 316 occurrences
- Patch Pattern: 284 occurrences
- Temp Directory: 133 occurrences
- RoadmapCore Init: 26 occurrences
- Issue Creation: 22 occurrences
- Mock Persistence: 3 occurrences

**Focus**: ~90% of violations are in the **test suite** (test fixtures, setup code, mocking patterns)

**Timeline**: Phased approach over 2-3 sessions
**Priority**: High - improves test maintainability and readability

---

## Phase 1: Foundation (Immediate - 1 Session)

### 1.1 Create Shared Test Fixtures (`tests/conftest.py`)

**Goal**: Centralize common test fixtures and utilities

**Status**: Tests already exist with repeated patterns - consolidate into fixtures

```python
# tests/conftest.py (new/expanded)

import pytest
from unittest.mock import MagicMock
from pathlib import Path
import tempfile

# === Persistence Fixtures ===

@pytest.fixture
def mock_persistence():
    """Shared mock for PersistenceInterface."""
    return MagicMock(spec=PersistenceInterface)

@pytest.fixture
def temp_dir():
    """Temporary directory fixture replacing tempfile.TemporaryDirectory()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

# === Issue Factory Fixture ===

@pytest.fixture
def issue_factory():
    """Factory for creating test issues with defaults."""
    def _create(
        id="test-1",
        title="Test Issue",
        status=Status.TODO,
        priority=Priority.MEDIUM,
        **kwargs
    ):
        return Issue(
            id=id,
            title=title,
            status=status,
            priority=priority,
            **kwargs
        )
    return _create

# === RoadmapCore Fixture ===

@pytest.fixture
def roadmap_core():
    """Shared RoadmapCore instance for integration tests."""
    return RoadmapCore()

# === Mock Setup Helpers ===

@pytest.fixture
def mock_github_client():
    """Shared mock GitHub client."""
    return MagicMock(spec=GitHubBackendInterface)

@pytest.fixture
def mock_git_service():
    """Shared mock Git service."""
    return MagicMock(spec=GitService)
```

**Files to Update**:
- `tests/conftest.py` - Add fixtures
- `tests/unit/conftest.py` - Layer-specific fixtures
- `tests/unit/core/conftest.py` - Core service fixtures
- `tests/unit/infrastructure/conftest.py` - Infrastructure fixtures
- `tests/unit/adapters/conftest.py` - Adapter fixtures

**Estimated Effort**: 2-3 hours
**DRY Violations Reduced**: ~100-150 (Mock Persistence 3, partial RoadmapCore init)

---

### 1.2 Create Test Data Factory Module

**Goal**: Replace 22 duplicated `Issue()` creations with factory pattern

**File**: `tests/fixtures/issue_factory.py` (new)

```python
"""Factory for creating test issues with common defaults."""

from roadmap.core.domain.entities import Issue, Status, Priority

class IssueFactory:
    """Factory for creating test Issue instances."""

    @staticmethod
    def create(
        id="issue-1",
        title="Test Issue",
        status=Status.TODO,
        priority=Priority.MEDIUM,
        assignee=None,
        progress=0,
        **kwargs
    ) -> Issue:
        """Create an Issue with sensible defaults."""
        return Issue(
            id=id,
            title=title,
            status=status,
            priority=priority,
            assignee=assignee,
            progress=progress,
            **kwargs
        )

    @staticmethod
    def create_in_progress(id="issue-1", **kwargs) -> Issue:
        """Create an in-progress issue."""
        return IssueFactory.create(id=id, status=Status.IN_PROGRESS, **kwargs)

    @staticmethod
    def create_done(id="issue-1", **kwargs) -> Issue:
        """Create a completed issue."""
        return IssueFactory.create(id=id, status=Status.DONE, progress=100, **kwargs)

    @staticmethod
    def create_blocked(id="issue-1", **kwargs) -> Issue:
        """Create a blocked issue."""
        return IssueFactory.create(id=id, status=Status.BLOCKED, **kwargs)

    @staticmethod
    def create_batch(count=5, **kwargs) -> list[Issue]:
        """Create multiple issues for batch testing."""
        return [
            IssueFactory.create(id=f"issue-{i}", **kwargs)
            for i in range(count)
        ]
```

**Usage**: Replace all `Issue(id="...", title="...", ...)` with `IssueFactory.create(...)`

**Files to Update**:
- `tests/unit/core/services/test_sync_state_updates.py` (6 occurrences)
- `tests/unit/adapters/sync/test_sync_services.py` (8 occurrences)
- `tests/integration/test_duplicate_prevention.py` (2 occurrences)
- Other test files with Issue creation patterns

**Estimated Effort**: 1-2 hours
**DRY Violations Reduced**: ~22 (Issue Creation pattern)

---

### 1.3 Create Pytest Plugin for Common Patches

**Goal**: Centralize decorator patterns to reduce patch repetition

**File**: `tests/fixtures/patch_helpers.py` (new)

```python
"""Common patch helpers and decorators for testing."""

from unittest.mock import patch
from functools import wraps

# Common patch targets
HEALTH_VALIDATOR_PATCH = "roadmap.core.services.health.infrastructure_validator"
BUILTIN_OPEN_PATCH = "builtins.open"
GIT_REPO_PATCH = "roadmap.adapters.git.repo"

def with_health_validator(test_func):
    """Decorator that patches health validator."""
    @patch(HEALTH_VALIDATOR_PATCH)
    @wraps(test_func)
    def wrapper(*args, **kwargs):
        return test_func(*args, **kwargs)
    return wrapper

def with_file_operations(test_func):
    """Decorator that patches file operations."""
    @patch(BUILTIN_OPEN_PATCH, create=True)
    @patch(GIT_REPO_PATCH)
    @wraps(test_func)
    def wrapper(*args, **kwargs):
        return test_func(*args, **kwargs)
    return wrapper
```

**Estimated Effort**: 1 hour
**DRY Violations Reduced**: ~50-75 (partial Patch Pattern)

---

## Phase 2: Core Consolidation (Session 2)

### 2.1 Consolidate Mock Setup Patterns (316 occurrences)

**Goal**: Replace individual `MagicMock()` calls with typed fixtures

**Strategy**:
1. Identify common mock types across tests
2. Create fixture variants in layer-specific conftest files
3. Replace inline mocks with fixture parameters

**Implementation Steps**:

```python
# Before (repeated in 316 places)
@patch("some.path")
def test_something(mock_obj):
    mock_dir = MagicMock()
    mock_test_file = MagicMock()
    # ... rest of test

# After (with fixture)
def test_something(mock_dir, mock_test_file):
    # ... rest of test
```

**Files to Create**:
- `tests/fixtures/mock_builders.py` - Common mock creation
- Layer-specific conftest fixtures

**Estimated Effort**: 3-4 hours
**DRY Violations Reduced**: ~200-250 (Mock Setup pattern)

---

### 2.2 Replace Patch Decorators with Pytest Plugin

**Goal**: Reduce 284 patch decorator occurrences

**Strategy**:
1. Use `pytest.mark.patch` for common patches
2. Create parametrized fixtures for parameterized tests
3. Move to fixture injection where possible

**Estimated Effort**: 3-4 hours
**DRY Violations Reduced**: ~100-150 (Patch Pattern)

---

### 2.3 Migrate TemporaryDirectory Usage (133 occurrences)

**Goal**: Use pytest's `tmp_path` fixture instead of `tempfile.TemporaryDirectory()`

**Strategy**:
1. Replace `with tempfile.TemporaryDirectory() as tmpdir:` with `tmp_path` fixture parameter
2. Adjust path handling (tmp_path is Path object, not string)
3. Update code that depends on string paths

**Before**:
```python
def test_something():
    with tempfile.TemporaryDirectory() as tmpdir:
        # use tmpdir as string path
```

**After**:
```python
def test_something(tmp_path):
    # use tmp_path as Path object
```

**Estimated Effort**: 2-3 hours
**DRY Violations Reduced**: ~133 (Temp Directory pattern)

---

### 2.4 Reorganize `tests/unit/core/services/` Directory Structure

**Goal**: Reduce root-level test files from 30+ to ~6-8 for better navigation

**Strategy**: Create subdirectories by service domain

**Subdirectories to create**:
- `baseline/` - Baseline state management (4 files)
- `github/` - GitHub integration (4 files)
- `comment/` - Comment service (3 files)
- `health/` - Entity health/validation/repair (5 files)
- `git/` - Git-related services (2 files)
- `issue/` - Issue services (2 files)
- `milestone/` - Milestone services (1 file)
- `analysis/` - Analysis/analysis services (4 files)
- `backup/` - Backup/cleanup services (2 files)

**Result**: ~27 files organized into 9 logical subdirectories, leaving 6-8 general service tests at root

**Estimated Effort**: 30 minutes - 1 hour (mostly moving files, no code changes)
**Impact**: Improved test discoverability and maintainability

---

### 2.4.5 Reorganize `tests/integration/` Directory Structure

**Goal**: Reduce root-level test files from 59 to ~4 for significantly better navigation

**Current State**: 59 test files at root level, very difficult to navigate

**Strategy**: Create 12 logical subdirectories by feature/domain

**Subdirectories to create**:
- `cli/` - CLI command tests (6 files)
- `core/` - Core RoadmapCore operations (10 files)
- `git/` - Git integration (7 files)
- `github/` - GitHub sync backend (5 files)
- `git_hooks/` - Git hooks workflow (7 files)
- `archive/` - Archive/restore operations (3 files)
- `lifecycle/` - Issue/Milestone lifecycle (4 files)
- `workflows/` - Cross-domain workflows (4 files)
- `data/` - Data/filtering/constraints (4 files)
- `init/` - Initialization/onboarding (2 files)
- `view/` - View/presentation tests (3 files)
- `performance/` - Performance/stress tests (1 file)

**Files Remaining at Root**: ~4 general integration tests

**Estimated Effort**: 1-2 hours (file moves + import path updates)
**Impact**: Improved test navigation and discoverability
**Note**: No DRY violations to eliminate (organizational improvement)

---

### 2.4.9 Investigate Top-Level Test Directory Consolidation

**Goal**: Determine optimal organization for top-level test directories and resolve potential redundancy

**Investigation Points**:

1. **`tests/common/` vs `tests/test_common/`**
   - Do both directories exist?
   - What's the purpose/content of each?
   - Should one absorb the other?
   - Recommendation: Consolidate or eliminate duplicate

2. **`tests/core/` vs `tests/test_core/`**
   - Do both directories exist?
   - Is one nested integration tests and one unit tests?
   - Should one absorb the other?
   - Could content move into `tests/unit/core/`?
   - Recommendation: Consolidate or clarify purpose

3. **`tests/test_cli/` naming inconsistency**
   - Why prefix with `test_` when it's already in tests/ directory?
   - Option A: Rename to `tests/cli/` for consistency
   - Option B: Is this already covered by `tests/integration/cli/`?
   - Option C: Move content into `tests/integration/cli/` and remove redundancy
   - Recommendation: Align with overall structure

**Estimated Effort**: 30-45 minutes (investigation + decisions)
**Outcome**: Clear consolidation plan to eliminate directory redundancy

**Follow-up**: Phase 2.4.10 (TBD based on findings)

---

## Phase 3: Integration & Cleanup (Session 3)

### 3.1 Consolidate RoadmapCore Initialization (26 occurrences)

**Status**: Already partially addressed with fixture in Phase 1

**Additional**: Ensure all tests using RoadmapCore use the fixture, not direct instantiation

**Estimated Effort**: 30 minutes
**DRY Violations Reduced**: ~26 (RoadmapCore Init pattern)

---

### 3.2 Validate Test Suite Integrity

**Goal**: Ensure all refactoring maintains test functionality

```bash
# Run full test suite with parallelization
poetry run pytest tests/ -v --tb=short -n auto

# Verify coverage unchanged
poetry run pytest tests/ --cov --cov-report=term-missing

# Check for fixture scope issues
poetry run pytest tests/ --fixtures
```

**Estimated Effort**: 1-2 hours

---

### 3.3 Verify DRY Scanner Results

```bash
# Re-run DRY scanner to measure improvement
python3 scripts/scan_dry_violations.py
```

**Expected Results**:
- Mock Setup: 316 → ~50-75 (75% reduction)
- Patch Pattern: 284 → ~50-100 (65% reduction)
- Temp Directory: 133 → 0 (100% reduction)
- Issue Creation: 22 → 0 (100% reduction)
- RoadmapCore Init: 26 → 0 (100% reduction)
- Mock Persistence: 3 → 0 (100% reduction)

**New Total**: ~100-200 occurrences (down from 784)

---

## Implementation Roadmap

### Session 1: Foundation (3-4 hours)
- [ ] Phase 1.1: Create conftest fixtures (2-3h)
- [ ] Phase 1.2: Create IssueFactory (1-2h)
- [ ] Phase 1.3: Create patch helpers (1h)
- [ ] Test suite validation

### Session 2: Core Consolidation (6-8 hours)
- [ ] Phase 2.1: Consolidate mock setup (3-4h)
- [ ] Phase 2.2: Replace patch decorators (3-4h)
- [ ] Phase 2.3: Migrate TemporaryDirectory (2-3h)
- [ ] Test suite validation

### Session 3: Integration (2-3 hours)
- [ ] Phase 3.1: Consolidate RoadmapCore (30m)
- [ ] Phase 3.2: Full test validation (1-2h)
- [ ] Phase 3.3: DRY scanner verification (30m)

---

## Success Criteria

✅ **Quantitative**:
- Reduce 784 violations to <200 occurrences
- Maintain 100% test pass rate (6,558 tests)
- No new Pylance errors
- Coverage unchanged or improved

✅ **Qualitative**:
- Tests are more readable (factory patterns vs. inline creation)
- Setup code is centralized and maintainable
- New tests can easily follow established patterns
- Test debugging is easier with clear fixtures

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Fixture scope issues | Test with `pytest --fixtures` before and after |
| Fixture parameter hell | Limit fixtures per test to 5-6 parameters |
| Path vs string confusion | Create clear Path/string handling helpers |
| Performance regression | Monitor test execution time with `pytest-benchmark` |

---

## Files to Create/Modify

### New Files
- `tests/fixtures/issue_factory.py` - Issue factory
- `tests/fixtures/patch_helpers.py` - Patch decorators
- `tests/fixtures/mock_builders.py` - Mock factories
- `tests/unit/conftest.py` - Layer conftest
- `tests/unit/core/conftest.py` - Core layer conftest
- `tests/unit/infrastructure/conftest.py` - Infrastructure conftest
- `tests/unit/adapters/conftest.py` - Adapter conftest

### Modified Files
- `tests/conftest.py` - Root fixtures
- `tests/unit/core/services/test_sync_state_updates.py`
- `tests/unit/adapters/sync/test_sync_services.py`
- And 80+ additional test files using the patterns

---

## Next Steps

1. **Tomorrow Morning**: Review and approve this plan
2. **Start Phase 1.1**: Create root conftest fixtures
3. **In Parallel**: Create issue factory and patch helpers
4. **Session 2**: Consolidate mock patterns
5. **Session 3**: Clean up and validate

---

**Created**: January 15, 2026
**Status**: Ready for implementation
**Estimated Total Effort**: 11-15 hours over 3 sessions
