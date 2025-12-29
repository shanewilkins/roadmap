# Test File Size Optimization Plan

## Executive Summary

Current Status: **45 files exceed 500 LOC hard limit** | **78 files exceed 400 LOC preferred limit**

This plan identifies strategic splits for all oversized test files while maintaining:
- Logical architectural groupings
- Clear module relationships
- Test discovery and execution patterns
- Import dependencies

### Quick Reference: Splitting Tiers

| Tier | Files | Action | Target Size | Impact |
|------|-------|--------|-------------|--------|
| **Tier 1** (>1000 LOC) | 3 files | **Immediate** | 300-400 LOC | High Priority |
| **Tier 2** (800-1000) | 2 files | Week 2 | 350-450 LOC | Medium-High |
| **Tier 3** (700-800) | 4 files | Week 3 | 300-400 LOC | Medium |
| **Tier 4** (600-700) | 9 files | Week 4 | 300-350 LOC | Medium-Low |
| **Tier 5** (550-600) | 11 files | Week 5+ | 250-350 LOC | Low (optional) |
| **Tier 6** (500-550) | 16 files | As needed | 250-350 LOC | Low (optional) |

**Total Files to Address:** 45 critical (>500) + 33 major (400-500) = 78 total

---

## Detailed Splitting Plans

## Tier 1: Critical (> 1000 LOC) - 3 Files

### 1. **test_security.py** (1135 LOC) → 3 files
**Location:** `tests/unit/shared/test_security.py`
**Test Classes (13):** Exceptions, CreateSecureFile, CreateSecureDirectory, ValidatePath, SanitizeFilename, CreateSecureTempFile, SecureFilePermissions, LogSecurityEvent, ConfigureSecurityLogging, ValidateExportSize, CleanupOldBackups, SecurityIntegration, SecurityPerformance

**Split Strategy:**
- **test_security_paths.py** (300-350 LOC)
  - `TestValidatePath` - Path validation/traversal attacks
  - `TestSanitizeFilename` - Filename security
  - `TestCreateSecureTempFile` - Temp file creation
  - `TestSecurityExceptions` - Exception definitions

- **test_security_file_ops.py** (300-350 LOC)
  - `TestCreateSecureFile` - File creation with permissions
  - `TestCreateSecureDirectory` - Directory creation with permissions
  - `TestSecureFilePermissions` - Permission handling
  - `TestCleanupOldBackups` - Backup cleanup logic

- **test_security_logging_and_integration.py** (250-300 LOC)
  - `TestLogSecurityEvent` - Security event logging
  - `TestConfigureSecurityLogging` - Logging setup
  - `TestValidateExportSize` - Export size validation
  - `TestSecurityIntegration` - Integration scenarios
  - `TestSecurityPerformance` - Performance tests

**Benefits:** Clear separation of concerns (path validation, file operations, logging)

---

### 2. **test_git_hooks_integration.py** (1006 LOC) → 2 files
**Location:** `tests/integration/test_git_hooks_integration.py`
**Test Classes (3):** TBD from analysis

**Split Strategy:** (Analysis needed - requires examining class structures)
- **test_git_hooks_[scenario1].py** - Specific hook scenario tests
- **test_git_hooks_[scenario2].py** - Alternative hook scenarios

---

### 3. **test_cli_commands.py** (1006 LOC) → 4 files
**Location:** `tests/integration/test_cli_commands.py`
**Test Classes (22):** Init, Status, Health, IssueCreate, HelpCommands, IssueList, IssueUpdate, IssueDelete, IssueWorkflow, IssueHelp, RootHelp, MilestoneCreate, MilestoneList, MilestoneAssign, MilestoneUpdate, MilestoneClose, MilestoneDelete, MilestoneHelp, DataExport, DataGroup, GitIntegration, GitGroup

**Split Strategy (by command domain):**
- **test_cli_issue_commands.py** (300-350 LOC)
  - `TestCLIIssueCreate`
  - `TestCLIIssueList`
  - `TestCLIIssueUpdate`
  - `TestCLIIssueDelete`
  - `TestCLIIssueWorkflow`
  - `TestCLIIssueHelp`

- **test_cli_milestone_commands.py** (250-300 LOC)
  - `TestCLIMilestoneCreate`
  - `TestCLIMilestoneList`
  - `TestCLIMilestoneAssign`
  - `TestCLIMilestoneUpdate`
  - `TestCLIMilestoneClose`
  - `TestCLIMilestoneDelete`
  - `TestCLIMilestoneHelp`

- **test_cli_data_and_git_commands.py** (200-250 LOC)
  - `TestCLIDataExport`
  - `TestCLIDataGroup`
  - `TestCLIGitIntegration`
  - `TestCLIGitGroup`

- **test_cli_root_commands.py** (150-200 LOC)
  - `TestCLIInit`
  - `TestCLIStatus`
  - `TestCLIHealth`
  - `TestCLIRootHelp`
  - `TestCLIHelpCommands` (shared help utilities)

**Benefits:** Natural grouping by domain (issues, milestones, data/git, root commands)

---

## Tier 2: Major (800-1000 LOC) - 2 Files

### 4. **test_queries_errors.py** (938 LOC) → 2 files
**Location:** `tests/test_cli/test_queries_errors.py`
**Test Classes (7):** Initialization, HasFileChanges, GetAllIssues, GetAllMilestones, GetMilestoneProgress, GetIssuesByStatus, QueryServiceIntegration

**Split Strategy (by query operation type):**
- **test_queries_read_operations.py** (400-450 LOC)
  - `TestQueryServiceInitialization`
  - `TestGetAllIssues`
  - `TestGetAllMilestones`
  - `TestGetMilestoneProgress`
  - `TestGetIssuesByStatus`

- **test_queries_state_operations.py** (350-400 LOC)
  - `TestHasFileChanges`
  - `TestQueryServiceIntegration`

**Benefits:** Clear separation between read operations and state-checking operations

---

### 5. **test_milestone_repository_errors.py** (864 LOC) → 2 files
**Location:** `tests/test_cli/test_milestone_repository_errors.py`

**Split Strategy (by operation type):**
- **test_milestone_repository_write_ops.py** (400-450 LOC)
  - `TestMilestoneRepositoryInitialization`
  - `TestMilestoneRepositoryCreate`
  - `TestMilestoneRepositoryUpdate`
  - `TestMilestoneRepositoryMarkArchived`

- **test_milestone_repository_read_ops.py** (350-400 LOC)
  - `TestMilestoneRepositoryGet`
  - Repository read/query operations
  - `TestMilestoneRepositoryConcurrency`
  - `TestMilestoneRepositorySequences`

**Benefits:** Write operations (with transaction complexity) separated from read operations

---

## Tier 3: Large (700-800 LOC) - 4 Files

### 6. **test_git_integration_ops_errors.py** (780 LOC) → 2 files
**Location:** `tests/test_cli/test_git_integration_ops_errors.py`
**Test Classes (10):** Initialization, GetGitContext, GetCurrentUserFromGit, CreateIssueWithGitBranch, LinkIssueToBranch, GetCommitsForIssue, UpdateIssueFromGitActivity, SuggestBranchName, GetBranchLinkedIssues, GitIntegrationOpsIntegration

**Split Strategy (by operation type):**
- **test_git_integration_branch_ops.py** (350-400 LOC)
  - `TestGitIntegrationOpsInitialization`
  - `TestCreateIssueWithGitBranch`
  - `TestSuggestBranchName`
  - `TestGetBranchLinkedIssues`

- **test_git_integration_commit_ops.py** (350-400 LOC)
  - `TestGetGitContext`
  - `TestGetCurrentUserFromGit`
  - `TestLinkIssueToBranch`
  - `TestGetCommitsForIssue`
  - `TestUpdateIssueFromGitActivity`
  - `TestGitIntegrationOpsIntegration`

**Benefits:** Branch operations separated from commit/linking operations

### 7. **test_entity_health_scanner.py** (746 LOC) → 2 files
**Location:** `tests/unit/core/services/test_entity_health_scanner.py`

**Split Strategy (by check type - requires analysis):**
- **test_entity_health_scanner_basic.py** (350-400 LOC)
  - Basic health check scenarios

- **test_entity_health_scanner_advanced.py** (300-350 LOC)
  - Complex/edge case scenarios
  - Integration scenarios

### 8. **test_entity_sync_coordinators.py** (714 LOC) → 2 files
**Location:** `tests/unit/adapters/persistence/test_entity_sync_coordinators.py`

**Split Strategy (by coordinator type - requires analysis):**
- **test_entity_sync_issue_coordinator.py** (350-400 LOC)
  - `TestIssueSyncCoordinator`
  - Issue-specific sync operations

- **test_entity_sync_milestone_coordinator.py** (300-350 LOC)
  - `TestMilestoneSyncCoordinator`
  - Other coordinator types
  - Base coordinator tests

### 9. **test_git_hook_auto_sync_service_coverage.py** (674 LOC) → 2 files
**Location:** `tests/unit/core/services/test_git_hook_auto_sync_service_coverage.py`

**Split Strategy (by scenario type - requires analysis):**
- **test_git_hook_auto_sync_basic.py** (300-350 LOC)
  - Basic auto-sync scenarios

- **test_git_hook_auto_sync_advanced.py** (300-350 LOC)
  - Advanced/edge case scenarios
  - Performance/stress tests

---

## Tier 4: Medium-Large (600-700 LOC) - 9 Files

These files exceed 400 LOC preferred limit but are below 700:
- test_error_validation_errors.py (667)
- test_archive_restore_cleanup.py (645)
- test_parser.py (641)
- test_core_advanced.py (unit: 640, integration: 616)
- test_github_sync_orchestrator_extended.py (628)
- test_git_hooks_manager_errors.py (617)
- test_core_comprehensive.py (integration: 614, unit: 608)

**General Strategy:** Split by logical test domains (e.g., create/update, success/failure paths)

---

## Tier 5: Medium (550-600 LOC) - 11 Files

Files between 550-600 LOC should be reviewed for single-responsibility:
- test_git_hooks.py (594 unit + 608 integration)
- test_project_service.py (593)
- test_sync_status_command.py (589)
- test_git_integration_coverage.py (580)
- test_error_logging.py (574)
- test_cleanup_functions.py (574)
- test_github_setup.py (564)
- test_folder_structure_validator.py (562)
- test_performance_tracking.py (551)
- test_file_repair_service.py (550)
- test_data_integrity_validator_service.py (549)

**Strategy:** Analyze and split if they contain multiple distinct testing domains

---

## Implementation Approach

### Phase 1: High-Impact Splits (Week 1)
Priority order based on impact and complexity:
1. **test_security.py** (1135 → 3 files) - Clear domains, high reusability
2. **test_cli_commands.py** (1006 → 4 files) - Clear command groupings, high frequency of use
3. **test_git_hooks_integration.py** (1006 → TBD) - Requires analysis

### Phase 2: Major Repository Splits (Week 2)
4. **test_queries_errors.py** (938 → 2-3 files)
5. **test_milestone_repository_errors.py** (864 → 2 files)

### Phase 3: Large Service Splits (Week 3)
6-9. Tier 3 files (700-800 LOC range)

### Phase 4: Medium-Large Optimization (Week 4)
Tier 4-5 files (550-700 LOC range) based on complexity analysis

---

## Architectural Constraints & Solutions

### 1. **Import Dependencies**
- **Problem:** Circular imports if split naively
- **Solution:** Share common fixtures in `conftest.py` or separate fixture modules
- **Example:** Git hook tests → move mock factories to `tests/fixtures/git_mocks.py`

### 2. **Shared Test Data**
- **Problem:** Test factories, test data builders scattered across files
- **Solution:** Consolidate into dedicated `tests/fixtures/` or `tests/test_data/`
- **Status:** Already using `tests/unit/domain/test_data_factory.py`

### 3. **Fixture Scope**
- **Problem:** Session/module-level fixtures needed across split files
- **Solution:** Use `conftest.py` at appropriate directory levels
- **Hierarchy:**
  - `tests/conftest.py` - Global fixtures (cli_runner, isolated_roadmap, etc.)
  - `tests/integration/conftest.py` - Integration-specific fixtures
  - `tests/unit/conftest.py` - Unit test fixtures
  - `tests/test_cli/conftest.py` - CLI error test fixtures

### 4. **Test Class Organization**
- **Problem:** Multiple test classes in same file (docstring consistency)
- **Solution:** Each file should have 1-3 logically related test classes
- **Guideline:** 300-400 LOC per file = 2-3 medium test classes

### 5. **Module/Package Structure**
- **Principle:** Mirror the application structure
- **Example:**
  ```
  roadmap/core/services/                 ← app structure
    issue_service.py
    milestone_service.py

  tests/unit/core/services/              ← test structure mirrors app
    test_issue_service_*.py
    test_milestone_service_*.py
  ```

---

## File Naming Convention

### Current Pattern
`test_<module_name>.py` → Works for small files

### New Pattern for Splits
When a module exceeds 500 LOC, split as:
- `test_<module>_<domain1>.py`
- `test_<module>_<domain2>.py`
- `test_<module>_<domain3>.py`

**Examples:**
- `test_security.py` (1135) →
  - `test_security_paths.py` (path validation)
  - `test_security_file_ops.py` (file operations)
  - `test_security_logging.py` (logging & integration)

- `test_cli_commands.py` (1006) →
  - `test_cli_issue_commands.py` (issue commands)
  - `test_cli_milestone_commands.py` (milestone commands)
  - `test_cli_data_git_commands.py` (data/git commands)
  - `test_cli_root_commands.py` (root/init/status commands)

---

## Success Criteria

- [ ] All test files < 500 LOC (hard limit)
- [ ] Minimum 80% of test files < 400 LOC (preferred)
- [ ] All tests remain passing after splits
- [ ] No increase in test execution time
- [ ] Clear, logical file organization following domain structure
- [ ] Reduced cognitive load for future maintenance
- [ ] Clear commit history documenting splits

---

## Risk Assessment

### Low Risk
- **test_security.py** split - Clear functional domains
- **test_cli_commands.py** split - No complex dependencies between command groups
- Simple fixture reorganization

### Medium Risk
- Repository error tests - May have tight mocking dependencies
- Service tests - May have complex setup/teardown

### High Risk
- Integration tests - May depend on implicit ordering or shared state
- Mitigated by: Careful analysis before splitting, comprehensive test runs

---

## Timeline Estimate

- **Analysis Phase:** 1-2 days (detailed examination of Tier 2-3 files)
- **Implementation Phase 1 (Tier 1):** 2-3 days
- **Implementation Phase 2 (Tier 2):** 2-3 days
- **Implementation Phase 3 (Tier 3):** 2-3 days
- **Implementation Phase 4 (Tier 4-5):** 2-3 days
- **Validation & Cleanup:** 1 day

**Total Estimated Effort:** 10-15 days

---

## Metrics to Track

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Files > 500 LOC | 45 | 0 | ❌ |
| Files > 400 LOC | 78 | ~10% (12-15) | ❌ |
| Max file size | 1135 LOC | 400 LOC | ❌ |
| Avg file size | ~350 LOC | 300-350 LOC | ℹ️ |
| Test execution time | baseline | ±5% | TBD |

---

## Next Steps

1. **Approval:** Review this plan and identify any architectural concerns
2. **Detailed Analysis:** Examine Tier 2-3 files for precise split points
3. **Fixture Consolidation:** Organize conftest.py hierarchy before major splits
4. **Phase 1 Execution:** Begin with test_security.py and test_cli_commands.py
5. **Continuous Validation:** Run full test suite after each split
