# Circular Import Solution - Implementation Guide

## Quick Reference: The Problem and Solution

### The Problem
- `RoadmapCore` (infrastructure) imports `ProjectService`, `HealthCheckService`, etc.
- These services need `RoadmapCore` for their `__init__` parameters
- This creates a circular dependency: A → B → A

### The Current Workaround
- `roadmap/core/services/__init__.py` uses lazy loading via `__getattr__`
- Services are imported only when first accessed, not at module load time
- By then, `RoadmapCore` has finished initializing

### The Better Solution
- Use Python's `TYPE_CHECKING` to import only for type hints
- No runtime import = no circular dependency
- Cleaner, more maintainable code

---

## Implementation Guide: TYPE_CHECKING Pattern

### Pattern Overview

```python
from typing import TYPE_CHECKING, Any

# Only imported during static type checking, not at runtime
if TYPE_CHECKING:
    from roadmap.infrastructure.coordination.core import RoadmapCore

class MyService:
    def __init__(self, core: "RoadmapCore"):  # String quotes delay evaluation
        self.core = core
```

**Key Points:**
- `TYPE_CHECKING` is `False` at runtime, `True` during static analysis
- String quotes `"RoadmapCore"` tell Python not to evaluate the type at runtime
- Static type checkers (pyright, mypy) still see the correct type
- No circular import because the class isn't actually imported until needed

---

## File-by-File Implementation

### 1. HealthCheckService
**File**: [roadmap/core/services/health/health_check_service.py](roadmap/core/services/health/health_check_service.py)

**Current Code (Lines 1-20):**
```python
"""Health check service for roadmap CLI.

This module handles system health checking and reporting, providing
component status information and overall system health assessment.
"""

from typing import Any

from roadmap.common.logging import get_logger
from roadmap.core.domain.health import HealthStatus
from roadmap.infrastructure.coordination.core import RoadmapCore  # ◄── DIRECT IMPORT
from roadmap.infrastructure.observability.health import HealthCheck

logger = get_logger(__name__)


class HealthCheckService:
    """Manages system health checks and reporting."""

    def __init__(self, core: RoadmapCore):  # ◄── TYPE ANNOTATION
        """Initialize the service.

        Args:
            core: RoadmapCore instance
        """
        self.core = core
```

**Refactored Code (TYPE_CHECKING):**
```python
"""Health check service for roadmap CLI.

This module handles system health checking and reporting, providing
component status information and overall system health assessment.
"""

from typing import TYPE_CHECKING, Any

from roadmap.common.logging import get_logger
from roadmap.core.domain.health import HealthStatus
from roadmap.infrastructure.observability.health import HealthCheck

if TYPE_CHECKING:
    from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger(__name__)


class HealthCheckService:
    """Manages system health checks and reporting."""

    def __init__(self, core: "RoadmapCore"):  # ◄── STRING QUOTE
        """Initialize the service.

        Args:
            core: RoadmapCore instance
        """
        self.core = core
```

**Changes Made:**
1. ✅ Add `TYPE_CHECKING` to imports (line 7)
2. ✅ Move `RoadmapCore` import inside `if TYPE_CHECKING:` block
3. ✅ Change parameter type from `RoadmapCore` to `"RoadmapCore"` (string)
4. ✅ Remove direct import

**Impact:**
- ✅ No circular dependency
- ✅ Type hints still work perfectly
- ✅ Runtime behavior unchanged (core still passed and stored)

---

### 2. ProjectStatusService
**File**: [roadmap/core/services/project/project_status_service.py](roadmap/core/services/project/project_status_service.py)

**Current Code (Lines 1-30):**
```python
"""Project status service for calculating project progress and status."""

import time
from pathlib import Path
from typing import Any

from roadmap.adapters.persistence.parser import MilestoneParser
from roadmap.common.constants import MilestoneStatus, ProjectStatus
from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger
from roadmap.infrastructure.coordination.core import RoadmapCore  # ◄── DIRECT IMPORT

# ... more code ...

class ProjectStatusService:
    """Service for calculating and managing project status."""

    def __init__(self, core: RoadmapCore):  # ◄── TYPE ANNOTATION
        """Initialize project status service.

        Args:
            core: RoadmapCore instance for accessing services
        """
        self.core = core
```

**Refactored Code:**
```python
"""Project status service for calculating project progress and status."""

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from roadmap.adapters.persistence.parser import MilestoneParser
from roadmap.common.constants import MilestoneStatus, ProjectStatus
from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger

if TYPE_CHECKING:
    from roadmap.infrastructure.coordination.core import RoadmapCore

# ... more code ...

class ProjectStatusService:
    """Service for calculating and managing project status."""

    def __init__(self, core: "RoadmapCore"):  # ◄── STRING QUOTE
        """Initialize project status service.

        Args:
            core: RoadmapCore instance for accessing services
        """
        self.core = core
```

**Changes Made:**
1. ✅ Add `TYPE_CHECKING` to imports
2. ✅ Remove direct `RoadmapCore` import
3. ✅ Add conditional import in `if TYPE_CHECKING:` block
4. ✅ Change parameter type from `RoadmapCore` to `"RoadmapCore"` (string)

---

### 3. GitHookAutoSyncService
**File**: [roadmap/core/services/git/git_hook_auto_sync_service.py](roadmap/core/services/git/git_hook_auto_sync_service.py)

**Current Code (Lines 1-25):**
```python
"""Auto-sync service for Git hooks - handles GitHub sync on Git events."""

from pathlib import Path
from typing import Any

from roadmap.common.console import get_console
from roadmap.core.services.github.github_integration_service import (
    GitHubIntegrationService,
)
from roadmap.core.services.sync.sync_metadata_service import SyncMetadataService


class GitHookAutoSyncConfig:
    """Configuration for git hook auto-sync behavior."""
    # ... config code ...


class GitHookAutoSyncService:
    """Service for handling automatic GitHub sync on Git events."""

    def __init__(self, core):  # ◄── IMPLICIT RoadmapCore
        """Initialize auto-sync service.

        Args:
            core: RoadmapCore instance
        """
        self.core = core
```

**Refactored Code:**
```python
"""Auto-sync service for Git hooks - handles GitHub sync on Git events."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from roadmap.common.console import get_console
from roadmap.core.services.github.github_integration_service import (
    GitHubIntegrationService,
)
from roadmap.core.services.sync.sync_metadata_service import SyncMetadataService

if TYPE_CHECKING:
    from roadmap.infrastructure.coordination.core import RoadmapCore


class GitHookAutoSyncConfig:
    """Configuration for git hook auto-sync behavior."""
    # ... config code ...


class GitHookAutoSyncService:
    """Service for handling automatic GitHub sync on Git events."""

    def __init__(self, core: "RoadmapCore"):  # ◄── TYPED WITH STRING QUOTE
        """Initialize auto-sync service.

        Args:
            core: RoadmapCore instance
        """
        self.core = core
```

**Changes Made:**
1. ✅ Add `TYPE_CHECKING` to imports (line 5)
2. ✅ Add conditional import in `if TYPE_CHECKING:` block
3. ✅ Add type annotation `core: "RoadmapCore"` instead of `core` (was untyped)

---

### 4. SyncMergeOrchestrator
**File**: [roadmap/adapters/sync/sync_merge_orchestrator.py](roadmap/adapters/sync/sync_merge_orchestrator.py)

**Current Code (Lines 1-50):**
```python
"""Generic sync orchestrator that works with any sync backend."""

from typing import Any

from structlog import get_logger

from roadmap.adapters.sync.services.sync_analysis_service import SyncAnalysisService
from roadmap.adapters.sync.services.sync_authentication_service import (
    SyncAuthenticationService,
)
# ... more imports ...
from roadmap.infrastructure.coordination.core import RoadmapCore  # ◄── DIRECT IMPORT

logger = get_logger(__name__)


class SyncMergeOrchestrator:
    """Orchestrates sync using a pluggable backend implementation."""

    def __init__(
        self,
        core: RoadmapCore,  # ◄── TYPE ANNOTATION
        backend: SyncBackendInterface,
        # ... other params ...
    ):
```

**Refactored Code:**
```python
"""Generic sync orchestrator that works with any sync backend."""

from typing import TYPE_CHECKING, Any

from structlog import get_logger

from roadmap.adapters.sync.services.sync_analysis_service import SyncAnalysisService
from roadmap.adapters.sync.services.sync_authentication_service import (
    SyncAuthenticationService,
)
# ... more imports ...
from roadmap.core.interfaces.sync_backend import SyncBackendInterface

if TYPE_CHECKING:
    from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger(__name__)


class SyncMergeOrchestrator:
    """Orchestrates sync using a pluggable backend implementation."""

    def __init__(
        self,
        core: "RoadmapCore",  # ◄── STRING QUOTE
        backend: SyncBackendInterface,
        # ... other params ...
    ):
```

**Changes Made:**
1. ✅ Add `TYPE_CHECKING` to imports
2. ✅ Remove direct `RoadmapCore` import
3. ✅ Add conditional import in `if TYPE_CHECKING:` block
4. ✅ Change parameter type from `RoadmapCore` to `"RoadmapCore"` (string)

---

### 5. Update services/__init__.py (Final Step)

**File**: [roadmap/core/services/__init__.py](roadmap/core/services/__init__.py)

**Current Code (Lines 90-130):**
```python
# Lazy imports for all services that cause circular dependencies
# These services import from adapters/infrastructure/validators that
# eventually import RoadmapCore
_lazy_modules = {
    "GitHookAutoSyncService": (
        "git.git_hook_auto_sync_service",
        "GitHookAutoSyncService",
    ),
    "HealthCheckService": ("health.health_check_service", "HealthCheckService"),
    "ProjectStatusService": ("project.project_status_service", "ProjectStatusService"),
    # ... 20+ more entries ...
}

def __getattr__(name: str):  # noqa: ANN001, ANN201
    """Lazy load services to avoid circular imports."""
    if name in _lazy_modules:
        module_path, class_name = _lazy_modules[name]
        module = __import__(
            f"roadmap.core.services.{module_path}", fromlist=[class_name]
        )
        return getattr(module, class_name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
```

**After TYPE_CHECKING Implementation (No lazy loading needed):**
```python
# Now we can safely import everything since TYPE_CHECKING breaks the cycle
from .git.git_hook_auto_sync_service import (  # noqa: F401
    GitHookAutoSyncConfig,
    GitHookAutoSyncService,
)
from .health.data_integrity_validator_service import (  # noqa: F401
    DataIntegrityValidatorService,
)
from .health.health_check_service import HealthCheckService  # noqa: F401
from .health.infrastructure_validator_service import (  # noqa: F401
    InfrastructureValidator,
)
from .project.project_status_service import ProjectStatusService  # noqa: F401

# Previously lazy-loaded sync services can now be eagerly loaded
from .sync.sync_change_computer import (  # noqa: F401
    compute_changes,
    compute_changes_remote,
)
from .sync.sync_conflict_detector import detect_field_conflicts  # noqa: F401
from .sync.sync_conflict_resolver import Conflict, ConflictField  # noqa: F401
from .sync.sync_conflict_resolver import SyncConflictResolver  # noqa: F401
# ... etc - no more __getattr__ needed
```

**Benefits:**
1. ✅ **Cleaner**: No complex dynamic import mechanism
2. ✅ **Faster**: No runtime dispatch overhead
3. ✅ **Explicit**: Clear what's being imported
4. ✅ **Type-safe**: IDE autocomplete works better
5. ✅ **Maintainable**: Future developers don't need to understand lazy loading

---

## Validation Checklist

After implementing TYPE_CHECKING changes:

### 1. Type Checking
```bash
# Run Pyright to ensure all type hints are correct
poetry run pyright roadmap/core/services/health/health_check_service.py
poetry run pyright roadmap/core/services/project/project_status_service.py
poetry run pyright roadmap/core/services/git/git_hook_auto_sync_service.py
poetry run pyright roadmap/adapters/sync/sync_merge_orchestrator.py

# Should show ✓ All type checking passed
```

### 2. Runtime Imports
```bash
# Test that imports work at runtime
poetry run python -c "
from roadmap.core.services import HealthCheckService
from roadmap.core.services import ProjectStatusService
from roadmap.core.services import GitHookAutoSyncService
print('✓ All imports successful')
"

# Should not show any warnings about circular imports
```

### 3. No Circular Import Warnings
```bash
# Check for circular import warnings
poetry run python -Walways -c "
import roadmap.infrastructure.coordination.core
import roadmap.core.services
print('✓ No circular import warnings')
" 2>&1 | grep -i "circular\|import"

# Should show nothing (no matches = success)
```

### 4. Unit Tests
```bash
# Run relevant tests
poetry run pytest tests/unit/services/test_health_check_service.py -xvs
poetry run pytest tests/unit/services/test_project_status_service.py -xvs
poetry run pytest tests/unit/services/git/ -xvs

# All should pass
```

### 5. Integration Tests
```bash
# Run full test suite
poetry run pytest tests/ -x

# All should pass
```

### 6. Check RoadmapCore Initialization
```bash
# Verify RoadmapCore still works correctly
poetry run python -c "
from roadmap.infrastructure.coordination.core import RoadmapCore
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    core = RoadmapCore(Path(tmpdir))
    print(f'✓ RoadmapCore initialized: {core}')
    print(f'✓ Has issue_service: {core.issue_service}')
    print(f'✓ Has milestone_service: {core.milestone_service}')
"
```

---

## Summary of Changes

| File | Change | Risk | Benefit |
|------|--------|------|---------|
| [health_check_service.py](roadmap/core/services/health/health_check_service.py) | Add TYPE_CHECKING, quote type | Very Low | Remove lazy load dependency |
| [project_status_service.py](roadmap/core/services/project/project_status_service.py) | Add TYPE_CHECKING, quote type | Very Low | Remove lazy load dependency |
| [git_hook_auto_sync_service.py](roadmap/core/services/git/git_hook_auto_sync_service.py) | Add TYPE_CHECKING, add type hint | Very Low | Remove lazy load dependency |
| [sync_merge_orchestrator.py](roadmap/adapters/sync/sync_merge_orchestrator.py) | Add TYPE_CHECKING, quote type | Very Low | Remove lazy load dependency |
| [services/__init__.py](roadmap/core/services/__init__.py) | Remove lazy loading mechanism | Low | Cleaner, faster imports |

**Total Changes:** ~25 lines across 5 files
**Total Risk:** Very Low
**Total Benefit:** High (cleaner architecture, faster imports, better maintainability)

---

## Before and After Comparison

### Before (With Lazy Loading)
```
Import roadmap.core.services
  → Initializes __getattr__ handler
  → Registers _lazy_modules dict
  → When HealthCheckService accessed:
    → __getattr__ called
    → __import__() executed at access time
    → Runtime dispatch overhead
    → Complex to debug

Problem: If code does `from roadmap.core.services import HealthCheckService`
         at module level, it won't trigger __getattr__ properly
```

### After (With TYPE_CHECKING)
```
Import roadmap.core.services
  → All imports executed eagerly
  → TYPE_CHECKING guard prevents circular reference
  → No special handling needed
  → Fast, simple, clear
  → Type hints work perfectly
  → IDE autocomplete works great
```

---

## Rollback Plan (If Issues Arise)

If anything breaks after the TYPE_CHECKING implementation:

1. **Keep lazy loading code** in services/__init__.py
2. **Dual import pattern** for transition:
   ```python
   # In each service that was lazy-loaded:
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from roadmap.infrastructure.coordination.core import RoadmapCore

   # Keep in __all__ for lazy loading to work as fallback
   ```
3. **Gradually remove** lazy loading once confident

**Expected:** This rollback is very unlikely needed since TYPE_CHECKING is a Python standard pattern.

---

## References

- Python `TYPE_CHECKING` docs: https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING
- Mypy type checking: https://mypy.readthedocs.io/en/stable/
- Pyright documentation: https://github.com/microsoft/pyright
- PEP 484 - Type Hints: https://www.python.org/dev/peps/pep-0484/
