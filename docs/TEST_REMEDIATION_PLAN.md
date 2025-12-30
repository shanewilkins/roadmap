# Test Suite Remediation Plan

**Status:** Ready for execution
**Timeline:** 3-4 weeks (1-2 person full-time equivalent)
**Target:** Transform from "good architecture, incomplete tests" → "production-quality test suite"

---

## Executive Strategy

### Three-Phase Approach
1. **Phase 1 (Days 1-5):** Fix critical issues (missing assertions)
2. **Phase 2 (Days 6-12):** Strengthen weak assertions
3. **Phase 3 (Days 13-20):** Optimize structure (parameterization, mocking, test size)

### Success Metrics
| Metric | Current | Target | Validation |
|--------|---------|--------|------------|
| Tests with assertions | 5,198 | 5,582 | `grep -c "assert " tests/**/*.py` |
| Avg assertions/test | 1.2 | 2.8+ | Analysis script |
| Vague assertions | 429 | <50 | Manual audit |
| Mocks per test (avg) | 2.1 | <1.5 | Decorator count analysis |
| Parameterized tests | 7.2% | 22% | File count scan |
| Test file avg size | 196 LOC | 180 LOC | `wc -l` |

---

## PHASE 1: CRITICAL ISSUES (Days 1-5) 🔴

### Goal: Eliminate all tests with zero assertions

#### 1.1 Identify All Offending Tests
**Task:** Create audit of all 384 tests with missing assertions

```bash
# Script to identify tests with no assertions
python3 << 'EOF'
import ast
import os
from pathlib import Path

class AssertionChecker(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.tests_without_asserts = []
        self.current_test = None

    def visit_FunctionDef(self, node):
        if node.name.startswith('test_'):
            self.current_test = node
            has_assert = any(
                isinstance(n, ast.Assert)
                for n in ast.walk(node)
            )
            if not has_assert:
                self.tests_without_asserts.append((
                    self.filename,
                    node.name,
                    node.lineno
                ))
        self.generic_visit(node)

# Scan all test files
for test_file in Path('tests').rglob('test_*.py'):
    with open(test_file) as f:
        try:
            tree = ast.parse(f.read())
            checker = AssertionChecker(str(test_file))
            checker.visit(tree)
            for filepath, func_name, lineno in checker.tests_without_asserts:
                print(f"{filepath}:{lineno} {func_name}")
        except:
            pass
EOF
```

**Output:** List of 384 tests with line numbers
**Effort:** 1 hour
**Owner:** Lead dev

#### 1.2 Triage and Categorize
**Task:** For each test, determine fix strategy

Categories:
1. **Incomplete tests (50%)** - Need assertions added
2. **Implicit success tests (30%)** - Call method, verify it ran without error
3. **Setup-only tests (15%)** - Part of larger test flow
4. **Broken tests (5%)** - Should be deleted

```python
# Template for categorization audit
AUDIT_TEMPLATE = {
    "file": "tests/test_infrastructure_validator_git_db.py",
    "test_name": "test_validate_git_repository_missing_files",
    "lineno": 156,
    "category": "incomplete",  # or "implicit", "setup_only", "broken"
    "action": "add_assertions",
    "new_assertions": [
        "assert not result.is_healthy",
        "assert result.status == HealthStatus.DEGRADED",
        "assert 'missing' in result.message.lower()"
    ],
    "estimated_minutes": 5,
    "difficulty": "easy"
}
```

**Effort:** 2-3 hours (384 tests ÷ 2 min per triage = 12+ hours for team, ~3 hrs parallel with right tools)
**Owner:** Team review

#### 1.3 Fix "Incomplete Tests" (50% of 384 = 192 tests)
**Task:** Add missing assertions to scaffolded tests

**Strategy:** Create dedicated remediation files

```
tests/remediation/
├── batch_001_infrastructure_validators.py
├── batch_002_git_operations.py
├── batch_003_core_services.py
└── REMEDIATION_LOG.md
```

**Example Fix Pattern:**

**BEFORE:**
```python
def test_validate_git_repository_missing_files(self):
    """Test validation fails with missing .git structure."""
    validator = GitRepositoryValidator(self.temp_dir)
    validator.validate()  # ← No assertion
```

**AFTER:**
```python
def test_validate_git_repository_missing_files(self):
    """Test validation fails when required files are missing."""
    import shutil
    shutil.rmtree(self.temp_dir / ".git")

    validator = GitRepositoryValidator(self.temp_dir)
    result = validator.validate()

    # Actual assertions
    assert not result.is_healthy, "Should detect missing .git"
    assert result.status == HealthStatus.DEGRADED
    assert "missing" in result.message.lower()
    assert result.error_count > 0
```

**Batch Processing:**
- Batch 001: 50 tests (1.5 hours)
- Batch 002: 50 tests (1.5 hours)
- Batch 003: 50 tests (1.5 hours)
- Batch 004: 42 tests (1.25 hours)

**Total effort:** 6 hours (spread across team)
**Parallelization:** 4 devs × 1.5 hours each = 6 wall-clock hours

#### 1.4 Fix "Implicit Success Tests" (30% of 384 = 115 tests)
**Task:** Tests that verify no exception thrown, not actual behavior

**Pattern:**
```python
# BEFORE: Calls method, no assertions
def test_process_issues(self):
    processor = IssueProcessor(self.core)
    processor.process_all()  # ← Just runs, no check

# AFTER: Verify actual behavior
def test_process_issues_updates_issue_status(self):
    processor = IssueProcessor(self.core)
    initial_count = len(self.core.get_issues())

    processor.process_all()

    # Verify actual behavior
    assert processor.processed_count == initial_count
    assert all(i.status == "processed" for i in self.core.get_issues())
```

**Effort:** 4 hours (2 min per test × 115)
**Parallelization:** 2 devs × 2 hours each = 4 wall-clock hours

#### 1.5 Clean Up "Setup-Only Tests" (15% of 384 = 58 tests)
**Task:** Migrate to fixtures or delete duplicates

**Action:** Move to conftest or remove if redundant
**Effort:** 1.5 hours
**Parallelization:** Can be done in parallel

#### 1.6 Delete Broken Tests (5% of 384 = 19 tests)
**Task:** Remove tests that test nothing/test deprecated code

**Process:** Document reason for deletion, commit separately
**Effort:** 0.5 hours

### Phase 1 Summary
**Total Effort:** ~13-15 hours (3-4 developer-days)
**Wall-Clock Time:** 3-5 days (1-2 devs, 4 hours/day)
**Result:** 384 tests → all with meaningful assertions
**Next:** Verify all tests still pass

---

## PHASE 2: STRENGTHEN WEAK ASSERTIONS (Days 6-12) 🟠

### Goal: Convert vague assertions to specific ones

#### 2.1 Identify Vague Assertions
**Task:** Find and categorize 429+ weak assertions

```python
# Script to find vague assertions
VAGUE_PATTERNS = [
    (r'assert\s+\w+\s*$', "Bare variable (assert result)"),
    (r'assert\s+\w+\.\w+\s*$', "Bare attribute (assert obj.prop)"),
    (r'assert\s+\w+\(.+\)\s*$', "Bare function (assert func())"),
    (r'assert\s+\w+\.called', "Mock called check only"),
    (r'assert\s+\w+\.call_count\s*[><=]', "Loose call count"),
    (r'assert.*\.return_value', "Asserting mock setup, not result"),
]
```

**Categories to fix:**
1. **`assert result`** (82 tests) → `assert result is True` + behavior
2. **`assert mock.called`** (67 tests) → `assert mock.call_count == N` + verify args
3. **`assert call_count >= 1`** (43 tests) → `assert call_count == exact_number`
4. **`assert x is not None`** (89 tests) → `assert x == expected_value`
5. **Missing side-effect verification** (148 tests) → Add file/state checks

**Effort:** 1 hour (categorization)
**Owner:** Lead dev with team assistance

#### 2.2 Fix "Bare Variable" Assertions (82 tests)

**BEFORE:**
```python
def test_generate_status_report(self):
    result = self.service.generate_status_report()
    assert result  # ← What is result? Bool? Dict? String?
```

**AFTER:**
```python
def test_generate_status_report(self):
    result = self.service.generate_status_report()
    assert result is not None, "Should return report"
    assert isinstance(result, dict), "Should return dict"
    assert "health_status" in result, "Should include health status"
    assert result["health_status"] in ["healthy", "degraded", "critical"]
```

**Effort:** 3 hours (2 min per test × 82)
**Parallelization:** 2 devs × 1.5 hours each

#### 2.3 Fix "Mock Called" Assertions (67 tests)

**BEFORE:**
```python
@patch('subprocess.run')
def test_get_current_user(self, mock_run):
    mock_run.return_value = Mock(stdout=b"John Doe")
    result = git_helper.get_current_user()
    assert mock_run.called  # ← Called how many times? With what args?
```

**AFTER:**
```python
@patch('subprocess.run')
def test_get_current_user(self, mock_run):
    mock_run.return_value = Mock(stdout=b"John Doe")
    result = git_helper.get_current_user()

    # Verify call count
    assert mock_run.call_count == 1, "Should call subprocess exactly once"

    # Verify arguments
    call_args = mock_run.call_args[0][0]
    assert "git config user.name" in call_args

    # Verify result
    assert result == "John Doe"
```

**Effort:** 2.5 hours (2.25 min per test × 67)
**Parallelization:** 2 devs × 1.25 hours each

#### 2.4 Fix "Loose Call Count" Assertions (43 tests)

**BEFORE:**
```python
def test_run_all_checks(self, mock_check):
    validator.run_all_infrastructure_checks()
    assert mock_check.call_count >= 1  # ← How many is "right"?
```

**AFTER:**
```python
def test_run_all_infrastructure_checks(self, mock_check):
    validator = InfrastructureValidator()
    validator.run_all_infrastructure_checks()

    # Exact count, not range
    assert mock_check.call_count == 1, "Should check exactly once"

    # Or if multiple calls expected:
    # assert mock_check.call_count == 6, "Should run 6 validators"
```

**Effort:** 1.5 hours (2 min per test × 43)

#### 2.5 Fix "None Checks" (89 tests)

**BEFORE:**
```python
def test_create_issue(self):
    issue = Issue(title="Test")
    assert issue is not None  # ← Too weak
```

**AFTER:**
```python
def test_create_issue_sets_title(self):
    issue = Issue(title="Test Issue")
    assert issue is not None
    assert issue.title == "Test Issue"
    assert issue.id is not None
    assert isinstance(issue.created_at, datetime)
```

**Effort:** 2 hours (1.35 min per test × 89)

#### 2.6 Add Missing Side-Effect Assertions (148 tests)

**BEFORE:**
```python
def test_install_hooks(self):
    manager = HookManager(self.repo)
    result = manager.install()
    assert result.success  # ← Checks return value, not side-effect
```

**AFTER:**
```python
def test_install_hooks_creates_files(self):
    manager = HookManager(self.repo)
    result = manager.install()

    # Verify return value
    assert result.success, "Should report success"

    # Verify side-effects
    hooks_dir = self.repo / ".git/hooks"
    assert (hooks_dir / "post-commit").exists(), "Should create post-commit hook"
    assert (hooks_dir / "pre-commit").exists(), "Should create pre-commit hook"

    # Verify permissions
    import os
    assert os.access(hooks_dir / "post-commit", os.X_OK), "Hook should be executable"
```

**Effort:** 3 hours (1.2 min per test × 148)

### Phase 2 Summary
**Total Effort:** ~13 hours (3 developer-days)
**Wall-Clock Time:** 4-6 days (2 devs)
**Result:** 429+ vague assertions → specific, meaningful assertions
**Validation:** Run tests, ensure all still pass

---

## PHASE 3: OPTIMIZE STRUCTURE (Days 13-20) 🟡

### 3.1 Reduce Excessive Mocking (128 tests)

**Goal:** Eliminate mock decorator stacks, test real behavior

**Current Pattern (BAD):**
```python
@patch.object(RoadmapDirectoryValidator, "check")
@patch.object(StateFileValidator, "check")
@patch.object(IssuesDirectoryValidator, "check")
@patch.object(MilestonesDirectoryValidator, "check")
@patch.object(GitRepositoryValidator, "check")
@patch.object(DatabaseIntegrityValidator, "check")
def test_run_all_infrastructure_checks(self, ...):
    # 6 mocks for 1 test; actual validators never run
```

**Strategy:** Test components separately, then integration

```python
# Unit: Test individual validators
def test_roadmap_directory_validator_healthy_state(self):
    """Test validator when directory is healthy."""
    validator = RoadmapDirectoryValidator(self.healthy_dir)
    status, message = validator.check()
    assert status == HealthStatus.HEALTHY

def test_state_file_validator_healthy_state(self):
    """Test validator when state file is valid."""
    validator = StateFileValidator(self.valid_state_file)
    status, message = validator.check()
    assert status == HealthStatus.HEALTHY

# Integration: Test orchestration
def test_infrastructure_validator_runs_all_checks(self):
    """Test that orchestrator runs all checks."""
    validator = InfrastructureValidator(self.healthy_infrastructure)
    results = validator.run_all_infrastructure_checks()

    # Verify all checks ran
    assert len(results) == 6
    assert "roadmap_directory" in results
    assert "state_file" in results
    # ... etc
```

**Effort:** 4-5 hours
- Identify mock-heavy tests: 1 hour
- Refactor to unit + integration: 3-4 hours

#### Specific Tests to Refactor:

| File | Issue | Strategy |
|------|-------|----------|
| test_infrastructure_validator_git_db.py | 6 mocks per test | Split into unit tests (no mocks) + integration test (1 mock) |
| test_entity_health_scanner_core_tests.py | 4-5 mocks per test | Test scanner + components separately |
| test_git_hooks_integration_complete.py | 7+ mocks | Keep integration, add unit tests for each component |

**Owner:** 1-2 devs
**Timeline:** 2-3 days

### 3.2 Increase Parameterization (Only 7.2%, need 22%)

**Goal:** Convert 300+ single-value tests to parameterized tests

**Current Pattern (BAD):**
```python
def test_priority_valid_low(self):
    assert validator.validate_priority("low")

def test_priority_valid_medium(self):
    assert validator.validate_priority("medium")

def test_priority_valid_high(self):
    assert validator.validate_priority("high")

def test_priority_invalid_urgent(self):
    assert not validator.validate_priority("urgent")

# ... 6 more nearly identical tests
```

**Target Pattern (GOOD):**
```python
@pytest.mark.parametrize("priority,expected", [
    ("low", True),
    ("medium", True),
    ("high", True),
    ("urgent", False),
    ("", False),
    (None, False),
    ("MEDIUM", False),  # case-sensitive
])
def test_priority_validation(self, priority, expected):
    assert validator.validate_priority(priority) == expected
```

**Benefits:**
- 12 tests → 1 parameterized test
- Easier to add new cases
- Better test discovery
- Reduces file count

**Scope:** Priority validators, status validators, type validators

**Effort:** 3-4 hours
- Identify parameterizable tests: 1 hour
- Consolidate: 2-3 hours

**Files to update:**
- tests/common/validation/test_roadmap_validator_basic.py (42 tests → 8)
- tests/common/validation/test_roadmap_validator_advanced.py (28 tests → 5)
- tests/unit/core/services/validators/ (60 tests → 15)

**Owner:** 1-2 devs
**Timeline:** 1-2 days

### 3.3 Split Large Tests (28 tests, 54-94 lines)

**Goal:** Break 88-line tests into 3-5 focused tests

**Current Pattern (BAD):**
```python
def test_complete_workflow(self):
    # SETUP: 20 lines
    with TemporaryDirectory() as tmpdir:
        repo = Repo.init(tmpdir)
        # ... create branches, configure hooks ...

    # EXECUTION: 25 lines
    result1 = repo.hooks.install()
    result2 = repo.hooks.configure(...)
    result3 = repo.hooks.validate(...)
    result4 = repo.hooks.cleanup()

    # ASSERTIONS: 43 lines
    assert result1.success
    # ... 40 more assertions on different concerns
```

**Target Pattern (GOOD):**
```python
class TestHookLifecycle:
    def test_install_creates_hook_files(self):
        """Install creates hook files."""
        manager = HookManager(self.repo)
        manager.install()
        assert (self.repo / ".git/hooks/post-commit").exists()

    def test_install_sets_executable_permissions(self):
        """Install makes hooks executable."""
        manager = HookManager(self.repo)
        manager.install()
        hook = self.repo / ".git/hooks/post-commit"
        assert os.access(hook, os.X_OK)

    def test_configure_updates_settings(self):
        """Configure updates manager settings."""
        manager = HookManager(self.repo)
        manager.configure({"auto_update": True})
        assert manager.config["auto_update"] == True

    def test_cleanup_removes_hooks(self):
        """Cleanup removes hook files."""
        manager = HookManager(self.repo)
        manager.install()
        manager.cleanup()
        assert not (self.repo / ".git/hooks/post-commit").exists()
```

**Files to refactor:**
- tests/integration/test_git_hooks_integration_complete.py (94 lines → 5 tests)
- tests/integration/test_integration_workflows.py (82 lines → 4 tests)
- tests/test_cli/test_milestone_repository_update_archive_concurrency.py (71 lines → 3 tests)

**Effort:** 2-3 hours
- Identify large tests: 0.5 hour
- Refactor: 2 hours (5-7 min per test × 28)

**Owner:** 1-2 devs
**Timeline:** 1 day

### Phase 3 Summary
**Total Effort:** ~12-14 hours (3 developer-days)
**Wall-Clock Time:** 5-7 days (2 devs)
**Results:**
- 128 mock-heavy tests refactored
- 22% of tests parameterized (vs. 7.2%)
- Large tests split into focused tests
- Avg test file size reduced to <180 LOC

---

## IMPLEMENTATION SCHEDULE

### Week 1: Phase 1 (Critical Issues)
```
Mon: Audit & triage (3-4 hours)
Tue: Fix incomplete tests (3 hours × 2 devs = 6 hours)
Wed: Fix implicit success tests (3 hours × 2 devs = 6 hours)
Thu: Fix setup-only + broken tests (2 hours)
Fri: Verification + commit (2 hours)
```
**Result:** All 384 tests have assertions ✓

### Week 2: Phase 2 (Weak Assertions)
```
Mon: Identify vague patterns (1 hour)
Tue-Wed: Fix bare assertions + mock assertions (4 hours × 2 devs)
Thu: Fix call_count + none checks (3 hours × 2 devs)
Fri: Add side-effect assertions + verification (3 hours × 2 devs)
```
**Result:** 429+ assertions strengthened ✓

### Week 3: Phase 3a (Mocking)
```
Mon-Tue: Refactor mock-heavy tests (4 hours × 2 devs)
Wed: Verification (2 hours)
```
**Result:** 128 tests with better coverage ✓

### Week 3-4: Phase 3b (Parameterization)
```
Wed-Thu: Parameterize validation tests (3 hours × 2 devs)
```

### Week 4: Phase 3c (Large Tests) + Wrap-up
```
Mon-Tue: Split large tests (2.5 hours × 2 devs)
Wed-Thu: Final verification, documentation
Fri: Commit, write summary
```

---

## RESOURCE ALLOCATION

### Option 1: Single Developer (20 days)
- Mon-Fri Week 1-4: Dedicated test remediation
- Manageable pace: 4-5 hours/day on remediation
- Leaves time for interruptions

### Option 2: Two Developers (10 days parallel)
- Both work Phase 1 Week 1: 3-5 days
- Split Phase 2 Week 2: 4-5 days
- Split Phase 3 Week 3-4: 4-5 days
- **Recommended:** Parallel work on independent test categories

### Option 3: Team Effort (5 days)
- 4 developers × 3 hours/day = 12 hours/day
- Phase 1: Mon-Tue
- Phase 2: Wed-Fri (partial)
- Finish Week 2

---

## QUALITY GATES & VALIDATION

### Before Committing Each Phase

#### Phase 1 Validation
```bash
# Verify all tests have assertions
python3 tests/validate_assertions.py
# Expected: 0 tests without assertions

# Run full test suite
poetry run pytest tests/ -v
# Expected: 5,582 tests passing

# Verify no regressions
git diff --name-only | xargs pytest
```

#### Phase 2 Validation
```bash
# Verify assertion specificity
python3 tests/validate_assertion_quality.py
# Expected: <50 vague assertions remaining

# Coverage analysis
poetry run pytest --cov=roadmap tests/
# Expected: Coverage maintained or improved
```

#### Phase 3 Validation
```bash
# Verify mock count
python3 tests/validate_mock_usage.py
# Expected: Avg mocks/test < 1.5

# Verify test distribution
python3 tests/validate_parameterization.py
# Expected: 22% parameterized

# File size analysis
python3 tests/validate_test_size.py
# Expected: Avg file < 180 LOC
```

---

## SUCCESS CRITERIA

### Quantitative
| Metric | Current | Target | Check |
|--------|---------|--------|-------|
| Tests with assertions | 5,198/5,582 (93%) | 5,582/5,582 (100%) | `grep -c "assert"` |
| Avg assertions per test | 1.2 | 2.8+ | Analysis |
| Vague assertions | 429 | <50 | Audit |
| Mock stacks >3 | 128 | <10 | Decorator count |
| Parameterized tests | 402 (7.2%) | 1,228 (22%) | File count |
| Large tests (>70 LOC) | 28 | <5 | `wc -l` |

### Qualitative
- [ ] All tests have clear, specific assertions
- [ ] No mock decorator stacks > 3
- [ ] Large integration tests split into focused unit tests
- [ ] Test names clearly describe what they test
- [ ] 100% of team agrees tests are production-quality
- [ ] All tests provide clear documentation of expected behavior

---

## RISK MITIGATION

### Risk 1: Tests Become Too Strict
**Symptom:** Tests fail after refactoring when behavior is actually correct
**Mitigation:**
- Run tests after each assertion addition
- Use `xfail` temporarily if unsure
- Get code review from domain expert

### Risk 2: Tests Take Too Long
**Symptom:** Test suite time increases 10x
**Mitigation:**
- Mark slow tests with `@pytest.mark.slow`
- Run parameterized tests in parallel
- Use selective mocking for performance-critical tests

### Risk 3: Assertion Duplication
**Symptom:** Many tests assert the same thing
**Mitigation:**
- Parameterize similar tests
- Extract assertion helpers

### Risk 4: Over-Engineering Tests
**Symptom:** Tests become too complex while trying to fix them
**Mitigation:**
- Keep changes focused and minimal
- Lean on existing patterns
- Use fixtures for complex setup

---

## TOOLS & UTILITIES

### Script 1: Find Tests Without Assertions
```python
# scripts/find_missing_assertions.py
import ast
from pathlib import Path

class AssertionChecker(ast.NodeVisitor):
    def __init__(self):
        self.tests_without = []

    def visit_FunctionDef(self, node):
        if node.name.startswith('test_'):
            if not any(isinstance(n, ast.Assert) for n in ast.walk(node)):
                self.tests_without.append((node.name, node.lineno))
        self.generic_visit(node)

for file in Path('tests').rglob('test_*.py'):
    with open(file) as f:
        tree = ast.parse(f.read())
        checker = AssertionChecker()
        checker.visit(tree)
        for name, line in checker.tests_without:
            print(f"{file}:{line} {name}")
```

### Script 2: Analyze Assertion Types
```python
# scripts/analyze_assertions.py
import re
from pathlib import Path

patterns = {
    'bare_bool': r'assert\s+\w+\s*$',
    'mock_called': r'assert.*\.called',
    'mock_count': r'assert.*\.call_count',
    'loose_range': r'assert.*\.call_count\s*[><=]',
}

for file in Path('tests').rglob('test_*.py'):
    with open(file) as f:
        content = f.read()
        for pattern_type, pattern in patterns.items():
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                print(f"{file}:{line_num} {pattern_type}: {match.group()[:60]}")
```

---

## DOCUMENTATION & COMMUNICATION

### Daily Standup
```
Status: "Fixing missing assertions - Phase 1 Day 2/5"
Progress: "Fixed 60/192 incomplete tests"
Blockers: "None"
Next: "Continue batch 2, pair review on uncertain cases"
```

### Weekly Summary
```markdown
## Week 1 Summary: Critical Issues
- Fixed 384 tests with missing assertions
- All tests now have meaningful assertions
- 5,582 tests passing
- No regressions detected
```

### Final Report
Template for post-remediation report:
- Before/after metrics
- Effort breakdown
- Lessons learned
- Recommendations for future test development

---

## NEXT STEPS AFTER REMEDIATION

Once Phase 3 complete, consider:

1. **Implement Assertion Helpers** (1 day)
   - Create reusable assertion patterns
   - Extract common mock verification logic

2. **Update Testing Standards** (2 days)
   - Document best practices
   - Create testing style guide
   - Add linting rules for assertions

3. **Establish Test Review Criteria** (1 day)
   - Code review checklist for tests
   - Minimum assertion count requirement
   - Mock usage guidelines

4. **Continuous Monitoring** (Ongoing)
   - Add CI checks for assertion quality
   - Monitor test-to-assertion ratio
   - Flag regressions in test quality

---

## CONCLUSION

This plan transforms a good test infrastructure into a production-quality test suite through **focused, incremental improvements**. The effort is **front-loaded** with quick wins (Phase 1), followed by systematic strengthening (Phase 2), and optimization (Phase 3).

**Bottom line:** 3-4 weeks of effort, 1-2 developers, achieves **world-class test suite** that serves as both safety net and documentation.
