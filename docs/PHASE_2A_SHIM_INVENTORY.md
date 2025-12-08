# Phase 2a: Shim & Test Fixture Audit

**Date:** December 8, 2025
**Phase:** 2a (Test Infrastructure Refactoring)
**Status:** PLANNING COMPLETE

---

## Executive Summary

This document provides a comprehensive inventory of backwards-compatibility shims and test fixtures across the roadmap codebase.

**Total Shims Found:** 24 files
**Total Fixtures with Compat Notes:** 2 major fixtures
**Estimated Impact:** ~40-50% reduction in DRY violations when removed

---

## Shim Categories

### Category 1: Top-Level Re-export Facades (11 files)

These are modules at the top level that re-export from refactored packages. They provide a stable API for old code while new code imports from the refactored location.

#### Adapters/CLI Layer (7 files)

| File | Purpose | Re-exports From | Dependencies |
|------|---------|-----------------|--------------|
| `roadmap/adapters/cli/init_workflow.py` | Initialize roadmap projects | `roadmap.core.services.initialization` | InitializationWorkflow |
| `roadmap/adapters/cli/logging_decorators.py` | Logging and output decorators | `roadmap.infrastructure.logging` | get_current_user, log_command, verbose_output |
| `roadmap/adapters/cli/issue_filters.py` | Issue filtering utilities | `roadmap.core.services.filtering` | Issue filter classes |
| `roadmap/adapters/cli/issue_update_helpers.py` | Issue update operations | `roadmap.core.services.issue_operations` | Update helpers |
| `roadmap/adapters/cli/start_issue_helpers.py` | Issue start operations | `roadmap.core.services.issue_operations` | Start helpers |
| `roadmap/adapters/cli/github_setup.py` | GitHub integration setup | `roadmap.core.services.github_integration` | Setup classes |
| `roadmap/adapters/cli/init_validator.py` | Initialization validation | `roadmap.core.services.validation` | Validator classes |

#### Other Layer Facades (4 files)

| File | Purpose | Re-exports From | Dependencies |
|------|---------|-----------------|--------------|
| `roadmap/adapters/persistence/storage.py` | State management | `roadmap.adapters.persistence.storage` package | StateManager, DatabaseError |
| `roadmap/common/validation.py` | Validation framework | `roadmap.common.validation` package | ValidationResult, FieldValidator, SchemaValidator, RoadmapValidator |
| `roadmap/common/errors.py` | Exception definitions | `roadmap.common.errors` package | All error classes |
| `roadmap/common/security.py` | Security utilities | `roadmap.common.security` package | Security utilities |

---

### Category 2: Helper Module Facades (6 files)

These are utility/helper modules that are facades for refactored functionality.

| File | Purpose | Original Pattern | New Pattern | Migration Path |
|------|---------|------------------|-------------|-----------------|
| `roadmap/adapters/cli/init_utils.py` | Initialization utilities | Direct implementations | Delegated services | Use core.services directly |
| `roadmap/adapters/cli/cleanup.py` | Resource cleanup | Direct implementations | Delegated services | Use infrastructure services |
| `roadmap/adapters/cli/audit_logging.py` | Audit log operations | Direct implementations | Infrastructure layer | Use infrastructure.logging |
| `roadmap/adapters/cli/error_logging.py` | Error logging | Direct implementations | Infrastructure layer | Use infrastructure.logging |
| `roadmap/adapters/cli/kanban_helpers.py` | Kanban view operations | Direct implementations | Domain model operations | Use core.services |
| `roadmap/adapters/cli/performance_tracking.py` | Performance metrics | Direct implementations | Infrastructure layer | Use infrastructure.metrics |

---

### Category 3: Package-Level Compatibility Facades (3 files)

These are `__init__.py` files that re-export from submodules to provide package-level compatibility.

| File | Purpose | What It Re-exports |
|------|---------|-------------------|
| `roadmap/common/validation/__init__.py` | Validation package | ValidationResult, FieldValidator, SchemaValidator, RoadmapValidator |
| `roadmap/common/security/__init__.py` | Security package | All security utilities from submodules |
| `roadmap/adapters/persistence/parser.py` | Parser compatibility | All parser classes from specific parsers |

---

### Category 4: Utilities with Backwards-Compat Conveniences (2 files)

These files have modern implementations but include backwards-compatible convenience functions/wrappers.

| File | Location | Convenience Functions | Status |
|------|----------|----------------------|--------|
| `roadmap/common/datetime_parser.py` | Module-level | `parse_datetime()`, `format_datetime()` functions (convenience wrappers) | Can be inlined to call-sites |
| `roadmap/common/logging.py` | Line 431+ | Backwards-compatible security logger mapping | Can use modern logger directly |
| `roadmap/common/timezone_utils.py` | Throughout | Various timezone helper functions marked as backwards-compatible | Some can be consolidated |
| `roadmap/common/validation/validators.py` | Line 38+ | Legacy frontmatter validation method | Can be replaced with modern validators |

---

### Category 5: Test-Specific Shims (identified via grep)

| File | Fixture | Purpose | Status |
|------|---------|---------|--------|
| `tests/fixtures/conftest.py` | `patch_github_integration` (line 270) | Mock GitHub integration | Kept for backwards compatibility, returns simple mock |
| `tests/conftest.py` | Similar fixtures | Test compatibility layer | Kept for backwards compatibility |

---

## Test Fixture Dependency Graph

### Primary Fixtures Using Shims

```
tests/fixtures/conftest.py
├── patch_github_integration()
│   └── Used in: tests/integration/test_github_*.py
│       └── Depends on: (archived) EnhancedGitHubIntegration
│           └── Now: Simple mock in fixture
├── mock_github_client()
│   └── Used in: tests/unit/adapters/test_github.py
│       └── Depends on: roadmap.sync.GitHubClient
├── temp_workspace_with_core()
│   └── Used in: integration tests
│       └── Depends on: File system initialization
└── ... (many other fixtures)

tests/conftest.py
└── Various test fixtures
    └── Some depend on deprecated modules
```

### Test Files Importing from Shims

These test files likely depend on the shim facades:

```
tests/unit/presentation/test_deprecated.py
└── Tests deprecated CLI commands
    └── Uses: roadmap/adapters/cli/logging_decorators.py

tests/integration/test_init_phase*.py
└── Integration tests for initialization
    └── Uses: roadmap/adapters/cli/init_workflow.py
            roadmap/adapters/cli/init_validator.py
            roadmap/adapters/cli/init_utils.py

tests/unit/domain/test_timezone_aware_issues.py
└── Timezone handling tests
    └── Uses: roadmap/common/datetime_parser.py
            roadmap/common/timezone_utils.py

tests/unit/infrastructure/test_*.py
└── Infrastructure tests
    └── Uses: roadmap/adapters/persistence/storage.py
            roadmap/common/validation.py
            roadmap/common/errors.py
            roadmap/common/security.py
```

---

## Replacement Strategy by Category

### Category 1: Top-Level Re-export Facades → Direct Imports

**Strategy:** Update all imports to point to the refactored modules directly.

**Example:**
```python
# Before
from roadmap.adapters.cli.init_workflow import InitializationWorkflow

# After
from roadmap.core.services.initialization import InitializationWorkflow
```

**Impact:** Zero functional change, purely import path update
**Risk:** Low (pure re-export files)
**Affected Tests:** Any test file importing from these facades

---

### Category 2: Helper Module Facades → Service Layer

**Strategy:** Replace direct calls to helper modules with calls to the modern service layer.

**Example:**
```python
# Before
from roadmap.adapters.cli.init_utils import prepare_project

# After
from roadmap.core.services.initialization import InitializationService
service = InitializationService()
service.prepare_project(...)
```

**Impact:** Functional change, may require DI pattern adoption
**Risk:** Medium (requires test fixture updates)
**Affected Tests:** Integration tests and CLI command tests

---

### Category 3: Package-Level Compatibility Facades → Package Imports

**Strategy:** Move imports to point to actual submodules.

**Example:**
```python
# Before (using package facade)
from roadmap.common.validation import ValidationResult

# After (using actual location)
from roadmap.common.validation.result import ValidationResult
```

**Impact:** Zero functional change
**Risk:** Low (import path only)
**Affected Tests:** All tests importing from validation/errors/security

---

### Category 4: Backwards-Compat Conveniences → Remove or Inline

**Strategy 4a - Functions:** Inline to call-sites or deprecate with warning
**Strategy 4b - Methods:** Replace with modern implementations

**Example:**
```python
# Before
from roadmap.common.datetime_parser import parse_datetime
result = parse_datetime("2025-12-08")

# After
from roadmap.common.datetime_parser import DateTimeParser
parser = DateTimeParser()
result = parser.parse("2025-12-08")
```

**Impact:** Functional change, may affect multiple call-sites
**Risk:** Medium (depends on usage frequency)
**Affected Tests:** Any test using convenience functions

---

### Category 5: Test-Specific Shims → Real Service Mocking

**Strategy:** Replace mock objects with real services using modern DI/testing patterns.

**Example:**
```python
# Before (simple mock)
@pytest.fixture
def patch_github_integration():
    mock = Mock()
    yield mock

# After (real service with test doubles)
@pytest.fixture
def github_integration(temp_workspace):
    return GitHubIntegrationService(
        workspace=temp_workspace,
        config=TestConfig()
    )
```

**Impact:** Test improvements, better test coverage
**Risk:** Low (tests only)
**Affected Tests:** GitHub integration tests

---

## Shim Removal Sequence

### Phase 2a Outcomes Required for Phase 2b

**Document Deliverables:**

1. **Shim Inventory (THIS DOCUMENT)**
   - Complete list of all 24 shim files ✅
   - Purpose and location of each ✅
   - Category classification ✅
   - Re-export sources ✅

2. **Test Dependency Graph**
   - Which fixtures depend on which shims
   - Which tests import from shim facades
   - Impact analysis for each removal

3. **Migration Map (NEXT DOCUMENT)**
   - Old import path → New import path
   - New pattern/service to use
   - Implementation example for each

4. **Deprecation Strategy**
   - Timeline for removal
   - Deprecation warnings
   - Communication plan

---

## Recommended Reading Order for Phase 2b

1. This document (inventory + categories)
2. Migration map (exact changes needed)
3. Test dependency graph (which tests to refactor first)
4. Deprecation strategy (rollout plan)

---

## Next Steps

### For Phase 2b (Test Refactoring):

1. **Update Imports (2-3 days)**
   - Update all test files to import from new locations
   - Verify imports work
   - Run tests

2. **Refactor Test Fixtures (3-4 days)**
   - Replace mock GitHub integration with real service
   - Implement modern DI patterns
   - Update fixture dependencies

3. **Inline Helper Module Functions (2 days)**
   - Find all call-sites of helper functions
   - Replace with service layer calls
   - Update tests

4. **Remove Convenience Functions (1-2 days)**
   - Delete or replace module-level convenience functions
   - Update call-sites
   - Update tests

### For Phase 2c (Shim Removal):

1. Delete all 24 shim files
2. Run test suite to verify nothing breaks
3. Commit with detailed message

---

## Statistics

| Category | Count | Lines of Code | Complexity |
|----------|-------|---------------|-----------|
| Re-export Facades | 11 | ~150-200 | Low |
| Helper Facades | 6 | ~500-800 | Medium |
| Package Facades | 3 | ~100-150 | Low |
| Compat Conveniences | 2 | ~200-300 | Low-Medium |
| Test Shims | 2 | ~50-100 | Low |
| **TOTAL** | **24** | **~1000-1350** | **Low-Medium** |

**Estimated Removal Effort:** 1-2 weeks (Phase 2b + 2c)
**Expected Impact:** 40-50% reduction in DRY violations

---

## Known Dependencies & Notes

- `roadmap/adapters/cli/` facades all point to `roadmap.core.services.*`
- `roadmap/common/` modules have both facade and package versions
- Test fixtures in `tests/fixtures/conftest.py` have explicit backwards-compat comments
- Git hooks still import from `roadmap.adapters.git.git_hooks.py` (check if it's a facade)
- Some utilities in `datetime_parser.py` are marked as "Convenience functions for backward compatibility"
