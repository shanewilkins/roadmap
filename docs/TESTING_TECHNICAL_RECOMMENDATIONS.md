# Test Quality Audit - Technical Recommendations

**Companion Document to**: TEST_QUALITY_AUDIT_REPORT.md

---

## Recommended Project Structure After Refactoring

### Current State
```
tests/
├── conftest.py
├── fixtures/
│   ├── __init__.py
│   ├── conftest.py
│   ├── assertions.py
│   ├── click_testing.py
│   ├── github.py
│   ├── io.py
│   ├── mocks.py
│   ├── performance.py
│   └── workspace.py
├── integration/
├── unit/
│   ├── adapters/
│   ├── application/
│   ├── core/
│   ├── domain/
│   ├── infrastructure/
│   ├── presentation/
│   ├── shared/
│   └── cli/  ← Legacy location
├── test_cli/  ← Legacy location
└── [security, performance, etc.]
```

### Recommended Structure
```
tests/
├── conftest.py                          ← Global fixtures
├── factories/                           ← NEW: Domain builders
│   ├── __init__.py
│   ├── domain.py                        ← Issue, Milestone, Project builders
│   ├── github.py                        ← GitHub API response factories
│   ├── cli.py                           ← CliRunner, context factories
│   └── persistence.py                   ← Database/persistence factories
├── fixtures/
│   ├── __init__.py
│   ├── conftest.py                      ← All centralized fixtures
│   ├── assertions.py
│   ├── click_testing.py                 ← Enhanced Click helpers
│   ├── github.py
│   ├── io.py
│   ├── mocks.py                         ← Contains all mock_core, etc.
│   ├── performance.py
│   └── workspace.py
├── unit/
│   ├── conftest.py                      ← NEW: Unit-specific fixtures
│   ├── adapters/
│   │   ├── cli/
│   │   │   ├── conftest.py              ← Click command fixtures only
│   │   │   └── ...
│   │   └── ...
│   ├── application/
│   ├── core/
│   ├── domain/
│   ├── infrastructure/
│   ├── presentation/
│   └── shared/
├── integration/
│   ├── conftest.py                      ← Integration-specific setup
│   └── ...
└── [security, performance, etc.]
```

---

## Specific Code Changes

### 1. Create Centralized Domain Factories

**File: `tests/factories/domain.py`**

```python
"""Domain object factories for testing.

Provides builder-style factories for creating test objects
with sensible defaults while allowing customization.
"""

from datetime import datetime, timedelta
from roadmap.core.domain import Issue, Milestone, Project, Status, Priority, MilestoneStatus
from roadmap.core.domain.issue import IssueType


class IssueBuilder:
    """Builder for creating test Issue objects."""

    def __init__(self):
        self.defaults = {
            'title': 'Test Issue',
            'status': Status.TODO,
            'priority': Priority.MEDIUM,
            'issue_type': IssueType.FEATURE,
            'milestone': 'v1.0',
        }
        self._overrides = {}

    def with_title(self, title: str) -> 'IssueBuilder':
        self._overrides['title'] = title
        return self

    def with_status(self, status: Status) -> 'IssueBuilder':
        self._overrides['status'] = status
        return self

    def with_priority(self, priority: Priority) -> 'IssueBuilder':
        self._overrides['priority'] = priority
        return self

    def with_milestone(self, milestone: str) -> 'IssueBuilder':
        self._overrides['milestone'] = milestone
        return self

    def build(self) -> Issue:
        params = {**self.defaults, **self._overrides}
        return Issue(**params)


class MilestoneBuilder:
    """Builder for creating test Milestone objects."""

    def __init__(self):
        self.defaults = {
            'name': 'v1.0',
            'description': 'First release',
            'status': MilestoneStatus.OPEN,
            'content': '# v1.0',
            'due_date': datetime.now() + timedelta(days=30),
        }
        self._overrides = {}

    def with_name(self, name: str) -> 'MilestoneBuilder':
        self._overrides['name'] = name
        return self

    def with_status(self, status: MilestoneStatus) -> 'MilestoneBuilder':
        self._overrides['status'] = status
        return self

    def with_due_date(self, due_date) -> 'MilestoneBuilder':
        self._overrides['due_date'] = due_date
        return self

    def build(self) -> Milestone:
        params = {**self.defaults, **self._overrides}
        return Milestone(**params)


# Convenience functions
def create_issue(**overrides) -> Issue:
    """Create a test issue with optional overrides."""
    return IssueBuilder().build().__class__(**{**IssueBuilder().defaults, **overrides})

def create_milestone(**overrides) -> Milestone:
    """Create a test milestone with optional overrides."""
    return MilestoneBuilder().build().__class__(**{**MilestoneBuilder().defaults, **overrides})
```

### 2. Centralize Mock Fixtures

**File: `tests/fixtures/mocks.py` (Enhanced)**

```python
"""Centralized mock fixtures for all tests.

Instead of defining mock_core in 35+ test files, define it once here.
"""

import pytest
from unittest.mock import MagicMock, Mock


@pytest.fixture
def mock_core():
    """Centralized mock RoadmapCore used across all tests.

    Returns a properly configured MagicMock that represents
    the core object with standard attribute access patterns.
    """
    core = MagicMock()

    # Standard attributes that many tests expect
    core.issues = MagicMock()
    core.milestones = MagicMock()
    core.projects = MagicMock()
    core.is_initialized = MagicMock(return_value=True)

    return core


@pytest.fixture
def mock_cli_runner():
    """Centralized CliRunner for Click command tests."""
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def mock_console():
    """Centralized Rich console mock."""
    return MagicMock()


# Builders for creating configured mocks
def create_configured_mock_core(**custom_attrs):
    """Create mock_core with custom attributes.

    Example:
        core = create_configured_mock_core(
            issues=MagicMock(get=MagicMock(return_value=None))
        )
    """
    core = MagicMock()
    core.issues = MagicMock()
    core.milestones = MagicMock()
    core.projects = MagicMock()

    for key, value in custom_attrs.items():
        setattr(core, key, value)

    return core
```

### 3. Click Command Testing Pattern

**File: `tests/fixtures/click_testing.py` (Enhanced)**

```python
"""Click command testing utilities and patterns.

Standardizes how we test Click commands to avoid Rich/Click mismatches.
"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner


class ClickCommandTest:
    """Base class for Click command tests.

    Handles proper mocking of Rich console to avoid Click/Rich conflicts.
    """

    @staticmethod
    def invoke_command(command, args, mock_core=None, **kwargs):
        """Safely invoke a Click command with mocked console.

        Args:
            command: The Click command function
            args: List of command-line arguments
            mock_core: Mock RoadmapCore instance (optional)
            **kwargs: Additional kwargs for invoke()

        Returns:
            Click CliRunner result
        """
        runner = CliRunner()

        # Determine the module path for the get_console patch
        module_path = command.__module__

        with patch(f"{module_path}.get_console") as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            # Prepare context object
            context_obj = {"core": mock_core} if mock_core else {}

            result = runner.invoke(command, args, obj=context_obj, **kwargs)

            return result, mock_console

    @staticmethod
    def assert_command_success(result):
        """Assert command exited successfully."""
        assert result.exit_code == 0, f"Command failed: {result.output}"

    @staticmethod
    def assert_command_printed(mock_console, text):
        """Assert console was called with specific text."""
        calls = mock_console.print.call_args_list
        for call in calls:
            if text in str(call):
                return
        raise AssertionError(f"'{text}' not found in console output")
```

**Usage in tests**:

```python
from tests.fixtures.click_testing import ClickCommandTest

class TestMyCommand(ClickCommandTest):
    def test_my_command(self, mock_core):
        result, console = self.invoke_command(
            my_command,
            ["arg1"],
            mock_core=mock_core
        )
        self.assert_command_success(result)
        self.assert_command_printed(console, "Success")
```

### 4. Create Unit Conftest

**File: `tests/unit/conftest.py` (NEW)**

```python
"""Unit test specific fixtures and configuration.

These fixtures are lighter-weight than integration fixtures,
using mocks instead of real objects where possible.
"""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def unit_mock_core():
    """Lightweight mock core for unit tests.

    This is a unit-specific variant that might skip
    some setup that integration tests need.
    """
    core = MagicMock()
    core.issues = MagicMock()
    core.milestones = MagicMock()
    core.projects = MagicMock()
    return core


@pytest.fixture
def unit_temp_dir(tmp_path):
    """Unit test temporary directory (faster than real filesystem)."""
    return tmp_path
```

---

## Migration Strategy for Duplicate Fixtures

### Step 1: Identify All Duplicates
```bash
grep -r "@pytest.fixture" tests/ --include="*.py" | \
  awk -F: '{print $3}' | \
  sort | uniq -c | sort -rn
```

### Step 2: Create Migration Plan
For each duplicate fixture (e.g., `mock_core`):
1. Move definition to centralized location
2. Create pytest marks to auto-migrate in old files
3. Deprecation period: Both locations work
4. Remove from old locations

### Step 3: Use pytest Plugins
```python
# tests/conftest.py - Add deprecation warning
import warnings

@pytest.fixture
def mock_core(request):
    # If test is in old location, warn
    if 'unit/adapters/cli' in request.fspath.strpath:
        warnings.warn(
            "mock_core fixture imported from test file. "
            "Use global fixture from tests/fixtures/mocks.py",
            DeprecationWarning
        )
```

---

## Parameterization Examples

### Example 1: Status Testing
**Before**:
```python
def test_issue_status_todo(): assert ...
def test_issue_status_in_progress(): assert ...
def test_issue_status_blocked(): assert ...
def test_issue_status_closed(): assert ...
```

**After**:
```python
@pytest.mark.parametrize("status", [
    Status.TODO,
    Status.IN_PROGRESS,
    Status.BLOCKED,
    Status.CLOSED,
])
def test_issue_status(status):
    issue = create_issue(status=status)
    assert issue.status == status
```

### Example 2: CRUD Operations
**Before**:
```python
def test_create_issue_minimal(): assert ...
def test_create_issue_with_priority(): assert ...
def test_create_issue_with_milestone(): assert ...
```

**After**:
```python
@pytest.mark.parametrize("field,value", [
    ("priority", Priority.HIGH),
    ("milestone", "v2.0"),
    ("description", "Long description"),
])
def test_create_issue_fields(field, value):
    issue = create_issue(**{field: value})
    assert getattr(issue, field) == value
```

---

## File Breaking Strategy

### Large File: `unit/shared/test_security.py` (1142 lines)

**Current Issues**:
- Tests too many concerns (credentials, validation, etc.)
- Hard to navigate, understand, maintain

**Recommended Split**:
```
unit/shared/test_security.py → Split into:
├── test_security_credentials.py
├── test_security_validation.py
├── test_security_encryption.py
└── test_security_integration.py  (if needed)
```

**Grouping strategy**:
```python
class TestSecurityCredentials:
    def test_load_credentials(self): ...
    def test_validate_credentials(self): ...

class TestSecurityEncryption:
    def test_encrypt_password(self): ...
    def test_decrypt_password(self): ...
```

---

## Rich/Click Safety Checklist

For every Click command test, ensure:

- [ ] Console is patched **at the module level** where `get_console()` is imported
- [ ] Patch path matches actual import: `roadmap.adapters.cli.{module}.get_console`
- [ ] Mock returns a `MagicMock()` (not a real console)
- [ ] Test uses `runner.invoke()` to invoke command, not direct call
- [ ] Test checks `result.exit_code` (Click's result object)
- [ ] Don't access console output directly; use `mock_console.print.assert_called()`

**Example Template**:
```python
def test_my_cli_command(self, mock_core):
    """Test my Click command safely."""
    with patch("roadmap.adapters.cli.mymodule.get_console") as mock_gc:
        mock_console = MagicMock()
        mock_gc.return_value = mock_console

        runner = CliRunner()
        result = runner.invoke(my_command, ["arg"], obj={"core": mock_core})

        assert result.exit_code == 0
        mock_console.print.assert_called()
```

---

## Test Guidelines Document Outline

**File to create**: `docs/TESTING_GUIDELINES.md`

```markdown
# Testing Guidelines

## 1. Fixture Usage
- Use centralized fixtures from `tests/fixtures/`
- Never define `mock_core` locally - use global fixture
- Use `tests/factories/` for object creation

## 2. Click Command Testing
- Always patch `get_console()` at module level
- Use `CliRunner.invoke()` not direct function calls
- Check `result.exit_code` not raw console output

## 3. Mocking Rules
- Mock at boundaries (database, API, filesystem)
- Don't mock objects you're testing
- Use builders for complex object setup

## 4. Parameterization
- Use `@pytest.mark.parametrize` for multiple inputs
- Group related tests with test classes
- Avoid 10+ test methods for the same logic

## 5. Test Organization
- One concept per test method
- Test files ≤ 500 lines (break up god objects)
- Test class names start with `Test`
```

---

## Risk Mitigation

### When Consolidating Fixtures
1. **Run full test suite after each change** - Don't batch changes
2. **Git commit after each fixture migration** - Easy to revert
3. **Use deprecation warnings** - Catch old usage patterns
4. **Keep old fixtures until all tests pass** - Don't delete prematurely

### When Breaking Up Large Files
1. **Don't move tests, copy and verify** - Then delete original
2. **Maintain class organization** - Group related tests
3. **Run tests after each file split** - Catch import issues
4. **Update documentation** - Link to new test locations

---

## Summary: Foundation Fixes in Order

1. **Week 1 - Fixtures** (Risk: Medium)
   - Create factories in `tests/factories/`
   - Centralize mocks in `tests/fixtures/mocks.py`
   - Create `tests/unit/conftest.py`
   - Create `tests/fixtures/click_testing.py` with helpers

2. **Week 2 - Consolidation** (Risk: High - do carefully)
   - Migrate top 10 duplicate fixtures
   - Use deprecation warnings for old locations
   - Run tests after each migration

3. **Week 3 - Refactoring** (Risk: Medium)
   - Break up 5 largest test files
   - Add parameterization to high-volume tests
   - Consolidate duplicates

4. **Week 4 - Documentation & Coverage** (Risk: Low)
   - Document patterns in TESTING_GUIDELINES.md
   - Audit Click command tests
   - Add coverage with refactored patterns

---

## Questions for You

1. **Timeline**: Can we afford 4 weeks of refactoring before release?
2. **Test Run Time**: How long does full test suite take now? Will parameterization help?
3. **Architecture**: Are there domain objects beyond Issue/Milestone/Project to factory-ize?
4. **Breaking Changes**: OK to move files/rename fixtures with deprecation period?
5. **Documentation**: Should this guide be in TESTING.md or CONTRIBUTING.md?
