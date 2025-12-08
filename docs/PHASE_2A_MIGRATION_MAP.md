# Phase 2a: Migration Map

**Date:** December 8, 2025
**Phase:** 2a (Test Infrastructure Refactoring)
**Document Type:** Migration Guide

---

## Overview

This document provides exact import path changes and migration strategies for each of the 24 shim files identified in the Shim Inventory.

---

## Category 1: Re-export Facades (Import Path Changes)

### Adapters/CLI Layer Facades

#### 1. `roadmap/adapters/cli/init_workflow.py` → Direct Import

**Current Pattern:**
```python
from roadmap.adapters.cli.init_workflow import InitializationWorkflow
```

**New Pattern:**
```python
from roadmap.core.services.initialization import InitializationWorkflow
```

**Files to Update:**
- `tests/integration/test_init_phase*.py` (likely 3-4 files)
- Any CLI command files importing from this facade

**Changes Required:**
- Update import statements
- No code logic changes needed
- No test fixture changes needed

**Validation:**
```bash
grep -r "from roadmap.adapters.cli.init_workflow" tests/
grep -r "from roadmap.adapters.cli.init_workflow" roadmap/
```

---

#### 2. `roadmap/adapters/cli/logging_decorators.py` → Direct Import

**Current Pattern:**
```python
from roadmap.adapters.cli.logging_decorators import (
    get_current_user,
    log_command,
    verbose_output
)
```

**New Pattern:**
```python
from roadmap.infrastructure.logging import (
    get_current_user,
    log_command,
    verbose_output
)
```

**Files to Update:**
- All CLI command files
- Test files in `tests/unit/presentation/`
- Test files in `tests/integration/`

**Changes Required:**
- Update import paths
- Verify function signatures match
- No functional changes

**Validation:**
```bash
grep -r "from roadmap.adapters.cli.logging_decorators" .
grep -r "from roadmap.infrastructure.logging" .
```

---

#### 3. `roadmap/adapters/cli/issue_filters.py` → Direct Import

**Current Pattern:**
```python
from roadmap.adapters.cli.issue_filters import IssueFilterManager
```

**New Pattern:**
```python
from roadmap.core.services.filtering import IssueFilterManager
```

**Files to Update:**
- CLI issue commands
- Test files related to filtering

**Changes Required:**
- Update imports
- No code changes needed

---

#### 4. `roadmap/adapters/cli/issue_update_helpers.py` → Service Layer

**Current Pattern:**
```python
from roadmap.adapters.cli.issue_update_helpers import update_issue_status
update_issue_status(issue, new_status)
```

**New Pattern:**
```python
from roadmap.core.services.issue_operations import IssueOperationsService

# In test or command
service = IssueOperationsService(repository)
service.update_issue_status(issue, new_status)
```

**Complexity:** MEDIUM
**Impact:** Affects issue update command and related tests

**Changes Required:**
1. Update imports
2. Instantiate IssueOperationsService
3. Update all call-sites
4. Update test fixtures

**Test Fixtures to Update:**
- Add `issue_operations_service` fixture
- Update any fixtures that mock issue operations

---

#### 5. `roadmap/adapters/cli/start_issue_helpers.py` → Service Layer

**Current Pattern:**
```python
from roadmap.adapters.cli.start_issue_helpers import start_issue
start_issue(issue_id)
```

**New Pattern:**
```python
from roadmap.core.services.issue_operations import IssueOperationsService

service = IssueOperationsService(repository)
service.start_issue(issue_id)
```

**Complexity:** MEDIUM
**Impact:** Affects issue start command and related tests

**Changes Required:**
1. Update imports
2. Instantiate IssueOperationsService
3. Update all call-sites
4. Update test fixtures

---

#### 6. `roadmap/adapters/cli/github_setup.py` → Service Layer

**Current Pattern:**
```python
from roadmap.adapters.cli.github_setup import GitHubSetupService
service = GitHubSetupService()
```

**New Pattern:**
```python
from roadmap.core.services.github_integration import GitHubSetupService
service = GitHubSetupService()
```

**Complexity:** LOW
**Impact:** GitHub setup and initialization tests

**Changes Required:**
1. Update import path
2. No functional changes

---

#### 7. `roadmap/adapters/cli/init_validator.py` → Service Layer

**Current Pattern:**
```python
from roadmap.adapters.cli.init_validator import InitializationValidator
validator = InitializationValidator()
```

**New Pattern:**
```python
from roadmap.core.services.validation import InitializationValidator
validator = InitializationValidator()
```

**Complexity:** LOW
**Impact:** Initialization validation tests

**Changes Required:**
1. Update import path
2. No functional changes

---

### Common/Persistence Layer Facades

#### 8. `roadmap/adapters/persistence/storage.py` → Package Import

**Current Pattern:**
```python
from roadmap.adapters.persistence.storage import StateManager, initialize_state_manager
manager = StateManager()
```

**New Pattern:**
```python
from roadmap.adapters.persistence.storage.state_manager import StateManager
from roadmap.adapters.persistence.storage.initialization import initialize_state_manager
manager = StateManager()
```

**Complexity:** LOW
**Impact:** All infrastructure/persistence tests

**Changes Required:**
1. Update import paths
2. No code logic changes

**Files to Update:**
- `tests/unit/infrastructure/test_storage*.py`
- `tests/unit/infrastructure/test_file_synchronizer.py`
- `tests/integration/test_*.py`

---

#### 9. `roadmap/common/validation.py` → Package Import

**Current Pattern:**
```python
from roadmap.common.validation import (
    ValidationResult,
    FieldValidator,
    SchemaValidator,
    RoadmapValidator
)
```

**New Pattern:**
```python
from roadmap.common.validation.result import ValidationResult
from roadmap.common.validation.field_validator import FieldValidator
from roadmap.common.validation.schema_validator import SchemaValidator
from roadmap.common.validation.roadmap_validator import RoadmapValidator
```

**Complexity:** MEDIUM
**Impact:** All validation tests and any code using validation

**Changes Required:**
1. Update import statements
2. Verify all test fixtures still work
3. Check validation API compatibility

**Files to Update:**
- `tests/unit/common/test_validation*.py`
- `tests/unit/infrastructure/test_validation*.py`
- Any test file using validators

**Batch Migration:**
```bash
# Find all imports
grep -r "from roadmap.common.validation import" tests/ roadmap/

# After migration, verify
grep -r "from roadmap.common.validation" tests/ roadmap/ | grep -v "package"
```

---

#### 10. `roadmap/common/errors.py` → Package Import

**Current Pattern:**
```python
from roadmap.common.errors import (
    RoadmapError,
    ValidationError,
    StorageError,
    GitError
)
```

**New Pattern:**
```python
from roadmap.common.errors.base import RoadmapError
from roadmap.common.errors.validation import ValidationError
from roadmap.common.errors.storage import StorageError
from roadmap.common.errors.git import GitError
```

**Complexity:** LOW-MEDIUM
**Impact:** All tests and code using error classes

**Changes Required:**
1. Update import statements
2. No API changes
3. Verify error hierarchy still works

**Files to Update:**
- All test files (most likely use errors)
- All code files

**Batch Migration:**
```bash
# Phase 1: Add new imports alongside old ones
grep -r "from roadmap.common.errors import" . | head -20

# Phase 2: Update to new pattern
# Phase 3: Remove old facade
```

---

#### 11. `roadmap/common/security.py` → Package Import

**Current Pattern:**
```python
from roadmap.common.security import (
    SecurityError,
    validate_path,
    get_secure_home_dir
)
```

**New Pattern:**
```python
from roadmap.common.security.exceptions import SecurityError
from roadmap.common.security.path_validation import validate_path
from roadmap.common.security.file_operations import get_secure_home_dir
```

**Complexity:** MEDIUM
**Impact:** All security-related tests and initialization code

**Changes Required:**
1. Update import statements across codebase
2. Verify security functionality still works
3. Test file operations

**Files to Update:**
- `tests/unit/common/test_security*.py`
- Initialization code
- File operation code

---

## Category 2: Helper Module Facades (Functional Changes)

### Helper Facade Migration Strategy

For these modules, we need to:
1. Identify all usage patterns
2. Determine the new service layer equivalent
3. Update test fixtures to use services instead of direct calls
4. Update command implementations

---

#### 12. `roadmap/adapters/cli/init_utils.py` → Service Injection

**Current Pattern:**
```python
from roadmap.adapters.cli.init_utils import (
    create_directory_structure,
    create_config_file,
    initialize_git
)

create_directory_structure(project_path)
config = create_config_file(project_path, config_data)
```

**New Pattern:**
```python
from roadmap.core.services.initialization import InitializationService

service = InitializationService(workspace_path)
service.create_directory_structure()
config = service.create_config_file(config_data)
```

**Complexity:** MEDIUM
**Impact:** Initialization command and integration tests

**Changes Required:**
1. Find all usage of init_utils functions
2. Replace with InitializationService calls
3. Update DI container if needed
4. Update test fixtures

**Test Fixture Update:**
```python
# Before
@pytest.fixture
def init_utils_setup():
    pass  # Just imports the module

# After
@pytest.fixture
def initialization_service(temp_workspace):
    return InitializationService(temp_workspace)
```

---

#### 13. `roadmap/adapters/cli/cleanup.py` → Service Layer

**Current Pattern:**
```python
from roadmap.adapters.cli.cleanup import cleanup_workspace
cleanup_workspace(workspace_path)
```

**New Pattern:**
```python
from roadmap.infrastructure.lifecycle import WorkspaceLifecycleService

service = WorkspaceLifecycleService()
service.cleanup(workspace_path)
```

**Complexity:** LOW-MEDIUM
**Impact:** Cleanup commands and test teardown

**Changes Required:**
1. Find cleanup usage patterns
2. Replace with WorkspaceLifecycleService
3. Update test fixtures

---

#### 14. `roadmap/adapters/cli/audit_logging.py` → Infrastructure Layer

**Current Pattern:**
```python
from roadmap.adapters.cli.audit_logging import log_audit_event
log_audit_event(event_type, details)
```

**New Pattern:**
```python
from roadmap.infrastructure.logging import AuditLogger

audit_logger = AuditLogger()
audit_logger.log_event(event_type, details)
```

**Complexity:** LOW
**Impact:** Commands that perform auditable operations

**Changes Required:**
1. Replace direct calls with AuditLogger
2. Update any test fixtures that check audit logs

---

#### 15. `roadmap/adapters/cli/error_logging.py` → Infrastructure Layer

**Current Pattern:**
```python
from roadmap.adapters.cli.error_logging import log_error, format_error
log_error(exception)
```

**New Pattern:**
```python
from roadmap.infrastructure.logging import ErrorLogger

error_logger = ErrorLogger()
error_logger.log(exception)
```

**Complexity:** LOW
**Impact:** Error handling across CLI

**Changes Required:**
1. Replace calls with ErrorLogger
2. Update error formatting calls
3. Verify error messages still display correctly

---

#### 16. `roadmap/adapters/cli/kanban_helpers.py` → Service Layer

**Current Pattern:**
```python
from roadmap.adapters.cli.kanban_helpers import (
    render_kanban_board,
    get_board_columns
)

board = render_kanban_board(issues, milestones)
```

**New Pattern:**
```python
from roadmap.core.services.kanban import KanbanService

service = KanbanService(repository)
board = service.render_board(issues, milestones)
```

**Complexity:** MEDIUM
**Impact:** Kanban view command and related tests

**Changes Required:**
1. Replace with KanbanService calls
2. Update test fixtures
3. Update board rendering tests

---

#### 17. `roadmap/adapters/cli/performance_tracking.py` → Infrastructure Layer

**Current Pattern:**
```python
from roadmap.adapters.cli.performance_tracking import (
    start_timer,
    end_timer,
    report_performance
)

timer = start_timer("operation")
# ... do work ...
duration = end_timer(timer)
```

**New Pattern:**
```python
from roadmap.infrastructure.metrics import PerformanceTracker

tracker = PerformanceTracker()
with tracker.measure("operation"):
    # ... do work ...
```

**Complexity:** LOW
**Impact:** Performance instrumentation across codebase

**Changes Required:**
1. Replace timer calls with context manager pattern
2. Update call-sites
3. Verify performance metrics still work

---

## Category 3: Package-Level Facades (Import Consolidation)

### Package Compatibility Facade Migration

These are already part of packages but need import updates.

---

#### 18. `roadmap/common/validation/__init__.py` → Direct Submodule Imports

**Current Pattern:**
```python
from roadmap.common.validation import ValidationResult
```

**New Pattern (Option A - Use submodule directly):**
```python
from roadmap.common.validation.result import ValidationResult
```

**New Pattern (Option B - Keep facade, consolidate submodules):**
```python
# Keep __init__.py but make it cleaner
from roadmap.common.validation.result import ValidationResult
from roadmap.common.validation.field_validator import FieldValidator
# ... etc
```

**Recommendation:** Keep facade in place for now (Option B). It's useful for package users. Deprecate if needed later.

---

#### 19. `roadmap/common/security/__init__.py` → Submodule Imports

**Current Pattern:**
```python
from roadmap.common.security import validate_path
```

**New Pattern:**
```python
from roadmap.common.security.path_validation import validate_path
```

**Recommendation:** Keep facade for backwards compatibility.

---

#### 20. `roadmap/adapters/persistence/parser.py` → Direct Imports

**Current Pattern:**
```python
from roadmap.adapters.persistence.parser import FrontmatterParser
```

**New Pattern:**
```python
from roadmap.adapters.persistence.frontmatter_parser import FrontmatterParser
```

**Changes Required:**
1. Update all imports
2. Files to update: Any test file parsing files

---

## Category 4: Convenience Functions (Inline or Remove)

---

#### 21. `roadmap/common/datetime_parser.py` Convenience Functions

**Functions to Handle:**
- `parse_datetime()`
- `format_datetime()`
- Other module-level convenience functions

**Strategy:**

**Option 1 - Inline:**
```python
# Before
from roadmap.common.datetime_parser import parse_datetime
result = parse_datetime("2025-12-08")

# After
from roadmap.common.datetime_parser import DateTimeParser
parser = DateTimeParser()
result = parser.parse("2025-12-08")
```

**Option 2 - Keep but mark deprecated:**
```python
import warnings

def parse_datetime(date_str: str):
    warnings.warn(
        "parse_datetime() is deprecated; use DateTimeParser.parse() instead",
        DeprecationWarning,
        stacklevel=2
    )
    parser = DateTimeParser()
    return parser.parse(date_str)
```

**Recommendation:** Use Option 1 (inline) for v1.0.0. Replace all call-sites.

**Files to Update:**
- `tests/unit/common/test_datetime_parser.py`
- Any code using these functions (likely minimal)

---

#### 22. `roadmap/common/logging.py` Backwards-Compatible Logger (line 431+)

**Current Pattern:**
```python
# Line 431+: Global instance for backward compatibility
security_logger = SecurityLogger()
```

**New Pattern:**
```python
# Just use the SecurityLogger directly
from roadmap.infrastructure.logging import SecurityLogger
security_logger = SecurityLogger()
```

**Changes Required:**
1. Remove the global instance
2. Update any code relying on it to instantiate locally
3. Minimal impact expected

---

#### 23. `roadmap/common/timezone_utils.py` Helper Functions

**Functions to Handle:**
- Various timezone helper functions marked as backwards-compatible

**Strategy:**
1. Identify which functions are actually used
2. Keep those that are used, inline the rest
3. Consider creating a TimeZoneHelper service

**Changes Required:**
1. Audit usage
2. Inline or replace with service layer calls

---

#### 24. `roadmap/common/validation/validators.py` Legacy Methods (line 38+)

**Current Pattern (line 38):**
```python
def validate_frontmatter_structure(data):
    """Validate frontmatter structure for backward compatibility."""
    # Old implementation
```

**New Pattern:**
```python
from roadmap.common.validation.schema_validator import SchemaValidator
validator = SchemaValidator()
validator.validate_frontmatter(data)
```

**Changes Required:**
1. Find all calls to legacy method
2. Replace with modern validator
3. Update tests

---

## Implementation Priority

### Phase 2b Order (by risk/complexity):

1. **Week 1: Low-Risk Imports (Days 1-3)**
   - Update logging_decorators imports (widespread but low risk)
   - Update init_workflow imports
   - Update errors imports
   - Update security imports

2. **Week 1-2: Medium-Risk Services (Days 4-7)**
   - Create test fixtures for issue_operations_service
   - Replace issue update/start helpers with service calls
   - Update cleanup calls

3. **Week 2: Convenience Functions (Days 8-10)**
   - Inline datetime_parser convenience functions
   - Replace timezone_utils calls
   - Update kanban_helpers calls

4. **Week 2-3: Advanced Services (Days 11-12)**
   - Refactor performance_tracking
   - Refactor audit_logging
   - Update initialization service calls

---

## Validation Checklist

After updating each migration:

- [ ] Import statement updated in all files
- [ ] Code still compiles/imports correctly
- [ ] Tests pass for updated module
- [ ] No broken references
- [ ] Type hints still valid
- [ ] IDE shows no import errors

---

## Rollback Plan

If any migration fails:

1. Revert the imports back to old paths
2. Keep the shim file in place
3. Document the blocker
4. Address blocker before retrying

All shim files should remain in place until Phase 2c.
