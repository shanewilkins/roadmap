# Phase 5: pytest-mock Migration Plan

## Overview
Migrate from `unittest.mock` to `pytest-mock` library for consistent pytest-native mocking across the test suite.

## Status
📋 **DEFERRED** - Planned for Phase 5+ (after Phase 4 mock consolidation completes)

## Rationale

**Current State:**
- Test suite uses `unittest.mock.Mock`, `unittest.mock.patch`, `MagicMock`
- Fixture factories added in Phase 4 reduced infrastructure mocks by ~100 calls
- Remaining ~400 Mock() calls are mostly legitimate domain object mocks
- All imports standardized to top-level (PEP 8 compliant) in Phase 4.3

**Framework Comparison:**

| Aspect | unittest.mock | pytest-mock |
|--------|---------------|-------------|
| **Import** | `from unittest.mock import Mock` | `def test(mocker):` fixture |
| **Syntax** | `Mock(attr=val)` | `mocker.Mock(attr=val)` |
| **Cleanup** | Manual or via teardown | Automatic after test |
| **Learning Curve** | Standard library (familiar) | pytest-specific (steeper) |
| **Boilerplate** | More explicit imports | Less boilerplate |
| **State Leakage Risk** | Higher (must remember teardown) | Lower (auto cleanup) |
| **Dependencies** | Built-in (0 deps) | Requires pytest-mock package |

**Why Phase 5+ (Decision Made):**
1. **Higher ROI after consolidation** - Phase 4 eliminates ~100 infrastructure mocks first
2. **Reduces refactoring churn** - Consolidate first, then migrate frameworks
3. **Allows team absorption** - Phase 4 changes are substantial; let team adjust
4. **Establishes baseline** - Cleaner mock patterns before framework shift
5. **unittest.mock is sufficient** - Current usage is well-structured with top-level imports

**Why NOT Phase 4:**
- Phase 4 is tactical consolidation (fixtures + pattern reduction)
- Phase 5 is strategic framework shift (requires mindset change)
- Mixing both creates too much churn
- Current top-level import pattern is PEP 8 compliant and maintainable

## Scope

### Convert These Patterns:

1. **Direct Mock Creation**
   ```python
   # Before
   from unittest.mock import Mock
   mock_obj = Mock(attr=value)

   # After
   def test_something(mocker):
       mock_obj = mocker.Mock(attr=value)
   ```

2. **patch() Context Managers**
   ```python
   # Before
   from unittest.mock import patch
   with patch("module.Class") as mock_class:
       ...

   # After
   def test_something(mocker):
       mocker.patch("module.Class")
   ```

3. **MagicMock Usage**
   ```python
   # Before
   from unittest.mock import MagicMock
   mock_db = MagicMock()

   # After
   def test_something(mocker):
       mock_db = mocker.MagicMock()
   ```

4. **Attribute Mocking**
   ```python
   # Before
   obj.attr = Mock(return_value=123)

   # After
   mocker.patch.object(obj, "attr", return_value=123)
   ```

## Implementation Plan

### Step 1: Dependency Verification (0.5 hours)
- [ ] Confirm `pytest-mock` is in `pyproject.toml` dev dependencies
- [ ] If not, add it: `poetry add --group dev pytest-mock`
- [ ] Verify version compatibility with current pytest version
- [ ] Update conftest.py to document mocker fixture usage

### Step 2: Create Migration Guide (1.5 hours)
- [ ] Document common patterns and their replacements
- [ ] Create `.md` file in docs/ for team reference
- [ ] Include before/after examples for each pattern
- [ ] Highlight pitfalls (MagicMock vs Mock, spec= parameter, side_effect)
- [ ] Document how to handle edge cases (fixtures + mocker interaction)

### Step 3: Gradual File-by-File Migration (6-8 hours)
**Priority Order (by Mock density and Phase 4 progress):**

1. **Already Refactored in Phase 4** - Use as first migration targets
   - tests/unit/adapters/vcs/test_git_branch_manager.py (27 mocks, + factories)
   - tests/unit/adapters/vcs/test_sync_monitor.py (24 mocks, + factories)
   - tests/unit/adapters/vcs/test_git_commit_analyzer.py (16 mocks, already using top-level imports)

2. **Phase 4.4 Targets** - Next priority
   - tests/unit/adapters/sync/test_sync_retrieval_orchestrator.py (23 mocks)
   - tests/unit/application/services/test_github_integration_service.py (10 mocks)
   - tests/unit/core/services/github/test_github_integration_service.py (24 mocks)

3. **Medium Priority (10-20 Mock calls)**
   - Sync orchestrator test files
   - Other adapter test files

4. **Low Priority (<10 Mock calls)**
   - Scattered test files
   - Presenter test files

### Step 4: Validation & Commit (2 hours)
- [ ] Run full test suite: `poetry run pytest`
- [ ] Verify all 6,567+ tests still passing
- [ ] Check linting: `poetry run pre-commit run --all-files`
- [ ] Commit with clear message: "Phase 5: Migrate to pytest-mock"

## Expected Benefits

✅ **Code Quality**
- Automatic mock cleanup (no state leakage)
- Cleaner, more Pythonic syntax
- Better IDE support and autocomplete

✅ **Maintenance**
- Single mocking framework
- Easier for new team members (pytest-native)
- Reduced boilerplate

✅ **Reliability**
- Fewer test isolation issues
- Better mock hygiene

## Estimated Effort
**Total: 9-11 hours**
- Dependency setup: 0.5 hours
- Documentation: 1.5 hours
- Migration: 6-8 hours
- Testing & commit: 2 hours

## Success Criteria
- [ ] All Mock imports removed from test files
- [ ] All tests using `mocker` fixture from conftest
- [ ] 100% of patch() calls converted to mocker.patch()
- [ ] All 6,567+ tests passing
- [ ] Zero regressions in test behavior
- [ ] Linting passes
- [ ] Fixture factories from Phase 4 continue working with mocker

## Notes

### Important Considerations
1. **MagicMock vs Mock** - Some tests specifically need MagicMock (for context managers, etc.)
   - These should become `mocker.MagicMock()`
   - Be careful not to over-simplify

2. **spec= Parameter** - Some Mock calls use spec for type safety
   - `Mock(spec=SomeClass)` → `mocker.Mock(spec=SomeClass)`
   - Maintain these for better test coverage

3. **side_effect Patterns** - These work identically
   - No change needed semantically
   - Just syntax shift

4. **Fixture Factories** - Phase 4 factories remain unchanged
   - They're orthogonal to this work
   - Can coexist with pytest-mock

### Risks & Mitigation
| Risk | Mitigation |
|------|-----------|
| Team unfamiliar with pytest-mock | Create comprehensive guide + examples, start with familiar files |
| Regressions in test behavior | Run full suite multiple times, careful review of cleanup behavior |
| Incomplete migration | Track in checklist, do file-by-file, verify each batch |
| Performance issues | Unlikely (pytest-mock is lightweight, auto-cleanup may improve) |
| Fixture factories compatibility | Verify factories work with mocker fixture (they should be orthogonal) |
| Mock cleanup interfering with fixtures | Test interaction between Phase 4 factories and pytest-mock auto-cleanup |

## Phased Rollout Strategy

**Phase 5a (Optional Pilot):**
- Migrate 1-2 of the refactored Phase 4 files to test approach
- Verify pytest-mock works smoothly with fixture factories
- Document any issues found

**Phase 5b (Main Migration):**
- Roll out file-by-file to remaining test suite
- Build team confidence through incremental adoption
- Ensure zero regressions at each step

**Phase 5c (Cleanup & Documentation):**
- Remove unittest.mock from all imports
- Update documentation and style guide
- Commit with comprehensive messaging

## Related Tasks
- **Phase 4**: Mock pattern consolidation (CURRENT - 3/5 sync files refactored, 67 mocks consolidated)
- **Phase 4.4**: Refactor remaining support files (59 mocks remaining)
- **Phase 4.5**: Full validation & commit (after Phase 4.4)
- **Phase 5**: pytest-mock migration (this plan, 9-11 hours)
- **Phase 6**: unittest.TestCase modernization (7 files, lower priority)

## References
- pytest-mock docs: https://pytest-mock.readthedocs.io/
- unittest.mock → pytest-mock migration patterns
- PEP 8 style guide for testing

---

**Created:** January 20, 2026
**Status:** Planning Phase
**Owner:** TBD
**Priority:** Medium (nice-to-have, not critical)
