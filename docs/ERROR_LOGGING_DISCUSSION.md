# Error Logging Discussion Summary

## What We Learned Today

### Critical Failure Patterns Discovered

Through expanding `archive`, `health`, `cleanup`, and `init` commands, we identified several recurring failure patterns:

1. **Silent Failures** - Operations fail without logging (archive file search, health parsing)
2. **Lost Context** - Exceptions caught but details discarded (cleanup type conversions)
3. **Checkpoint Gaps** - Major operations have no intermediate state logging
4. **Partial Failures** - Batch operations don't distinguish between failed items and successes
5. **Recovery Info Missing** - Error messages don't suggest how to recover

### Archive Command Specific Issues

**The Root Cause We Fixed:**

- `.glob()` searches only at root level, not in subfolders
- Changed to `.rglob()` for recursive search
- But errors during this transition went unlogged

**What We Learned:**

```python
If file search fails silently → No logging = No diagnosis possible
If file move fails → User sees "File not found" but actual error was "Permission denied"
If database marking fails → File is moved but database is out of sync (no warning)
```

### Health Command Specific Issues

The health checks find issues but don't log each discovery:

- Malformed files are detected (scan_for_malformed_files) but not logged individually
- Folder structure issues are found but severity not tracked
- Duplicate detection works, but what happens next? Unknown.

**Pattern Identified:**

```python
Health = Detection without Action + No Logging = Invisible Problems
```

### Cleanup Command Specific Issues

When fixing malformed YAML (git_commits/git_branches type conversions), we have no visibility into:

- What was wrong with each file
- What conversions were performed
- Whether the write succeeded
- Which files had to be skipped and why

**Pattern Identified:**

```python
Type Conversions = Invisible Transformations = No Audit Trail
```

### Init Command Specific Issues

Initialization is complex with multiple failure points:

- Lock conflicts not logged (who holds the lock?)
- Directory creation failures don't explain WHY (permissions? disk full?)
- Rollback failures are silently ignored
- Partial initialization leaves orphaned state

**Pattern Identified:**

```python
Multi-Step Init = Many Failure Points + No Checkpoints = Mysterious Failures
```

---

## Key Principles for Robust Error Logging

### 1. Log Before and After Operations

```python
# Bad: Only log on failure
try:
    file.rename(new_name)
except Exception as e:
    logger.error(f"Rename failed: {e}")  # Too late, no context

# Good: Log the attempt and result
logger.debug("attempting_file_rename", source=str(file), dest=str(new_name))
try:
    file.rename(new_name)
    logger.info("file_renamed_successfully", source=str(file), dest=str(new_name))
except OSError as e:
    logger.error("file_rename_failed",
        source=str(file),
        dest=str(new_name),
        error_code=e.errno,
        error_message=str(e))
```

### 2. Log with Sufficient Context

```python
# Bad: Generic error
logger.error("Operation failed")

# Good: Operational context
logger.error("archive_operation_failed",
    operation="move_issue_to_archive",
    issue_id="8a00a17e",
    source_path=".roadmap/issues/v.0.4.0/...",
    destination_path=".roadmap/archive/issues/v.0.4.0/...",
    error_type="FileNotFoundError",
    classification="system_error")
```

### 3. Track Batch Operations Item-by-Item

```python
# Bad: Report only final count
archived_count = 0
for issue in issues:
    archive(issue)
    archived_count += 1
logger.info(f"Archived {archived_count} issues")  # What about failures?

# Good: Track each item
successes = []
failures = []
for issue in issues:
    try:
        archive(issue)
        logger.info("issue_archived", issue_id=issue.id)
        successes.append(issue.id)
    except Exception as e:
        logger.error("issue_archive_failed", issue_id=issue.id, error=str(e))
        failures.append((issue.id, str(e)))
logger.info("batch_archive_complete",
    total=len(issues),
    succeeded=len(successes),
    failed=len(failures))
```

### 4. Provide Recovery Information

```python
# Bad: Just report the error
logger.error("Failed to create directory")

# Good: Include recovery suggestion
logger.error("directory_creation_failed",
    path=path,
    error_type="PermissionError",
    classification="system_error",
    suggested_action="check_permissions",
    recovery_hint="Run: chmod 755 $(dirname {})",
    current_permissions=oct(os.stat(path.parent).st_mode))
```

### 5. Use Correlation IDs for Request Tracing

```python
# All logs from one command invocation share same request_id
request_id = str(uuid.uuid4())[:8]
logger = logger.bind(request_id=request_id)

logger.info("command_started", command="issue archive", request_id=request_id)
# ... all subsequent logs have request_id automatically
logger.info("file_found", issue_id="8a00a17e", request_id=request_id)
logger.info("file_moved", request_id=request_id)
logger.info("command_completed", request_id=request_id)
```

---

## Implementation Strategy

### Phase 1: Archive Command (This Week)

- Add detailed file search logging (what pattern, where, found?)
- Log each file operation (rename source/dest, success/failure)
- Log database operations (what was updated, succeeded/failed)
- Add correlation IDs to all logs

### Phase 2: Health Command (Next)

- Log each discovery individually (duplicate, misplaced, orphaned, malformed)
- Track severity levels
- Add checkpoint logging for scan completion

### Phase 3: Cleanup Command (Following)

- Log YAML parsing attempts and failures
- Track type conversions with before/after values
- Log file write operations
- Report summary statistics

### Phase 4: Init Command (Following)

- Log lock state (acquisition, holder, age)
- Log each initialization step with timing
- Log rollback attempts and results
- Track manifest creation

### Phase 5: Infrastructure (Last)

- Create per-command error loggers
- Implement recovery suggestion engine
- Add dry-run operation simulation logging
- Create log analysis utilities

---

## Error Classification Framework

We should standardize how we classify errors to enable proper routing and recovery:

### Classification Dimensions

**By Origin:**

- `user_error` - Invalid input, wrong flags, conflicting options
- `system_error` - OS failures, permissions, disk space, file not found
- `external_error` - GitHub API, network timeouts
- `logic_error` - Unexpected program state, invariant violations

**By Recoverability:**

- `recoverable` - Can retry (network timeout, transient lock)
- `irrecoverable` - Cannot retry (file permissions, logic error)
- `requires_manual_intervention` - User needs to fix something

**By Severity:**

- `DEBUG` - Diagnostic detail (search patterns, type checks)
- `INFO` - Normal operation progress
- `WARNING` - Unexpected but handled (skipped file, partial success)
- `ERROR` - Operation failed but program continues
- `CRITICAL` - Program cannot continue

### Example: Archive File Not Found

```python
error_classification = {
    "origin": "system_error",              # File doesn't exist
    "recoverability": "irrecoverable",     # Can't retry
    "severity": "HIGH",                    # Breaks the operation
    "suggested_action": "verify_issue_exists",
    "recovery_hint": "roadmap issue list | grep <id>"
}
```

---

## What Happens When We Get This Right

### Before (Current State)

```shell
$ roadmap issue archive --all-done
❌ Failed to archive issue
```

→ User is confused, we can't debug

### After (With Proper Logging)

```shell
$ roadmap issue archive --all-done
✅ Archived 12 issues
⚠️  3 issues skipped (database marking failed - see logs)

$ tail ~/.roadmap/logs/roadmap.log
[INFO] batch_archive_starting, count=15, request_id=a7f2k9m3
[INFO] issue_archived, issue_id=8a00a17e, request_id=a7f2k9m3
[WARNING] database_marking_failed, issue_id=8b11a18f, error=connection_timeout
[ERROR] archive_path_permission_denied, path=.roadmap/archive/v.0.6.0
```

→ User knows exactly what succeeded/failed, we can diagnose problems

---

## Testing This Strategy

### For Each Command, We Need Tests

**Happy Path:**

- [ ] Single operation succeeds, logs info/success
- [ ] Batch operation all succeed, logs count
- [ ] Dry-run mode shows what would happen

**Error Paths:**

- [ ] Operation fails with user error, logs suggestion
- [ ] Operation fails with system error, logs details
- [ ] Batch operation partially fails, logs per-item
- [ ] Cleanup on error succeeds, logs rollback
- [ ] Cleanup on error fails, logs failure + recovery steps

---

## Immediate Action Items

1. **Review** `ERROR_LOGGING_STRATEGY.md` (comprehensive reference)
2. **Choose Priority**: Archive (most fragile) vs Health (most incomplete)
3. **Implement Phase 1**: Pick one command and add structured logging
4. **Test**: Verify logs appear as expected for happy path and error scenarios
5. **Document**: Add logging expectations to that command's tests

---

## Conclusion

The archive command's hidden `.glob()` vs `.rglob()` bug taught us a valuable lesson: **If an operation can fail, it MUST log its attempt.** Silent failures are worse than loud failures because they're invisible.

By implementing this error logging strategy, we transform our commands from opaque black boxes to transparent operations where we can:

- Understand what went wrong
- Suggest how to fix it
- Prevent the same issue next time
- Build confidence through visibility
- Build confidence through visibility
