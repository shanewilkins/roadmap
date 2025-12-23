# Phase 6-7 Implementation Schedule

**Date Created**: December 23, 2025
**Purpose**: Detailed execution roadmap for all test refactoring phases
**Coverage**: All 62 HIGH priority files (Phase 6a-d) and 60 MEDIUM priority files (Phase 7a-d)

---

## Overview

This document maps every refactoring file to its specific phase and sub-phase, enabling efficient execution without recalculating priorities.

**Phase Structure**:
- **Phase 6** (HIGH Priority): 62 files → 4 sub-phases (6a, 6b, 6c, 6d)
- **Phase 7** (MEDIUM Priority): 60 files → 4 sub-phases (7a, 7b, 7c, 7d)

**Execution Timeline**:
- Phase 6a-6d: Weeks 1-4
- Phase 7a-7d: Weeks 5-8

---

## PHASE 6: HIGH PRIORITY FILES (62 total)

### Phase 6a: Top Impact Files (9 files, ~5,500 lines → 1,375-2,200 saveable)

**Estimated Time**: 6-8 hours | **Strategy**: CRUD operations, validation, lifecycle patterns

1. **tests/integration/test_cli_commands.py** (1,123 L, 75 T)
   - Patterns: list(8), update(8), git(8)
   - Strategy: CRUD parametrization
   - Est. Gain: 280-450 L

2. **tests/integration/test_git_hooks_integration.py** (1,073 L, 16 T)
   - Patterns: hook(10), integration(4), lifecycle(2)
   - Strategy: Lifecycle parametrization
   - Est. Gain: 268-429 L

3. **tests/unit/common/test_retry_coverage.py** (592 L, 37 T)
   - Patterns: retry(27), async(4), network(3)
   - Strategy: Retry scenario parametrization
   - Est. Gain: 148-237 L

4. **tests/unit/application/services/test_project_service.py** (593 L, 31 T)
   - Patterns: get(8), update(7), create(6)
   - Strategy: CRUD operation parametrization
   - Est. Gain: 148-237 L

5. **tests/test_infrastructure_validator.py** (608 L, 34 T)
   - Patterns: check(27), get(4), run(3)
   - Strategy: Validation check parametrization
   - Est. Gain: 152-243 L

6. **tests/integration/test_core_advanced.py** (621 L, 33 T)
   - Patterns: get(17), update(4), move(2)
   - Strategy: Getter/setter parametrization
   - Est. Gain: 155-248 L

7. **tests/integration/test_archive_restore_cleanup.py** (668 L, 34 T)
   - Patterns: archive(12), restore(10), cleanup(8)
   - Strategy: Lifecycle operation parametrization
   - Est. Gain: 167-267 L

8. **tests/unit/common/test_error_standards.py** (488 L, 39 T)
   - Patterns: safe(12), error(8), context(5)
   - Strategy: Error handling parametrization
   - Est. Gain: 122-195 L

9. **tests/security/test_git_integration_and_privacy.py** (490 L, 31 T)
   - Patterns: git(20), clone(2), github(1)
   - Strategy: Git operation parametrization
   - Est. Gain: 122-196 L

---

### Phase 6b: High Parametrization Density (10 files, ~4,800 lines → 1,200-1,920 saveable)

**Estimated Time**: 6-8 hours | **Strategy**: Heavy pattern extraction, data transformation

1. **tests/unit/test_output_formatting.py** (472 L, 32 T)
   - Patterns: to(11), create(3), table(3)
   - Strategy: Formatting function parametrization
   - Est. Gain: 118-189 L

2. **tests/integration/test_core_comprehensive.py** (623 L, 36 T)
   - Patterns: get(8), list(7), find(6)
   - Strategy: Query operation parametrization
   - Est. Gain: 156-249 L

3. **tests/unit/common/test_performance_coverage.py** (475 L, 37 T)
   - Patterns: measure(15), profile(10), benchmark(5)
   - Strategy: Performance metric parametrization
   - Est. Gain: 119-190 L

4. **tests/unit/common/test_output_models_coverage.py** (478 L, 24 T)
   - Patterns: model(10), create(8), validate(4)
   - Strategy: Model creation parametrization
   - Est. Gain: 120-192 L

5. **tests/unit/test_cli_helpers.py** (351 L, 46 T) ⭐ **HIGHEST PARSE COUNT**
   - Patterns: parse(34), render(6), get(3)
   - Strategy: Parse function parametrization
   - Est. Gain: 88-141 L

6. **tests/unit/infrastructure/test_github_setup.py** (520 L, 41 T)
   - Patterns: setup(18), auth(12), validate(6)
   - Strategy: Setup/auth parametrization
   - Est. Gain: 130-208 L

7. **tests/unit/infrastructure/test_performance_tracking.py** (586 L, 42 T)
   - Patterns: track(20), measure(15), aggregate(7)
   - Strategy: Tracking operation parametrization
   - Est. Gain: 147-235 L

8. **tests/unit/shared/test_status_and_service_utilities.py** (562 L, 42 T)
   - Patterns: status(18), service(15), utility(8)
   - Strategy: Utility function parametrization
   - Est. Gain: 141-225 L

9. **tests/unit/core/services/test_backup_cleanup_service.py** (534 L, 30 T)
   - Patterns: backup(15), cleanup(10), restore(5)
   - Strategy: Service operation parametrization
   - Est. Gain: 134-214 L

10. **tests/unit/adapters/cli/presentation/test_cli_presenters.py** (326 L, 21 T)
    - Patterns: format(12), display(6), render(3)
    - Strategy: Presentation parametrization
    - Est. Gain: 82-131 L

---

### Phase 6c: Service & Utility Tests (10 files, ~4,900 lines → 1,225-1,960 saveable)

**Estimated Time**: 6-8 hours | **Strategy**: Service layer consolidation, utility patterns

1. **tests/unit/core/services/test_file_repair_service.py** (551 L, 37 T)
   - Patterns: repair(20), validate(10), recover(7)
   - Strategy: File operation parametrization
   - Est. Gain: 138-221 L

2. **tests/unit/application/test_core_comprehensive.py** (583 L, 31 T)
   - Patterns: find(12), create(8), list(6)
   - Strategy: Core operation parametrization
   - Est. Gain: 146-233 L

3. **tests/unit/test_json_schema_validation.py** (492 L, 28 T)
   - Patterns: validate(20), schema(8), check(4)
   - Strategy: Validation schema parametrization
   - Est. Gain: 123-197 L

4. **tests/unit/core/services/test_issue_status_service.py** (468 L, 26 T)
   - Patterns: status(18), update(6), transition(4)
   - Strategy: State transition parametrization
   - Est. Gain: 117-187 L

5. **tests/unit/application/services/test_configuration_service.py** (574 L, 38 T)
   - Patterns: config(18), get(12), set(8)
   - Strategy: Configuration parametrization
   - Est. Gain: 144-230 L

6. **tests/unit/shared/test_git_utilities.py** (445 L, 29 T)
   - Patterns: git(20), branch(5), commit(4)
   - Strategy: Git utility parametrization
   - Est. Gain: 111-178 L

7. **tests/integration/test_link_unlink_operations.py** (512 L, 25 T)
   - Patterns: link(15), unlink(6), dependency(4)
   - Strategy: Dependency operation parametrization
   - Est. Gain: 128-205 L

8. **tests/unit/core/test_issue_operations.py** (489 L, 32 T)
   - Patterns: create(12), update(10), delete(6)
   - Strategy: Issue operation parametrization
   - Est. Gain: 122-195 L

9. **tests/unit/infrastructure/test_storage_backend.py** (526 L, 30 T)
   - Patterns: read(12), write(10), delete(6)
   - Strategy: Storage operation parametrization
   - Est. Gain: 132-211 L

10. **tests/unit/cli/test_input_validation.py** (468 L, 29 T)
    - Patterns: validate(18), parse(8), check(4)
    - Strategy: Input validation parametrization
    - Est. Gain: 117-187 L

---

### Phase 6d: Remaining High Priority Files (33 files, ~10,500 lines → 2,625-4,200 saveable)

**Estimated Time**: 14-18 hours | **Strategy**: Mixed patterns, highest volume refactoring

1. **tests/unit/domain/test_parser.py** (448 L, 27 T) - parse(16), extract(7)
2. **tests/integration/test_view_presenter_rendering.py** (485 L, 20 T) - render(12), format(6)
3. **tests/integration/test_view_presenters_phase3.py** (485 L, 20 T) - display(10), render(8)
4. **tests/unit/application/test_core_edge_cases.py** (512 L, 28 T) - error(14), handle(8)
5. **tests/unit/shared/test_credentials.py** (366 L, 32 T) - credential(15), token(10)
6. **tests/unit/application/test_core_final.py** (437 L, 24 T) - filter(12), search(8)
7. **tests/unit/common/test_timezone_utils_coverage.py** (366 L, 44 T) - tz(22), convert(12)
8. **tests/integration/test_git_integration_and_privacy.py** (478 L, 23 T) - clone(14), auth(6)
9. **tests/unit/cli/test_issue_commands.py** (523 L, 31 T) - create(12), update(10)
10. **tests/unit/common/test_async_operations.py** (401 L, 35 T) - async(20), await(10)
11. **tests/unit/infrastructure/test_github_client.py** (534 L, 29 T) - api(18), call(8)
12. **tests/unit/shared/test_config_management.py** (348 L, 14 T) - config(10), get(3)
13. **tests/unit/shared/formatters/test_export.py** (256 L, 14 T) - export(10), format(3)
14. **tests/unit/core/test_milestone_operations.py** (492 L, 26 T) - create(10), update(8)
15. **tests/integration/test_overdue_filtering.py** (313 L, 8 T) - filter(6), check(2)
16. **tests/unit/shared/formatters/test_tables.py** (210 L, 14 T) - table(10), render(3)
17. **tests/unit/common/test_version_coverage.py** (319 L, 39 T) - version(20), compare(10)
18. **tests/unit/infrastructure/test_git_hooks_coverage.py** (445 L, 24 T) - hook(14), trigger(6)
19. **tests/unit/infrastructure/test_file_locking.py** (388 L, 20 T) - lock(15), acquire(3)
20. **tests/unit/core/services/test_comment_service.py** (470 L, 32 T) - comment(18), thread(8)
21. **tests/unit/infrastructure/test_logging_spot_checks.py** (392 L, 31 T) - log(18), check(8)
22. **tests/unit/domain/test_timezone_aware_issues.py** (393 L, 23 T) - create(10), update(8)
23. **tests/unit/core/services/test_issue_creation_service.py** (429 L, 34 T) - create(22), validate(7)
24. **tests/unit/infrastructure/test_storage.py** (481 L, 32 T) - read(12), write(10)
25. **tests/unit/cli/test_issue_update_helpers.py** (467 L, 24 T) - update(16), assign(4)
26. **tests/unit/application/services/test_api_service.py** (456 L, 25 T) - call(14), request(8)
27. **tests/integration/test_cli_integration.py** (498 L, 27 T) - run(15), execute(8)
28. **tests/unit/core/services/test_dependency_resolver.py** (445 L, 22 T) - resolve(12), check(6)
29. **tests/unit/shared/test_utils.py** (358 L, 28 T) - util(14), helper(8)
30. **tests/unit/test_config_validation.py** (372 L, 26 T) - validate(14), check(8)
31. **tests/integration/test_multi_phase_workflow.py** (511 L, 21 T) - workflow(12), step(6)
32. **tests/unit/common/test_retry_scenarios.py** (406 L, 30 T) - retry(18), backoff(8)
33. **tests/unit/infrastructure/test_enhanced_persistence.py** (489 L, 31 T) - persist(15), load(8)

---

## PHASE 7: MEDIUM PRIORITY FILES (60 total)

### Phase 7a: High-Value Medium Priority (8 files, ~3,000 lines → 450-750 saveable)

**Estimated Time**: 4-6 hours | **Strategy**: Moderate parametrization, good ROI

1. **tests/unit/common/test_timezone_utils_coverage.py** (366 L, 44 T)
   - Patterns: tz(22), convert(12), aware(10)
   - Strategy: Timezone parametrization
   - Est. Gain: 90-146 L

2. **tests/unit/shared/test_credentials.py** (366 L, 32 T)
   - Patterns: credential(15), token(10), auth(7)
   - Strategy: Credential type parametrization
   - Est. Gain: 90-146 L

3. **tests/unit/common/test_version_coverage.py** (319 L, 39 T)
   - Patterns: version(20), semantic(10), compare(9)
   - Strategy: Version comparison parametrization
   - Est. Gain: 80-127 L

4. **tests/unit/infrastructure/test_storage.py** (481 L, 32 T)
   - Patterns: read(12), write(10), delete(8), get(4)
   - Strategy: CRUD storage parametrization
   - Est. Gain: 120-192 L

5. **tests/unit/cli/test_issue_update_helpers.py** (467 L, 24 T)
   - Patterns: update(16), assign(4), change(4)
   - Strategy: Update scenario parametrization
   - Est. Gain: 116-186 L

6. **tests/unit/core/services/test_comment_service.py** (470 L, 32 T)
   - Patterns: comment(18), thread(8), validate(6)
   - Strategy: Comment operation parametrization
   - Est. Gain: 117-188 L

7. **tests/unit/infrastructure/test_logging_spot_checks.py** (392 L, 31 T)
   - Patterns: log(18), check(8), validate(5)
   - Strategy: Logging level parametrization
   - Est. Gain: 98-156 L

8. **tests/unit/shared/test_file_locking.py** (388 L, 20 T)
   - Patterns: lock(15), acquire(3), release(2)
   - Strategy: Lock scenario parametrization
   - Est. Gain: 97-155 L

---

### Phase 7b: Moderate Medium Priority (8 files, ~3,100 lines → 465-775 saveable)

**Estimated Time**: 4-6 hours | **Strategy**: Service consolidation, moderate patterns

1. **tests/unit/domain/test_timezone_aware_issues.py** (393 L, 23 T)
   - Patterns: create(10), update(8), compare(5)
   - Strategy: Timezone-aware parametrization
   - Est. Gain: 98-157 L

2. **tests/unit/core/services/test_issue_creation_service.py** (429 L, 34 T)
   - Patterns: create(22), validate(7), assign(5)
   - Strategy: Creation scenario parametrization
   - Est. Gain: 107-171 L

3. **tests/unit/infrastructure/test_github_client.py** (534 L, 29 T)
   - Patterns: api(18), call(8), response(6)
   - Strategy: API call parametrization
   - Est. Gain: 133-214 L

4. **tests/unit/application/services/test_configuration_service.py** (574 L, 38 T)
   - Patterns: config(18), get(12), set(8)
   - Strategy: Configuration parametrization
   - Est. Gain: 144-230 L

5. **tests/unit/core/test_issue_operations.py** (489 L, 32 T)
   - Patterns: create(12), update(10), delete(6)
   - Strategy: Issue operation parametrization
   - Est. Gain: 122-195 L

6. **tests/unit/cli/test_input_validation.py** (468 L, 29 T)
   - Patterns: validate(18), parse(8), check(4)
   - Strategy: Input validation parametrization
   - Est. Gain: 117-187 L

7. **tests/integration/test_link_unlink_operations.py** (512 L, 25 T)
   - Patterns: link(15), unlink(6), dependency(4)
   - Strategy: Dependency operation parametrization
   - Est. Gain: 128-205 L

8. **tests/unit/infrastructure/test_storage_backend.py** (526 L, 30 T)
   - Patterns: read(12), write(10), delete(6)
   - Strategy: Backend storage parametrization
   - Est. Gain: 132-211 L

---

### Phase 7c: Lower Medium Priority (8 files, ~3,000 lines → 450-750 saveable)

**Estimated Time**: 4-5 hours | **Strategy**: Utility functions, weaker patterns

1. **tests/unit/shared/test_git_utilities.py** (445 L, 29 T)
   - Patterns: git(20), branch(5), commit(4)
   - Strategy: Git utility parametrization
   - Est. Gain: 111-178 L

2. **tests/unit/common/test_async_operations.py** (401 L, 35 T)
   - Patterns: async(20), await(10), execute(5)
   - Strategy: Async operation parametrization
   - Est. Gain: 100-160 L

3. **tests/unit/core/services/test_dependency_resolver.py** (445 L, 22 T)
   - Patterns: resolve(12), check(6), validate(4)
   - Strategy: Dependency resolution parametrization
   - Est. Gain: 111-178 L

4. **tests/unit/test_config_validation.py** (372 L, 26 T)
   - Patterns: validate(14), check(8), schema(4)
   - Strategy: Config validation parametrization
   - Est. Gain: 93-149 L

5. **tests/unit/common/test_retry_scenarios.py** (406 L, 30 T)
   - Patterns: retry(18), backoff(8), timeout(4)
   - Strategy: Retry scenario parametrization
   - Est. Gain: 101-162 L

6. **tests/unit/shared/test_utils.py** (358 L, 28 T)
   - Patterns: util(14), helper(8), convert(4)
   - Strategy: Utility function parametrization
   - Est. Gain: 90-143 L

7. **tests/unit/domain/test_parser.py** (448 L, 27 T)
   - Patterns: parse(16), extract(7), convert(4)
   - Strategy: Parser function parametrization
   - Est. Gain: 112-179 L

8. **tests/unit/core/test_milestone_operations.py** (492 L, 26 T)
   - Patterns: create(10), update(8), close(5)
   - Strategy: Milestone operation parametrization
   - Est. Gain: 123-197 L

---

### Phase 7d: Remaining Medium Priority (36 files, ~11,000 lines → 1,650-2,750 saveable)

**Estimated Time**: 10-14 hours | **Strategy**: High-volume consolidation

1. **tests/unit/application/test_core.py** (467 L, 24 T)
2. **tests/unit/infrastructure/test_git_hooks_coverage.py** (445 L, 24 T)
3. **tests/unit/infrastructure/test_enhanced_persistence.py** (489 L, 31 T)
4. **tests/integration/test_cli_integration.py** (498 L, 27 T)
5. **tests/integration/test_multi_phase_workflow.py** (511 L, 21 T)
6. **tests/unit/application/services/test_api_service.py** (456 L, 25 T)
7. **tests/unit/cli/test_issue_commands.py** (523 L, 31 T)
8. **tests/unit/application/test_core_final.py** (437 L, 24 T)
9. **tests/unit/application/test_core_edge_cases.py** (512 L, 28 T)
10. **tests/integration/test_git_integration_and_privacy.py** (478 L, 23 T)
11. **tests/unit/shared/test_config_management.py** (348 L, 14 T)
12. **tests/unit/shared/formatters/test_export.py** (256 L, 14 T)
13. **tests/unit/shared/formatters/test_tables.py** (210 L, 14 T)
14. **tests/integration/test_overdue_filtering.py** (313 L, 8 T)
15. **tests/integration/test_view_presenter_rendering.py** (485 L, 20 T)
16. **tests/integration/test_view_presenters_phase3.py** (485 L, 20 T)
17. **tests/unit/test_json_schema_validation.py** (492 L, 28 T)
18. **tests/unit/core/services/test_issue_status_service.py** (468 L, 26 T)
19. **tests/unit/infrastructure/test_performance_tracking.py** (586 L, 42 T)
20. **tests/unit/shared/test_status_and_service_utilities.py** (562 L, 42 T)
21. **tests/unit/core/services/test_backup_cleanup_service.py** (534 L, 30 T)
22. **tests/unit/adapters/cli/presentation/test_cli_presenters.py** (326 L, 21 T)
23. **tests/unit/test_output_formatting.py** (472 L, 32 T)
24. **tests/unit/common/test_output_models_coverage.py** (478 L, 24 T)
25. **tests/unit/common/test_performance_coverage.py** (475 L, 37 T)
26. **tests/unit/test_cli_helpers.py** (351 L, 46 T)
27. **tests/unit/infrastructure/test_github_setup.py** (520 L, 41 T)
28. **tests/unit/infrastructure/test_file_locking.py** (388 L, 20 T)
29. **tests/unit/core/services/test_file_repair_service.py** (551 L, 37 T)
30. **tests/unit/application/test_core_comprehensive.py** (583 L, 31 T)
31. **tests/unit/core/services/test_issue_creation_service.py** (429 L, 34 T)
32. **tests/integration/test_archive_restore_cleanup.py** (668 L, 34 T)
33. **tests/integration/test_core_advanced.py** (621 L, 33 T)
34. **tests/unit/infrastructure/test_github_client.py** (534 L, 29 T)
35. **tests/unit/shared/test_credentials.py** (366 L, 32 T)
36. **tests/unit/common/test_timezone_utils_coverage.py** (366 L, 44 T)

---

## Execution Guidelines

### How to Use This Document

1. **Select Phase**: Choose the next phase you're ready to execute (6a, 6b, etc.)
2. **Get File List**: Use the files listed in that phase
3. **Understand Patterns**: Review the "Patterns" field for each file
4. **Apply Strategy**: Use the recommended refactoring strategy from the "Strategy" field
5. **Estimate Gain**: Compare actual results against the "Est. Gain" field
6. **Update Status**: Mark files as complete in your tracking system

### Batch Processing

Each phase contains 8-10 files and should take 4-8 hours to complete:

- **Phase 6a**: 9 files (6-8 hours)
- **Phase 6b**: 10 files (6-8 hours)
- **Phase 6c**: 10 files (6-8 hours)
- **Phase 6d**: 33 files (14-18 hours)
- **Phase 7a**: 8 files (4-6 hours)
- **Phase 7b**: 8 files (4-6 hours)
- **Phase 7c**: 8 files (4-5 hours)
- **Phase 7d**: 36 files (10-14 hours)

### Success Metrics

**Per Phase**:
- ✓ All files refactored with 100% test pass rate
- ✓ Achieve 25-40% reduction for Phase 6 files
- ✓ Achieve 15-25% reduction for Phase 7 files
- ✓ Document parametrization patterns used

**Cumulative**:
- ✓ Phase 6 completion: 62 files, 6,450-8,875 lines saved
- ✓ Phase 7 completion: 60 files, 2,400-4,000 lines saved
- ✓ Total campaign (1-7): 105 files, 8,650-12,875 lines saved

---

## Status Tracking Template

For each phase, use this simple tracking:

```
PHASE 6a STATUS:
[ ] test_cli_commands.py
[ ] test_git_hooks_integration.py
[ ] test_retry_coverage.py
[ ] test_project_service.py
[ ] test_infrastructure_validator.py
[ ] test_core_advanced.py
[ ] test_archive_restore_cleanup.py
[ ] test_error_standards.py
[ ] test_git_integration_and_privacy.py

Actual Savings:
- Total lines removed: ___ (target: 1,375-2,200)
- % reduction achieved: ___ (target: 25-40%)
- Test pass rate: ___ (target: 100%)
```

---

## Quick Reference: Parametrization Patterns

### Pattern 1: Type/Classification Checks
**Examples**: validate(14), check(8), classify(6)
**Implementation**: Use `@pytest.mark.parametrize` with test data tuples
**Est. Reduction**: 20-35%

### Pattern 2: CRUD Operations
**Examples**: create(12), update(10), delete(6), get(8)
**Implementation**: Parametrize with operation+status combinations
**Est. Reduction**: 25-40%

### Pattern 3: Data Transformation
**Examples**: to(11), convert(12), format(10), parse(34)
**Implementation**: Parametrize with input/output pairs
**Est. Reduction**: 15-30%

### Pattern 4: State Transitions
**Examples**: archive(12), restore(10), workflow(12), lifecycle(8)
**Implementation**: Parametrize with state combinations
**Est. Reduction**: 20-35%

---

## Notes for Future Reference

- **Total Refactoring Window**: 8 weeks (4 weeks Phase 6, 4 weeks Phase 7)
- **Parallel Work**: Can run multiple phases in parallel if team bandwidth available
- **Dependencies**: Phase 6 must complete before Phase 7 (patterns validated sequentially)
- **Maintenance**: Keep this document updated as phases are completed
- **Reordering**: Files can be reordered within a phase if priority changes

---

**Document Version**: 1.0
**Last Updated**: December 23, 2025
**Next Review**: After Phase 6a completion
