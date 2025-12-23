# Test Refactoring Progress & Next Steps

**Last Updated**: December 23, 2025  
**Overall Strategy**: Option B (Staged Comprehensive Refactoring)  
**Current Phase**: Phase 1B (Starting)

---

## ✅ Completed: Phase 1A

**Work Done**:
- [x] Refactored test_cli_commands_extended.py
- [x] Consolidated 31 test methods → 10 parametrized tests
- [x] Removed unnecessary `isolated_filesystem()` nesting
- [x] Reduced 277 lines → 154 lines (44% reduction)
- [x] All 31 tests passing in ~0.7s (12% faster)

**Commit**: 96b6ee2 - "Phase 1A: Refactor test_cli_commands_extended.py"

**Pattern Established**:
1. ✅ Parametrization for input variations
2. ✅ Remove unnecessary filesystem operations
3. ✅ Function-based tests vs class-based
4. ✅ Clear documentation with before/after metrics

---

## 🚀 Next: Phase 1B (This Week)

**Focus**: Fixture Optimization  
**Files**: test_estimated_time.py, test_assignee_validation.py, test_git_integration.py

**What to Do**:
1. Create combo fixtures in conftest.py:
   - `cli_runner_mocked` (runner + mock)
   - `initialized_core` (core without nested contexts)
   - `cli_runner_initialized` (runner + initialized core)

2. Refactor each file:
   - Remove `with cli_runner.isolated_filesystem():` from mock tests
   - Use `initialized_core` fixture
   - Consolidate repeated setup code

3. Measure:
   - Before/after execution time
   - Fixture instantiation count
   - I/O operations

**Expected Results**:
- 15-20% speedup
- 30% fewer fixture instantiations
- Cleaner, more readable tests

**Estimated Effort**: 2-3 days

**Files to Review**:
- [tests/unit/presentation/conftest.py](../tests/unit/presentation/conftest.py) - Update fixtures
- [tests/unit/presentation/test_estimated_time.py](../tests/unit/presentation/test_estimated_time.py) - Example refactoring
- [docs/PHASE_1B_THROUGH_4_ROADMAP.md](PHASE_1B_THROUGH_4_ROADMAP.md) - Detailed instructions

---

## 📋 Full Roadmap at a Glance

| Phase | Focus | Files | Effort | Status |
|-------|-------|-------|--------|--------|
| 1A | Output parsing + DRY | test_cli_commands_extended | ✅ Done | Complete |
| 1B | Fixtures + Context | 3 Tier 1 files | 2-3 days | 🚀 NEXT |
| 1C | Mock Realism | All mocks | 1-2 days | Planned |
| 2 | Tier 1 Polish | Validate all Tier 1 | 1 day | Planned |
| 3 | Tier 2-3 Rollout | 8+ files | 8-12 days | Planned |
| 4 | Polish + Docs | All files | 3-5 days | Planned |

**Total**: 4-6 weeks | 40% faster | 50% less code | 99%+ xdist compatible

---

## 📚 Key Documents

1. **[COMPREHENSIVE_REFACTORING_PLAN.md](COMPREHENSIVE_REFACTORING_PLAN.md)**
   - Original scope & strategy
   - Output parsing issues identified
   - DRY violations catalog

2. **[EXPANDED_REFACTORING_STRATEGY.md](EXPANDED_REFACTORING_STRATEGY.md)**
   - DRY violations in detail
   - Fixture efficiency problems
   - Performance anti-patterns
   - Comprehensive checklist

3. **[PHASE_1B_THROUGH_4_ROADMAP.md](PHASE_1B_THROUGH_4_ROADMAP.md)** ⭐ START HERE
   - Weekly breakdown
   - Detailed implementation steps
   - Code examples
   - Success metrics

---

## 🎯 Phase 1B: Quick Start

### Step 1: Update conftest.py (30 min)
```python
# Add to tests/unit/presentation/conftest.py

@pytest.fixture
def cli_runner_mocked():
    """CLI runner + mock core (no filesystem)."""
    return CliRunner(), MagicMock()

@pytest.fixture  
def initialized_core(tmp_path):
    """RoadmapCore with proper temp dir."""
    core = RoadmapCore(data_dir=str(tmp_path / ".roadmap"))
    core.initialize()
    return core

@pytest.fixture
def cli_runner_initialized(tmp_path):
    """Runner + initialized core combo."""
    runner = CliRunner()
    core = RoadmapCore(data_dir=str(tmp_path / ".roadmap"))
    core.initialize()
    return runner, core
```

### Step 2: Refactor test_estimated_time.py (1-2 hours)
**Before**:
```python
def test_create_issue(cli_runner):
    with cli_runner.isolated_filesystem():
        core = RoadmapCore()
        core.initialize()
        # ... test ...
```

**After**:
```python
def test_create_issue(cli_runner, initialized_core):
    # Use initialized_core directly, no nesting
    result = cli_runner.invoke(...)
    # ... test ...
```

### Step 3: Apply Same Pattern to Other Files (2-3 hours)
- test_assignee_validation.py (same pattern)
- test_git_integration.py (separate mock vs DB tests)

### Step 4: Measure & Validate (30 min)
```bash
poetry run pytest tests/unit/presentation/test_estimated_time.py -v
poetry run pytest tests/unit/presentation/test_assignee_validation.py -v
poetry run pytest tests/integration/test_git_integration.py -v
```

---

## 📊 Phase 1A Results Summary

**Metrics**:
```
Before Phase 1A:
├── Test methods: 31
├── Lines of code: 277
├── DRY violations: 20+
├── Unnecessary I/O: Multiple nested contexts
└── Execution: ~0.8-1.0s

After Phase 1A:
├── Test methods: 10 parametrized + 1 standalone
├── Lines of code: 154
├── DRY violations: <5
├── Unnecessary I/O: Eliminated
└── Execution: ~0.7s (12% faster)

Reduction:
├── Code: 44% ✅
├── Test methods: 68% ✅
├── Speed: 12% ✅
└── Test coverage: SAME ✅
```

**What Changed**:
- 4 test method groups → 1 parametrized test each
- Removed 10+ `with cli_runner.isolated_filesystem():` blocks
- Consolidated repeated assertions
- Added clear documentation

---

## 🔍 Code Review Checklist for Phase 1B

When refactoring in Phase 1B, ensure:

- [ ] No `with cli_runner.isolated_filesystem():` in mock tests
- [ ] Fixtures used for all setup code
- [ ] No repeated `RoadmapCore()` instantiation in test bodies
- [ ] Fixture docstrings explain what they provide
- [ ] Test docstrings explain what they test
- [ ] All tests passing (`pytest -v -n0`)
- [ ] All tests passing with xdist (`pytest -v`)
- [ ] Before/after metrics documented

---

## 💡 Tips for Phase 1B

### Tip 1: Fixture Scope Matters
```python
# Function scope: New instance per test (slower but isolated)
@pytest.fixture
def isolated_core(tmp_path):  # tmp_path is function-scoped
    return RoadmapCore(data_dir=str(tmp_path / ".roadmap"))

# Module scope: Single instance for all tests (faster but less isolated)
@pytest.fixture(scope="module")
def shared_core(tmp_path_factory):
    tmpdir = tmp_path_factory.mktemp("data")
    return RoadmapCore(data_dir=str(tmpdir / ".roadmap"))
```

**Decision**: Start with function scope (isolation first, optimize later)

### Tip 2: Use Fixture Parameters
```python
# Instead of creating multiple similar fixtures:
@pytest.fixture
def mock_core_with_issues():
    ...

@pytest.fixture
def mock_core_with_comments():
    ...

# Use fixture parameters:
@pytest.fixture
def mock_core(request):
    if request.param == "issues":
        return create_mock_issues()
    else:
        return create_mock_comments()
```

### Tip 3: Combo Fixtures Save Repetition
```python
# Bad: Repeated in every test
def test_something(cli_runner, mock_core):
    runner, core = cli_runner, mock_core
    # ...

# Good: Single combo fixture
@pytest.fixture
def cli_mocked(cli_runner, mock_core):
    return cli_runner, mock_core

def test_something(cli_mocked):
    runner, core = cli_mocked
    # ...
```

---

## 🚦 Status Indicators

**Phase 1A**: 🟢 Complete
- All work done
- All tests passing
- Ready for next phase

**Phase 1B**: 🟡 Starting
- Planning complete
- Ready to implement
- Start with fixtures in conftest.py

**Phase 1C-4**: ⚪ Scheduled
- Fully planned
- Instructions documented
- Will start after Phase 1B

---

## 🆘 If You Get Stuck

### Problem: "Test fails with 'RoadmapCore not found in isolated_filesystem'"
**Solution**: 
- Ensure RoadmapCore is created INSIDE the isolated context
- Use fixture that handles context creation for you
- See Pattern Example 2 in Phase 1B roadmap

### Problem: "All tests pass individually but fail together"
**Solution**:
- Tests may be sharing state (filesystem pollution)
- Use isolated fixtures with tmp_path
- Ensure proper cleanup in fixture teardown

### Problem: "Fixture instantiation too slow"
**Solution**:
- Check if fixture scope can be increased (but maintain isolation)
- Consider lazy initialization in fixture
- Use pytest-benchmark to measure specific operations

### Problem: "xdist still not working"
**Solution**:
- Check for output parsing that slipped through
- Verify fixtures are properly isolated (not global state)
- Use `pytest --lf` to run only failed tests

---

## ✨ Next Check-In

**When**: After Phase 1B complete (end of this week)  
**What to Validate**:
- [ ] All Tier 1 files using new fixtures
- [ ] No unnecessary nested contexts
- [ ] All tests passing with xdist
- [ ] 15-20% speedup achieved
- [ ] Metrics documented

**Then**: Move to Phase 1C (mock improvement)

---

## 📞 Questions?

Refer to:
- **Pattern examples**: [PHASE_1B_THROUGH_4_ROADMAP.md](PHASE_1B_THROUGH_4_ROADMAP.md) - Section "Phase 1B: Pattern Examples"
- **Fixture hierarchy**: [PHASE_1B_THROUGH_4_ROADMAP.md](PHASE_1B_THROUGH_4_ROADMAP.md) - Section "Cross-Cutting Concerns"
- **Implementation steps**: [PHASE_1B_THROUGH_4_ROADMAP.md](PHASE_1B_THROUGH_4_ROADMAP.md) - Section "Phase 1B: Implementation Steps"
- **Test helpers**: [tests/unit/shared/test_helpers.py](../tests/unit/shared/test_helpers.py)

