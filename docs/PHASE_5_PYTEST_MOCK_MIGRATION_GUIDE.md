# Phase 5: pytest-mock Migration Guide

## Overview

This guide documents the migration from `unittest.mock` to `pytest-mock` (the `mocker` fixture).

## Why pytest-mock?

- **Automatic cleanup**: Mocks are automatically cleaned up after each test (no state leakage)
- **Cleaner syntax**: More Pythonic, `mocker` is available as a fixture parameter
- **Better integration**: Native pytest plugin, no extra cleanup needed
- **Consistency**: Unified mocking approach across the test suite

## Migration Patterns

### Pattern 1: Direct Mock Creation

**Before (unittest.mock):**
```python
from unittest.mock import Mock

def test_something():
    mock_obj = Mock(attr=value)
    mock_obj.method.return_value = 123
    assert mock_obj.method() == 123
```

**After (pytest-mock):**
```python
def test_something(mocker):
    mock_obj = mocker.Mock(attr=value)
    mock_obj.method.return_value = 123
    assert mock_obj.method() == 123
```

**Key change**: Replace `Mock()` with `mocker.Mock()` - the `mocker` parameter provides access to pytest-mock API.

---

### Pattern 2: patch() Context Managers

**Before (unittest.mock):**
```python
from unittest.mock import patch

def test_api_call():
    with patch("module.SomeClass") as mock_class:
        result = function_that_uses_class()
        mock_class.assert_called_once()
```

**After (pytest-mock):**
```python
def test_api_call(mocker):
    mock_class = mocker.patch("module.SomeClass")
    result = function_that_uses_class()
    mock_class.assert_called_once()
```

**Key change**: Replace `with patch(...) as X:` with `mocker.patch(...)` - no need for context manager.

---

### Pattern 3: MagicMock Usage

**Before (unittest.mock):**
```python
from unittest.mock import MagicMock

def test_with_context_manager():
    mock_db = MagicMock()
    with mock_db.transaction():
        mock_db.execute("SELECT *")
    mock_db.execute.assert_called_once()
```

**After (pytest-mock):**
```python
def test_with_context_manager(mocker):
    mock_db = mocker.MagicMock()
    with mock_db.transaction():
        mock_db.execute("SELECT *")
    mock_db.execute.assert_called_once()
```

**Key change**: Replace `MagicMock()` with `mocker.MagicMock()`.

---

### Pattern 4: Patching Object Attributes

**Before (unittest.mock):**
```python
from unittest.mock import Mock, patch

def test_attribute_override():
    obj = MyClass()
    with patch.object(obj, "method", return_value=42):
        result = obj.method()
        assert result == 42
```

**After (pytest-mock):**
```python
def test_attribute_override(mocker):
    obj = MyClass()
    mocker.patch.object(obj, "method", return_value=42)
    result = obj.method()
    assert result == 42
```

**Key change**: Replace `patch.object(...) as X:` with `mocker.patch.object(...)`.

---

### Pattern 5: side_effect

**Before (unittest.mock):**
```python
from unittest.mock import Mock

def test_side_effect():
    mock_func = Mock(side_effect=[1, 2, 3])
    assert mock_func() == 1
    assert mock_func() == 2
    assert mock_func() == 3
```

**After (pytest-mock):**
```python
def test_side_effect(mocker):
    mock_func = mocker.Mock(side_effect=[1, 2, 3])
    assert mock_func() == 1
    assert mock_func() == 2
    assert mock_func() == 3
```

**Key change**: Same pattern, just use `mocker.Mock()` instead of `Mock()`.

---

### Pattern 6: spec Parameter

**Before (unittest.mock):**
```python
from unittest.mock import Mock
from my_module import RealClass

def test_with_spec():
    mock_obj = Mock(spec=RealClass)
    # mock_obj now has the same interface as RealClass
```

**After (pytest-mock):**
```python
def test_with_spec(mocker):
    mock_obj = mocker.Mock(spec=RealClass)
    # mock_obj now has the same interface as RealClass
```

**Key change**: Spec parameter works the same with mocker.

---

### Pattern 7: Multiple Patches

**Before (unittest.mock):**
```python
from unittest.mock import patch

def test_multiple_patches():
    with patch("module.func1") as mock1, patch("module.func2") as mock2:
        mock1.return_value = "a"
        mock2.return_value = "b"
        result = orchestrate()
```

**After (pytest-mock):**
```python
def test_multiple_patches(mocker):
    mock1 = mocker.patch("module.func1", return_value="a")
    mock2 = mocker.patch("module.func2", return_value="b")
    result = orchestrate()
```

**Key change**: No nesting needed - each patch is independent.

---

## Important Considerations

### 1. Import Removal

Remove these imports from all test files:
```python
# REMOVE THESE:
from unittest.mock import Mock
from unittest.mock import patch
from unittest.mock import MagicMock
from unittest.mock import call
```

Leave pytest import:
```python
# KEEP THIS:
import pytest
```

### 2. Fixture Parameter Required

Every test using mocker must have `mocker` as a parameter:
```python
# OLD (no mocker needed):
def test_something():
    mock_obj = Mock()

# NEW (mocker required):
def test_something(mocker):
    mock_obj = mocker.Mock()
```

### 3. Automatic Cleanup

With pytest-mock, cleanup happens automatically - no need for teardown:
```python
# NO LONGER NEEDED:
def tearDown(self):
    mock.stop()  # pytest-mock handles this
```

### 4. `call` Object Still Available

```python
from unittest.mock import call

def test_calls(mocker):
    mock_func = mocker.Mock()
    mock_func(1, 2)
    mock_func(3, 4)
    mock_func.assert_has_calls([call(1, 2), call(3, 4)])
```

### 5. Spy on Real Functions

pytest-mock allows spying on real functions:
```python
def test_spy(mocker):
    mocker.spy(module, "real_function")
    module.real_function(42)
    module.real_function.assert_called_with(42)
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Fixture Factories with Mocker

**Problem**: Using mocker inside fixture factories (not fixtures themselves)

**Solution**: Pass mocker to the factory if needed, or use mocker in the test:
```python
# DON'T DO THIS:
@pytest.fixture
def my_factory(mocker):  # ❌ This is wrong
    return mocker.Mock()

# DO THIS INSTEAD:
def test_something(mocker):
    mock_obj = mocker.Mock()  # ✅ Use mocker in test
    # or
    mock_obj = Mock()  # ✅ Still fine if you keep Mock import for special cases
```

### Pitfall 2: Forgetting Mocker Parameter

**Problem**: Test fails with "fixture 'mocker' not found"

**Solution**: Add `mocker` parameter to test function:
```python
# BEFORE (fails):
def test_something():
    mock_obj = mocker.Mock()  # NameError: mocker not defined

# AFTER (works):
def test_something(mocker):
    mock_obj = mocker.Mock()  # ✅
```

### Pitfall 3: Context Manager Syntax

**Problem**: Forgetting mocker.patch doesn't use context managers

**Solution**: Use mocker.patch directly without `with`:
```python
# OLD (context manager style):
with patch("module.Class") as mock_class:
    ...

# NEW (direct assignment):
mock_class = mocker.patch("module.Class")
...
```

---

## Migration Checklist

For each test file to migrate:

- [ ] Add `mocker` parameter to test functions that mock
- [ ] Remove `from unittest.mock import Mock, patch, MagicMock` lines
- [ ] Replace all `Mock()` calls with `mocker.Mock()`
- [ ] Replace all `patch()` with `mocker.patch()`
- [ ] Replace all `MagicMock()` with `mocker.MagicMock()`
- [ ] Replace all `patch.object()` with `mocker.patch.object()`
- [ ] Run tests to verify: `poetry run pytest <file> -v`
- [ ] Check linting: `poetry run pre-commit run --all-files`

---

## File Migration Order (Priority)

1. **High Priority** (already refactored in Phase 4 - best candidates):
   - tests/unit/adapters/vcs/test_git_branch_manager.py (27 mocks)
   - tests/unit/adapters/vcs/test_sync_monitor.py (24 mocks)
   - tests/unit/adapters/sync/test_sync_retrieval_orchestrator.py (23 mocks)
   - tests/unit/adapters/vcs/test_git_commit_analyzer.py (16 mocks)

2. **Medium Priority** (10-20 mocks):
   - tests/unit/core/services/github/test_github_integration_service.py (24 mocks)
   - tests/unit/application/services/test_github_integration_service.py (10 mocks)
   - Other adapter/service tests

3. **Low Priority** (<10 mocks):
   - Scattered test files with minimal mocking

---

## Validation

After migration, verify:
1. All tests pass: `poetry run pytest -q`
2. No linting errors: `poetry run pre-commit run --all-files`
3. Zero regressions in test behavior
4. All Mock imports removed from migrated files

---

## References

- pytest-mock documentation: https://pytest-mock.readthedocs.io/
- pytest fixtures: https://docs.pytest.org/en/stable/how-to/fixtures.html
- unittest.mock documentation: https://docs.python.org/3/library/unittest.mock.html

---

**Estimated Time**: 9-11 hours total for Phase 5
**Status**: Ready to begin file-by-file migration
