# Quick Reference: 5-Phase Error Handling Plan

## Overview
Comprehensive plan to improve error logging in `archive`, `cleanup`, `health`, and `init` commands through 5 phases over 6-10 hours.

---

## Phase 1: Archive Command (2-3 hours) ⭐ START HERE

### Current Problems
- Line 98: Silent parse errors (no logging)
- Line 186: DB failures logged as warnings, not errors
- Lines 156-186: Batch operations don't track per-item failures
- Missing: Partial failure detection (file moved but DB update failed)

### Key Changes
```python
# BEFORE: One generic success count
archived_count = 0
for issue in issues_to_archive:
    # ... archive ...
    archived_count += 1

# AFTER: Track successes/failures/partial
archive_results = {
    "succeeded": [],
    "failed": [],
    "partial_failures": []  # File moved but DB failed
}

for issue in issues_to_archive:
    try:
        logger.debug("archiving_issue", issue_id=issue.id)
        # ... archive file ...
        logger.info("issue_file_archived", issue_id=issue.id)

        try:
            core.db.mark_issue_archived(issue.id)
            archive_results["succeeded"].append(issue.id)
        except Exception as e:
            logger.error("database_marking_failed",  # Not warning!
                issue_id=issue.id, file_moved=True)
            archive_results["partial_failures"].append(issue.id)
    except OSError as e:
        logger.error("file_operation_failed", issue_id=issue.id)
        archive_results["failed"].append(issue.id)

logger.info("batch_archive_completed",
    total=len(issues_to_archive),
    succeeded=len(archive_results["succeeded"]),
    partial_failures=len(archive_results["partial_failures"]),
    failed=len(archive_results["failed"]))
```

### Files to Modify
- `roadmap/presentation/cli/issues/archive.py` (lines 98, 156-186, 256)

### Test After
```bash
poetry run roadmap issue archive --all-done --dry-run
poetry run roadmap issue archive --all-done --force
# Check logs: tail ~/.roadmap/logs/roadmap.log
```

---

## Phase 2: Cleanup Command (1-2 hours)

### Current Problems
- Type conversions happen without logging (lines 55-103)
- Generic exception handling (line 107: `except Exception:`)
- No logging of what files were processed

### Key Changes
```python
# BEFORE: Silent conversions
if isinstance(commit, str):
    fixed_commits.append({"hash": commit})
    needs_fix = True

# AFTER: Log each conversion
for i, commit in enumerate(frontmatter["git_commits"]):
    if isinstance(commit, str):
        logger.debug("converting_git_commit",
            file_path=str(file_path),
            index=i,
            from_type="str",
            to_type="dict",
            commit_hash=commit[:8])
        fixed_commits.append({"hash": commit})
```

### Files to Modify
- `roadmap/presentation/cli/cleanup.py` (fix_malformed_files function)

---

## Phase 3: Health Command (1-2 hours)

### Current Problems
- Discoveries found but not logged (lines 78-98, 126-137)
- Generic exception handling (line 109: `except Exception:`)
- No severity classification

### Key Changes
```python
# BEFORE: Silent discovery
if issue and issue.milestone:
    potential_issues["misplaced"].append({...})

# AFTER: Log discovery with severity
if issue and issue.milestone:
    logger.warning("misplaced_issue_discovered",
        issue_id=issue.id,
        current_location=str(issue_file),
        expected_location=str(milestone_folder / issue_file.name),
        severity="high")
    potential_issues["misplaced"].append({...})
```

### Files to Modify
- `roadmap/application/health.py` (scan functions)

---

## Phase 4: Init Command (1-2 hours)

### Current Problems
- Lock conflicts not logged with holder info (line 151)
- Multi-step workflow has no checkpoints
- Rollback failures silently ignored

### Key Changes
```python
# BEFORE: No lock info
if not lock.acquire():
    console.print("❌ Initialization already in progress...")

# AFTER: Log lock holder details
lock = InitializationLock(lock_path)
if not lock.acquire():
    lock_info = lock.get_lock_info()
    logger.error("init_lock_conflict",
        lock_holder_pid=lock_info.get("pid"),
        lock_acquired_at=lock_info.get("timestamp"),
        suggested_action="wait_or_force")
```

### Files to Modify
- `roadmap/cli/core.py` (init command)
- `roadmap/cli/init_workflow.py` (InitializationLock, InitializationWorkflow)

---

## Phase 5: Infrastructure (1-2 hours)

### Components
1. **Specialized error loggers** (per command)
2. **Correlation IDs** (trace multi-step operations)
3. **BatchOperationTracker** (utility for Phase 1-2)

### New Files to Create
- `roadmap/presentation/cli/command_error_logging.py` - Command-specific loggers
- `roadmap/presentation/cli/batch_operations.py` - BatchOperationTracker class

---

## Implementation Checklist

### Phase 1 Checklist
- [ ] Add batch tracking dictionary
- [ ] Replace `except Exception:` on line 98 with specific handling
- [ ] Add per-item logging in archive loop
- [ ] Log database errors as ERROR not WARNING
- [ ] Log partial failure scenario explicitly
- [ ] Run tests: `poetry run pytest tests/ -xvs -k archive`
- [ ] Manual test: `roadmap issue archive --all-done --dry-run`

### Phase 2 Checklist
- [ ] Add conversion logging to fix_malformed_files
- [ ] Replace generic `except Exception:` with specific types
- [ ] Add YAML error logging
- [ ] Add file write operation logging
- [ ] Run tests: `poetry run pytest tests/ -xvs -k cleanup`

### Phase 3 Checklist
- [ ] Add per-discovery logging to scan functions
- [ ] Add severity classification (HIGH/MEDIUM/LOW)
- [ ] Replace generic exception handling
- [ ] Add scan completion logging with statistics
- [ ] Run tests: `poetry run pytest tests/ -xvs -k health`

### Phase 4 Checklist
- [ ] Enhance InitializationLock to track holder info
- [ ] Add step checkpoint logging in InitializationWorkflow
- [ ] Add rollback operation logging
- [ ] Log PermissionError and OSError with error codes
- [ ] Run tests: `poetry run pytest tests/ -xvs -k init`

### Phase 5 Checklist
- [ ] Create command_error_logging.py with specialized loggers
- [ ] Create batch_operations.py with BatchOperationTracker
- [ ] Add correlation ID decorator to logging_decorators.py
- [ ] Run full test suite: `poetry run pytest`

---

## Testing Strategy

For each phase, verify:
1. **Happy path**: Operation succeeds, logs contain SUCCESS entries
2. **Error path**: Operation fails, logs contain ERROR entries with details
3. **Batch path**: Multiple items, logs show per-item progress
4. **Dry-run**: Shows what would happen without making changes

### Test Command
```bash
# Run specific command tests
poetry run pytest tests/ -xvs -k <command_name>

# Run all tests
poetry run pytest tests/ -q

# Check log output
tail -f ~/.roadmap/logs/roadmap.log
```

---

## Expected Outcome

### Before Implementation
```
$ roadmap issue archive --all-done
❌ Failed to archive issue
```
→ No context, hard to debug

### After Implementation
```
$ roadmap issue archive --all-done --force
✅ Archived 12 issues
⚠️  1 issue had DB error (see logs)

$ tail ~/.roadmap/logs/roadmap.log
[INFO] batch_archive_starting, count=13, issues=[...]
[INFO] issue_archived, issue_id=8a00a17e, file_path=.roadmap/archive/issues/v.0.6.0/...
[ERROR] database_marking_failed, issue_id=8b11a18f, file_moved=true
[INFO] batch_archive_completed, succeeded=12, partial_failures=1, failed=0
```
→ Complete visibility into what happened and why

---

## Priority vs Effort

| Phase | Priority | Effort | Impact | Risk |
|-------|----------|--------|--------|------|
| 1 | ⭐⭐⭐ | 2-3h | Highest | Low |
| 2 | ⭐⭐⭐ | 1-2h | High | Low |
| 3 | ⭐⭐ | 1-2h | Medium | Low |
| 4 | ⭐⭐ | 1-2h | Medium | Medium |
| 5 | ⭐ | 1-2h | Medium | Low |

**Recommended Start**: Phase 1 (highest impact, lowest risk)

---

## Key Principles

### ✅ DO
- Log before AND after operations
- Use specific exception types (not `except Exception:`)
- Include context (file paths, IDs, operation names)
- Log failures at ERROR level, not WARNING
- Track partial failures separately

### ❌ DON'T
- Catch all exceptions generically
- Log only on failure (log attempts too)
- Lose context by catching and re-raising
- Treat database failures as warnings
- Assume operations succeed silently

---

## References

See full documentation:
- `docs/ERROR_LOGGING_STRATEGY.md` - Comprehensive framework
- `docs/ERROR_LOGGING_DISCUSSION.md` - Principles and patterns
- `docs/ERROR_HANDLING_IMPLEMENTATION_PLAN.md` - Detailed implementation guide

---

## Next Steps

1. **Review** this quick reference
2. **Start Phase 1** with archive command
3. **Run tests** after each change
4. **Commit** working changes regularly
5. **Move to Phase 2** when Phase 1 is complete
