# Phase 6d: Test Layer Refactoring

## Objective
Mirror the test structure to the application code structure and fix architectural inconsistencies in the test directory.

## Current Issues Identified

### 1. Duplicate Test Layer Directories
**Problem**: Tests have inconsistent naming conventions for layer mirroring:
- Both `tests/unit/core/` and `tests/unit/tests_core/` exist
- Both `tests/unit/common/` and `tests/unit/test_common/` exist (or similar patterns)
- `tests/unit/cli/` vs other naming variants

**Impact**: Confusing for developers, unclear which directory tests for which layer, test discovery issues

**Solution**:
- Consolidate to single, consistent naming: `tests/unit/{layer_name}/`
- Map to application layers: adapters, core, common, infrastructure, domain, presentation
- Example: `tests/unit/core/` for core layer tests, `tests/unit/common/` for common layer tests

### 2. Test Layer Dependency Violations
**Problem**: Tests may have their own layer violation issues (unit tests importing from integration, tests importing from non-shared layers, etc.)

**Impact**: Tests aren't isolated, test dependencies bleed across layers, brittle tests

**Solution**:
- Scan tests/ directory using similar layer violation checker
- Ensure tests/ follows same layer rules as roadmap/
- Unit tests should only import domain and interfaces, not implementations
- Integration tests can import broader but should still respect boundaries

### 3. Infrastructure Test Subdirectories
**Problem**: With infrastructure/ now organized into subdirectories (coordination/, git/, observability/, validation/, security/, maintenance/), tests must also be organized accordingly

**Impact**: Tests for moved modules need updated directory structure

**Solution**:
- Create tests/unit/infrastructure/{coordination,git,observability,validation,security,maintenance}/
- Update test_infrastructure/ to mirror the new structure

## Timeline

- **Phase 6d.1**: Consolidate duplicate test layer directories (30-45 min)
  - Identify all duplicate directories (tests_core vs core, test_common vs common, etc.)
  - Choose canonical naming convention
  - Move and update imports

- **Phase 6d.2**: Refactor infrastructure tests to match new subdirectories (20-30 min)
  - Create subdirectories under tests/unit/infrastructure/
  - Move test files to appropriate subdirectories
  - Update imports in test files

- **Phase 6d.3**: Scan test layer violations (15-20 min)
  - Create/adapt layer violation scanner for tests/
  - Run analysis and document findings
  - Identify which test imports are problematic

- **Phase 6d.4**: Fix critical test layer violations (1-2 hours)
  - Focus on high-impact violations (broken test isolation)
  - Use mocking/patching where needed to avoid layer violations
  - Ensure unit tests stay isolated from implementation details

## Success Criteria

✅ No duplicate test directories with different naming
✅ Test directory structure mirrors application code structure
✅ All tests organized by layer (unit/adapters, unit/core, unit/common, etc.)
✅ Layer violation scanner shows <10 violations in tests/ (acceptable for test utilities)
✅ Unit tests properly mocked/isolated from implementation details
✅ All tests still pass after refactoring

## Priority
**LOW** - After completing Phase 6c (layer violations <50), but before 6e

## Estimated Effort
3-4 hours total across all subtasks

## Notes
- This is a structural refactoring, not a functional one - tests should still pass
- May reveal hidden test coupling issues
- Good opportunity to improve test maintainability and clarity
- Can be parallelized with Phase 6c work if needed
