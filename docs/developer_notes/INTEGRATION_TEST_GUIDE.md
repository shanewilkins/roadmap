"""Integration Test Best Practices Guide

This guide documents the new integration test helpers and patterns to use for
writing robust, maintainable integration tests.
"""

# Integration Test Best Practices Guide

## Overview

The new `IntegrationTestBase` class provides utilities to write integration tests that are:
- **Robust**: Test behavior through APIs, not fragile text parsing
- **Maintainable**: Reduce boilerplate with helper functions
- **Debuggable**: Get full error context when tests fail
- **Isolated**: Proper setup/teardown with CLI initialization

## Quick Start

### Basic Test Structure

```python
from tests.fixtures import IntegrationTestBase

def test_create_issue(cli_runner):
    """Test creating an issue."""
    # Setup: Initialize roadmap
    IntegrationTestBase.init_roadmap(cli_runner)

    # Action: Use helper to create issue
    IntegrationTestBase.create_issue(
        cli_runner,
        title="My Task",
        priority="high",
    )

    # Assert: Verify through API (not text parsing!)
    core = IntegrationTestBase.get_roadmap_core()
    issues = core.issues.list()
    assert len(issues) == 1
    assert issues[0].title == "My Task"
    assert issues[0].priority.value == "high"
```

## Available Helpers

### `init_roadmap(cli_runner, project_name="Test Project", skip_github=True)`

Initialize a roadmap in the current isolated filesystem.

**Example:**
```python
core = IntegrationTestBase.init_roadmap(cli_runner)
# Now .roadmap directory exists with proper initialization
```

**Why use this instead of manual setup?**
- Uses actual CLI init command (replicates real user workflow)
- Ensures proper initialization manifest is created
- Fails fast with clear error if something goes wrong
- Works with any future initialization changes

---

### `create_milestone(cli_runner, name, description="", due_date=None)`

Create a milestone and return it.

**Example:**
```python
IntegrationTestBase.create_milestone(
    cli_runner,
    name="v1.0",
    description="First release",
    due_date="2024-03-31",
)
```

**Advantages over manual CLI invocation:**
- Automatic error handling with context
- Returns structured data
- Cleaner syntax
- Easier to read test intent

---

### `create_issue(cli_runner, title, description="", priority=None, milestone=None, assignee=None)`

Create an issue.

**Example:**
```python
IntegrationTestBase.create_issue(
    cli_runner,
    title="Bug in login flow",
    description="Users can't log in with SSO",
    priority="critical",
    milestone="v1.0",
)
```

---

### `get_roadmap_core()`

Get the RoadmapCore instance for the current workspace.

**Example:**
```python
core = IntegrationTestBase.get_roadmap_core()
issues = core.issues.list()
milestones = core.milestones.list()
```

---

### `roadmap_state()`

Get the complete roadmap state (issues, milestones, projects).

**Example:**
```python
state = IntegrationTestBase.roadmap_state()
assert len(state["issues"]) == 5
assert len(state["milestones"]) == 2
```

---

### `assert_cli_success(result, context="", show_traceback=True)`

Assert CLI command succeeded with detailed error context.

**Example:**
```python
result = cli_runner.invoke(main, ["issue", "create", "Task"])
IntegrationTestBase.assert_cli_success(result, context="Creating issue")
```

**Output on failure:**
```
❌ Creating issue
Exit code: 1

--- CLI Output ---
Error: Database not initialized

--- Exception ---
RuntimeError: No .roadmap directory

--- Traceback ---
[Full traceback here]
```

---

### `assert_exit_code(result, expected, context="", show_output=True)`

Assert specific exit code with error context.

**Example:**
```python
result = cli_runner.invoke(main, ["invalid", "command"])
IntegrationTestBase.assert_exit_code(result, 2, context="Invalid command")
```

---

## Pattern Examples

### Pattern 1: Verify Feature Through API

**OLD (Fragile - depends on output format):**
```python
def test_create_issue(cli_runner):
    cli_runner.invoke(main, ["init", ...])
    result = cli_runner.invoke(main, ["issue", "create", "Task"])
    assert result.exit_code == 0
    assert "Created issue" in result.output  # ← Breaks on UI changes
    assert "Task" in result.output           # ← Brittle parsing
```

**NEW (Robust - tests actual behavior):**
```python
def test_create_issue(cli_runner):
    IntegrationTestBase.init_roadmap(cli_runner)
    IntegrationTestBase.create_issue(cli_runner, title="Task")

    # Verify through API
    core = IntegrationTestBase.get_roadmap_core()
    issues = core.issues.list()
    assert len(issues) == 1
    assert issues[0].title == "Task"
```

---

### Pattern 2: Verify Multiple State Changes

**Example: Create milestone and assign issues to it**

```python
def test_milestone_workflow(cli_runner):
    """Test creating milestone and assigning issues."""
    IntegrationTestBase.init_roadmap(cli_runner)

    # Setup: Create milestone
    IntegrationTestBase.create_milestone(
        cli_runner,
        name="Beta",
        description="Beta release",
    )

    # Action: Create 3 issues for the milestone
    for i in range(3):
        IntegrationTestBase.create_issue(
            cli_runner,
            title=f"Feature {i+1}",
            milestone="Beta",
        )

    # Assert: Complete state
    core = IntegrationTestBase.get_roadmap_core()
    issues = core.issues.list()
    milestones = core.milestones.list()

    assert len(milestones) == 1
    assert milestones[0].name == "Beta"
    assert len(issues) == 3

    # All issues in milestone
    for issue in issues:
        assert issue.milestone == "Beta"
```

---

### Pattern 3: Test Error Handling

**Example: Create duplicate milestone**

```python
def test_duplicate_milestone_error(cli_runner):
    """Test that creating duplicate milestone fails."""
    IntegrationTestBase.init_roadmap(cli_runner)

    # Create first milestone
    IntegrationTestBase.create_milestone(cli_runner, name="v1.0")

    # Try to create duplicate
    result = cli_runner.invoke(
        main,
        ["milestone", "create", "v1.0"],
    )

    # Should fail
    assert result.exit_code != 0
    # Verify state unchanged
    core = IntegrationTestBase.get_roadmap_core()
    milestones = core.milestones.list()
    assert len(milestones) == 1  # Only one milestone
```

---

### Pattern 4: Parametrized Tests with Helpers

**Example: Test multiple priorities**

```python
import pytest

@pytest.mark.parametrize(
    "priority,priority_value",
    [
        ("critical", "critical"),
        ("high", "high"),
        ("medium", "medium"),
        ("low", "low"),
    ],
)
def test_issue_priorities(cli_runner, priority, priority_value):
    """Test creating issues with different priorities."""
    IntegrationTestBase.init_roadmap(cli_runner)

    IntegrationTestBase.create_issue(
        cli_runner,
        title=f"{priority.title()} Issue",
        priority=priority,
    )

    core = IntegrationTestBase.get_roadmap_core()
    issues = core.issues.list()
    assert issues[0].priority.value == priority_value
```

---

## Enhanced Assertion Helpers

The `CLIAssertion` class now includes better error reporting:

### `success_with_context(result, context="")`

Assert success with optional context.

```python
result = cli_runner.invoke(main, ["issue", "create", "Task"])
from tests.fixtures import CLIAssertion

CLIAssertion.success_with_context(result, "Creating issue")
```

### `exit_code_with_output(result, expected, show_output=True, context="")`

Assert exit code with full output display.

```python
CLIAssertion.exit_code_with_output(
    result,
    expected=0,
    context="Issue creation",
    show_output=True,
)
```

---

## Migration Guide: Refactoring Existing Tests

### Step 1: Replace Manual Init with Helper

**Before:**
```python
def test_something(cli_runner):
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(
            main,
            [
                "init",
                "--project-name",
                "Test Project",
                "--non-interactive",
                "--skip-github",
            ],
        )
        assert result.exit_code == 0
        # ... rest of test
```

**After:**
```python
def test_something(cli_runner):
    with cli_runner.isolated_filesystem():
        IntegrationTestBase.init_roadmap(cli_runner)
        # ... rest of test
```

---

### Step 2: Replace Output Assertions with API Checks

**Before:**
```python
result = cli_runner.invoke(main, ["issue", "create", "Task"])
assert result.exit_code == 0
assert "Created issue" in result.output
assert "Task" in result.output
```

**After:**
```python
IntegrationTestBase.create_issue(cli_runner, title="Task")
core = IntegrationTestBase.get_roadmap_core()
issues = core.issues.list()
assert any(issue.title == "Task" for issue in issues)
```

---

### Step 3: Add Better Error Context

**Before:**
```python
result = cli_runner.invoke(main, ["milestone", "create", "v1.0"])
assert result.exit_code == 0
```

**After:**
```python
result = cli_runner.invoke(main, ["milestone", "create", "v1.0"])
IntegrationTestBase.assert_cli_success(result, "Creating v1.0 milestone")
```

---

## Testing Tips

### 1. **Test Behavior, Not Output**

✅ GOOD:
```python
core = IntegrationTestBase.get_roadmap_core()
assert len(core.issues.list()) == 1
```

❌ BAD:
```python
assert "1 issue" in result.output
```

---

### 2. **Use Helpers for Setup**

✅ GOOD:
```python
IntegrationTestBase.init_roadmap(cli_runner)
IntegrationTestBase.create_issue(cli_runner, title="Task")
```

❌ BAD:
```python
cli_runner.invoke(main, ["init", ...lots of options...])
cli_runner.invoke(main, ["issue", "create", "Task"])
```

---

### 3. **Isolate Each Test**

✅ GOOD - Each test initializes independently:
```python
def test_a(cli_runner):
    IntegrationTestBase.init_roadmap(cli_runner)
    # ...

def test_b(cli_runner):
    IntegrationTestBase.init_roadmap(cli_runner)  # Fresh start
    # ...
```

❌ BAD - Tests share state:
```python
@pytest.fixture(scope="module")  # ← Shares state across tests!
def shared_roadmap(cli_runner):
    # ...
```

---

### 4. **Use Fixtures for Complex Scenarios**

For complex multi-step setups, create a fixture:

```python
@pytest.fixture
def roadmap_with_multiple_milestones(cli_runner):
    """Setup with multiple milestones and issues."""
    IntegrationTestBase.init_roadmap(cli_runner)

    for i in range(3):
        IntegrationTestBase.create_milestone(
            cli_runner,
            name=f"Sprint {i+1}",
        )

    return IntegrationTestBase.get_roadmap_core()

def test_with_fixture(roadmap_with_multiple_milestones):
    """Test using pre-configured roadmap."""
    core = roadmap_with_multiple_milestones
    assert len(core.milestones.list()) == 3
```

---

## Common Patterns

### Testing Complete Workflows

```python
def test_complete_release_workflow(cli_runner):
    """Test: Plan milestone → Create issues → Complete workflow."""
    # Setup
    IntegrationTestBase.init_roadmap(cli_runner)

    # Plan: Create milestone
    IntegrationTestBase.create_milestone(
        cli_runner,
        name="v2.0",
        due_date="2024-06-30",
    )

    # Create issues
    issues_to_create = [
        ("Feature A", "high"),
        ("Feature B", "high"),
        ("Bug fix", "medium"),
    ]

    for title, priority in issues_to_create:
        IntegrationTestBase.create_issue(
            cli_runner,
            title=title,
            priority=priority,
            milestone="v2.0",
        )

    # Verify complete state
    state = IntegrationTestBase.roadmap_state()
    assert len(state["milestones"]) == 1
    assert len(state["issues"]) == 3

    # Verify structure
    core = IntegrationTestBase.get_roadmap_core()
    for issue in core.issues.list():
        assert issue.milestone == "v2.0"
        assert issue.priority.value in ["high", "medium"]
```

---

## Debugging Failed Tests

### View Full Error Context

Failed tests now show:
1. CLI exit code
2. Complete CLI output
3. Exception type and message
4. Full traceback

**Example:**
```
❌ Creating issue
Exit code: 1

--- CLI Output ---
Error: Issue title is required

--- Exception ---
Click.UsageError: Issue title is required

--- Traceback ---
[Full Python traceback]
```

---

### Common Debugging Scenarios

**Scenario 1: CLI command fails unexpectedly**

```python
result = cli_runner.invoke(main, ["issue", "create", "Task"])
IntegrationTestBase.assert_cli_success(result, "Creating issue")
# If this fails, you'll see full output and exception
```

**Scenario 2: State check fails**

```python
core = IntegrationTestBase.get_roadmap_core()
issues = core.issues.list()
print(f"Number of issues: {len(issues)}")
for issue in issues:
    print(f"  - {issue.title} (priority: {issue.priority})")
```

---

## Next Steps

1. **Identify brittle tests**: Look for tests with many text assertions
2. **Refactor iteratively**: Replace text assertions with API checks
3. **Add helpers for common patterns**: Create fixtures for your specific scenarios
4. **Document test intent**: Use clear test names and docstrings

---

## Reference

- [IntegrationTestBase API](tests/fixtures/integration_helpers.py)
- [Example Tests](tests/integration/test_integration_patterns_example.py)
- [CLIAssertion Helpers](tests/fixtures/assertions.py)
- [Integration Test Fragility Analysis](INTEGRATION_TEST_FRAGILITY_ANALYSIS.md)
