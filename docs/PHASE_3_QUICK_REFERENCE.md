# Quick Reference: Phase 3 Completion

**When:** December 8, 2025
**What:** Phase 3a-3b (Error Handling Audit & Universal Handler)
**Status:** ✅ Complete and Ready for Phase 3b Execution

---

## What Was Built

### 1. Universal Error Handler: `handle_cli_error()`

Located in: `roadmap/adapters/cli/cli_error_handlers.py`

```python
def handle_cli_error(
    error: Exception,
    operation: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    fatal: bool = True,
) -> None:
```

**Does:**
- Generates 8-char correlation ID for tracing
- Classifies error (user/system/external)
- Extracts user/command context from Click
- Logs with full infrastructure system (with stack trace)
- Displays user-friendly message to console
- Shows recovery suggestion
- Includes error ID for support

**Use it when:** Already in a try-except block
```python
try:
    some_operation()
except Exception as e:
    handle_cli_error(e, operation="archive_project", entity_type="project", entity_id=name)
    ctx.exit(1)
```

### 2. Error Handling Decorator: `@with_error_handling()`

Located in: `roadmap/adapters/cli/cli_error_handlers.py`

```python
@with_error_handling(operation="archive_project", entity_type="project", fatal=True)
def some_command():
    # Exceptions automatically caught and handled
```

**Does:**
- Wraps function and catches all exceptions
- Automatically extracts entity_id from kwargs
- Calls `handle_cli_error()` with full context
- Exits with code 1 if fatal

**Use it when:** Decorating entire CLI command functions

---

## What Was Discovered (Phase 3a Audit)

### Error Handler Patterns Found
- **Pattern A (Silent Catch):** 35 instances - Catches, prints to console, no logging
- **Pattern B (Delegated):** 12 instances - Uses display_operation_error() + logging
- **Pattern C (Nested Retry):** 8 instances - Multiple try-except levels
- **Pattern D (Click Abort):** 5 instances - Validation failures with Abort

### Error Types
- File operations: 28
- Validation: 15
- Git operations: 8
- Storage/database: 12
- Network/API: 6
- User input: 10
- Internal/unexpected: 28

### Context Loss (Now Fixed)
| Lost | Impact | Solution |
|------|--------|----------|
| User/session | No audit trail | `extract_user_context()` |
| Stack trace | Debugging impossible | `logger.error(exc_info=e)` |
| Correlation ID | Can't trace through logs | `generate_correlation_id()` |
| Operation name | Can't identify which command failed | Required parameter to handler |
| Error classification | Can't determine severity | `classify_error()` |

---

## Documents Created

### 1. Phase 3A Audit: `docs/PHASE_3A_ERROR_HANDLING_AUDIT.md`
- Complete error flow analysis
- Pattern catalog with examples
- File-by-file inventory of 70 handlers
- Context loss mapping
- Consolidation opportunities

### 2. Phase 3B Guide: `docs/PHASE_3B_IMPLEMENTATION_GUIDE.md`
- 3-phase refactoring plan
- 60+ specific files/blocks to refactor
- Before/after code examples for each pattern
- Testing strategy (unit/integration/manual)
- Success criteria and rollback plan

### 3. Phase 3 Status: `docs/PHASE_3_STATUS_REPORT.md`
- Session summary
- Architecture decisions
- Risk analysis
- v1.0.0 progress (85%+)

---

## Phase 3b Refactoring Plan

### Phase 3b-1: Archive/Restore (HIGH PRIORITY)
**21 error handler blocks across 5 files:**
- projects/archive.py: 9 blocks → 4 handlers
- projects/restore.py: 6 blocks → 3 handlers
- issues/archive.py: 8 blocks → 3 handlers
- issues/restore.py: 7 blocks → 3 handlers
- milestones/archive.py: 6 blocks → 3 handlers

**Time:** 6-8 hours

### Phase 3b-2: Mutation Commands (MEDIUM PRIORITY)
**18 error handler blocks across 6 files:**
- issues/close.py, issues/start.py, issues/deps.py
- git/commands.py
- services/project_status_service.py
- milestones/restore.py

**Time:** 6-8 hours

### Phase 3b-3: List/View Commands (LOW PRIORITY)
**22 error handler blocks across 7 files:**
- issues/list.py, milestones/list.py, projects/list.py
- git/status.py, git/status_display.py
- issues/delete.py, issue_status_helpers.py

**Time:** 6-8 hours

**Total: ~20-24 hours (2-3 days)**

---

## How to Execute Phase 3b

### 1. Start with Phase 3b-1 (High Priority)

```bash
# Read the implementation guide
vim docs/PHASE_3B_IMPLEMENTATION_GUIDE.md
# Look for "Phase 3b-1" section for specific examples

# Edit first file
vim roadmap/adapters/cli/projects/archive.py

# Find: All try-except blocks (9 total)
# Replace: with handle_cli_error() calls
# Example: look for pattern A in the guide

# Run tests
pytest tests/unit/adapters/cli/projects/test_archive.py -v

# Commit
git commit -m "Phase 3b-1a: Refactor projects/archive.py error handlers"
```

### 2. Follow the Pattern

For each file:
1. Open the file in editor
2. Find try-except blocks (use grep: `grep -n "try:\|except" file.py`)
3. For each block, check if it matches Pattern A, B, C, or D
4. Use the before/after examples in the guide
5. Replace with appropriate handler/decorator
6. Run relevant tests
7. Commit with descriptive message

### 3. Validate After Each File

```bash
# Quick test of affected module
pytest tests/unit/adapters/cli/projects/ -x -q

# Full suite periodically
pytest -x -q  # Should always show: 1730 passed
```

### 4. Track Progress

Document your progress in Phase 3b sub-phases:
- Phase 3b-1: Archive/restore (21 blocks)
- Phase 3b-2: Mutations (18 blocks)
- Phase 3b-3: Lists (22 blocks)

---

## Code Examples from Implementation Guide

### Pattern A: Silent Catch → Universal Handler

**Before:**
```python
try:
    data = load_data()
except Exception as e:
    console.print(f"Error: {e}", style="red")
    ctx.exit(1)
```

**After:**
```python
try:
    data = load_data()
except Exception as e:
    handle_cli_error(
        error=e,
        operation="load_data",
        entity_type="data",
        context={"stage": "initialization"}
    )
    ctx.exit(1)
```

### Pattern B: Delegated → Enhanced Handler

**Before:**
```python
except Exception as e:
    display_operation_error("archive", "project", project_name, str(e))
    ctx.exit(1)
```

**After:**
```python
except Exception as e:
    handle_cli_error(
        error=e,
        operation="archive_project",
        entity_type="project",
        entity_id=project_name,
        context={"force": force, "dry_run": dry_run}
    )
    ctx.exit(1)
```

### Pattern D: Click Abort → Decorator

**Before:**
```python
@issues.command()
@click.argument("issue_id")
def close_command(issue_id: str):
    try:
        core.issues.close(issue_id)
    except Exception as e:
        display_operation_error(...)
        ctx.exit(1)
```

**After:**
```python
@with_error_handling(operation="close_issue", entity_type="issue", fatal=True)
@issues.command()
@click.argument("issue_id")
def close_command(issue_id: str):
    # No try-except needed - decorator handles all exceptions
    core.issues.close(issue_id)
```

---

## Testing During Refactoring

### Unit Tests (Run After Each File)
```bash
# Example for projects/archive.py
pytest tests/unit/adapters/cli/projects/test_archive.py -v

# Example for issues/close.py
pytest tests/unit/adapters/cli/issues/test_close.py -v

# Check all CLI tests
pytest tests/unit/adapters/cli/ -x -q
```

### Integration Tests
```bash
# Test the actual command behavior
pytest tests/integration/test_cli_commands.py -v -k "archive or close"
```

### Manual Validation
```bash
# Test error message display
poetry run roadmap project archive nonexistent

# Should show:
# ❌ Archive project 'nonexistent' failed: <error>
# 💡 Recovery suggestion here
# 📊 Error ID: a1b2c3d4
```

---

## Success Metrics

When Phase 3b is complete, the system should have:

✅ **70 handlers → 20-30 consolidated** (reduction of ~60%)
✅ **100% classified errors** (all errors have category/severity)
✅ **100% correlation ID injection** (all errors traceable)
✅ **100% stack trace capture** (all errors logged fully)
✅ **100% test suite passing** (1730 tests, 0 regressions)
✅ **100% user context capture** (who, what command, which entity)
✅ **Consistent error messages** across all CLI commands
✅ **Recovery suggestions** shown to users
✅ **Code reduction** of ~300 LOC (less duplication)

---

## Rollback Plan

If something goes wrong:

### Per-File Rollback
```bash
# Rollback single file to last working version
git checkout HEAD -- roadmap/adapters/cli/projects/archive.py
```

### Full Phase 3b Rollback
```bash
# See how many commits were Phase 3b
git log --oneline | head -20

# Rollback all Phase 3b work
git reset --hard <commit-before-phase-3b>
```

### Partial Rollback
- Keep successful refactors
- Revert problematic ones
- Continue with other files

---

## v1.0.0 Timeline

**Current Status:** 85%+ toward completion

- **Phase 1:** ✅ Complete (Output formatting)
- **Phase 2:** ✅ Complete (Test infrastructure cleanup)
- **Phase 3a:** ✅ Complete (Error audit)
- **Phase 3b:** 🔄 Ready to Execute (2-3 days)
- **Phase 3c:** ⏳ Future (OTEL integration, 1-2 weeks)
- **Release prep:** ⏳ Final polish (1 week)

**ETA to v1.0.0:** ~3-4 weeks (after Phase 3 complete)

---

## Quick Start Now

1. **Read the implementation guide:**
   ```bash
   less docs/PHASE_3B_IMPLEMENTATION_GUIDE.md
   ```

2. **Find Phase 3b-1 section** for high-priority files

3. **Start with `projects/archive.py`:**
   - 9 try-except blocks
   - Mix of Pattern A and B
   - Good example for learning
   - Has tests to validate against

4. **Use before/after examples** from the guide

5. **Run tests frequently** to catch regressions early

6. **Commit after each file** with descriptive messages

---

## Contact & Questions

All documentation is in `/docs/`:
- `PHASE_3A_ERROR_HANDLING_AUDIT.md` - Full audit details
- `PHASE_3B_IMPLEMENTATION_GUIDE.md` - Detailed refactoring plan
- `PHASE_3_STATUS_REPORT.md` - Architecture & progress

All code is in `roadmap/adapters/cli/`:
- `cli_error_handlers.py` - The new universal handler system
- Various command files - Ready for refactoring

Test suite: `pytest` (1730 tests, all passing)

---

**You've got this! Phase 3b is mechanical work following a clear pattern. Follow the guide and run tests frequently.** 🚀
