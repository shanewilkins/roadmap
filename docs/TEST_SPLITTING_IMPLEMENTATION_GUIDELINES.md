# Test File Splitting Implementation Guidelines

## Pre-Splitting Checklist

### Analysis Phase
- [ ] Count test classes and methods in the file
- [ ] Identify logical groupings (domains, operations, entity types)
- [ ] Map dependencies between test classes
- [ ] Identify shared fixtures
- [ ] Check for implicit test ordering or state dependencies

### Safety Phase
- [ ] Run full test suite on current branch (baseline)
- [ ] Create backup branch: `git branch backup-pre-split`
- [ ] Commit any pending work
- [ ] Ensure CI/CD passing

### Planning Phase
- [ ] Create detailed split plan (which classes go where)
- [ ] Identify which fixtures need to be shared
- [ ] Plan conftest.py structure
- [ ] Document any architectural decisions

---

## Splitting Process (Step by Step)

### Step 1: Create Directory Structure (if needed)

```bash
# For test_cli_commands.py split
mkdir -p tests/integration/cli_commands
touch tests/integration/cli_commands/__init__.py
touch tests/integration/cli_commands/conftest.py
```

### Step 2: Create conftest.py for Shared Fixtures

Extract fixtures specific to the test domain:

```python
# tests/integration/cli_commands/conftest.py
import pytest
from tests.fixtures.cli import isolated_roadmap, isolated_roadmap_with_issues

# Re-export fixtures for consistency
__all__ = ["isolated_roadmap", "isolated_roadmap_with_issues"]
```

### Step 3: Create Individual Test Files

For each split:
```bash
# Start with first domain
cp tests/integration/test_cli_commands.py \
   tests/integration/cli_commands/test_cli_issue_commands.py

# Edit to remove unrelated test classes
# Keep only: TestCLIIssueCreate, TestCLIIssueList, etc.
```

### Step 4: Update Imports

In each split file, ensure correct imports:

```python
"""Tests for CLI issue commands.

Tests CLI issue commands: create, list, update, delete, start, close.
"""

# Keep existing imports
import pytest
from click.testing import CliRunner
from roadmap.adapters.cli import main

# Fixtures will come from conftest.py
# (accessed automatically by pytest)
```

### Step 5: Verify and Cleanup

```bash
# Run tests in new structure
pytest tests/integration/cli_commands/ -v

# If passing, remove old file
# git rm tests/integration/test_cli_commands.py

# Update any __init__.py files as needed
```

### Step 6: Validate

```bash
# Full test suite
pytest tests/ -v

# Check for import errors
python -m py_compile tests/integration/cli_commands/*.py

# Check line counts
wc -l tests/integration/cli_commands/*.py
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Broken Imports

**Problem:** After splitting, imports fail because fixtures are lost

**Solution:**
```python
# DON'T do this - fixtures get lost when splitting
from tests.integration.test_cli_commands import isolated_roadmap

# DO use conftest.py for fixture sharing
# conftest.py at appropriate level re-exports shared fixtures
```

**Prevention:**
- Keep conftest.py one level up from split files
- Re-export fixtures that multiple split files need
- Use `from . import` for relative imports

### Pitfall 2: Test Ordering Dependencies

**Problem:** Tests pass individually but fail when run together (test ordering issue)

**Solution:**
```python
# DON'T: Create test state in one test for another test to use
class TestFoo:
    def test_create_item(self):
        # Creates global state
        self.item_id = 1  # BAD!

    def test_update_item(self):
        # Depends on test_create_item running first
        update_item(self.item_id)  # BAD!

# DO: Make each test self-contained
class TestFoo:
    def test_create_item(self):
        item_id = create_item()
        assert item_id

    def test_update_item(self):
        item_id = create_item()  # Re-create for this test
        result = update_item(item_id)
        assert result
```

**Prevention:**
- Each test should be independent
- Use fixtures for setup, not shared class state
- Run tests with `pytest --random-order-bucket=global` to catch ordering issues

### Pitfall 3: Fixture Duplication

**Problem:** Fixtures are copy-pasted into multiple split files

**Solution:**
```python
# DON'T: Duplicate in each split file
# test_cli_issue_commands.py
@pytest.fixture
def isolated_roadmap(cli_runner):
    ...

# test_cli_milestone_commands.py
@pytest.fixture
def isolated_roadmap(cli_runner):
    ... # DUPLICATED!

# DO: Create shared fixture module
# tests/fixtures/cli.py
@pytest.fixture
def isolated_roadmap(cli_runner):
    ...

# tests/integration/cli_commands/conftest.py
from tests.fixtures.cli import isolated_roadmap
__all__ = ["isolated_roadmap"]
```

**Prevention:**
- Create fixtures/ module for shared fixtures
- Use conftest.py to re-export from fixtures/
- Establish clear ownership of each fixture

### Pitfall 4: Unrelated Classes in Same File

**Problem:** After split, still have multiple unrelated test classes in one file

**Solution:** Verify 1-3 logically related classes per file

```python
# TOO MANY UNRELATED CLASSES (BAD)
class TestIssueCreate:
    ...

class TestIssueList:
    ...

class TestMilestoneCreate:  # Unrelated!
    ...

class TestMilestoneList:  # Unrelated!
    ...

# BETTER: Split into domain-specific files
# test_cli_issue_commands.py
class TestIssueCreate:
    ...

class TestIssueList:
    ...

# test_cli_milestone_commands.py
class TestMilestoneCreate:
    ...

class TestMilestoneList:
    ...
```

### Pitfall 5: Performance Regression

**Problem:** Tests run slower after splitting (usually fixture overhead)

**Solution:**
```python
# DON'T: Create separate fixtures per split file
# This creates multiple isolated filesystems

# DO: Share fixtures at appropriate scope
# conftest.py
@pytest.fixture(scope="module")
def isolated_roadmap():
    # Created once per module
    with cli_runner.isolated_filesystem():
        ...
```

**Prevention:**
- Profile test execution before and after split
- Use appropriate fixture scopes (function, class, module, session)
- Avoid unnecessary fixture re-creation

---

## File Naming Conventions

### Principle: Clarity from Filename

```python
# GOOD: Filename clearly indicates content
tests/integration/cli_commands/test_cli_issue_commands.py
# → Contains CLI tests for issue commands

tests/unit/core/services/health_scanner/test_entity_health_scanner_basic.py
# → Contains basic health scanner tests

# AVOID: Ambiguous naming
tests/integration/test_commands.py           # Too vague
tests/unit/services/test_scanner_1.py       # Unclear domain
tests/test_foo_bar_baz.py                   # Meaningless
```

### Pattern: `test_<domain>_<subdomain>[_<scope>].py`

```
test_cli_issue_commands.py
       ↑    ↑    ↑
   domain  |    specificity
           subdomain

test_entity_health_scanner_basic.py
       ↑      ↑      ↑         ↑
   domain  subdomain noun     scope
```

---

## Commit Strategy

### Commit Per Split (Atomic)

```bash
# Commit each split separately for clarity
git add tests/integration/cli_commands/test_cli_issue_commands.py
git add tests/integration/cli_commands/conftest.py
git commit -m "Split test_cli_commands.py: Extract CLI issue commands tests

- Created test_cli_issue_commands.py with 200 LOC
- Contains: TestCLIIssueCreate, TestCLIIssueList, TestCLIIssueUpdate, etc.
- Moved shared fixtures to cli_commands/conftest.py
- All 89 tests passing in both new and old location during transition
- Next: Remove test_cli_commands.py after verifying all splits"

# Remove old file once all splits verified
git rm tests/integration/test_cli_commands.py
git commit -m "Remove old test_cli_commands.py after successful split

- All CLI command tests now in tests/integration/cli_commands/
- Verified all 89 tests passing in new locations
- All imports working correctly"
```

### Commit Message Template

```
Tier [N] Split: <target_file>

- Created <new_file_1.py> with <LOC> LOC (<class_count> test classes)
- Created <new_file_2.py> with <LOC> LOC (<class_count> test classes)
- Moved shared fixtures to conftest.py
- All <test_count> tests passing in new structure
- [KEEP] or [REMOVE] old file after transition verification

Closes: <issue_if_exists>
```

---

## Verification Checklist (Post-Split)

### Local Verification
- [ ] All test files compile (no syntax errors)
- [ ] All tests pass: `pytest <new_split_files> -v`
- [ ] No import errors: `python -m py_compile tests/.../test_*.py`
- [ ] File sizes in acceptable range (300-400 LOC)
- [ ] Clear logical grouping verified by code review
- [ ] Fixtures properly shared through conftest.py

### Integration Verification
- [ ] Full test suite passes: `pytest tests/ -v`
- [ ] No change in overall test count
- [ ] No increase in test execution time (>5%)
- [ ] CI/CD pipeline green
- [ ] No flaky tests introduced

### Documentation Verification
- [ ] Module docstring updated if needed
- [ ] Test class docstrings clear about domain
- [ ] README or docs updated if structure changed
- [ ] Code comments explain any non-obvious splits

### Cleanup Verification
- [ ] Old files removed or confirmed as unneeded
- [ ] Unused imports removed
- [ ] No commented-out code left behind
- [ ] __init__.py files appropriate

---

## Performance Optimization Tips

### Fixture Overhead
```python
# SLOW: Fixture created for every test
@pytest.fixture
def expensive_setup():
    return complex_initialization()

class TestFoo:
    def test_1(self, expensive_setup):
        ...
    def test_2(self, expensive_setup):
        ...
    # expensive_setup recreated twice!

# FAST: Use appropriate scope
@pytest.fixture(scope="class")
def expensive_setup():
    return complex_initialization()

# FASTER: Only use when needed
@pytest.fixture(scope="module")
def expensive_setup():
    return complex_initialization()
```

### Test Ordering
```python
# SLOW: Random test order causes repeated setup/teardown
pytest tests/ --random-order-bucket=global

# FAST: Keep related tests together
# Keep related tests in same file or use markers:
pytest tests/ -m "slow or fast"
```

---

## Rollback Procedure

If critical issues discovered post-split:

```bash
# 1. Immediately switch to backup
git checkout backup-pre-split

# 2. Investigate issue
# (Keep the split branch for analysis)
git checkout broken-split
git log --oneline | head
# Identify problematic commit

# 3. Cherry-pick individual good commits if possible
git checkout main
git cherry-pick <good_commit_hash>

# 4. Or simply revert everything
git revert HEAD~N..HEAD
git push
```

---

## Checklist for Review

Before PR submission:

- [ ] Commit messages clear and atomic
- [ ] Test files renamed/organized as planned
- [ ] Fixtures properly shared
- [ ] All tests passing
- [ ] No performance regression
- [ ] Documentation updated
- [ ] Related files updated (setup.py, tox.ini, etc.)
