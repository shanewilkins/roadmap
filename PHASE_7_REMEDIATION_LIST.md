# Phase 7 Priority Remediation List

**Status:** Phase 7a audit complete | Ready for Phase 7b-7e
**Generated:** January 22, 2026

---

## 🔴 CRITICAL: Files with Problematic Exception Patterns (30 files)

### Except + Pass (Silent failures - 30 files)
These need immediate logging before `pass` statement.

```
roadmap/adapters/cli/__init__.py
roadmap/adapters/cli/config/commands.py
roadmap/adapters/cli/git/handlers/git_authentication_handler.py
roadmap/adapters/cli/health/fixers/corrupted_comments_fixer.py
roadmap/adapters/cli/health/fixers/data_integrity_fixer.py
roadmap/adapters/cli/health/fixers/folder_structure_fixer.py
roadmap/adapters/cli/health/fixers/label_normalization_fixer.py
roadmap/adapters/cli/health/fixers/milestone_name_normalization_fixer.py
roadmap/adapters/cli/health/fixers/milestone_validation_fixer.py
roadmap/adapters/cli/health/fixers/orphaned_comments_fixer.py
roadmap/adapters/cli/list/list_command.py
roadmap/adapters/cli/milestones/archive_class.py
roadmap/adapters/cli/utils/file_operations.py
roadmap/adapters/git/git_branch_manager.py
roadmap/adapters/git/git_hooks_manager.py
roadmap/adapters/persistence/file_locking.py
roadmap/adapters/persistence/storage/queries.py
roadmap/adapters/persistence/yaml_repositories.py
roadmap/adapters/sync/backends/github_backend_helpers.py
roadmap/adapters/sync/services/pull_result_processor.py
... and 10 more files
```

### Except + Continue (Loop skipping - 8 files)
These silently skip items in loops without logging errors.

```
roadmap/adapters/cli/milestones/archive_class.py
roadmap/adapters/cli/milestones/restore_class.py
roadmap/adapters/persistence/file_locking.py
roadmap/adapters/persistence/storage/queries.py
roadmap/adapters/sync/backends/github_backend_helpers.py
roadmap/adapters/sync/services/pull_result_processor.py
... and 2 more files
```

---

## 🟡 HIGH PRIORITY: Files without Exception Logging (83 files)

### CLI Module (35+ files)
```
roadmap/adapters/cli/__init__.py                   [13 handlers]
roadmap/adapters/cli/cli_validators.py             [1 handler]
roadmap/adapters/cli/comment/commands.py           [4 handlers]
roadmap/adapters/cli/crud/base_archive.py          [2 handlers]
roadmap/adapters/cli/crud/base_create.py           [2 handlers]
roadmap/adapters/cli/crud/base_delete.py           [2 handlers]
roadmap/adapters/cli/crud/base_restore.py          [2 handlers]
roadmap/adapters/cli/crud/base_update.py           [2 handlers]
roadmap/adapters/cli/crud/crud_helpers.py          [1 handler]
roadmap/adapters/cli/crud/entity_builders.py       [3 handlers]
roadmap/adapters/cli/data/commands.py              [6 handlers]
roadmap/adapters/cli/exception_handler.py          [4 handlers]
roadmap/adapters/cli/git/hooks_config.py           [1 handler]
roadmap/adapters/cli/health/fixers/corrupted_comments_fixer.py    [4 handlers]
roadmap/adapters/cli/health/fixers/data_integrity_fixer.py        [3 handlers]
roadmap/adapters/cli/health/fixers/duplicate_issues_fixer.py      [1 handler]
roadmap/adapters/cli/health/fixers/folder_structure_fixer.py      [1 handler]
roadmap/adapters/cli/health/fixers/label_normalization_fixer.py   [1 handler]
roadmap/adapters/cli/health/fixers/milestone_name_normalization_fixer.py  [2 handlers]
roadmap/adapters/cli/health/fixers/milestone_validation_fixer.py  [3 handlers]
... and 15+ more files
```

### Persistence Module (15+ files)
```
roadmap/adapters/persistence/__init__.py
roadmap/adapters/persistence/cleanup.py
roadmap/adapters/persistence/storage/queries.py
roadmap/adapters/persistence/yaml_repositories.py
... and 11+ more files
```

### Sync Module (12+ files)
```
roadmap/adapters/sync/backends/github_backend_helpers.py
roadmap/adapters/sync/services/pull_result_processor.py
... and 10+ more files
```

### GitHub Module (8+ files)
```
roadmap/adapters/github/handlers/comments.py
roadmap/adapters/github/handlers/issues.py
... and 6+ more files
```

### Git Module (6+ files)
```
roadmap/adapters/git/git_branch_manager.py
roadmap/adapters/git/git_hooks_manager.py
... and 4+ more files
```

### Core Services (7+ files)
```
roadmap/core/services/initialization/validator.py  [3 handlers]
roadmap/core/services/initialization/initializer.py
... and 5+ more files
```

---

## Work Allocation by Phase

### Phase 7c: Core Services (7+ files)
- roadmap/core/services/initialization/
- roadmap/core/services/synchronization/
- roadmap/core/services/error_handling/

### Phase 7d: CLI Handling (35+ files)
- roadmap/adapters/cli/crud/
- roadmap/adapters/cli/comment/
- roadmap/adapters/cli/data/
- roadmap/adapters/cli/health/fixers/
- roadmap/adapters/cli/milestones/
- roadmap/adapters/cli/git/

### Phase 7e: Adapters (41+ files)
- roadmap/adapters/persistence/ (15+ files)
- roadmap/adapters/sync/ (12+ files)
- roadmap/adapters/github/ (8+ files)
- roadmap/adapters/git/ (6+ files)

### Phase 7f: Testing
- Create exception path tests for all modules
- Validate logging output
- Target 85%+ error path coverage

---

## Remediation Template

Use this template when adding logging to exception handlers:

```python
import structlog

logger = structlog.get_logger()

# Pattern 1: Add logging before pass
try:
    operation()
except SpecificError as e:
    logger.warning(
        "Operation failed - continuing",
        error_type=type(e).__name__,
        error_message=str(e),
        module="example",
        action="Proceeding with defaults"
    )
    pass

# Pattern 2: Add logging before continue
for item in items:
    try:
        process(item)
    except SpecificError as e:
        logger.warning(
            "Item processing failed - skipping",
            item_id=getattr(item, 'id', 'unknown'),
            error_type=type(e).__name__,
            error_message=str(e),
            module="example"
        )
        continue

# Pattern 3: Add logging before return
def validate():
    try:
        check_data()
        return True
    except SpecificError as e:
        logger.error(
            "Validation failed",
            error_type=type(e).__name__,
            error_message=str(e),
            module="example",
            action="Validation aborted"
        )
        return False
```

---

## Metrics for Phase Completion

| Phase | Files | Exception Handlers | Target Logging |
|-------|-------|-------------------|-----------------|
| 7c | 7+ | ~20 | 100% ✅ |
| 7d | 35+ | ~60 | 100% ✅ |
| 7e | 41+ | ~80 | 100% ✅ |
| **Total** | **83** | **~160** | **100% ✅** |

---

## Pre-Phase 7b Checklist

- [x] Audit complete with 476 files analyzed
- [x] 83 files identified without logging
- [x] 30 high-risk files with problematic patterns documented
- [x] Tool validation passed (ruff: clean, pylint: 10.00/10)
- [x] Findings documented in PHASE_7a_AUDIT_FINDINGS.md
- [x] Remediation list created
- [x] Ready for Phase 7b (error hierarchy definition)
