# DRY Violations Remediation - Status & Tomorrow's Agenda

**Date:** January 16, 2026
**Branch:** `fix/tests-lints`
**Status:** Analysis complete, implementation ready

---

## What Was Completed Today

### ✅ Analysis Phase
- Installed JSCPD and attempted large-scale scanning (too memory-heavy)
- Built custom Python duplicate detection tool (token-based, lightweight)
- Identified **790 token-sequence duplicates** across 910 Python files
- **Actionable violations:** ~330 consolidatable patterns

### ✅ Key Findings
See [docs/JSCPD_ANALYSIS_REPORT.md](docs/JSCPD_ANALYSIS_REPORT.md) for full details.

**Top violations by impact:**
1. **Git repo setup** (120+ duplicates) - 12+ test files reinitialize git separately
2. **Issue/Milestone creation** (200+ duplicates) - Repeated object instantiation, factory pattern opportunity
3. **@patch decorator stacks** (3 duplicates) - Same mock combinations repeated
4. **RoadmapCore initialization** (4 duplicates) - Same test setup repeated

### 📊 Codebase Status
- **6,558 tests passing** ✓
- **76% code coverage** ✓
- **All fixtures in place** (Phase 2/3 work complete)
- **Test directory reorganization done** (101 files in hierarchical structure)

---

## Tomorrow's Work: Phase 4 - Consolidation Implementation

### Priority 1: Git Fixture (HIGH impact, low complexity)
**Location:** `tests/conftest.py`
**What:** Extract repeated git setup to reusable fixture
**Affected files:** 12+ in `tests/integration/git/` and `tests/integration/git_hooks/`

```python
@pytest.fixture
def git_repo(tmp_path):
    """Initialize a bare git repository with test user config."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    yield tmp_path
```

**Estimated time:** 1 hour (write fixture + update 12 test files)

### Priority 2: Issue/Milestone Factories (HIGH impact, medium complexity)
**Location:** `tests/common/factories.py` (new file)
**What:** Create builder pattern for Issue and Milestone objects
**Affected files:** 50+ tests using `Issue()` or `Milestone()` directly

```python
class IssueFactory:
    @staticmethod
    def create(title="Test Issue", status=None, priority=None, **kwargs) -> Issue:
        defaults = {
            "title": title,
            "status": status or Status.OPEN,
            "priority": priority or Priority.MEDIUM,
            "estimated_hours": 1.0,
        }
        defaults.update(kwargs)
        return Issue(**defaults)

class MilestoneFactory:
    @staticmethod
    def create(name="v1.0", **kwargs) -> Milestone:
        defaults = {"name": name, "status": Status.OPEN}
        defaults.update(kwargs)
        return Milestone(**defaults)
```

**Estimated time:** 1.5 hours (write factories + update 50+ test files)

### Priority 3: @patch Decorator Consolidation (MEDIUM impact, low complexity)
**Location:** `tests/conftest.py`
**What:** Create helper fixtures for repeated @patch stacks
**Affected files:** `tests/unit/core/services/backup/` (3+ files)

**Estimated time:** 30 minutes

### Priority 4: RoadmapCore Init Fixture (LOW impact, low complexity)
**Location:** `tests/conftest.py` or `tests/common/fixtures.py`
**Affected files:** 4 test files in `tests/unit/application/`
**Estimated time:** 15 minutes

---

## How to Resume

1. **Start with Priority 1 (Git Fixture)**
   - Open `tests/conftest.py`
   - Add git_repo fixture
   - Update git-related tests to use `git_repo(tmp_path)` instead of manual setup

2. **Then Priority 2 (Factories)**
   - Create `tests/common/factories.py`
   - Add IssueFactory and MilestoneFactory
   - Update test files: search-replace `Issue(` → `IssueFactory.create(`

3. **Run full test suite after each priority**
   - `poetry run pytest tests/ -q --tb=short`
   - Should maintain 6,558 passing tests

4. **Commit after each priority**
   - `git add -A && git commit -m "Phase 4.1: Extract git_repo fixture"`
   - etc.

---

## Reference Materials

- [Full JSCPD Analysis Report](docs/JSCPD_ANALYSIS_REPORT.md)
- [Phase 3 Complete Documentation](docs/PHASE_3_COMPLETE.md)
- Custom analysis scripts (can be deleted):
  - `find_duplicates.py`
  - `analyze_duplicates.py`
  - `.jscpdrc.json`

---

## Expected Outcome

**Before:** 790 token duplicates → ~330 actionable patterns
**After Phase 4:** ~200-250 duplicate patterns remaining (40-50% reduction)
**Code savings:** ~300+ lines eliminated
**Maintainability:** Tests become easier to update (centralized patterns)

---

## Notes

- All work stays on `fix/tests-lints` branch
- No test failures expected - all changes are refactoring
- Use `pytest -k` to test fixture updates in isolation if needed
- Consider running with xdist for speed: `poetry run pytest tests/ -n auto`
