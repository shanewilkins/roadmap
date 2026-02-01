# Test Suite Naming Guide

This document explains the naming conventions used in our comprehensive test suite.

## File Naming Principles

All test files use **descriptive names** that clearly indicate what they test, without internal "Phase" or batch terminology that would be confusing to contributors.

### Test Files

#### Domain Layer Tests

**test_issue_domain_comprehensive.py**
- Tests the Issue domain model comprehensively
- Covers: creation, relationships, status transitions, serialization
- 66 tests - all enum combinations and edge cases
- Location: `tests/unit/domain/`

**test_milestone_comment_models.py**
- Tests Milestone and Comment domain models
- Covers: model lifecycle, threading, integration scenarios
- 47 tests - status transitions, progress tracking, comments
- Location: `tests/unit/domain/`

#### Persistence Layer Tests

**test_issue_repository_persistence.py**
- Tests YAML-based Issue repository operations
- Covers: CRUD operations, filtering, serialization, error handling
- 36 tests - real file I/O with temporary directories
- Location: `tests/unit/adapters/persistence/`

#### Service Layer Tests

**test_issue_service_operations.py**
- Tests IssueService business logic and operations
- Covers: creation, updates, deletion, filtering, caching
- 32 tests - realistic workflows and edge cases
- Location: `tests/unit/services/`

### Documentation Files

**COMPREHENSIVE_TESTING_STRATEGY.md**
- Strategic analysis of testing approach
- Originally: PHASE_7_ANALYSIS.md

**TESTING_IMPLEMENTATION_PLAN.md**
- Implementation roadmap for test suite
- Originally: PHASE_8_STRATEGIC_PLAN.md

**DOMAIN_MODELS_TEST_SUITE_COMPLETE.md**
- Completion report for domain model tests
- Originally: PHASE_8_BATCH1_PROGRESS.md

**TEST_SUITE_BATCHES_1_2_3_SUMMARY.md**
- Summary of domain and persistence layer tests
- Originally: PHASE_8_BATCHES_1_2_3_PROGRESS.md

**SERVICE_LAYER_TESTS_COMPLETE.md**
- Completion report for service layer tests
- Originally: PHASE_8_BATCH4_COMPLETION.md

**COMPREHENSIVE_TEST_SUITE_SUMMARY.md**
- Complete overview of all test suites
- Originally: PHASE_8_COMPLETE_SUMMARY.md

## Fixture Naming Convention

Reusable test fixtures use the **p8_** prefix to indicate they are part of the comprehensive test infrastructure:

```python
# Domain model data
p8_valid_issue_data         # Dict with required fields
p8_complete_issue_data      # Dict with all fields
p8_issue                    # Issue object with defaults

# Persistence fixtures
p8_yaml_issue_repository    # Real repository with tmp_path
p8_populated_issue_repository  # Pre-populated with test data

# Supporting fixtures
p8_issues_dir               # Temporary directory for issues
p8_mock_state_manager       # Mock state manager for testing
```

Note: The p8_ prefix refers to the test infrastructure generation, not any "Phase" concept.

## Running Tests

### All Test Suites
```bash
poetry run pytest \
  tests/unit/domain/test_issue_domain_comprehensive.py \
  tests/unit/domain/test_milestone_comment_models.py \
  tests/unit/adapters/persistence/test_issue_repository_persistence.py \
  tests/unit/services/test_issue_service_operations.py \
  -v
```

### Individual Test Suite
```bash
poetry run pytest tests/unit/domain/test_issue_domain_comprehensive.py -v
poetry run pytest tests/unit/domain/test_milestone_comment_models.py -v
poetry run pytest tests/unit/adapters/persistence/test_issue_repository_persistence.py -v
poetry run pytest tests/unit/services/test_issue_service_operations.py -v
```

### Specific Test Class
```bash
poetry run pytest tests/unit/domain/test_issue_domain_comprehensive.py::TestIssueCreation -v
```

### Specific Test
```bash
poetry run pytest tests/unit/domain/test_issue_domain_comprehensive.py::TestIssueCreation::test_create_with_minimal_required_fields -xvs
```

## Test Organization

### By Layer (Pyramid)
1. **Domain Models** (113 tests)
   - Issue model (66 tests)
   - Milestone & Comment models (47 tests)

2. **Persistence** (36 tests)
   - YAML repository CRUD and filtering

3. **Service Layer** (32 tests)
   - IssueService business logic and workflows

### By Characteristics
- **Real Code Paths**: Minimal mocking, actual implementations
- **Behavioral Assertions**: Testing behavior, not just "no errors"
- **Isolation**: Fresh fixtures for each test, no cross-test dependencies
- **Coverage**: All public interfaces and edge cases

## Total Test Suite

- **181 tests** across 4 test files
- **100% passing** consistently
- **~3-5 seconds** execution time
- All test files follow naming conventions for clarity

---

Last Updated: February 1, 2026
