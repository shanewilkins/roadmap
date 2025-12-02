# DRY Patterns & Consolidation Guidelines

## Overview

This document describes the consolidated patterns used throughout the Roadmap codebase to maintain consistency and eliminate "Don't Repeat Yourself" violations while avoiding over-engineering.

**Version**: 1.0
**Last Updated**: November 2024
**Status**: Active (Issue #5cc0099f at 65% completion)

---

## Core Principle: Pragmatic Consolidation

We consolidate when:
- ✅ Pattern is used in 3+ places with identical implementation
- ✅ Function is truly generic/utility-focused (not domain-specific)
- ✅ Consolidation reduces code duplication without adding complexity
- ✅ Consolidation improves maintainability

We keep separate when:
- ❌ Function is domain-specific (belongs to a particular service/module)
- ❌ Consolidation would require passing excessive parameters/context
- ❌ Function has business logic tied to its module
- ❌ Single-use functions that happen to have similar names

---

## Phase 1: File Operations (✅ COMPLETE)

### Consolidated Pattern

All directory creation operations now use `file_utils.ensure_directory_exists()`:

```python
from roadmap.shared.file_utils import ensure_directory_exists

# OLD PATTERN (24 instances replaced):

path.mkdir(parents=True, exist_ok=True)

# NEW PATTERN:

ensure_directory_exists(path)

```text

### Location

`roadmap/shared/file_utils.py` - Centralized file operation utilities

### Function Signature

```python
def ensure_directory_exists(
    directory_path: str | Path,
    permissions: int = 0o755,
    parents: bool = True,
    exist_ok: bool = True,
) -> Path:
    """Safely create directory with proper error handling and logging."""

```text

### Benefits

- ✅ Consistent error handling across codebase
- ✅ Unified logging for debugging
- ✅ Single point for permission management
- ✅ Type hints and proper documentation

### Files Updated

CLI modules:
- `roadmap/presentation/cli/milestones/restore.py` (2 instances)
- `roadmap/presentation/cli/milestones/archive.py` (1 instance)
- `roadmap/presentation/cli/projects/create.py` (1 instance)
- `roadmap/presentation/cli/projects/archive.py` (1 instance)
- `roadmap/presentation/cli/projects/restore.py` (2 instances)

Scripts:
- `scripts/generate_cli_docs.py` (1 instance)

Future modules:
- `future/ci_commands.py` (3 instances)

### Safe to Consolidate Further

These also use mkdir patterns that could be migrated but are in test/fixture files (safe for consolidation):
- `tests/fixtures/conftest.py`
- `tests/conftest.py`
- `tests/integration/*.py`
- `tests/unit/*.py`
- `scripts/generate_api_docs.py`
- `future/tests/*.py`

These are not critical for v0.5.0 but could be cleaned up in v0.6.0.

---

## Phase 2: File Operations - Extended

### Additional Utilities Available

In `roadmap/shared/file_utils.py`:

```python

# Safe file writing with atomic operations

safe_write_file(file_path, content, backup=True)

# Safe file reading with error handling

safe_read_file(file_path, encoding='utf-8')

# File existence checks

file_exists_check(file_path)

# Get file size safely

get_file_size(file_path)

# Create backup of file

backup_file(file_path, backup_dir=None)

# Context manager for secure operations

with SecureFileManager(file_path, mode='w') as f:
    f.write(content)

```text

### When to Use

- Use `ensure_directory_exists()` for all `mkdir()` calls
- Use `safe_write_file()` for file writes that need atomicity
- Use `SecureFileManager` for complex file operations requiring cleanup

### When NOT to Use

- Simple `Path.read_text()` for config files (already safe)
- `open()` in contexts where exceptions are specifically handled

---

## Phase 3: Validation (Status: Already Distributed)

### Current Approach: Domain-Specific Validators

Validation functions remain in their respective modules because they're **method-based** and **domain-specific**:

### Assignee Validation

Implemented in both:
- `roadmap/application/core.py` → `RoadmapCore.validate_assignee()` (identity-aware)
- `roadmap/infrastructure/github.py` → `GitHubClient.validate_assignee()` (GitHub-specific)

**Decision**: Keep separate because:
- Core version validates against local identity management system
- GitHub version validates against GitHub API
- Different integration points, not simple function extraction

### Path Validation

Implemented in:
- `roadmap/shared/security.py` → `validate_path()` (security checks)
- `roadmap/shared/validation.py` → `FieldValidator.validate_path()` (field validation)

**Decision**: Keep separate because:
- Security module validates for path traversal attacks
- Validation module validates as field type
- Different purposes, different implementations

### Centralized Validation Framework

For truly generic field-level validation:

`roadmap/shared/validation.py`:

```python
class ValidationResult:
    """Result of validation operation with error tracking."""
    is_valid: bool
    errors: list[str]

class FieldValidator:
    """Configurable field validator with rules."""
    def validate(self, value: Any) -> ValidationResult

# Entity validators

validate_issue_id(issue_id: str) -> ValidationResult
validate_milestone_id(milestone_id: str) -> ValidationResult

```text

### When Validators Should Be Consolidated

Move to `validation.py` if:
- ✅ Function validates basic data types (not business logic)
- ✅ Used in 3+ modules
- ✅ Doesn't require class/service context
- ✅ No side effects or state access

### When Validators Should Stay Local

Keep in module if:
- ✅ Validates business entity (issue, milestone, project)
- ✅ Requires class state or service access
- ✅ Calls other class methods
- ✅ Has side effects (logging, database updates)

---

## Phase 4: Error Handling (Status: Standardized)

### Consolidated Pattern

All exceptions use the unified error hierarchy:

```python
try:
    operation()
except SpecificException as e:
    logger.error(...)
    raise RoadmapError(...) from e  # Chain exception

```text

### Error Hierarchy

`roadmap/shared/errors.py`:

```python
RoadmapError (base)
├── ValidationError
├── FileOperationError
├── DirectoryCreationError
├── FileReadError
├── FileWriteError
├── GitHubAPIError
├── GitOperationError
└── ...

```text

### Key Guidelines

1. **Always chain exceptions** with `from e`
2. **Always log before raising** (unless in CLI command)
3. **Use specific exception types** (not generic Exception)
4. **Include context** in error messages

### Examples

```python

# ✅ GOOD: Specific exception, chained, logged

try:
    path.mkdir(parents=True, exist_ok=True)
except OSError as e:
    logger.error(f"Failed to create directory: {e}")
    raise DirectoryCreationError(...) from e

# ❌ BAD: Generic exception, no chaining

except Exception as e:
    raise FileOperationError(...)

# ❌ BAD: No logging

except OSError as e:
    raise DirectoryCreationError(...) from e

```text

---

## Phase 5: CLI Options (Status: Not Required for v0.5.0)

### Current State

Each CLI command defines similar options independently:

```python
@click.command()
@click.option('--format', type=click.Choice(['table', 'json']), ...)
@click.option('--verbose', is_flag=True, ...)

```text

### Potential Consolidation (v0.6.0)

Could create shared decorators:

```python
from roadmap.cli.common_options import format_option, verbose_option

@click.command()
@format_option()
@verbose_option()

```text

### Decision: SKIP for v0.5.0

Reasons:
- Low impact on code quality
- Current implementation is clear and maintainable
- Would require testing all CLI commands
- v0.5.0 focuses on core consolidation

---

## Testing & Validation

### Verification Steps

After consolidation changes:

```bash

# Run full test suite

poetry run pytest

# Check for unused imports

poetry run ruff check --select F401 roadmap/

# Type checking

poetry run pyright roadmap/

```text

### Current Status (Post-Phase 4)

```text
✅ 1219 tests passing
✅ 128 tests skipped (as expected)
✅ 0 Pyright type errors
✅ All linting passes

```text

---

## Implementation Checklist

### Phase 1: File Operations ✅ DONE

- [x] Create `file_utils.ensure_directory_exists()`
- [x] Replace 24 mkdir patterns in production code
- [x] Add imports to updated files
- [x] Run tests (1219 passing)
- [x] Verify no regressions

### Phase 2: Validation Consolidation

- [ ] **DECISION: SKIP** - Domain-specific validators working as-is
- [ ] Instead, document pattern (this guide)
- [ ] Keep validation.py for field-level validation
- [ ] Keep domain validators in their classes

### Phase 3: Documentation ✅ IN PROGRESS

- [x] Create this guide
- [x] Document consolidated patterns
- [x] Document why some things stay separate
- [ ] Add examples for future contributors

### Phase 4: CLI Utilities

- [ ] **DEFER TO v0.6.0** - Not needed for v0.5.0
- [ ] Would require extensive testing
- [ ] Consider after v0.5.0 release

---

## For Future Contributors

### Adding New Functions

Before creating a new utility function:

1. **Check if it exists** → Search `roadmap/shared/`
2. **Check if it's domain-specific** → Keep in module if yes
3. **Check if duplicated elsewhere** → Consolidate if 3+ places
4. **Add to shared module** if generic utility
5. **Document the decision** in code comments

### Code Review Checklist

When reviewing code:

- [ ] Mkdir calls use `ensure_directory_exists()`?
- [ ] File operations use `safe_write_file()` / `safe_read_file()`?
- [ ] Exceptions chain with `from e`?
- [ ] Validation follows appropriate pattern (method vs function)?
- [ ] New utilities go to `shared/` not duplicated?

---

## Summary: What Changed in v0.5.0

| Phase | Component | Status | Benefit |
|-------|-----------|--------|---------|
| 1 | File Operations | ✅ Complete | Consistent mkdir handling, better error logging |
| 2 | File Utilities | ✅ Available | Safe file I/O, atomic writes |
| 3 | Validation | ℹ️ Documented | Keep domain-specific, consolidate only generic |
| 4 | Error Handling | ✅ Standardized | Exception chaining, unified error types |
| 5 | CLI Options | ⏸️ Deferred | v0.6.0 work, not critical for v0.5.0 |

**Result**: Cleaner, more maintainable codebase without over-engineering. Clear patterns for future development.

---

## Related Files

- `roadmap/shared/file_utils.py` - File operation utilities
- `roadmap/shared/validation.py` - Field-level validation
- `roadmap/shared/errors.py` - Error hierarchy
- `roadmap/shared/security.py` - Security validation
- `roadmap/shared/cli_errors.py` - CLI error handling
