# Phase 6d.3: Test Layer Violations Analysis

## Summary
Found **52 test layer violations** across the test suite.

### Breakdown by Test Layer
- ✅ **Integration Tests**: 0 violations (as expected - can import across layers)
- ✅ **Adapters Tests**: 0 violations (good isolation)
- ⚠️ **Common Tests**: 11 violations (test dependencies on core.domain)
- ⚠️ **Core Tests**: 2 violations (imports from adapters)
- ⚠️ **Domain Tests**: 14 violations (imports from adapters, infrastructure, cli)
- ⚠️ **Infrastructure Tests**: 19 violations (imports from adapters)
- ⚠️ **Presentation Tests**: 6 violations (imports from infrastructure)

## Analysis

### Critical Violations (High Priority)
**Domain Tests (14 violations)** - Most problematic
- Domain layer should NOT import from adapters, infrastructure, or CLI
- These are circular/cross-layer dependencies
- Need to refactor tests to avoid these imports

**Infrastructure Tests (19 violations)** - Significant
- Infrastructure tests importing from adapters
- Should use mocking/interfaces instead of concrete implementations
- Some may be acceptable if testing infrastructure/adapter integration

### Minor Violations (Lower Priority)
**Common Tests (11 violations)** - Acceptable
- Common layer tests importing from core.domain (type definitions)
- Using `from core.domain` for test data models is reasonable
- Could be avoided with separate test fixtures

**Core Tests (2 violations)** - Few enough to fix quickly
- Test files importing from adapters for testing purposes
- Should use interfaces or mocking instead

**Presentation Tests (6 violations)** - Moderate
- Presentation tests importing from infrastructure
- May be acceptable for integration testing presentation layer

## Recommended Actions

### Phase 6d.4.1 (Quick Wins)
1. **Core Tests** (2 violations) - Use mocking instead of direct adapter imports
2. **Presentation Tests** (6 violations) - Use infrastructure interfaces where possible

### Phase 6d.4.2 (Medium Effort)
3. **Infrastructure Tests** (19 violations) - Refactor to use mocking/patching
4. **Common Tests** (11 violations) - Extract test fixtures to avoid core.domain imports

### Phase 6d.4.3 (Major Refactoring)
5. **Domain Tests** (14 violations) - Significant refactoring needed
   - These should NOT import from adapters/cli/infrastructure
   - Suggests domain tests are too tightly coupled to implementations
   - Consider extracting domain test utilities

## Key Insights

### Why These Violations Exist
1. **Test convenience**: Using real objects instead of mocks
2. **Shared test utilities**: Common test fixtures living in wrong layer
3. **Integration testing as unit tests**: Tests mixing layers inappropriately
4. **Domain tests overly complex**: Testing too many concerns

### Pattern: Infrastructure Layer Testing
- Infrastructure tests frequently import from adapters
- This may be acceptable since infrastructure coordinates between layers
- Need to determine if this is true infrastructure/adapter integration testing

### Pattern: Domain Tests
- Domain tests have most violations relative to size
- Suggests domain is being tested with implementation details
- Should focus on domain model behavior, not implementations

## Acceptance Criteria for Phase 6d.4
- Reduce violations from 52 → <20
- Focus on critical violations (domain, infrastructure)
- Ensure test isolation without breaking functionality
- Document why remaining violations are acceptable

## Files to Modify
- Domain tests: 14 files
- Infrastructure tests: 4-5 files  
- Presentation tests: 6 files
- Common tests: Multiple files
- Core tests: 2 files

---

**Date**: January 15, 2026
**Status**: Analysis Complete - Ready for Phase 6d.4
