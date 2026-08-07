# Test Independence Patterns

This document outlines best practices for writing independent, non-flaky tests in the Roadmap CLI project. Test flakiness occurs when tests pass in isolation but fail when run alongside other tests, typically due to shared state.

## Problem: Global State Leakage

### What Happened
The `test_milestone_assign_invalid_target` test was failing when run with the full test suite but passing in isolation. Root cause: **global session cache singleton not being cleared between tests**.

Location: [roadmap/common/cache.py](../../roadmap/common/cache.py)

```python
_session_cache = SessionCache()  # Global singleton
```

The `clear_session_cache()` function existed but was never called between tests, causing state from early tests to contaminate later tests.

### Why This Matters
- **Intermittent failures**: Tests fail unpredictably depending on test execution order
- **Debugging nightmare**: "Works on my machine" - works in isolation but not in CI
- **CI instability**: Test suite becomes unreliable and harder to trust
- **Developer frustration**: Flaky tests erode confidence in test suite

## Pattern 1: Autouse Cache Cleanup Fixture

### The Solution
Use pytest's `autouse=True` fixture to automatically clear shared state before and after each test.

**Location:** [tests/conftest.py](../../tests/conftest.py#L428)

```python
@pytest.fixture(autouse=True)
def clear_session_cache_between_tests():
    """Clear the session cache before and after each test.

    This ensures tests don't share cached state, which is critical for
    CLI tests that invoke commands sequentially.
    """
    from roadmap.common.cache import clear_session_cache

    # Clear before test
    clear_session_cache()

    # Test runs here
    yield

    # Clear after test
    clear_session_cache()
```

### Key Points
- **autouse=True**: Automatically applied to all tests without explicit use
- **Fixture scope: function** (default): Runs before and after every test
- **Clear before AND after**: Before prevents contamination from previous test, after prevents affecting future tests
- **Resilient**: Even if test raises exception, cleanup still runs (finally block equivalent)

## Pattern 2: Factory Fixtures for Consistent Test Data

### Problem Solved
Avoid creating test data that depends on shared state or side effects.

### Solution
Use factory fixtures that create fresh, independent test objects.

**Example:** [tests/unit/core/services/test_issue_matching_service.py](../../tests/unit/core/services/test_issue_matching_service.py#L20)

```python
@pytest.fixture
def issue_factory():
    """Factory for creating test Issue objects."""
    def _create(
        id: str = "TEST-1",
        title: str = "Test Issue",
        content: str = "Test content",
        status: str = "open",
        **kwargs
    ) -> Issue:
        return Issue(
            id=id,
            title=title,
            content=content,
            status=status,
            **kwargs
        )
    return _create


def test_matching_service(issue_factory):
    issue1 = issue_factory(id="ISSUE-1", title="Login button broken")
    issue2 = issue_factory(id="ISSUE-2", title="Fix login button")
    # Each test gets fresh objects
```

### Benefits
- **Isolation**: Each test gets its own test objects
- **Readability**: Clear what data the test uses (explicit kwargs)
- **Reusability**: Consistent factory across multiple tests
- **Customization**: Easy to override defaults per test

## Pattern 3: Parametrization Over Duplication

### Problem Solved
Avoid creating similar tests repeatedly - they can interfere with each other if state isn't properly isolated.

### Solution
Use `pytest.mark.parametrize` to test multiple scenarios in a single test function.

**Example:** [tests/unit/core/services/test_issue_matching_service.py](../../tests/unit/core/services/test_issue_matching_service.py#L85)

```python
@pytest.mark.parametrize(
    "title,content,min_threshold,expected_match",
    [
        ("Bug: Login fails", "User cannot login", 0.5, True),
        ("Feature: Dark mode", "Add dark mode support", 0.5, False),
        ("urgent: password reset broken", "Password reset not working", 0.6, True),
    ],
)
def test_matching_with_threshold(
    title, content, min_threshold, expected_match, issue_factory
):
    """Test that matching respects similarity thresholds."""
    local_issue = issue_factory(title="Bug: Login fails")
    remote_issue = {"title": title, "body": content}

    result = issue_matching_service.find_match(
        local_issue, [remote_issue], min_threshold
    )

    assert (result is not None) == expected_match
```

### Benefits
- **Reduced duplication**: One test function tests multiple scenarios
- **Consistent logic**: Same setup/assertions for all variations
- **Better reporting**: Clear which parameter combination failed
- **Maintainability**: Change assertion once, applies to all cases

## Pattern 4: Isolated Filesystem for File Operations

### Problem Solved
Tests that create/modify files can pollute the real filesystem and interfere with each other.

### Solution
Use Click's `isolated_filesystem()` context manager.

```python
from click.testing import CliRunner

def test_create_roadmap():
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Test has its own temporary directory
        result = runner.invoke(create_command, ["my-roadmap"])
        assert result.exit_code == 0
        # Files only exist in isolated temp dir
        # Automatically cleaned up after test
```

### Benefits
- **Complete isolation**: Each test has its own filesystem sandbox
- **Automatic cleanup**: Temporary directory automatically deleted
- **No side effects**: Tests can't interfere with each other's files
- **Safe to run in parallel**: Multiple tests can run simultaneously

## Pattern 5: Explicit State Cleanup Over Implicit

### Rule
Never assume state will be automatically cleaned up. Be explicit.

**Avoid:**
```python
def test_something():
    cache.set("key", "value")  # Assume it's cleaned up
    # ... test code
```

**Prefer:**
```python
@pytest.fixture
def cache_context():
    cache.clear()
    yield cache
    cache.clear()

def test_something(cache_context):
    cache_context.set("key", "value")  # Clean before and after
    # ... test code
```

## Pattern 6: Mock External Dependencies

### Problem Solved
Tests that make real HTTP calls, database queries, or file I/O depend on external state and can be flaky.

### Solution
Mock external dependencies using `unittest.mock` or `pytest-mock`.

**Example:**
```python
def test_fetch_remote_issue(monkeypatch):
    """Mock GitHub API instead of making real calls."""
    def mock_fetch(org, repo, issue_num):
        return {"id": "123", "title": "Test"}

    monkeypatch.setattr(
        "roadmap.adapters.github_adapter.fetch_issue",
        mock_fetch
    )

    # Test uses mock instead of real API
    result = fetch_remote_issue("org", "repo", 1)
    assert result["id"] == "123"
```

### Benefits
- **Fast tests**: No network latency
- **Deterministic**: Same input always produces same output
- **No external dependencies**: Tests pass even if GitHub is down
- **CI-friendly**: Tests don't require authentication tokens

## Test Independence Checklist

When writing tests, verify:

- [ ] **No global state**: Tests don't share singleton objects or caches
- [ ] **Fresh data**: Each test creates its own test objects via factories
- [ ] **Explicit cleanup**: Use autouse fixtures to clear state
- [ ] **Isolation**: Tests pass in any order (run with `pytest --random-order` to verify)
- [ ] **No side effects**: Tests don't modify shared files, databases, or configs
- [ ] **Mock externals**: Network calls, file I/O, database queries are mocked
- [ ] **Parametrize duplicates**: Similar tests use parametrization, not duplication
- [ ] **Descriptive names**: Test name describes what scenario it covers

## Running Tests to Verify Independence

### Test a single test in isolation
```bash
poetry run pytest tests/path/to/test_file.py::test_name
```

### Run full suite (should all pass)
```bash
poetry run pytest
```

### Run with random order (verifies no test ordering dependencies)
```bash
poetry run pytest --random-order
```

### Run with specific seed to reproduce failures
```bash
poetry run pytest --random-order-seed=12345
```

## Debugging Flaky Tests

If you encounter a flaky test:

1. **Reproduce the flakiness**:
   ```bash
   for i in {1..10}; do poetry run pytest test_name -x || break; done
   ```

2. **Check for global state**:
   - Search for module-level variables
   - Check for singleton patterns
   - Look for class variables that aren't reset

3. **Check fixture scope**:
   - Session-scoped fixtures can leak state
   - Use function-scoped fixtures (default) for isolation

4. **Check test order dependency**:
   ```bash
   poetry run pytest test_file.py::test_a test_file.py::test_b  # Passes
   poetry run pytest test_file.py::test_b test_file.py::test_a  # Fails?
   ```

5. **Add debug output**:
   ```python
   def test_flaky(caplog):
       caplog.set_level(logging.DEBUG)
       # Test code
       # Review logs to see what state was inherited
   ```

## Real-World Example: The Cache Flakiness Fix

### Before (Flaky)
```python
# tests/conftest.py - NO cache cleanup
@pytest.fixture
def roadmap_config():
    return Config()
```

Result: `_session_cache` global persisted between tests → flakiness

### After (Fixed)
```python
# tests/conftest.py - WITH cache cleanup autouse fixture
@pytest.fixture(autouse=True)
def clear_session_cache_between_tests():
    from roadmap.common.cache import clear_session_cache
    clear_session_cache()
    yield
    clear_session_cache()
```

Result: Cache cleared before/after every test → all tests pass consistently

**Impact:**
- Before: 6615 tests, 1 flaky (`test_milestone_assign_invalid_target`)
- After: 6616 tests, 0 flaky
- Fix was one autouse fixture with 4 lines of actual code

## References

- [pytest fixtures documentation](https://docs.pytest.org/en/stable/fixture.html)
- [pytest parametrize documentation](https://docs.pytest.org/en/stable/parametrize.html)
- [Click testing guide](https://click.palletsprojects.com/en/8.1.x/testing/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
