# Phase 3b: Unified Error Handler Implementation

**Date:** December 8, 2025
**Status:** In Progress
**Objective:** Consolidate 70 error handlers into unified system with full instrumentation
**Target:** 100% error observability with context capture, logging, and recovery suggestions

---

## I. Phase 3b Deliverables: What's New

### 1.1 Universal Error Handler: `handle_cli_error()`

**Location:** `roadmap/adapters/cli/cli_error_handlers.py`

New function signature:
```python
def handle_cli_error(
    error: Exception,
    operation: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    fatal: bool = True,
    include_traceback: bool = True,
) -> None:
```

**What it does:**
1. Generates unique correlation ID (8-char UUID)
2. Extracts user/command context from Click
3. Classifies error (user/system/external)
4. Determines if error is recoverable
5. Suggests recovery action
6. Logs with full context to infrastructure logger
7. Displays user-friendly message with emoji
8. Shows recovery suggestion if applicable
9. Includes error ID for support tracking

**Example usage:**
```python
try:
    result = archive_project(project_name)
except Exception as e:
    handle_cli_error(
        error=e,
        operation="archive_project",
        entity_type="project",
        entity_id=project_name,
        context={"dry_run": dry_run, "force": force}
    )
    ctx.exit(1)
```

### 1.2 Error Handling Decorator: `@with_error_handling()`

**Location:** `roadmap/adapters/cli/cli_error_handlers.py`

New decorator signature:
```python
@with_error_handling(
    operation="archive_project",
    entity_type="project",
    fatal=True
)
def some_command(project_name: str, ctx: click.Context):
    # Auto-handled errors - decorator catches all exceptions
    pass
```

**What it does:**
1. Wraps function and catches all exceptions
2. Automatically extracts entity_id from kwargs
3. Calls `handle_cli_error()` with operation context
4. Exits with code 1 if fatal
5. Returns None and continues if not fatal

**Example usage:**
```python
@with_error_handling(operation="archive_project", entity_type="project", fatal=True)
def archive_project(project_name: str, ctx: click.Context, force: bool = False):
    # If this raises any exception, decorator will:
    # 1. Classify it
    # 2. Log with full context
    # 3. Display user message
    # 4. Exit with code 1
    core.projects.archive(project_name)
```

### 1.3 Helper Functions Added

**Correlation ID generation:**
```python
def generate_correlation_id() -> str:
    """Generate unique 8-char ID for error tracing."""
    return str(uuid.uuid4())[:8]
```

**User context extraction:**
```python
def extract_user_context() -> dict[str, Any]:
    """Extract user, command, and parameters from Click context."""
```

---

## II. Implementation Plan: 3 Phases

### Phase 3b-1: Refactor High-Priority Files (30% of error handlers)

**Target:** Archive and restore operations (highest complexity)

**Files (21 try-except blocks total):**
- `projects/archive.py` (9 blocks) → 4 consolidated handlers
- `projects/restore.py` (6 blocks) → 3 consolidated handlers
- `issues/archive.py` (8 blocks) → 3 consolidated handlers
- `issues/restore.py` (7 blocks) → 3 consolidated handlers
- `milestones/archive.py` (6 blocks) → 3 consolidated handlers

**Approach:** Convert Pattern A (silent catch) blocks to use `handle_cli_error()`

**Example refactor:**

Before:
```python
# projects/archive.py line 87-90
try:
    roadmap_dir = Path.cwd() / ".roadmap"
    archive_dir = roadmap_dir / "archive" / "projects"
except Exception:
    console.print(f"⚠️  Warning: Failed to mark in database: {e}", style="yellow")
```

After:
```python
try:
    roadmap_dir = Path.cwd() / ".roadmap"
    archive_dir = roadmap_dir / "archive" / "projects"
except Exception as e:
    handle_cli_error(
        error=e,
        operation="setup_archive_directory",
        entity_type="project",
        entity_id=project_name,
        context={"stage": "directory_setup"},
        fatal=False  # Warning, not fatal
    )
```

### Phase 3b-2: Refactor Medium-Priority Files (35% of error handlers)

**Target:** Mutation commands (create, update, delete, start)

**Files (18 try-except blocks):**
- `issues/close.py` (5 blocks) → 2 consolidated
- `issues/start.py` (3 blocks) → 1 consolidated
- `issues/deps.py` (2 blocks) → 1 consolidated
- `issues/progress.py` (2 blocks) → 1 consolidated
- `milestones/restore.py` (5 blocks) → 2 consolidated
- `milestones/kanban.py` (2 blocks) → 1 consolidated
- `services/project_status_service.py` (3 blocks) → 2 consolidated

**Approach:**
- Convert Pattern A to `handle_cli_error()`
- Convert Pattern B to `handle_cli_error()` with user context
- Convert Pattern C (nested retry) to `@retry` decorator with logging

**Example Pattern C refactor:**

Before:
```python
try:
    result = parse_issue_file(path)
except ValueError:
    try:
        result = parse_issue_legacy_format(path)
    except ValueError:
        # Silent failure, continue
        result = None
```

After:
```python
@retry(
    on=ValueError,
    max_attempts=2,
    backoff=0,
    log_attempts=True,
    operation="parse_issue"
)
def safe_parse_issue(path):
    try:
        return parse_issue_file(path)
    except ValueError:
        return parse_issue_legacy_format(path)

result = safe_parse_issue(path)
```

### Phase 3b-3: Refactor Low-Priority Files (35% of error handlers)

**Target:** List commands and git operations

**Files (22 try-except blocks):**
- `git/commands.py` (7 blocks) → 3 consolidated
- `issues/list.py` (2 blocks) → 1 consolidated
- `milestones/list.py` (2 blocks) → 1 consolidated
- `projects/list.py` (3 blocks) → 1 consolidated
- `git/status.py` (2 blocks) → 1 consolidated
- `issues/delete.py` (2 blocks) → 1 consolidated
- `issues/issue_status_helpers.py` (2 blocks) → 1 consolidated

**Approach:** Use `@with_error_handling()` decorator on command functions

**Example decorator usage:**

Before:
```python
@issues.command()
@click.argument("issue_id")
def close_command(issue_id: str, ctx: click.Context):
    try:
        # ... code ...
    except Exception as e:
        display_operation_error(...)
        ctx.exit(1)
```

After:
```python
@with_error_handling(operation="close_issue", entity_type="issue", fatal=True)
@issues.command()
@click.argument("issue_id")
def close_command(issue_id: str, ctx: click.Context):
    # No try-except needed - decorator handles all exceptions
    # ... code ...
```

---

## III. Implementation Checklist

### Phase 3b-1: Archive/Restore Commands
- [ ] Refactor `projects/archive.py`
  - [ ] Replace 9 try-except with `handle_cli_error()` calls
  - [ ] Add operation context to each
  - [ ] Test with archive operations
  - [ ] Verify logging includes correlation ID
- [ ] Refactor `projects/restore.py`
  - [ ] Replace 6 try-except blocks
  - [ ] Consistency check with archive
  - [ ] Test with restored projects
- [ ] Refactor `issues/archive.py`
  - [ ] Replace 8 try-except blocks
  - [ ] Handle Pattern C nested retries with logging
  - [ ] Test batch archive operations
- [ ] Refactor `issues/restore.py`
  - [ ] Replace 7 try-except blocks
  - [ ] Test with restored issues
- [ ] Refactor `milestones/archive.py`
  - [ ] Replace 6 try-except blocks
  - [ ] Ensure consistency with issues/projects

**Validation:** Run full test suite after each file
```bash
pytest tests/unit/adapters/cli/projects/test_archive.py -v
pytest tests/unit/adapters/cli/issues/test_archive.py -v
pytest tests/unit/adapters/cli/milestones/test_archive.py -v
```

### Phase 3b-2: Mutation Commands
- [ ] Refactor `issues/close.py`
  - [ ] Add `@with_error_handling()` to command
  - [ ] Remove internal try-except blocks
  - [ ] Test close operations
- [ ] Refactor `issues/start.py`
  - [ ] Use decorator for command
  - [ ] Handle git integration errors
  - [ ] Test branch creation flow
- [ ] Refactor git commands (`git/commands.py`)
  - [ ] Handle git-specific errors (branches, detached HEAD, etc.)
  - [ ] Provide recovery suggestions for common git issues
  - [ ] Test git operations
- [ ] Refactor `services/project_status_service.py`
  - [ ] Add operation context to status gathering
  - [ ] Log partial failures in multi-step operations
  - [ ] Test status aggregation

**Validation:**
```bash
pytest tests/unit/adapters/cli/issues/test_close.py -v
pytest tests/unit/adapters/cli/issues/test_start.py -v
pytest tests/unit/adapters/cli/git/ -v
```

### Phase 3b-3: List/View Commands
- [ ] Refactor `issues/list.py`
  - [ ] Add `@with_error_handling()` decorator
  - [ ] Handle file parse errors gracefully
  - [ ] Test list operations with corrupted data
- [ ] Refactor `milestones/list.py`
  - [ ] Same as issues/list.py
  - [ ] Test with archived milestones
- [ ] Refactor `projects/list.py`
  - [ ] Same refactoring pattern
  - [ ] Test with large project counts
- [ ] Refactor `git/status.py` and `git/commands.py`
  - [ ] Handle git not installed, repo not initialized, etc.
  - [ ] Provide clear recovery steps
  - [ ] Test on repo without .git

**Validation:**
```bash
pytest tests/unit/adapters/cli/issues/test_list.py -v
pytest tests/unit/adapters/cli/milestones/test_list.py -v
pytest tests/unit/adapters/cli/projects/test_list.py -v
pytest tests/unit/adapters/cli/git/ -v
```

---

## IV. Context Loss Remediation

| Previously Lost | Now Captured | How |
|---|---|---|
| **Operation Name** | ✅ Always | Passed to `handle_cli_error()` |
| **Entity Type/ID** | ✅ Always | Extracted from kwargs, passed as params |
| **User/Session** | ✅ Always | `extract_user_context()` from Click |
| **Timestamp** | ✅ Implicit | Via logger.error() call |
| **Error Classification** | ✅ Always | Via `classify_error()` function |
| **Stack Trace** | ✅ Always | Captured by `logger.error(exc_info=error)` |
| **Correlation ID** | ✅ Always | Generated and included in logs |
| **Retry Attempts** | ✅ Optional | Via `@retry` decorator with logging |
| **Recovery Suggestion** | ✅ Always | Via `suggest_recovery()` |
| **Batch Operation Status** | ⏳ Phase 3c | Track partial failures in multi-item ops |

---

## V. Testing Strategy

### Unit Tests for New Functions

**File:** `tests/unit/adapters/cli/test_error_handlers.py` (new)

```python
def test_generate_correlation_id():
    """Correlation ID should be 8 characters."""
    cid = generate_correlation_id()
    assert len(cid) == 8

def test_extract_user_context_no_click_context():
    """Should handle missing Click context gracefully."""
    context = extract_user_context()
    assert "user" in context
    assert context["user"] is None

def test_handle_cli_error_fatal():
    """Fatal error should be logged and displayed."""
    with patch('roadmap.adapters.cli.cli_error_handlers.logger') as mock_logger:
        with patch('roadmap.adapters.cli.cli_error_handlers.console.print') as mock_print:
            handle_cli_error(
                error=ValueError("test error"),
                operation="test_op",
                entity_type="test_entity",
                entity_id="123",
                fatal=True
            )
            assert mock_logger.error.called
            assert mock_print.called
            # Should print error message
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("failed" in str(call).lower() for call in print_calls)

def test_handle_cli_error_with_context():
    """Additional context should be included in logs."""
    with patch('roadmap.adapters.cli.cli_error_handlers.logger') as mock_logger:
        with patch('roadmap.adapters.cli.cli_error_handlers.console.print'):
            handle_cli_error(
                error=Exception("test"),
                operation="archive",
                context={"force": True, "dry_run": False}
            )
            assert mock_logger.error.called
            call_kwargs = mock_logger.error.call_args[1]
            assert call_kwargs.get("force") is True
            assert call_kwargs.get("dry_run") is False

def test_with_error_handling_decorator():
    """Decorator should catch exceptions and handle them."""
    @with_error_handling(operation="test_op", entity_type="test", fatal=True)
    def failing_function(entity_id: str):
        raise ValueError("intentional error")

    with patch('roadmap.adapters.cli.cli_error_handlers.handle_cli_error'):
        with pytest.raises(SystemExit) as exc_info:
            failing_function(entity_id="123")
        assert exc_info.value.code == 1

def test_with_error_handling_non_fatal():
    """Non-fatal decorator should not exit."""
    @with_error_handling(operation="test_op", fatal=False)
    def failing_function():
        raise ValueError("intentional error")

    with patch('roadmap.adapters.cli.cli_error_handlers.handle_cli_error'):
        result = failing_function()
        assert result is None
```

### Integration Tests

**File:** `tests/integration/test_error_handling_integration.py` (new)

```python
def test_archive_command_error_handling(cli_runner):
    """Archive command should handle errors with correlation ID."""
    result = cli_runner.invoke(projects, ["archive", "nonexistent"])
    assert result.exit_code != 0
    assert "Error ID:" in result.output  # Correlation ID shown

def test_create_issue_command_error_handling(cli_runner):
    """Create command should show recovery suggestions."""
    result = cli_runner.invoke(issues, ["create"])  # Missing required args
    assert result.exit_code != 0
    # Should show either validation error or recovery suggestion

def test_git_error_handling_no_repo(cli_runner, tmp_path):
    """Git commands should handle missing repo gracefully."""
    import os
    os.chdir(tmp_path)  # Not a git repo
    result = cli_runner.invoke(git, ["status"])
    assert result.exit_code != 0
    # Should suggest initializing repo or checking git setup
```

### CLI Testing

**Manual validation of error messages:**
```bash
# Test archive with nonexistent project
poetry run roadmap project archive nonexistent-project

# Should show:
# ❌ Archive project 'nonexistent-project' failed: Project not found
# 💡 Try again - this error may be temporary
# 📊 Error ID: a1b2c3d4

# Test with git error
poetry run roadmap git status  # In non-git directory

# Should show:
# ❌ Git status failed: not a git repository
# 💡 Check your input and try again
# 📊 Error ID: e5f6g7h8
```

---

## VI. Success Criteria

### Quantitative
- ✅ All 70 try-except blocks reviewed
- ✅ ~40 converted to `handle_cli_error()` calls
- ✅ ~20 converted to `@with_error_handling()` decorator
- ✅ ~10 converted to `@retry` decorator with logging
- ✅ 100% of errors classified
- ✅ 100% of errors logged with correlation ID
- ✅ 100% test suite passing (1,730 tests)
- ✅ Zero regressions

### Qualitative
- ✅ All errors logged to infrastructure system
- ✅ All errors include user/command context
- ✅ All errors show recovery suggestions
- ✅ Error messages consistent across commands
- ✅ Stack traces available for debugging
- ✅ Code duplication reduced by ~300 LOC
- ✅ Error handling fully testable

---

## VII. Rollback Plan

If issues arise during implementation:

1. **Per-file rollback:** Each file is independently testable
   ```bash
   git checkout HEAD -- roadmap/adapters/cli/projects/archive.py
   ```

2. **Full rollback:**
   ```bash
   git reset --hard HEAD~N  # Where N = number of commits in Phase 3b
   ```

3. **Partial rollback:** Keep successful refactors, revert problematic ones

---

## Summary

Phase 3b will consolidate 70 scattered error handlers into:
- 1 unified handler function (`handle_cli_error()`)
- 1 reusable decorator (`@with_error_handling()`)
- Full instrumentation (correlation IDs, stack traces, user context)
- Automatic recovery suggestions
- 100% observability in logs

**Target timeline:** 2-3 days
**Key deliverable:** All errors are now observable, attributable, and recoverable
