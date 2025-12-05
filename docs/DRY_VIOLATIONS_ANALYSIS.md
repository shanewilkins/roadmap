# DRY Violations Analysis - Roadmap Codebase

**Analysis Date:** December 5, 2025
**Scope:** `roadmap/` and `tests/` modules
**Focus Areas:** Large and medium-level redundancies, service patterns

---

## Executive Summary

This analysis identifies **7 major DRY violation clusters** across the codebase, representing significant opportunities for refactoring. The most impactful violations involve:

1. **Repeated file enumeration patterns** (5 instances)
2. **Duplicate exception handling boilerplate** (15+ instances)
3. **Parallel validator class patterns** (8 validator classes with identical structure)
4. **Duplicate test fixtures and setup** (test modules)
5. **Redundant parsing logic** (multiple entities with similar parse/save patterns)
6. **Duplicate status/summary calculation logic** (4 services computing similar summaries)
7. **Repeated error handling in status methods** (try/except/log patterns)

---

## Part 1: Large-Level DRY Violations

### 🔴 VIOLATION #1: File Enumeration and Parsing Pattern (LARGE)

**Impact Level:** HIGH
**Frequency:** 5+ instances
**Estimated Code Duplication:** ~200 LOC

#### Location & Examples

**IssueService.list_issues()** (lines 136-156):
```python
for issue_file in self.issues_dir.rglob("*.md"):
    try:
        issue = IssueParser.parse_issue_file(issue_file)
        issue.file_path = str(issue_file)

        # Apply filters
        if milestone and issue.milestone != milestone:
            continue
        if status and issue.status != status:
            continue
        # ... more filters
    except Exception as e:
        # Log parsing error but continue processing other files
        continue
```

**ProjectService.list_projects()** (lines 32-45):
```python
projects = []
for project_file in self.projects_dir.rglob("*.md"):
    try:
        project = ProjectParser.parse_project_file(project_file)
        projects.append(project)
    except Exception:
        continue

projects.sort(key=lambda x: x.created)
```

**MilestoneService.list_milestones()** (lines 71-91):
```python
milestones = []
for milestone_file in self.milestones_dir.rglob("*.md"):
    try:
        milestone = MilestoneParser.parse_milestone_file(milestone_file)
        if status is None or milestone.status == status:
            milestones.append(milestone)
    except Exception:
        continue
```

**DuplicateIssuesValidator.scan_for_duplicate_issues()** (lines 51-68):
```python
for issue_file in issues_dir.glob("**/*.md"):
    if ".backup" in issue_file.name:
        continue
    issue_id = extract_issue_id(issue_file.name)
    if issue_id:
        issues_by_id[issue_id].append(issue_file)
```

**FolderStructureValidator.scan_for_folder_structure_issues()** (lines 122+):
```python
for issue_file in issues_dir.glob("*.md"):
    # Similar pattern with parsing and filtering
```

#### The Problem

1. **Repeated enumeration logic:** Each service re-implements the pattern of walking directories with `rglob("*.md")`
2. **Identical exception handling:** All catch generic `Exception` and silently continue
3. **Redundant filtering:** Services re-implement similar filtering logic (milestones, status, etc.)
4. **Scattered concerns:** File location, backup filtering, parsing, filtering mixed together

#### Recommended Solution

Create a `FileEnumerationService` in the shared/infrastructure layer:

```python
# roadmap/infrastructure/file_enumeration.py

class FileEnumerationService:
    """Unified service for enumerating and filtering markdown files."""

    @staticmethod
    def enumerate_and_parse(
        directory: Path,
        parser_func: Callable,
        backup_filter: bool = True,
        logger_context: dict | None = None,
    ) -> list:
        """Enumerate files and parse with consistent error handling.

        Args:
            directory: Directory to enumerate
            parser_func: Parser function (e.g., IssueParser.parse_issue_file)
            backup_filter: Skip .backup files
            logger_context: Logging context for errors

        Returns:
            List of parsed objects
        """
        # Implementation here

    @staticmethod
    def enumerate_with_filter(
        directory: Path,
        parser_func: Callable,
        filter_func: Callable[[Any], bool],
    ) -> list:
        """Enumerate, parse, and filter files."""
        # Implementation here

    @staticmethod
    def find_by_id(
        directory: Path,
        id_value: str,
        parser_func: Callable,
    ) -> Any | None:
        """Find a single file by ID pattern."""
        # Implementation here
```

---

### 🔴 VIOLATION #2: Validator Class Structure Duplication (LARGE)

**Impact Level:** VERY HIGH
**Frequency:** 8 validator classes
**Estimated Code Duplication:** ~400 LOC

#### Location & Examples

**`infrastructure_validator_service.py`** contains:
- `RoadmapDirectoryValidator`
- `StateFileValidator`
- `IssuesDirectoryValidator`
- `MilestonesDirectoryValidator`
- `GitRepositoryValidator`
- `DatabaseValidator` (implied)
- Plus similar classes in `data_integrity_validator_service.py`

#### The Problem

Each validator class follows an identical pattern:

```python
class SomethingValidator:
    """Validator for something."""

    @staticmethod
    def check_something() -> tuple[str, str]:
        """Check if something exists and is accessible.

        Returns:
            Tuple of (status, message)
        """
        try:
            # Check logic
            logger.debug("health_check_something", status="healthy")
            return HealthStatus.HEALTHY, "Something is accessible"
        except Exception as e:
            logger.error("health_check_something_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking something: {e}"
```

**Every validator class:**
- Uses `@staticmethod`
- Returns `tuple[str, str]` of (status, message)
- Has identical try/except/logger pattern
- Returns HealthStatus constants

#### Recommended Solution

Create a `BaseValidator` abstract class:

```python
# roadmap/application/services/base_validator.py

from abc import ABC, abstractmethod
from roadmap.shared.logging import get_logger

class BaseValidator(ABC):
    """Base class for all health validators."""

    logger = get_logger(__name__)

    @staticmethod
    @abstractmethod
    def get_check_name() -> str:
        """Return the name of this check."""
        pass

    @staticmethod
    @abstractmethod
    def perform_check() -> tuple[str, str]:
        """Perform the actual check logic.

        Should raise exceptions on failure or return (status, message).
        """
        pass

    @classmethod
    def check(cls) -> tuple[str, str]:
        """Execute the check with standard error handling."""
        try:
            status, message = cls.perform_check()
            cls.logger.debug(f"health_check_{cls.get_check_name()}", status=status)
            return status, message
        except Exception as e:
            cls.logger.error(
                f"health_check_{cls.get_check_name()}_failed",
                error=str(e)
            )
            return HealthStatus.UNHEALTHY, f"Error: {e}"
```

Then each validator becomes:

```python
class RoadmapDirectoryValidator(BaseValidator):
    @staticmethod
    def get_check_name() -> str:
        return "roadmap_directory"

    @staticmethod
    def perform_check() -> tuple[str, str]:
        roadmap_dir = Path(".roadmap")
        if not roadmap_dir.exists():
            return HealthStatus.DEGRADED, ".roadmap directory not initialized"

        # Actual check logic only
        return HealthStatus.HEALTHY, "Accessible and writable"
```

---

### 🔴 VIOLATION #3: Exception Handling Boilerplate (LARGE)

**Impact Level:** HIGH
**Frequency:** 15+ instances
**Estimated Code Duplication:** ~150 LOC

#### Location & Examples

**Pattern appearing in 15+ methods:**

```python
# In ProjectStatusService
def get_project_overview(self, project_id: str | None = None) -> dict[str, Any]:
    try:
        # ... logic ...
        return result
    except Exception as e:
        logger.error("Failed to get project overview", error=str(e))
        return {"error": str(e)}
```

**In HealthCheckService:**
```python
def run_all_checks(self) -> dict[str, tuple[HealthStatus, str]]:
    try:
        checks = HealthCheck.run_all_checks(self.core)
        logger.debug("health_checks_completed", check_count=len(checks))
        return checks
    except Exception as e:
        logger.error("health_checks_failed", error=str(e))
        return {}
```

#### The Problem

1. **Repetitive try/except blocks** in nearly every service method
2. **Inconsistent return values** on error (sometimes `{}`, sometimes `None`, sometimes `{"error": str(e)}`)
3. **Logging boilerplate** with predictable pattern: `logger.error("operation_failed", error=str(e))`
4. **Similar error names** generated from method names

#### Recommended Solution

Create a `ServiceMethodDecorator`:

```python
# roadmap/shared/decorators.py

from functools import wraps
from typing import Any, Callable

def service_operation(default_return: Any = None, error_message: str | None = None):
    """Decorator for service methods with standard error handling.

    Args:
        default_return: Value to return on error (default {})
        error_message: Custom error message (auto-generated if None)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                result = func(self, *args, **kwargs)
                logger.debug(f"{func.__name__}_completed")
                return result
            except Exception as e:
                msg = error_message or f"Error in {func.__name__}"
                logger.error(msg, error=str(e))
                return default_return if default_return is not None else {}
        return wrapper
    return decorator
```

Usage:

```python
class HealthCheckService:

    @service_operation(default_return={})
    def run_all_checks(self) -> dict[str, tuple[HealthStatus, str]]:
        checks = HealthCheck.run_all_checks(self.core)
        return checks

    @service_operation(default_return=HealthStatus.UNHEALTHY)
    def get_overall_status(self, checks=None):
        if checks is None:
            checks = self.run_all_checks()
        return HealthCheck.get_overall_status(checks)
```

---

## Part 2: Medium-Level DRY Violations

### 🟡 VIOLATION #4: Parsing and Serialization Pattern (MEDIUM)

**Impact Level:** MEDIUM-HIGH
**Frequency:** 3 parsers (Issue, Milestone, Project)
**Estimated Code Duplication:** ~250 LOC

#### Location & Examples

Each parser (`IssueParser`, `MilestoneParser`, `ProjectParser`) implements:

1. **Parse file:** Read file → extract frontmatter → parse YAML → convert types
2. **Serialize file:** Convert types → dump YAML → write frontmatter
3. **Type conversion:** Handle datetime, enums, lists
4. **Validation:** Check enum values, handle missing fields

**IssueParser.parse_issue_file()** converts datetime strings:
```python
if "created" in frontmatter and isinstance(frontmatter["created"], str):
    frontmatter["created"] = parse_datetime(frontmatter["created"], "file")
if "updated" in frontmatter and isinstance(frontmatter["updated"], str):
    frontmatter["updated"] = parse_datetime(frontmatter["updated"], "file")
# ... repeated for 5+ datetime fields
```

**IssueParser** also validates enums:
```python
if "priority" in frontmatter:
    try:
        frontmatter["priority"] = Priority(frontmatter["priority"])
    except ValueError as e:
        valid_priorities = [p.value for p in Priority]
        raise ValueError(f"Invalid priority...") from e
```

#### Recommended Solution

Create a `PydanticYAMLParser` base class that leverages Pydantic:

```python
# roadmap/infrastructure/persistence/pydantic_parser.py

from pydantic import BaseModel, ValidationError
from typing import Type, TypeVar

T = TypeVar('T', bound=BaseModel)

class PydanticYAMLParser:
    """Generic parser for Pydantic models from YAML frontmatter."""

    @staticmethod
    def parse_file(file_path: Path, model_class: Type[T]) -> T:
        """Parse a markdown file and return a Pydantic model instance.

        Handles:
        - YAML frontmatter extraction
        - Type conversion (datetime, enums, lists)
        - Validation
        - Error reporting with context
        """
        frontmatter, content = FrontmatterParser.parse_file(file_path)

        try:
            # Pydantic handles all type conversion and validation
            instance = model_class(**frontmatter, content=content)
            return instance
        except ValidationError as e:
            # Rich error message with file context
            raise ValueError(f"Invalid {model_class.__name__} in {file_path}: {e}")

    @staticmethod
    def save_file(instance: BaseModel, file_path: Path) -> None:
        """Save a Pydantic model instance to a markdown file."""
        data = instance.model_dump(exclude={"content"})
        FrontmatterParser.serialize_file(data, instance.content, file_path)
```

Then parsers simplify to:

```python
class IssueParser:
    @classmethod
    def parse_issue_file(cls, file_path: Path) -> Issue:
        return PydanticYAMLParser.parse_file(file_path, Issue)

    @classmethod
    def save_issue_file(cls, issue: Issue, file_path: Path) -> None:
        return PydanticYAMLParser.save_file(issue, file_path)
```

---

### 🟡 VIOLATION #5: Status/Summary Calculation Methods (MEDIUM)

**Impact Level:** MEDIUM
**Frequency:** 4 instances
**Code Pattern Location:**

1. **HealthCheckService.get_health_summary()** (lines 79-114)
2. **ProjectStatusService.get_status_summary()** (lines 89-103)
3. **Data integrity validators** (implicit in check methods)
4. **Infrastructure validators** (get_overall_status methods)

#### The Problem

All services count status values similarly:

```python
# HealthCheckService
healthy_count = sum(1 for _, (status, _) in checks.items() if status == HealthStatus.HEALTHY)
degraded_count = sum(1 for _, (status, _) in checks.items() if status == HealthStatus.DEGRADED)
unhealthy_count = sum(1 for _, (status, _) in checks.items() if status == HealthStatus.UNHEALTHY)

# Similar code appears in multiple validators
```

#### Recommended Solution

Create a `StatusSummary` utility:

```python
# roadmap/shared/status_utils.py

from collections import Counter
from enum import Enum

class StatusSummary:
    """Utility for computing status summaries from check results."""

    @staticmethod
    def count_by_status(
        items: list[tuple[str, Enum]]
    ) -> dict[str, int]:
        """Count items by status enum value."""
        counter = Counter(status for _, status in items)
        return {status.value: count for status, count in counter.items()}

    @staticmethod
    def summarize_checks(
        checks: dict[str, tuple[Enum, str]]
    ) -> dict[str, int]:
        """Get summary counts from health checks."""
        statuses = [status for _, (status, _) in checks.items()]
        return StatusSummary.count_by_status([(None, s) for s in statuses])
```

---

### 🟡 VIOLATION #6: Test Fixture Duplication (MEDIUM)

**Impact Level:** MEDIUM
**Frequency:** Multiple test files
**Affected Files:**
- `test_project_service.py`
- `test_health_check_service.py`
- `test_initialization_service.py`

#### The Problem

Each test file re-implements similar fixtures:

```python
# test_project_service.py
@pytest.fixture
def mock_db():
    return Mock()

@pytest.fixture
def temp_dirs(tmp_path):
    projects_dir = tmp_path / "projects"
    milestones_dir = tmp_path / "milestones"
    projects_dir.mkdir()
    milestones_dir.mkdir()
    return {"projects": projects_dir, "milestones": milestones_dir}
```

```python
# test_health_check_service.py
@pytest.fixture
def mock_core():
    return Mock(spec=RoadmapCore)
```

**Repeated patterns:**
1. Generic `Mock()` fixtures for database, core, config
2. Temporary directory setup with specific subdirectories
3. Sample entity creation (Project, Issue, Milestone)

#### Recommended Solution

Create `tests/conftest.py` with shared fixtures:

```python
# tests/conftest.py

import pytest
from unittest.mock import Mock
from roadmap.application.core import RoadmapCore

@pytest.fixture
def mock_db():
    """Create a mock StateManager."""
    return Mock()

@pytest.fixture
def mock_core():
    """Create a mock RoadmapCore."""
    return Mock(spec=RoadmapCore)

@pytest.fixture
def temp_roadmap_dirs(tmp_path):
    """Create standard .roadmap directory structure."""
    roadmap_dir = tmp_path / ".roadmap"
    (roadmap_dir / "issues").mkdir(parents=True)
    (roadmap_dir / "milestones").mkdir(parents=True)
    (roadmap_dir / "projects").mkdir(parents=True)
    (roadmap_dir / "db").mkdir(parents=True)
    return roadmap_dir
```

---

### 🟡 VIOLATION #7: Similar Filtering Logic (MEDIUM)

**Impact Level:** MEDIUM
**Frequency:** 3 instances in IssueService
**Location:** `issue_service.py` lines 136-169

#### The Problem

**IssueService.list_issues()** implements inline filtering:
```python
if milestone and issue.milestone != milestone:
    continue
if status and issue.status != status:
    continue
if priority and issue.priority != priority:
    continue
# ... more
```

**IssueService.list_issues_assigned_to()** (if it exists) would likely duplicate this.

**Similar pattern in MilestoneService** for status filtering.

#### Recommended Solution

Create a `FilterBuilder` utility:

```python
# roadmap/shared/filtering.py

from typing import Callable, Generic, TypeVar, Any

T = TypeVar('T')

class FilterBuilder(Generic[T]):
    """Builder for composable filters."""

    def __init__(self, items: list[T]):
        self.items = items
        self.predicates: list[Callable[[T], bool]] = []

    def where(self, field: str, value: Any) -> 'FilterBuilder[T]':
        """Add a field equality filter."""
        if value is not None:
            self.predicates.append(lambda item: getattr(item, field) == value)
        return self

    def where_in(self, field: str, values: list[Any]) -> 'FilterBuilder[T]':
        """Add a field membership filter."""
        if values:
            self.predicates.append(lambda item: getattr(item, field) in values)
        return self

    def apply(self) -> list[T]:
        """Apply all predicates."""
        result = self.items
        for predicate in self.predicates:
            result = [item for item in result if predicate(item)]
        return result
```

Usage:

```python
def list_issues(self, milestone=None, status=None, priority=None, assignee=None):
    all_issues = [IssueParser.parse_issue_file(f) for f in self.issues_dir.rglob("*.md")]

    return (FilterBuilder(all_issues)
        .where("milestone", milestone)
        .where("status", status)
        .where("priority", priority)
        .where("assignee", assignee)
        .apply())
```

---

## Part 3: Smaller DRY Violations (Worth Investigating)

### 🟢 VIOLATION #8: String Formatting in Logging (SMALL)

**Impact Level:** LOW
**Frequency:** 5+ instances

Consistent pattern of logging with formatted strings:
```python
logger.error(f"health_check_{cls.get_check_name()}_failed", error=str(e))
```

Consider a logging utility that generates these automatically.

### 🟢 VIOLATION #9: Path Construction Pattern (SMALL)

**Impact Level:** LOW
**Frequency:** 3 instances

```python
roadmap_dir = Path(".roadmap")
roadmap_dir / "issues"
roadmap_dir / "milestones"
```

Could benefit from a `RoadmapPaths` utility class.

### 🟢 VIOLATION #10: Similar get_X methods (SMALL)

**Impact Level:** LOW
**Frequency:** 3 instances in services

Generic getter methods like `get_issue()`, `get_project()`, `get_milestone()` follow similar patterns of searching and returning None.

---

## Summary Table

| Violation | Type | Priority | Frequency | Est. Code Impact | Effort |
|-----------|------|----------|-----------|------------------|--------|
| #1: File Enumeration | Large | HIGH | 5 instances | 200 LOC | 3-4 hrs |
| #2: Validator Classes | Large | VERY HIGH | 8 classes | 400 LOC | 4-5 hrs |
| #3: Exception Handling | Large | HIGH | 15+ methods | 150 LOC | 2-3 hrs |
| #4: Parsing/Serialization | Medium | MEDIUM-HIGH | 3 parsers | 250 LOC | 3-4 hrs |
| #5: Status Summary | Medium | MEDIUM | 4 instances | 50 LOC | 1-2 hrs |
| #6: Test Fixtures | Medium | MEDIUM | 3 test files | 100 LOC | 1-2 hrs |
| #7: Filtering Logic | Medium | MEDIUM | 3 instances | 80 LOC | 1-2 hrs |
| **Total Estimated Impact** | | | | **1,230 LOC** | **16-22 hrs** |

---

## Severity Classification

- **VERY HIGH:** Impacts multiple systems, harms maintainability significantly
- **HIGH:** Impacts multiple areas, creates maintenance burden
- **MEDIUM-HIGH:** Noticeable duplication, worth refactoring
- **MEDIUM:** Good to eliminate but lower priority
- **LOW:** Nice-to-have improvements
