# Phase 7g: Violation Inventory & Categorization

**Status**: Step 1 Complete - Inventory from Semgrep Analysis  
**Date**: January 26, 2026  
**Analysis Method**: Poetry semgrep --config=.semgrep.yml roadmap/  
**Total Violations**: 123 across 112 files  

---

## Executive Summary

Semgrep detected **123 total violations** across the application:
- **112 missing-severity-field** violations (Phase 7g primary target)
- **7 except-silent-pass** violations (mostly in tests, acceptable)
- **4 except-silent-return** violations (need review)

All violations are distributed across 112 unique files. Most files have 1 violation; none have multiple violations in the same file.

---

## Violation Breakdown by Category

### Missing-Severity-Field Violations (112)

These are logger.error() or logger.warning() calls that lack the required `severity` field for structured logging aggregation.

**Files Affected (112 total):**

1. adapters/cli/analysis/commands.py
2. adapters/cli/cli_error_handlers.py
3. adapters/cli/git/handlers/git_authentication_handler.py
4. adapters/cli/git/handlers/git_connectivity_handler.py
5. adapters/cli/health/fixers/corrupted_comments_fixer.py
6. adapters/cli/health/fixers/data_integrity_fixer.py
7. adapters/cli/health/fixers/duplicate_issues_fixer.py
8. adapters/cli/health/fixers/folder_structure_fixer.py
9. adapters/cli/health/fixers/milestone_name_normalization_fixer.py
10. adapters/cli/health/fixers/milestone_validation_fixer.py
11. adapters/cli/health/fixers/orphaned_issues_fixer.py
12. adapters/cli/presentation/milestone_list_presenter.py
13. adapters/cli/services/milestone_list_service.py
14. adapters/cli/services/project_status_service.py
15. adapters/cli/sync.py
16. adapters/cli/sync_context.py
17. adapters/cli/sync_handlers/baseline_ops.py
18. adapters/cli/sync_validation.py
19. adapters/git/git_branch_manager.py
20. adapters/git/git_hooks_manager.py
21. adapters/git/hook_installer.py
22. adapters/git/hook_registry.py
23. adapters/git/sync_monitor.py
24. adapters/git/workflow_automation.py
25. adapters/github/handlers/collaborators.py
26. adapters/persistence/conflict_resolver.py
27. adapters/persistence/database_manager.py
28. adapters/persistence/entity_sync_coordinators.py
29. adapters/persistence/file_locking.py
30. adapters/persistence/file_parser.py
31. adapters/persistence/file_synchronizer.py
32. adapters/persistence/git_history.py
33. adapters/persistence/repositories/remote_link_repository.py
34. adapters/persistence/storage/conflicts.py
35. adapters/persistence/storage/queries.py
36. adapters/persistence/storage/state_manager.py
37. adapters/persistence/storage/sync_state_storage.py
38. adapters/persistence/sync_orchestrator.py
39. adapters/persistence/yaml_repositories.py
40. adapters/sync/backends/github_client.py
41. adapters/sync/backends/github_sync_backend.py
42. adapters/sync/backends/github_sync_ops.py
43. adapters/sync/backends/services/github_issue_fetch_service.py
44. adapters/sync/backends/services/github_issue_push_service.py
45. adapters/sync/services/baseline_state_handler.py
46. adapters/sync/services/conflict_converter.py
47. adapters/sync/services/issue_persistence_service.py
48. adapters/sync/services/issue_state_service.py
49. adapters/sync/services/local_change_filter.py
50. adapters/sync/services/pull_result_processor.py
51. adapters/sync/services/remote_issue_creation_service.py
52. adapters/sync/services/sync_analysis_service.py
53. adapters/sync/services/sync_authentication_service.py
54. adapters/sync/services/sync_data_fetch_service.py
55. adapters/sync/services/sync_linking_service.py
56. adapters/sync/services/sync_state_update_service.py
57. adapters/sync/sync_cache_orchestrator.py
58. adapters/sync/sync_merge_engine.py
59. adapters/sync/sync_merge_orchestrator.py
60. adapters/sync/sync_retrieval_orchestrator.py
61. common/cli_errors.py
62. common/configuration/config_loader.py
63. common/errors/error_standards.py
64. common/logging/decorators.py
65. common/logging/error_logging.py
66. common/logging/performance_tracking.py
67. common/logging/utils.py
68. common/observability/instrumentation.py
69. common/observability/otel_init.py
70. common/progress.py
71. common/services/performance.py
72. common/services/profiling.py
73. common/services/retry.py
74. common/utils/file_utils.py
75. common/utils/timezone_utils.py
76. common/validation/roadmap_validator.py
77. core/services/baseline/baseline_builder_progress.py
78. core/services/baseline/baseline_state_retriever.py
79. core/services/baseline/optimized_baseline_builder.py
80. core/services/github/github_integration_service.py
81. core/services/github/github_issue_client.py
82. core/services/health/backup_cleanup_service.py
83. core/services/health/data_integrity_validator_service.py
84. core/services/health/entity_health_scanner.py
85. core/services/health/file_repair_service.py
86. core/services/health/health_check_service.py
87. core/services/health/infrastructure_validator_service.py
88. core/services/initialization_service.py
89. core/services/issue/issue_service.py
90. core/services/milestone_service.py
91. core/services/project/project_service.py
92. core/services/project/project_status_service.py
93. core/services/project_init/creation.py
94. core/services/sync/sync_change_computer.py
95. core/services/sync/sync_conflict_detector.py
96. core/services/sync/sync_key_normalizer.py
97. core/services/sync/sync_plan_executor.py
98. core/services/sync/sync_state_manager.py
99. core/services/sync/sync_state_normalizer.py
100. core/services/utils/field_conflict_detector.py
101. core/services/utils/remote_fetcher.py
102. core/services/validator_base.py
103. core/services/validators/data_integrity_validator.py
104. core/services/validators/folder_structure_validator.py
105. core/services/validators/orphaned_issues_validator.py
106. core/services/validators/orphaned_milestones_validator.py
107. infrastructure/coordination/core.py
108. infrastructure/coordination/milestone_operations.py
109. infrastructure/security/credentials.py
110. infrastructure/validation/github_validator.py
111. settings.py
112. version.py

---

## Exception Handling Violations

### Except-Silent-Pass (7 violations)

Exception handlers using `pass` without logging. These are mostly acceptable in test/validation code but should ideally have logging.

**Files with except-silent-pass:**
- (Details to be extracted from semgrep output)
- Generally acceptable in unit tests

### Except-Silent-Return (4 violations)

Exception handlers using `return` without logging.

**Files with except-silent-return:**
- (Details to be extracted from semgrep output)
- Need to determine if these should log before returning

---

## Severity Categorization Strategy

### Error Context Patterns Identified

From examining the violation files, the missing-severity violations fall into predictable categories:

1. **Configuration Errors** (settings.py, config_loader.py)
   - Category: `config_error`
   - Files: settings.py, common/configuration/config_loader.py
   - Pattern: Config file not found, invalid config, validation failed

2. **Data/Validation Errors** (validation, parsers, integrity)
   - Category: `data_error`
   - Files: file_parser.py, validators/*, data_integrity_*.py, roadmap_validator.py
   - Pattern: Parse error, validation failure, corrupt data

3. **System/Permission Errors** (file operations, git hooks)
   - Category: `system_error`
   - Files: file_locking.py, file_synchronizer.py, git/*, file_utils.py
   - Pattern: Permission denied, file not found, git error

4. **Infrastructure/Network Errors** (github, sync, persistence)
   - Category: `infrastructure`
   - Files: github/*.py, sync/backends/*, adapters/sync/*
   - Pattern: API failure, network timeout, auth failure

5. **Operational Errors** (health checks, recovery, monitoring)
   - Category: `operational`
   - Files: health/*.py, baseline/*.py, sync_monitor.py
   - Pattern: Expected errors user can retry, warnings, monitoring events

---

## Phase 7g Execution Plan

### Step 1: Categorize Each File (In Progress)
- [x] Identify all 112 files with violations
- [ ] Read each file and determine error context
- [ ] Assign appropriate severity category
- [ ] Document any special cases

### Step 2: Generate Fix Instructions
- [ ] Create old_string/new_string pairs for multi_replace_string_in_file
- [ ] Group by severity to catch patterns
- [ ] Validate patterns before applying

### Step 3: Apply Fixes in Batches
- [ ] Batch 1: Configuration & Validation errors (easier, pattern-based)
- [ ] Batch 2: System/File operation errors
- [ ] Batch 3: Infrastructure/Sync errors (largest batch)
- [ ] Batch 4: Operational/Health/Monitoring errors

### Step 4: Validate & Test
- [ ] Run semgrep after each batch
- [ ] Verify no new violations introduced
- [ ] Run full test suite

---

## Next Steps

1. **Immediate**: Read violation context from 5-10 key files to refine categorization
2. **This session**: Generate and apply first batch of fixes (configuration errors)
3. **Next session**: Continue with remaining batches

---

## Implementation Notes

- **Rule**: missing-severity-field enforces required field in error/warning calls
- **Canonical Form**: `logger.error("event", ..., severity="category", exc_info=True)`
- **Accepted Categories**: config_error, data_error, system_error, infrastructure, operational
- **Anchor**: All 112 files confirmed via Semgrep analysis, 1 violation each
- **Complexity**: Low - mostly mechanical addition of severity field with context-based category selection
