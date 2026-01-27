# Phase 9: Temporary Directory Factories - Implementation Summary

**Status:** ✅ Factories Created & Ready for Refactoring
**Date:** January 27, 2026
**Impact:** 585 hardcoded `tmp_path` usages → Consolidate into 4 reusable factories

---

## What Was Done

### 1. Created Priority Analysis Scripts
- **`scripts/phase9_factory_priority.py`** — ROI-based factory ranking
  - Identifies which factories give highest impact
  - Shows test file distribution across patterns
  - Provides actionable rollout plan

- **`scripts/phase9_tempdir_refactoring.py`** — Pattern-specific analysis
  - Maps hardcoded patterns to factory types
  - Lists high-impact test files by usage count
  - Prioritizes refactoring order

### 2. Built 4 Reusable Factory Fixtures
**File:** `tests/fixtures/temp_dir_factories.py`

#### `temp_file_factory`
Consolidates 37 test files using file operations:
```python
temp_file_factory.create_toml("config.toml", version="1.0.0")
temp_file_factory.create_yaml("config.yaml", project="test")
temp_file_factory.create_file("README.md", "# Content")
```

#### `git_repo_factory`
Consolidates 3 test files initializing git repos:
```python
git_repo_factory.create_repo()  # Init repo with initial commit
git_repo_factory.create_with_branch("feature/test")  # Add feature branch
git_repo_factory.create_with_file("data.json", content)  # Add file
```

#### `roadmap_structure_factory`
Consolidates 62 test files creating `.roadmap/` structure:
```python
roadmap_structure_factory.create_minimal()  # Just directories
roadmap_structure_factory.create_with_config(version="1.0")  # Add config
roadmap_structure_factory.create_full_with_issues(5)  # Populate issues
```

#### `isolated_workspace`
Consolidates 28 test files managing directory isolation:
```python
with isolated_workspace as workspace:
    # cwd automatically changed to workspace root
    # Auto-restored on exit
    pass

isolated_workspace.change_to("subdir")  # Switch dirs
isolated_workspace.get_path("deep/path")  # Build paths
```

### 3. Created Documentation
**File:** `docs/PHASE_9_TEMPDIR_GUIDE.md`
- Before/after refactoring examples
- Prioritized file list (Tier 1 & 2)
- Quick reference for factory methods
- Refactoring checklist
- Testing validation steps

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Total `tmp_path` patterns | 585 occurrences |
| Test files affected | 80+ files |
| Pattern types | 8 distinct types |
| Factories created | 4 reusable fixtures |
| High-impact files | 15 files (Tier 1 & 2) |
| Expected refactoring time (Tier 1) | ~2 hours |
| Effort per file | 15-20 minutes |

---

## Prioritized Refactoring Targets

### Tier 1 (Highest ROI - ~60 minutes total)
1. **test_version_coverage.py** — 5 patterns (config files)
   - Use: `temp_file_factory.create_toml()` + `create_yaml()`

2. **test_version_errors.py** — 28 patterns (TOML creation)
   - Use: `temp_file_factory`

3. **test_project_initialization_service.py** — 5 patterns
   - Use: `roadmap_structure_factory` + `temp_file_factory`

4. **test_export_manager.py** — 5 patterns (file I/O)
   - Use: `temp_file_factory`

### Tier 2 (High ROI - ~75 minutes total)
5. **test_git_hooks_workflow_integration.py** — 5 patterns
   - Use: `git_repo_factory` + `isolated_workspace`

6. **test_health.py** — 4 patterns (isolation)
   - Use: `isolated_workspace`

7. **test_roadmap_core_comprehensive.py** — 4 patterns
   - Use: `roadmap_structure_factory`

8. **test_create_branch_edgecases.py** — 20 patterns (git repos)
   - Use: `git_repo_factory`

**Subtotal: 8 files, ~2 hours of focused refactoring = ~40-50 tests improved**

---

## Benefits After Refactoring

### Immediate (Per File)
✅ Reduced hardcoded setup by 80-90%
✅ More readable test code
✅ Easier to debug test failures
✅ Centralized file/directory logic

### Project-Wide
✅ Single source of truth for tmp setup
✅ Future test changes are localized
✅ New tests can use proven patterns
✅ Easier to change fixture behavior globally

### Quality Metrics
✅ Test code becomes DRY (Don't Repeat Yourself)
✅ Reduced maintenance risk when APIs change
✅ Improved test clarity and intent
✅ Foundation for Phase 10 (Mock reduction)

---

## How to Use This Work

### For Refactoring a Single File
1. Run analysis to see patterns:
   ```bash
   python scripts/phase9_tempdir_refactoring.py --refactor-list
   ```

2. Pick a file from Tier 1 or Tier 2

3. Read the before/after examples:
   ```bash
   cat docs/PHASE_9_TEMPDIR_GUIDE.md
   ```

4. Add factory to test function:
   ```python
   def test_something(self, tmp_path, temp_file_factory):
       # Use temp_file_factory methods
   ```

5. Run tests:
   ```bash
   poetry run pytest tests/path/to/file.py -v
   ```

### For Understanding All Patterns
```bash
python scripts/phase9_factory_priority.py --plan
```

### For Deep Dive on Specific Pattern
```bash
python scripts/phase9_factory_priority.py --pattern datetime_hardcoded
```

---

## Files Created/Modified

### New Files
- ✅ `tests/fixtures/temp_dir_factories.py` (360 lines, 4 fixtures)
- ✅ `scripts/phase9_factory_priority.py` (250 lines, priority analysis)
- ✅ `scripts/phase9_tempdir_refactoring.py` (300 lines, pattern analysis)
- ✅ `docs/PHASE_9_TEMPDIR_GUIDE.md` (refactoring guide)

### Modified Files
- ✅ `tests/fixtures/__init__.py` (added imports + exports)

### No Breaking Changes
- All fixtures are new (no existing code changed)
- Factories are opt-in (existing tests continue to work)
- Ready for gradual rollout

---

## Next Steps

### Option A: Refactor High-ROI Files First
1. Start with `test_version_coverage.py` (5 patterns)
2. Move to `test_version_errors.py` (28 patterns)
3. Continue with Tier 1 files
4. Validate with full test suite
5. Commit when stable

### Option B: Refactor by Pattern Type
1. Focus on `roadmap_structure_factory` (62 files)
2. Then `temp_file_factory` (37 files)
3. Then `state_files` pattern (118 files)
4. Finally `isolated_workspace` (28 files)

### Validation
After refactoring each file:
```bash
# Test single file
poetry run pytest tests/path/to/file.py -v

# Test all (should take <3 min)
poetry run pytest tests/ -x
```

---

## Success Criteria

- [ ] Tier 1 files (4 files) refactored and passing
- [ ] Tier 2 files (4 files) refactored and passing
- [ ] No regression in test coverage
- [ ] All tests pass in <3 minutes
- [ ] Code review confirms consistent factory usage
- [ ] Documentation updated with pattern usage stats

---

## Related Phases

- **Phase 8:** Coverage & pytest modernization (completed)
- **Phase 9:** Test data hygiene (current)
  - Sub-phase 9a: Temporary directories ← **You are here**
  - Sub-phase 9b: Hardcoded values (datetime, magic numbers)
  - Sub-phase 9c: Test data consolidation
- **Phase 10:** Mock reduction (next after Phase 9)

---

## Commands Quick Reference

```bash
# View priority ranking
python scripts/phase9_factory_priority.py --plan

# View pattern distribution
python scripts/phase9_tempdir_refactoring.py --refactor-list

# Get details on specific pattern
python scripts/phase9_factory_priority.py --pattern issue_creation

# Test after refactoring
poetry run pytest tests/unit/test_version_errors.py -v
```

---

## Questions?

Refer to:
- **Before/After Examples:** `docs/PHASE_9_TEMPDIR_GUIDE.md`
- **Factory API Docs:** `tests/fixtures/temp_dir_factories.py` (docstrings)
- **Pattern Analysis:** Run `python scripts/phase9_factory_priority.py`
