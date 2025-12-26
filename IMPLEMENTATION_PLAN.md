# Test Suite Refactoring Implementation Plan

**Total Estimated Effort**: 75-113 hours over 4-6 weeks
**Risk Level**: Medium (but manageable with proper approach)
**Timeline**: Parallel execution possible in Phases 2 & 3

---

## Phase 1: Foundation Fixes (Weeks 1-2)
**Duration**: 15-22 hours
**Risk**: Low
**Must Complete Before**: Phase 2 and Phase 3

### 1.1 Centralize `mock_core` Fixture
- **Effort**: 4-6 hours
- **Files Touched**: 35 test files
- **Steps**:
  1. Create `tests/fixtures/mocks.py` with centralized `mock_core`
  2. Search all test files for `def mock_core` definitions
  3. Remove local definitions, import from `tests/fixtures/mocks.py`
  4. Run full test suite to verify no breakage
  5. Verify all tests still pass
- **Success Criteria**:
  - ✅ Single source of truth for `mock_core`
  - ✅ All 35 files import from central location
  - ✅ Tests pass with no changes to logic

### 1.2 Consolidate 18 Duplicate Fixtures
- **Effort**: 8-12 hours
- **Files Touched**: 100+ test files
- **Steps**:
  1. Create `tests/fixtures/conftest.py` as central registry
  2. Audit current fixtures in `tests/unit/presentation/conftest.py` (261 lines)
  3. Move global-useful fixtures to `tests/fixtures/conftest.py`
  4. Update 100+ imports to use consolidated locations
  5. Delete old local definitions
  6. Run full test suite
- **Success Criteria**:
  - ✅ Fixtures defined once, used everywhere
  - ✅ Clear import pattern: `from tests.fixtures import <fixture>`
  - ✅ No duplicate definitions
  - ✅ All tests pass

### 1.3 Create Conftest Hierarchy
- **Effort**: 3-4 hours
- **Files Created**: 2 new files
- **Steps**:
  1. Create `tests/unit/conftest.py` for unit-specific fixtures
  2. Create `tests/unit/adapters/cli/conftest.py` for Click helpers only
  3. Update `tests/conftest.py` to be global entry point
  4. Document hierarchy: global → unit → domain-specific
  5. Update 10-15 test file imports
- **Success Criteria**:
  - ✅ Conftest hierarchy matches folder structure
  - ✅ Clear ownership: global/unit/integration/domain-specific
  - ✅ Tests still pass

**Phase 1 Validation**:
- Run `poetry run pytest` - all tests pass
- Run test coverage - should maintain current 83%+
- Check imports work: `grep -r "from tests.fixtures import"`

---

## Phase 2: Safety Check & CRUD Audit (Weeks 2-3)
**Duration**: 17-24 hours
**Risk**: Low-Medium (audit work, fixes are low-risk)
**Can Run Parallel To**: Phase 3

### 2.1 Audit CRUD Operations (CREATE, UPDATE, DELETE)
- **Effort**: 8-12 hours
- **Files Examined**: 91 test files (42 CREATE + 30 UPDATE + 19 DELETE)
- **Steps**:
  1. Run same audit we did for archive/restore
  2. Check each CRUD operation for:
     - Cache invalidation (same bug as archive/restore?)
     - State transition validation
     - Parent/child relationship updates
     - Proper error handling
  3. Create test files for any missing operations (DELETE likely needs dedicated file)
  4. Fix any bugs found
  5. Document findings
- **Success Criteria**:
  - ✅ CREATE operations validated (no cache issues)
  - ✅ UPDATE operations validated (state transitions correct)
  - ✅ DELETE operations validated (cleanup proper)
  - ✅ Any bugs found are fixed
  - ✅ Tests pass with fixes
  - ✅ Report: `docs/CRUD_AUDIT_RESULTS.md`

### 2.2 Audit Rich/Click Safety (5 Vulnerable Files)
- **Effort**: 6-8 hours
- **Files Examined**: 17 CLI test files
- **Steps**:
  1. Check each `@patch()` decorator in CLI tests
  2. Verify patch location matches where function is used
  3. Verify `get_console()` patches are at import location (not definition)
  4. Fix any incorrect patch locations
  5. Document correct pattern
  6. Validate your new tests (kanban, recalculate) as template
- **Success Criteria**:
  - ✅ All 17 CLI test files use correct patch locations
  - ✅ Rich console mocking works correctly
  - ✅ No future Click/Rich compatibility issues
  - ✅ Tests pass

### 2.3 Create Testing Guidelines Document
- **Effort**: 3-4 hours
- **Output**: `docs/TESTING_GUIDELINES.md` (1000+ words)
- **Steps**:
  1. Document Click command testing pattern (with correct Rich patches)
  2. Document when to use factories vs. fixtures
  3. Document how to organize new test files
  4. Include code examples from working tests (kanban, recalculate)
  5. Add pytest best practices specific to roadmap
  6. Add reference for common mistakes
- **Success Criteria**:
  - ✅ Contributors can answer "how should I test X?" from document
  - ✅ Code examples are copy-paste ready
  - ✅ Clear guidance on Rich/Click safety
  - ✅ Linked from README

**Phase 2 Validation**:
- Run `poetry run pytest` - all tests pass (possibly with new tests added)
- Review `docs/CRUD_AUDIT_RESULTS.md` for any surprising bugs
- Verify TESTING_GUIDELINES matches actual test patterns

---

## Phase 3: Quality & Maintainability (Weeks 3-6)
**Duration**: 43-67 hours
**Risk**: Medium (breaking large files requires understanding structure)
**Can Run Parallel To**: Phase 2

### 3.1 Create Domain Factories
- **Effort**: 8-12 hours (creation) + 20-30 hours (migration)
- **Files Created**: `tests/factories/` directory with builders
- **Files Updated**: 150-200 test methods across 40+ files
- **Steps**:
  1. Create `tests/factories/__init__.py`
  2. Create `tests/factories/domain.py` with:
     - `IssueBuilder` class with fluent interface
     - `MilestoneBuilder` class with fluent interface
     - `ProjectBuilder` class with fluent interface
     - Other domain object builders as needed
  3. Identify high-duplication test data creation patterns
  4. Migrate 150-200 test methods to use builders
  5. Update factories if model changes (single location)
  6. Run tests frequently (after every 10-15 migrations)
- **Success Criteria**:
  - ✅ Factories work and pass tests
  - ✅ Test files that previously hardcoded objects now use builders
  - ✅ Tests more readable and less verbose
  - ✅ All tests pass
  - ✅ Changing test data is single-location change

### 3.2 Break Up Large Test Files (31 files > 20KB)
- **Effort**: 20-30 hours
- **Target Files**: Start with 15 files > 500 lines
- **Strategy**:
  1. Process files in priority order (largest first):
     - `test_security.py` (1,142 lines) → 4-5 smaller files
     - `test_git_hooks_integration.py` (1,007 lines) → 3-4 smaller files
     - etc.
  2. For each file:
     - Identify logical test classes/domains
     - Split into 200-300 line files
     - Ensure each file has clear purpose
     - Run tests after each split
  3. Update imports if files reference each other
- **Success Criteria**:
  - ✅ No test file > 500 lines
  - ✅ Preferably no file > 400 lines
  - ✅ Each file has clear, focused purpose
  - ✅ All tests still pass
  - ✅ Test execution time ~same or faster

### 3.3 Add Parameterization (4,686 Tests)
- **Effort**: 15-25 hours (scattered, done alongside other work)
- **Target**: 4-5% → 20%+ parameterization rate
- **Strategy**:
  1. Identify patterns (e.g., same test with different inputs)
  2. Find tests with 4+ similar methods
  3. Convert to `@pytest.mark.parametrize`
  4. Update descriptions to be test-name-agnostic
  5. Works great with factories (less duplication)
- **Opportunities**:
  - Status tests (open/closed/blocked patterns)
  - Validation tests (valid/invalid inputs)
  - Error handling tests (different error types)
  - Edge cases (empty/null/boundary conditions)
- **Success Criteria**:
  - ✅ Parameterization rate increases to 15-25%
  - ✅ No loss of test coverage
  - ✅ Test file sizes decrease
  - ✅ Easier to add new test cases
  - ✅ All tests still pass

**Phase 3 Validation**:
- Run `poetry run pytest` frequently (after each major step)
- Check coverage hasn't decreased: `poetry run pytest --cov`
- Verify test execution time: `poetry run pytest --durations=0`
- Spot-check broken files are properly split

---

## Implementation Sequence

### Week 1 (Phase 1a)
- **Days 1-2**: Centralize `mock_core` (4-6h)
- **Days 3-4**: Start consolidating duplicates (4-6h)

### Week 2 (Phase 1b + Start Phase 2)
- **Days 1-2**: Finish consolidating duplicates (4-6h)
- **Days 3-4**: Create conftest hierarchy (3-4h)
- **Days 5**: Start CRUD audit OR Rich/Click audit (parallel)

### Week 3 (Phase 2 + Start Phase 3)
- **Days 1-3**: Finish audit work (8-10h)
- **Days 4-5**: Create testing guidelines (3-4h)
- **Parallel**: Start domain factories (Days 3-5)

### Weeks 4-6 (Phase 3)
- **Week 4**: Domain factories migration (20-30h)
- **Weeks 5-6**: Break large files (20-30h) + Parameterization (15-25h)
- *Can work in parallel*

---

## Risk Mitigation

### Risk 1: Breaking tests during refactoring
**Mitigation**:
- Run full test suite after each phase
- Commit changes frequently (git commits after each sub-task)
- Have a rollback plan: `git revert`
- Test on current branch before merging

### Risk 2: Fixture changes breaking tests
**Mitigation**:
- Keep old fixtures for 1-2 days (don't delete immediately)
- Test each import change: search for the fixture name, update in batches
- Run tests after each batch of imports

### Risk 3: Large file breakup missing tests
**Mitigation**:
- Before splitting, verify line count matches grep count: `wc -l` vs `grep "def test_" | wc -l`
- After splitting, count tests in new files should equal original
- Check test ids: `pytest --collect-only` before and after

### Risk 4: Factories having bugs
**Mitigation**:
- Write factory tests: `tests/factories/test_factories.py`
- Test each builder creates valid objects
- Test each builder method works in isolation
- Run tests before migrating test files

---

## Success Metrics

### Phase 1 Complete ✅
- [ ] No duplicate `mock_core` fixtures
- [ ] All 18 duplicate fixtures consolidated
- [ ] Conftest hierarchy in place
- [ ] All tests pass
- [ ] Coverage maintained at 83%+

### Phase 2 Complete ✅
- [ ] CRUD operations audited and validated
- [ ] All 17 CLI test files use correct Rich/Click patterns
- [ ] `docs/TESTING_GUIDELINES.md` created and linked
- [ ] All tests pass
- [ ] All bugs found are fixed

### Phase 3 Complete ✅
- [ ] Domain factories created and tested
- [ ] 150-200 test methods migrated to factories
- [ ] No test file > 500 lines (ideally < 400)
- [ ] Parameterization rate 15-25%+
- [ ] All tests pass
- [ ] Test execution time maintained or faster

---

## Total Work Summary

| Phase | Focus | Hours | Weeks | Risk |
|-------|-------|-------|-------|------|
| 1 | Foundation (fixtures, conftest) | 15-22h | 1-2 | Low |
| 2 | Safety (CRUD, Rich/Click, docs) | 17-24h | 1-2 | Low-Medium |
| 3 | Quality (factories, files, params) | 43-67h | 2-4 | Medium |
| **Total** | **Complete rewrite of test foundation** | **75-113h** | **4-6 weeks** | **Medium** |

---

## Next Steps

1. **Today**: Review this plan, ask clarifying questions
2. **Tomorrow**: Start Phase 1.1 (centralize `mock_core`)
3. **Week 1-2**: Complete Phase 1 (foundation)
4. **Week 2-3**: Complete Phase 2 (safety)
5. **Week 3-6**: Complete Phase 3 (quality)

---

## Questions Before Starting?

- Effort estimates reasonable?
- Timeline fits your schedule?
- Risk mitigation strategies adequate?
- Want to adjust scope (defer Phase 3 Nice-to-Have items)?
- Ready to start Phase 1?
