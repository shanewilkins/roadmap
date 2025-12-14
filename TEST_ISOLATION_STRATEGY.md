# Test Isolation & Cleanup Strategy

## Problem Statement

When running tests in parallel (pytest-xdist with multiple workers), test fixture data was leaking across test boundaries. This occurred because:

1. All test workers shared the same `.roadmap` directory in the real filesystem
2. Tests that created issues/milestones/projects weren't properly isolated
3. The cleanup process couldn't reliably distinguish test artifacts from real data
4. Parallel test execution made sequential cleanup ineffective

**Result**: Test fixture data accumulated (28+ duplicate issues in `.roadmap/issues/`), confusing test results and polluting the repository state.

## Solution Architecture

### 1. **Workspace Isolation (Autouse Fixture)**

**File**: `tests/conftest.py::isolate_roadmap_workspace`

**Strategy**: Each integration test runs in its own temporary directory.

```python
@pytest.fixture(autouse=True, scope="function")
def isolate_roadmap_workspace(request, tmp_path):
    """Isolate each test in a temporary directory unless marked as @pytest.mark.unit"""
    # Skip for unit tests (performance optimization)
    if request.node.get_closest_marker("unit"):
        yield
        return

    # For integration tests: change to unique temp directory
    # e.g., /tmp/pytest-xxx/test_0/test_issue_create_0
    test_temp_dir = tmp_path / f"test_{request.node.name}"
    test_temp_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(str(test_temp_dir))

    # Test runs in isolation
    yield

    # Automatic cleanup via pytest's tmp_path fixture
    os.chdir(original_cwd)
```

**Benefits**:
- ✅ Each test gets its own isolated filesystem
- ✅ Automatic cleanup via pytest (no manual cleanup needed)
- ✅ No interference between parallel workers
- ✅ Works seamlessly with pytest-xdist
- ✅ No "magic" cleanup logic that can fail

### 2. **CLI Command Isolation (run_command Fixture)**

**File**: `tests/fixtures/click_testing.py::run_command`

**Strategy**: Wrap CLI invocations in Click's `isolated_filesystem()` context manager.

```python
@pytest.fixture
def run_command(isolated_cli_runner, click_test_result_wrapper):
    """Run a CLI command in an isolated filesystem."""
    def _run_command(args, catch_exceptions=False, input=None, env=None):
        with isolated_cli_runner.isolated_filesystem():
            # Command runs in temp directory, .roadmap created/modified there
            result = isolated_cli_runner.invoke(main, args, ...)
        # .roadmap automatically cleaned up when context exits
        return click_test_result_wrapper(result)
    return _run_command
```

**Benefits**:
- ✅ Explicit isolation at the command level
- ✅ Clear intent (readable test code)
- ✅ Double protection (workspace + command isolation)

### 3. **Test Markers**

**File**: `pytest.ini`

**Available Markers**:
- `@pytest.mark.unit` - Fast tests, no filesystem (skips workspace isolation)
- `@pytest.mark.integration` - Slower tests, filesystem needed (uses isolation)
- `@pytest.mark.filesystem` - Requires real filesystem operations
- `@pytest.mark.slow` - May be skipped in CI
- `@pytest.mark.performance` - Performance-focused tests

**Usage**:
```python
@pytest.mark.integration
def test_create_issue(roadmap_with_data):
    """Integration test automatically isolated in temp directory."""
    pass

@pytest.mark.unit
def test_issue_validation():
    """Unit test runs normally (no isolation overhead)."""
    pass
```

## Guidelines for Test Authors

### ✅ DO: Use Isolated Filesystem for CLI Tests

```python
def test_issue_create():
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create issues here - safe from parallel workers
        result = runner.invoke(main, ["issue", "create", "Test"])
        assert result.exit_code == 0
```

### ✅ DO: Mark Tests Appropriately

```python
@pytest.mark.integration
@pytest.mark.filesystem
def test_cli_workflow():
    """Clearly communicate that this test needs filesystem."""
    pass

@pytest.mark.unit
def test_validation_logic():
    """Unit test - isolated from filesystem."""
    pass
```

### ✅ DO: Use Fixtures for Setup

```python
def test_issue_operations(roadmap_with_data):
    """Fixture handles isolation automatically."""
    cli_runner, temp_dir, data = roadmap_with_data
    # Already in isolated temp directory
    # .roadmap already initialized
    pass
```

### ❌ DON'T: Create .roadmap in Real Filesystem

```python
# ❌ BAD: Creates .roadmap in current directory (shared by all workers)
def test_bad():
    result = CliRunner().invoke(main, ["init", ...])
    # If run in parallel, multiple workers create .roadmap in same location
```

### ❌ DON'T: Rely on Manual Cleanup

```python
# ❌ BAD: Cleanup can fail in parallel execution
def test_bad():
    # ... create test data ...
    os.remove(".roadmap")  # May not run if test fails
```

### ❌ DON'T: Skip the autouse Fixture

```python
# ❌ BAD: Disabling isolation removes protection
@pytest.fixture(autouse=False)
def some_fixture():
    pass
```

## Test Execution Flow

### Sequential (Single Worker)
```
test_1 runs in /tmp/test_1
  └─ .roadmap created here
  └─ Cleanup via autouse fixture
test_2 runs in /tmp/test_2
  └─ .roadmap created here
  └─ Cleanup via autouse fixture
```

### Parallel (8 Workers)
```
Worker 1: test_1 in /tmp/w1/test_1
Worker 2: test_2 in /tmp/w2/test_2
Worker 3: test_3 in /tmp/w3/test_3
... (separate .roadmap for each)
All run concurrently without interference
```

## Verification

To verify isolation is working:

```bash
# Run tests in parallel (8 workers)
pytest tests/ -n 8 -v

# Check that no spurious .roadmap exists
find . -name ".roadmap" -type d  # Should only find your real project
```

## Performance Impact

| Test Type | Isolation | Time Impact |
|-----------|-----------|------------|
| Unit tests (@pytest.mark.unit) | ❌ Skipped | None |
| Integration tests | ✅ Enabled | ~5-10% overhead |
| With parallel workers (8x) | ✅ Enabled | 70-80% faster overall |

The isolation overhead is negligible compared to test execution time and is more than offset by parallel execution.

## Debugging Failed Tests

### Test leaves .roadmap behind

**Cause**: Test fixture didn't properly exit isolation context

**Fix**: Check that test uses `isolated_filesystem()` or relies on autouse fixture

### Different behavior in parallel vs sequential

**Cause**: Test might be accessing shared .roadmap directory

**Fix**:
1. Mark test with `@pytest.mark.integration`
2. Verify test uses `isolated_filesystem()`
3. Check for hardcoded paths (use relative paths instead)

### Test data pollution in git

**Cause**: Fixture data committed to repository

**Fix**:
1. Add to `.gitignore`: `.roadmap` directory
2. Run: `git rm --cached .roadmap && git commit`
3. Ensure future tests use isolation

## Future Improvements

1. **Docker Isolation**: Run each test in isolated Docker container
2. **Database Isolation**: Use separate database per test
3. **Environment Variables**: Isolate environment variables per test
4. **Module State**: Reset module-level caches between tests
