# Test Remediation: Tactical Execution Guide

Practical examples, patterns, and templates for fixing test issues.

---

## PHASE 1 TACTICS: Missing Assertions

### Tactic 1.1: Convert "Bare Method Call" Tests

**Pattern Recognition:**
```python
def test_something(self):
    result = some_method()  # Called but not verified
    # End of test - no assertions
```

**Fix Strategy:**
1. Understand what the method should do
2. Add 2-4 assertions per test
3. Verify both return value AND side-effects

#### Example 1: Validation Method

**BEFORE:**
```python
def test_validate_git_repository_healthy(self):
    """Test valid Git repository passes validation."""
    validator = GitRepositoryValidator(self.temp_dir)
    validator.validate()  # ← No assertion
```

**AFTER:**
```python
def test_validate_git_repository_healthy(self):
    """Test valid Git repository passes validation."""
    validator = GitRepositoryValidator(self.temp_dir)
    result = validator.validate()

    # Assertion 1: Check return value exists
    assert result is not None
    # Assertion 2: Check status
    assert result.status == HealthStatus.HEALTHY
    # Assertion 3: Check no errors reported
    assert result.error_count == 0
    # Assertion 4: Check has message
    assert len(result.message) > 0
```

#### Example 2: Processing Method

**BEFORE:**
```python
def test_process_all_issues(self):
    processor = IssueProcessor(self.core)
    processor.process_all()  # ← Just runs
```

**AFTER:**
```python
def test_process_all_issues_updates_status(self):
    processor = IssueProcessor(self.core)

    # Setup verification
    initial_issues = self.core.get_issues()
    initial_count = len(initial_issues)

    # Execute
    processed = processor.process_all()

    # Verify return value
    assert processed is not None
    assert processed.success, "Should complete successfully"
    assert processed.count == initial_count

    # Verify side-effects
    final_issues = self.core.get_issues()
    assert all(i.status == "processed" for i in final_issues)
    assert processor.last_run_time is not None
```

#### Example 3: State-Changing Method

**BEFORE:**
```python
def test_install_hooks(self):
    manager = HookManager(self.repo)
    manager.install()  # ← No verification
```

**AFTER:**
```python
def test_install_hooks_creates_hook_files(self):
    manager = HookManager(self.repo)
    result = manager.install()

    # Return value assertions
    assert result is not None
    assert result.success == True
    assert result.error_message is None

    # File existence assertions
    hooks_path = self.repo / ".git/hooks"
    assert (hooks_path / "post-commit").exists()
    assert (hooks_path / "pre-commit").exists()
    assert (hooks_path / "pre-push").exists()

    # Permission assertions
    import os
    assert os.access(hooks_path / "post-commit", os.X_OK)

    # Content assertions
    content = (hooks_path / "post-commit").read_text()
    assert "#!/bin/bash" in content or "#!/usr/bin/env python" in content
```

### Tactic 1.2: The Assertion Checklist

For each test you fix, ask:

- [ ] Does it verify the **return value**?
- [ ] Does it verify the **type** of return value?
- [ ] Does it verify the **expected behavior** (not just "no error")?
- [ ] Does it verify **side-effects** (files created, state changed)?
- [ ] Does it verify **error cases** (or have separate test)?
- [ ] Could a typo in the code make this test fail? (If no, too weak)

**Minimum:** 2 assertions per test
**Good:** 3-4 assertions per test
**Excellent:** 4-5 assertions plus side-effect verification

---

## PHASE 2 TACTICS: Weak Assertions

### Tactic 2.1: Fix "Bare Bool" Assertions

**Pattern:**
```python
assert result  # ← What is result? What should it be?
assert value   # ← Too vague
```

**Fix:**
```python
# Instead of: assert result
assert result is True  # Explicit boolean check

# Or if it's a dict/object:
assert result is not None
assert isinstance(result, dict)
assert "key" in result
assert result["key"] == expected_value

# Or if return value indicates success:
assert result == expected_value
assert result.status == HealthStatus.HEALTHY
```

**Examples:**

**❌ BEFORE:**
```python
def test_generate_status_report(self):
    result = self.service.generate_status_report()
    assert result  # Could be {}, None, empty string...
```

**✅ AFTER:**
```python
def test_generate_status_report_returns_dict_with_status(self):
    result = self.service.generate_status_report()

    assert result is not None, "Should return report"
    assert isinstance(result, dict), "Should be dictionary"
    assert "status" in result, "Should include status key"
    assert result["status"] in ["healthy", "degraded", "critical"]
    assert "issues" in result, "Should include issues"
```

### Tactic 2.2: Fix "Mock Called" Assertions

**Pattern:**
```python
@patch('module.function')
def test_something(self, mock_func):
    something()
    assert mock_func.called  # ← How many times? With what args?
```

**Fix:** Verify **exact call count** and **arguments**

```python
@patch('module.function')
def test_something(self, mock_func):
    something()

    # Verify exact call count
    assert mock_func.call_count == 1, "Should call exactly once"

    # Verify arguments
    mock_func.assert_called_once_with('expected_arg', key='value')

    # Or inspect call details
    args, kwargs = mock_func.call_args
    assert args[0] == 'expected_arg'
    assert kwargs['key'] == 'value'
```

**Complete Example:**

**❌ BEFORE:**
```python
@patch('git.Repo.commit')
def test_create_commit(self, mock_commit):
    git_handler.create_commit("test message")
    assert mock_commit.called
```

**✅ AFTER:**
```python
@patch('git.Repo.commit')
def test_create_commit_with_message(self, mock_commit):
    message = "Fix: address issue #123"
    git_handler.create_commit(message)

    # Verify call count and arguments
    assert mock_commit.call_count == 1
    mock_commit.assert_called_once_with(message)

    # Or verify return value
    assert mock_commit.return_value is not None
```

### Tactic 2.3: Fix Call Count Assertions

**Pattern:**
```python
assert mock.call_count >= 1   # ← Wrong: too loose
assert mock.call_count <= 3   # ← Wrong: what's correct number?
assert mock.call_count > 0    # ← Wrong: imprecise
```

**Fix:** Use exact numbers

```python
assert mock.call_count == 1  # ← Right: exactly 1

# Or use assert_called_once methods
mock.assert_called_once()
mock.assert_called_once_with(arg)
```

**Why:** Loose ranges hide bugs. If you expect 1 call and get 5, that's a bug!

**Example:**

**❌ BEFORE:**
```python
def test_run_validators(self, mock_check):
    result = orchestrator.run_all()
    assert mock_check.call_count >= 1  # ← Could be 1, 2, 5, 100...
```

**✅ AFTER:**
```python
def test_run_validators_checks_each_component(self, mock_check):
    # The orchestrator checks 6 components
    result = orchestrator.run_all()

    # Verify it ran the right number of times
    assert mock_check.call_count == 6, "Should check all 6 components"

    # Verify what was checked
    calls = [call[0][0] for call in mock_check.call_args_list]
    expected = ["dir", "state", "issues", "milestones", "git", "db"]
    assert sorted(calls) == sorted(expected)
```

### Tactic 2.4: Add Missing Side-Effect Verification

**Pattern:** Tests verify mock was called but not actual result

**❌ BEFORE:**
```python
def test_create_branch(self):
    with patch('git.Repo.create_head') as mock_create:
        git_handler.create_branch("feature/test")
        assert mock_create.called  # ← Checks mock, not branch
```

**✅ AFTER:**
```python
def test_create_branch_creates_actual_branch(self):
    with self.repo:  # Use real repo
        git_handler.create_branch("feature/test")

        # Verify side-effect: branch exists
        branches = [h.name for h in self.repo.heads]
        assert "feature/test" in branches

        # Verify branch points to correct commit
        assert self.repo.heads["feature/test"].commit == self.repo.head.commit
```

**Complete Example with Both:**

**❌ BEFORE:**
```python
@patch('Path.mkdir')
def test_create_directory(self, mock_mkdir):
    handler.ensure_directory("/test/path")
    assert mock_mkdir.called  # ← Only verifies mock
```

**✅ AFTER:**
```python
@pytest.mark.parametrize("path,parents,exist_ok", [
    (Path("/test/dir"), True, True),
    (Path("/test/nested/dir"), True, True),
])
def test_create_directory_with_options(self, path, parents, exist_ok):
    # Use real file system (or mocking for specific case)
    with TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / path.name

        handler.ensure_directory(str(test_path), parents=parents, exist_ok=exist_ok)

        # Verify side-effect
        assert test_path.exists(), f"Directory {test_path} should exist"
        assert test_path.is_dir(), f"{test_path} should be directory, not file"
```

---

## PHASE 3 TACTICS: Structure Optimization

### Tactic 3.1: Reduce Mock Stacks

**The Problem:**
```python
@patch('module.Class1')
@patch('module.Class2')
@patch('module.Class3')
@patch('module.Class4')
@patch('module.Class5')
@patch('module.Class6')
def test_orchestrator(self, m6, m5, m4, m3, m2, m1):
    # Need to understand 6 mocks just to read the test
    # Can't test if real implementations work together
```

**Strategy 1: Test components separately**

```python
class TestClass1:
    def test_class1_with_real_class2(self):
        """Test Class1 with real Class2, mock Class3."""
        c2 = Class2()  # Real
        with patch('module.Class3') as m3:
            c1 = Class1(c2, m3)
            result = c1.do_something()
            assert result.success

class TestClass2:
    def test_class2_standalone(self):
        """Test Class2 in isolation."""
        c2 = Class2()
        result = c2.process()
        assert result is not None

class TestOrchestrator:
    def test_orchestrator_coordinates_classes(self):
        """Test that orchestrator calls classes in right order."""
        c1 = Class1(Class2())
        c2 = Class2()

        with patch.object(c1, 'do_something') as mock1, \
             patch.object(c2, 'process') as mock2:
            orchestrator = Orchestrator(c1, c2)
            orchestrator.run()

            # Verify orchestration order
            assert mock1.called
            assert mock2.called
            # Both should be called exactly once
            assert mock1.call_count == 1
            assert mock2.call_count == 1
```

**Strategy 2: Use fixtures instead of decorators**

```python
# Instead of decorator stacks, use fixtures
@pytest.fixture
def orchestrator_with_mocks(self):
    mocks = {
        'class1': Mock(),
        'class2': Mock(),
        'class3': Mock(),
    }
    orchestrator = Orchestrator(
        mocks['class1'],
        mocks['class2'],
        mocks['class3']
    )
    return orchestrator, mocks

def test_with_fixture(self, orchestrator_with_mocks):
    orchestrator, mocks = orchestrator_with_mocks
    result = orchestrator.run()
    # Much clearer what's mocked
```

### Tactic 3.2: Parameterize Similar Tests

**❌ BEFORE: 12 separate tests**
```python
def test_validate_priority_low(self):
    assert validator.validate_priority("low") == True

def test_validate_priority_medium(self):
    assert validator.validate_priority("medium") == True

def test_validate_priority_high(self):
    assert validator.validate_priority("high") == True

# ... 9 more very similar tests
```

**✅ AFTER: 1 parameterized test**
```python
@pytest.mark.parametrize("priority,expected", [
    # Valid values
    ("low", True),
    ("medium", True),
    ("high", True),
    ("critical", True),
    # Invalid values
    ("urgent", False),
    ("MEDIUM", False),  # case-sensitive
    ("  high  ", False),  # whitespace
    ("", False),
    (None, False),
    (123, False),
])
def test_priority_validation(self, priority, expected):
    result = validator.validate_priority(priority)
    assert result == expected, f"Priority {priority!r} validation mismatch"
```

**Benefits:**
- 12 test functions → 1 parameterized test
- 240 lines → 20 lines
- Easy to add new cases
- Better test discovery (shows all parameter values)
- Clearer what values are tested

**Candidates for Parameterization:**
1. Enum/constant validation (Priority, Status, etc.)
2. Date/time format tests
3. Path validation tests
4. String pattern tests
5. Error code tests

### Tactic 3.3: Split Large Tests

**Symptom:** Test >70 lines, mixes setup/execution/assertions

**Before:**
```python
def test_complete_workflow(self):  # 88 lines!
    # Lines 1-20: Setup
    with TemporaryDirectory() as tmpdir:
        repo = Repo.init(tmpdir)
        # ... setup ...

    # Lines 21-50: Execution
    result1 = handler.install_hooks(repo)
    result2 = handler.configure_hooks({"auto": True})
    result3 = handler.validate_hooks(repo)

    # Lines 51-88: Assertions (38 different assertions)
    assert result1.success
    # ... many more assertions ...
```

**After: Split into focused tests**
```python
class TestHookWorkflow:
    def setup_method(self):
        self.repo = Repo.init(self.temp_dir)
        self.handler = HookHandler(self.repo)

    def test_install_hooks_creates_files(self):
        """Install creates hook files."""
        result = self.handler.install_hooks(self.repo)
        assert result.success
        assert (self.repo / ".git/hooks/post-commit").exists()

    def test_install_hooks_sets_executable(self):
        """Install makes hooks executable."""
        self.handler.install_hooks(self.repo)
        import os
        assert os.access(
            self.repo / ".git/hooks/post-commit",
            os.X_OK
        )

    def test_configure_hooks_updates_config(self):
        """Configure updates settings."""
        result = self.handler.configure_hooks({"auto": True})
        assert result.success
        assert self.handler.config["auto"] == True

    def test_validate_hooks_checks_setup(self):
        """Validate checks hook installation."""
        self.handler.install_hooks(self.repo)
        result = self.handler.validate_hooks(self.repo)
        assert result.valid == True
        assert len(result.errors) == 0
```

**Guidelines:**
- **Max 50 lines per test** (including comments)
- **Max 10 assertions per test**
- **One primary behavior per test**
- **Use descriptive names** (test_X_does_Y)

---

## ASSERTION HELPERS & PATTERNS

### Pattern: "Assertion with Helpful Message"

```python
# BAD: No message
assert result.count == 5

# GOOD: With message
assert result.count == 5, f"Expected 5 items, got {result.count}"

# BETTER: With context
assert result.count == 5, (
    f"Processed {result.count} items, expected 5. "
    f"Details: {result.details}"
)
```

### Pattern: "Complex Assertion"

```python
# For assertions that need explanation:
def test_issue_ordering(self):
    issues = processor.get_sorted_issues()

    # Verify all issues present
    ids = [i.id for i in issues]
    assert len(ids) == 5, f"Expected 5 issues, got {len(ids)}"

    # Verify ordering
    priorities = [i.priority for i in issues]
    expected_order = ["critical", "high", "medium", "low", "low"]
    assert priorities == expected_order, (
        f"Wrong order. Got {priorities}, expected {expected_order}"
    )
```

### Pattern: "Verify Collection Properties"

```python
def test_collection_results(self):
    results = analyzer.find_issues()

    # Type check
    assert isinstance(results, list)
    assert len(results) == 3
    assert all(isinstance(r, Issue) for r in results)

    # Content check
    ids = {r.id for r in results}
    assert ids == {"issue-1", "issue-2", "issue-3"}

    # Property check
    assert all(r.status == "open" for r in results)
```

### Pattern: "Exception Testing"

```python
# ✓ CORRECT way
def test_invalid_priority_raises_error(self):
    with pytest.raises(ValueError) as exc_info:
        validator.validate_priority("invalid")

    # Verify error message
    assert "invalid" in str(exc_info.value).lower()
    assert "priority" in str(exc_info.value).lower()

# ✗ WRONG way (catches but doesn't verify)
def test_invalid_priority_raises_error(self):
    try:
        validator.validate_priority("invalid")
        assert False, "Should raise ValueError"
    except ValueError:
        pass  # ← Too weak; could be any ValueError
```

---

## QUICK REFERENCE: Assertion Checklist

### For RETURN VALUES:
- [ ] Verify type (is not None, isinstance, etc.)
- [ ] Verify value (== expected)
- [ ] Verify content if container (keys, items, etc.)

### For SIDE-EFFECTS:
- [ ] Files created/deleted
- [ ] State changed in objects
- [ ] Database entries added/modified
- [ ] Mocks called with correct arguments

### For ERROR CASES:
- [ ] Exception raised
- [ ] Exception message contains key words
- [ ] Exception type is correct

### For MOCKS:
- [ ] Call count exact (==, not >=)
- [ ] Arguments verified
- [ ] Side-effects verified (not just mock.called)

---

## Practical Example: One Test From Start to Finish

### STARTING POINT
```python
def test_process_repository(self):
    repo = Repository(self.test_dir)
    repo.process()
```
**Issues:** No assertions, no setup verification, unclear what it tests

### STEP 1: Understand What It Should Do
Reading code and docs: "Process repository should scan all issues and update their status based on Git history"

### STEP 2: Add Setup Verification
```python
def test_process_repository_updates_issue_status(self):
    repo = Repository(self.test_dir)

    # Setup: Create some test issues
    issue1 = repo.create_issue("Issue 1")
    issue2 = repo.create_issue("Issue 2")
    initial_status_1 = issue1.status
    initial_status_2 = issue2.status

    repo.process()
```

### STEP 3: Add Behavior Verification
```python
def test_process_repository_updates_issue_status(self):
    repo = Repository(self.test_dir)

    # Setup
    issue1 = repo.create_issue("Issue 1")
    issue2 = repo.create_issue("Issue 2")
    initial_status_1 = issue1.status
    initial_status_2 = issue2.status

    # Execute
    result = repo.process()

    # Verify return value
    assert result is not None
    assert result.success == True
    assert result.processed_count == 2

    # Verify side-effects
    assert issue1.status != initial_status_1  # Status changed
    assert issue2.status != initial_status_2  # Status changed
    assert issue1.status in ["open", "closed", "in-progress"]  # Valid status
```

### STEP 4: Add Edge Case Verification
```python
def test_process_repository_with_no_issues(self):
    """Test process handles empty repository gracefully."""
    repo = Repository(self.test_dir)  # No issues created

    result = repo.process()

    assert result.success == True
    assert result.processed_count == 0
    assert result.error_count == 0

def test_process_repository_with_invalid_issue_state(self):
    """Test process handles corrupted issue data."""
    repo = Repository(self.test_dir)
    issue = repo.create_issue("Test")
    issue.data_file.write_text("{invalid json")  # Corrupt data

    result = repo.process()

    assert result.success == False
    assert "corrupted" in result.error_message.lower()
    assert result.error_count == 1
```

### FINAL TEST
```python
class TestRepositoryProcessing:
    def test_process_updates_issue_status_from_git_history(self):
        """Process scans Git history and updates issue status."""
        repo = Repository(self.test_dir)

        # Create issues with known state
        issue1 = repo.create_issue("Feature A", status="open")
        issue2 = repo.create_issue("Bug B", status="open")

        # Git history shows both were committed
        # (Set up commits in test repo)

        result = repo.process()

        # Verify processing succeeded
        assert result.success == True
        assert result.processed_count == 2
        assert result.error_count == 0

        # Verify issues updated based on Git
        assert issue1.status == "closed"  # Was committed
        assert issue2.status == "closed"  # Was committed
        assert issue1.last_commit_sha is not None

    def test_process_skips_missing_issue_data(self):
        """Process handles missing issue data gracefully."""
        repo = Repository(self.test_dir)
        issue = repo.create_issue("Test")
        issue.data_file.unlink()  # Delete issue data

        result = repo.process()

        assert result.success == False
        assert result.error_count >= 1
        assert "missing" in result.error_message.lower()
```

---

## Success Indicators

You'll know you're doing this right when:

✅ Each test has 3+ assertions
✅ Test name matches what it actually tests
✅ Assertions are specific (not just "truthy")
✅ No decorator stacks >3 deep
✅ Similar tests are parameterized
✅ Tests <60 lines
✅ Test failures give clear error messages
✅ New team member can understand test purpose in 1 minute
✅ Test covers happy path + edge cases
✅ Mock-heavy tests have separate real-component tests

---

## Resources

**Test Quality Standards:**
- Python Testing with pytest (Brian Okken)
- Working Effectively with Legacy Code (Michael Feathers) - ch 10-12
- xUnit Test Patterns (Gerard Meszaros)

**Pytest Docs:**
- https://docs.pytest.org/en/stable/parametrize.html
- https://docs.pytest.org/en/stable/monkeypatch.html
- https://docs.pytest.org/en/stable/reference.html#pytest-mark
