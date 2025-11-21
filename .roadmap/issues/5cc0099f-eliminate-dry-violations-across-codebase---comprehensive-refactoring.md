---
id: 5cc0099f
title: Eliminate DRY violations across codebase - comprehensive refactoring
priority: high
status: in-progress
issue_type: feature
milestone: v.0.5.0
labels: []
github_issue: null
created: '2025-11-16T21:10:47.034739+00:00'
updated: '2025-11-21T12:14:00.000000+00:00'
assignee: shanewilkins
estimated_hours: 16.0
due_date: null
depends_on: []
blocks: []
actual_start_date: '2025-11-16T15:13:48.397561+00:00'
actual_end_date: null
progress_percentage: 65.0
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
---

# Eliminate DRY violations across codebase - comprehensive refactoring

## Description

Following the successful implementation of the unified datetime parser (#6f111c60), this issue addresses comprehensive elimination of DRY violations across the roadmap codebase. Through systematic analysis, 6 major categories of code duplication have been identified with 75+ instances of duplicate patterns.

**Context**: Building on the datetime parser refactoring that eliminated 150+ lines of duplicate code across 10 modules, we now expand this approach to other major duplication patterns throughout the system.

## Analysis Summary

### 🔍 **Major DRY Violations Identified**

1. **File Operations & Path Management** (🔴 HIGH PRIORITY)
   - **Pattern**: Repeated file/directory creation and validation logic
   - **Occurrences**: ~18+ instances across multiple modules
   - **Impact**: Code scattered across 9+ modules

2. **Error Handling Patterns** (🔴 HIGH PRIORITY)
   - **Pattern**: Repetitive try/except blocks with similar error handling
   - **Occurrences**: ~25+ instances
   - **Impact**: Inconsistent error reporting and handling

3. **Validation Logic** (🟡 MEDIUM PRIORITY)
   - **Pattern**: Similar validation methods across modules
   - **Occurrences**: ~13 `validate_*` functions with overlapping logic
   - **Impact**: Duplicate assignee/path validation

4. **CLI Options & Commands** (🟡 MEDIUM PRIORITY)
   - **Pattern**: Repeated Click decorators and option patterns
   - **Occurrences**: ~20+ similar option patterns
   - **Impact**: Inconsistent CLI interface patterns

5. **Logging & Progress Reporting** (🟡 MEDIUM PRIORITY)
   - **Pattern**: Similar logging and progress callback patterns
   - **Occurrences**: ~15+ instances
   - **Impact**: Inconsistent progress reporting

6. **JSON/YAML File Operations** (🟠 MEDIUM-LOW PRIORITY)
   - **Pattern**: Repeated file read/write with error handling
   - **Occurrences**: ~12+ instances
   - **Impact**: Inconsistent file operation patterns

## Implementation Phases

### **Phase 1: File Operations Utility** (Immediate - High Impact)

**Target**: Create unified file operations utility similar to datetime parser

- Create `roadmap/file_utils.py` - Centralized file/directory operations
- Eliminate ~18 duplicate mkdir/exists patterns
- Standardize error handling for file operations
- **Estimated**: 4 hours

### **Phase 2: Error Handling Framework** (High Impact)

**Target**: Create standardized error handling patterns

- Create `roadmap/error_utils.py` - Common error handling decorators/patterns
- Unified exception handling for batch operations
- Consistent error reporting across modules
- **Estimated**: 4 hours

### **Phase 3: Validation Framework** (Medium Impact)

**Target**: Consolidate validation logic

- Create `roadmap/validation_utils.py` - Unified validation methods
- Eliminate duplicate assignee/path validation
- Standardize validation patterns
- **Estimated**: 4 hours

### **Phase 4: CLI Utilities** (Medium Impact)

**Target**: Create common CLI patterns

- Create `roadmap/cli/common.py` - Shared decorators and options
- Eliminate duplicate Click option patterns
- Standardize CLI error handling
- **Estimated**: 4 hours

## Expected Outcomes

- **Code Reduction**: Eliminate 200+ lines of duplicate code
- **Maintainability**: Single source of truth for common operations
- **Consistency**: Standardized patterns across entire codebase
- **Test Coverage**: Maintain 100% test coverage (1337/1337 tests passing)
- **Performance**: No behavioral regressions

## Acceptance Criteria

### Phase 1: File Operations Utility

- [ ] Create `roadmap/file_utils.py` with unified file operations
- [ ] Replace all duplicate `file_path.parent.mkdir(parents=True, exist_ok=True)` patterns
- [ ] Replace all duplicate file existence checks
- [ ] Update affected modules: parser.py, identity.py, security.py, persistence.py, timezone_migration.py, file_locking.py, repository_scanner.py, models.py
- [ ] All tests pass (1337/1337)
- [ ] No behavioral regressions

### Phase 2: Error Handling Framework

- [ ] Create `roadmap/error_utils.py` with standardized error handling
- [ ] Replace duplicate try/except patterns in bulk_operations.py, performance_sync.py, enhanced_github_integration.py
- [ ] Implement consistent error reporting framework
- [ ] All tests pass (1337/1337)
- [ ] No behavioral regressions

### Phase 3: Validation Framework

- [ ] Create `roadmap/validation_utils.py` with unified validation methods
- [ ] Consolidate duplicate validation functions from core.py, github_client.py, security.py
- [ ] Eliminate overlapping validation logic
- [ ] All tests pass (1337/1337)
- [ ] No behavioral regressions

### Phase 4: CLI Utilities

- [ ] Create `roadmap/cli/common.py` with shared CLI patterns
- [ ] Replace duplicate Click option decorators across CLI modules
- [ ] Standardize CLI error handling and progress reporting
- [ ] All tests pass (1337/1337)
- [ ] No behavioral regressions

### Overall Completion

- [ ] All 4 phases completed
- [ ] Comprehensive test suite validates refactoring (1337/1337 tests passing)
- [ ] Documentation updated to reflect new unified utilities
- [ ] Code review completed
- [ ] Performance validation confirms no regressions
