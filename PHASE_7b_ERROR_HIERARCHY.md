# Phase 7b: Error Hierarchy & Handling Standards

**Status:** Phase 7b in-progress
**Objective:** Define standardized error handling framework for Phases 7c-7e
**Scope:** Error taxonomy, handling patterns, logging requirements

---

## Part 1: Error Hierarchy (5 Categories)

### 1. Operational Errors
**What they are:** Expected errors during normal operation - recoverable and anticipated
**Root cause:** User input, external service behavior, resource constraints
**Examples:**
- File not found (user provided wrong path)
- Network timeout (service temporarily unavailable)
- Validation failure (user provided invalid data)
- Rate limit exceeded (API throttling)
- File already exists (attempting duplicate operation)

**Characteristics:**
- Predictable and frequently occur
- User/caller can often fix or retry
- Not a bug - normal operation path
- Should be handled gracefully

**Recovery strategy:**
- Suggest corrective action to user
- Provide clear error message
- Allow retry with different input

**Log level:** `WARNING`
**Log examples:**
```python
logger.warning(
    "file_not_found",
    filename=path,
    action="Please provide valid file path",
    severity="user_error"
)

logger.warning(
    "validation_failed",
    field="email",
    value=provided_email,
    error="Invalid email format"
)
```

---

### 2. Configuration Errors
**What they are:** Errors in application setup - should be fixed before running
**Root cause:** Wrong settings, missing environment variables, incorrect configuration files
**Examples:**
- Missing API key / credentials
- Invalid configuration parameter
- Required config file not found
- Port already in use
- Database connection string malformed

**Characteristics:**
- Prevents application from starting/functioning
- Requires administrator intervention
- Not transient - fails consistently
- Indicates deployment/setup issue

**Recovery strategy:**
- Fail fast and clearly
- Point to specific config issue
- Suggest how to fix (location, format, example)
- Exit with non-zero code

**Log level:** `ERROR`
**Log examples:**
```python
logger.error(
    "missing_config",
    config_key="GITHUB_TOKEN",
    error="Required environment variable not set",
    hint="Set GITHUB_TOKEN=<your_token> before running"
)

logger.error(
    "invalid_port",
    requested_port=8000,
    error="Port 8000 already in use",
    solution="Use different port or kill process on 8000"
)
```

---

### 3. Data Errors
**What they are:** Invalid, corrupted, or inconsistent data found
**Root cause:** Data validation failure, database corruption, API response format mismatch
**Examples:**
- Database record missing expected fields
- API response has unexpected structure
- Data consistency violation (foreign key broken)
- File format invalid or corrupted
- Deserialization failure

**Characteristics:**
- Data is malformed or inconsistent
- May indicate data corruption or attack
- Recovery might require data cleanup
- Affects data integrity/reliability

**Recovery strategy:**
- Log full error context
- Decide: skip item, abort, or manual intervention
- Prevent cascading corruption

**Log level:** `ERROR`
**Log examples:**
```python
logger.error(
    "data_integrity_violation",
    table="issues",
    record_id=issue_id,
    error="Required field 'title' is null",
    action="Skipping record, manual review needed"
)

logger.error(
    "api_response_malformed",
    endpoint="/repos/{owner}/{repo}/issues",
    expected_fields=["id", "title", "state"],
    missing_fields=["state"],
    response=response_dict
)
```

---

### 4. System Errors
**What they are:** System-level failures - OS, I/O, permissions, resources
**Root cause:** Filesystem issues, permission problems, out of memory, system calls fail
**Examples:**
- Permission denied (file/directory access)
- Out of memory / disk full
- System resource exhausted (too many open files)
- Permission denied on git operations
- Symlink issues / path resolution failures

**Characteristics:**
- Usually beyond application's control
- May be environment-specific (dev vs prod)
- Often indicates infrastructure problem
- Retry may or may not help

**Recovery strategy:**
- Log detailed context (exact resource, limits)
- Suggest infrastructure fix if possible
- May need operator intervention

**Log level:** `ERROR`
**Log examples:**
```python
logger.error(
    "permission_denied",
    path="/var/log/roadmap.log",
    error="Permission denied",
    current_user=os.getuid(),
    hint="File owned by different user, check permissions"
)

logger.error(
    "disk_space_exhausted",
    path="/tmp",
    available_bytes=0,
    required_bytes=file_size,
    error="No space left on device"
)
```

---

### 5. Infrastructure Errors
**What they are:** External service or network failures - out of application's control
**Root cause:** Database down, API unavailable, network unreachable, cloud service outage
**Examples:**
- Database connection refused
- GitHub API unavailable
- Network timeout to external service
- SSH key authentication failed
- Cloud service rate limit

**Characteristics:**
- Temporary (usually) - service will recover
- Retry is often appropriate
- Not a bug in our code
- Should not bubble up to user (handle gracefully)

**Recovery strategy:**
- Log with context for debugging
- Implement backoff/retry if appropriate
- Fall back to cached data if available
- Queue for retry if possible

**Log level:** `WARNING` (first attempt) → `ERROR` (after retries exhausted)
**Log examples:**
```python
logger.warning(
    "github_api_unavailable",
    endpoint="https://api.github.com/repos",
    error="Connection timeout after 5s",
    retry_attempt=1,
    max_retries=3,
    action="Retrying with exponential backoff"
)

logger.error(
    "database_connection_failed",
    host="db.internal",
    port=5432,
    error="Connection refused",
    retry_attempt=3,
    total_attempts=3,
    action="All retries exhausted, aborting operation"
)
```

---

## Part 2: Error Handling Decision Tree

```
Error occurs → Catch exception

  ↓ Is it expected during normal operation?
  ├─ YES → Operational Error (WARNING)
  │         User can fix or retry
  │         Provide helpful message
  │
  └─ NO ↓ Is it a configuration/setup issue?
        ├─ YES → Configuration Error (ERROR)
        │         Fail fast, point to solution
        │
        └─ NO ↓ Is it invalid/corrupted data?
              ├─ YES → Data Error (ERROR)
              │         Skip/abort, prevent corruption
              │
              └─ NO ↓ Is it OS/system resource issue?
                    ├─ YES → System Error (ERROR)
                    │         Log context, suggest fix
                    │
                    └─ NO → Infrastructure Error (WARNING→ERROR)
                            Retry with backoff, queue if possible
```

---

## Part 3: Logging Requirements by Error Type

| Error Type | Log Level | Required Fields | Error Context | Exit Behavior |
|------------|-----------|-----------------|----------------|---------------|
| **Operational** | WARNING | error_type, field/resource, error_message | User input, suggested action | Continue/retry |
| **Configuration** | ERROR | config_key, error, hint, expected_value | What's wrong, where to fix | Exit(1) |
| **Data** | ERROR | table/entity, record_id, field, error | Schema violation details | Skip/abort |
| **System** | ERROR | resource, permission, limit, current_value | What failed, limits | Exit(1) or Continue |
| **Infrastructure** | WARNING/ERROR | service, endpoint, timeout, retry_count | External service context | Retry/queue |

---

## Part 4: Structlog Integration

All errors logged via structlog with consistent format:

```python
import structlog

logger = structlog.get_logger()

# Pattern for all errors:
logger.error(
    "error_code",  # Specific, searchable error identifier
    error_type=str(type(e).__name__),  # Exception class
    error_message=str(e),  # Human-readable message
    context={...},  # Operation-specific context
    action="What we're doing about this"  # Recovery action
)
```

**Required fields in context:**
- `operation` - What operation was being performed
- `resource` - What resource was involved (file, URL, record)
- `user_action` - Suggested action for user (if applicable)
- Any domain-specific context

**Example:**
```python
try:
    result = fetch_github_issue(issue_id)
except requests.Timeout as e:
    logger.error(
        "github_api_timeout",
        error_type="Infrastructure",
        operation="fetch_github_issue",
        resource=f"issues/{issue_id}",
        timeout_seconds=5,
        retry_attempt=attempt_number,
        action="Retrying with exponential backoff"
    )
```

---

## Part 5: Error Output Routing

### stdout: Results/Success Output
```
✅ Operation completed
Successfully created 5 issues
Found 3 duplicates
```

### stderr: Errors/Diagnostics/Logging
```
[WARNING] file_not_found: /tmp/config.yaml
[ERROR] database_connection_failed: Connection refused on db.internal:5432
[INFO] retry_attempt: 1 of 3
```

**Rule:** If exception caught → log to stderr (via structlog), NOT stdout

---

## Part 6: Error Taxonomy Summary Table

| Category | Severity | Expected | Recoverable | User Action | Log Level | Example |
|----------|----------|----------|-------------|-------------|-----------|---------|
| Operational | Low | Yes | Often | Retry/Fix | WARNING | File not found |
| Configuration | Critical | No | Only with fix | Fix config | ERROR | Missing API key |
| Data | High | No | Partial | Manual review | ERROR | Corrupted record |
| System | High | No | Varies | Infrastructure fix | ERROR | Permission denied |
| Infrastructure | Medium | Yes | Yes | Retry | WARN→ERR | Service timeout |

---

## Part 7: Next Steps (Phases 7c-7e)

Use this hierarchy to:

1. **Phase 7c (Core Services):** Classify exceptions in `roadmap/core/services/`
2. **Phase 7d (CLI Handling):** Apply patterns to `roadmap/adapters/cli/`
3. **Phase 7e (Adapters):** Standardize in persistence/sync/github/git adapters

For each file:
1. Identify exception handlers (83 files flagged in audit)
2. Classify error type using this hierarchy
3. Add appropriate logging with required context fields
4. Verify error is going to stderr (not stdout)
5. Test error path (Phase 7f)

---

## Acceptance Criteria for Phase 7b

- [ ] Error hierarchy documented with 5 clear categories
- [ ] Decision tree for classifying errors
- [ ] Logging requirements defined by error type
- [ ] Structlog integration pattern established
- [ ] Code examples for each error type (Phase 7b-2)
- [ ] Developers can reference this to guide implementation
- [ ] Ready for Phase 7c without clarifications needed
