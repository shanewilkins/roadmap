# Logging Coverage Analysis & Recommendations

**Date**: November 25, 2025
**Status**: Initial Assessment

## Executive Summary

The roadmap project has **solid foundational logging infrastructure** with:

- ✅ Structured logging via structlog
- ✅ Correlation ID tracking for request tracing
- ✅ Sensitive data redaction (tokens, passwords, etc.)
- ✅ Database schema initialization logging
- ✅ File sync tracking
- ✅ Security operation logging

**However, significant gaps exist in:**

- ❌ CLI command execution logging (create, update, delete operations)
- ❌ Error handling and exception context logging
- ❌ Performance/latency tracking
- ❌ User action audit trail
- ❌ Data migration/sync operation logs
- ❌ Operational metrics (throughput, error rates)

---

## Current Logging Coverage by Layer

### Infrastructure Layer ✅ **Good Coverage**

**File**: `roadmap/infrastructure/storage.py`

**Currently Logged:**

- Database schema initialization
- Database migrations
- CRUD operations (create_project, create_issue, create_milestone)
- File sync operations
- Smart sync strategy decisions
- Conflicts detected
- Errors in file sync and database operations

**Example:**

```python
logger.info("Created project", project_id=project_data["id"])
logger.info(f"Synced issue file: {issue_id}", file_path=str(file_path))
```

### Application Services Layer ⚠️ **Partial Coverage**

**Files**:

- `roadmap/application/services/progress_service.py`
- `roadmap/application/health.py`

**Currently Logged:**

- Progress/milestone updates
- Health check results (system state validation)
- Configuration validation

**Missing:**

- Business logic decisions
- Validation failures
- Transformation operations
- Data aggregations

### CLI Layer ❌ **Minimal Coverage**

**Directory**: `roadmap/presentation/cli/**/*.py`

**Currently Logged:**

- ❌ Almost nothing - only user-facing console output

**What Should Be Logged:**

- Issue/milestone/project creation (who, what, when, why)
- Update operations (before/after values)
- Delete operations (retention, recovery info)
- Archive/restore operations
- User selections and confirmations
- Command execution time
- Validation failures that don't raise exceptions

---

## Key Logging Gaps & Recommendations

### Gap 1: CLI Command Lifecycle Logging

**Severity**: HIGH
**Impact**: Makes it impossible to audit user actions or debug issues

**Currently Missing:**

```python
# Issues don't log who created them or when
@click.command("create")
def create_issue(title, priority, ...):
    issue = core.create_issue(...)
    # No log entry here!
    click.echo(f"Created: {issue.id}")
```

**Recommendation:**

```python
logger = get_logger(__name__)

@click.command("create")
@click.pass_context
def create_issue(ctx, title, priority, ...):
    user = get_current_user()
    logger.info(
        "issue_create_initiated",
        user=user,
        title=title,
        priority=priority,
        correlation_id=get_correlation_id()
    )

    try:
        issue = core.create_issue(...)
        logger.info(
            "issue_created",
            issue_id=issue.id,
            title=title,
            user=user,
            duration_ms=timer.elapsed
        )
        click.echo(f"✅ Created: {issue.id}")
    except Exception as e:
        logger.error(
            "issue_create_failed",
            user=user,
            title=title,
            error=str(e),
            error_type=type(e).__name__
        )
        raise
```

**Implementation Plan:**

1. Create `roadmap/presentation/cli/logging_decorators.py` with `@log_command` decorator
2. Apply to all CRUD commands (create, update, delete, archive, restore)
3. Include command context, user, duration, and outcome

### Gap 2: Error Context & Root Cause Analysis

**Severity**: HIGH
**Impact**: Hard to diagnose issues in production

**Currently Missing:**

- Error classification (user error vs system error)
- Contextual state at time of failure
- Stack traces with local variables (when safe)
- Recovery suggestions

**Recommendation:**

```python
def handle_database_error(error: Exception, context: dict):
    """Log database errors with actionable context."""
    logger.error(
        "database_operation_failed",
        error_type=type(error).__name__,
        error_message=str(error),
        operation=context.get("operation"),
        entity_id=context.get("entity_id"),
        retry_count=context.get("retries", 0),
        is_recoverable=is_error_recoverable(error),
        suggested_action="retry" if is_error_recoverable(error)
        else "manual_intervention"
    )
```

### Gap 3: Performance & Latency Tracking

**Severity**: MEDIUM
**Impact**: No visibility into slow operations

**Currently Missing:**

- Command execution time
- Database query times
- File I/O times
- Sync operation duration

**Recommendation:**

```python
from roadmap.shared.logging import log_operation_duration

@log_operation_duration("issue_sync", warn_threshold_ms=5000)
def sync_issues_to_github(self):
    """Sync all issues to GitHub with duration tracking."""
    logger.info("Starting issue sync to GitHub")
    # ... sync logic ...
    logger.info(f"Synced {count} issues")
```

**Implementation:**

- Create timing context manager in `shared/logging.py`
- Log WARN level for slow operations (>5s)
- Log DEBUG level for all operations with duration

### Gap 4: User Action Audit Trail

**Severity**: MEDIUM
**Impact**: Can't track who did what when

**Currently Missing:**

- User identification on all mutations
- Before/after value tracking
- Change timestamps

**Recommendation:**

```python
def log_audit_event(
    action: str,
    entity_type: str,
    entity_id: str,
    user: str,
    before: dict | None = None,
    after: dict | None = None,
    reason: str | None = None
):
    """Log auditable user action with before/after state."""
    logger.info(
        "audit_event",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        before=before,
        after=after,
        reason=reason,
        timestamp=datetime.utcnow().isoformat()
    )
```

### Gap 5: Data Sync & Migration Logging

**Severity**: MEDIUM
**Impact**: Hard to debug sync issues or track data integrity

**Currently Partially Covered** - Could be enhanced with:

- Item-level sync decisions (included/excluded/conflicted)
- Schema version tracking
- Migration rollback information
- Data validation results

**Recommendation:**

```python
def log_sync_summary(sync_result: SyncResult):
    """Log comprehensive sync operation summary."""
    logger.info(
        "sync_completed",
        duration_ms=sync_result.duration_ms,
        issues_synced=sync_result.issues_synced,
        milestones_synced=sync_result.milestones_synced,
        conflicts_resolved=sync_result.conflicts_resolved,
        errors_encountered=len(sync_result.errors),
        success_rate=sync_result.success_rate,
        data_integrity_verified=sync_result.integrity_check_passed
    )
```

### Gap 6: Archive, Restore & Cleanup Logging

**Severity**: MEDIUM
**Impact**: Recent feature lacks observability

**Currently Missing:**

- Archive operations don't log retention rationale
- Restore operations don't log recovery info
- Cleanup doesn't track what was removed

**Recommendation:**

```python
# In archive.py
logger.info(
    "issue_archived",
    issue_id=issue_id,
    archive_reason=reason,  # "done", "duplicate", "invalid", etc.
    retention_days=retention_policy.days,
    location=archive_path,
    user=current_user
)

# In cleanup.py
logger.info(
    "backup_cleanup_executed",
    backup_files_checked=total_files,
    backup_files_removed=deleted_count,
    total_bytes_freed=total_freed,
    retention_policy_applied=policy_type,
    start_time=start,
    end_time=end
)
```

---

## Logging Pattern Best Practices

### ✅ Good Patterns (Already in codebase)

1. **Structured logging with context:**

```python
logger.info("Created issue", issue_id=issue.id, title=title)
```

2. **Correlation ID for tracing:**

```python
# Automatically added by correlation_id processor
event_dict["correlation_id"] = correlation_id
```

3. **Sensitive data redaction:**

```python
scrub_sensitive_data("token", "secret", "password", "api_key")
```

### ⚠️ Patterns to Improve

1. **Inconsistent log levels:**
   - Some errors use `logger.warning` instead of `logger.error`
   - Not all errors are logged before raising

2. **Missing context in exceptions:**

```python
# Current (not great):
except Exception as e:
    logger.error(f"Failed to create issue: {e}")

# Better:
except ValidationError as e:
    logger.error(
        "issue_validation_failed",
        error_type=type(e).__name__,
        errors=e.errors(),
        proposed_values={...}
    )
```

3. **No duration tracking:**

```python
# Add to long-running operations:
start = time.time()
result = expensive_operation()
duration_ms = (time.time() - start) * 1000
logger.info("operation_completed", duration_ms=duration_ms)
```

---

## Testing Logging Coverage

### Current Test Coverage

- ✅ Security logging tests exist
- ✅ Configuration logging tests exist
- ❌ CLI command logging tests missing
- ❌ Integration logging tests minimal

### Recommendation: Create comprehensive logging tests

**File**: `tests/integration/test_logging_coverage.py`

```python
def test_issue_creation_logs_audit_event(caplog):
    """Verify issue creation logs audit trail."""
    with caplog.at_level(logging.INFO):
        result = runner.invoke(main, ["issue", "create", "Test Issue"])

    # Should find audit event log
    audit_logs = [r for r in caplog.records if r.msg == "audit_event"]
    assert len(audit_logs) >= 1
    assert audit_logs[0].action == "create"
    assert audit_logs[0].entity_type == "issue"

def test_archive_operation_logs_retention_info(caplog):
    """Verify archive logs retention policy."""
    with caplog.at_level(logging.INFO):
        result = runner.invoke(main, ["issue", "archive", issue_id, "--force"])

    archive_logs = [r for r in caplog.records if "archived" in r.msg]
    assert archive_logs[0].retention_days == expected_days
    assert archive_logs[0].location.endswith(".roadmap/archive/issues/")

def test_database_error_logged_with_context(caplog, mocker):
    """Verify database errors include recovery suggestions."""
    mocker.patch.object(db, "create_issue", side_effect=sqlite3.OperationalError)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(Exception):
            runner.invoke(main, ["issue", "create", "Test"])

    error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
    assert error_logs[0].suggested_action in ["retry", "manual_intervention"]
```

---

## Implementation Roadmap

### Phase 1: CLI Command Logging (HIGH PRIORITY)

**Effort**: 4-5 hours
**Impact**: High - Enables audit trail

1. Create `roadmap/presentation/cli/logging_decorators.py`
2. Add `@log_command` decorator for all CRUD commands
3. Add command timing tracking
4. Add error context logging

### Phase 2: Error & Exception Logging (HIGH PRIORITY)

**Effort**: 3-4 hours
**Impact**: High - Better diagnostics

1. Create standardized error logging utility
2. Update all exception handlers to use structured logging
3. Add error classification (user vs system)
4. Add recovery suggestions

### Phase 3: Performance Tracking (MEDIUM PRIORITY)

**Effort**: 2-3 hours
**Impact**: Medium - Identifies bottlenecks

1. Create timing context manager
2. Add to key database operations
3. Add to sync operations
4. Add configurable slow operation threshold

### Phase 4: Audit Trail (MEDIUM PRIORITY)

**Effort**: 2-3 hours
**Impact**: Medium - User action tracking

1. Create audit logging utilities
2. Add before/after value tracking
3. Add user identification
4. Create audit log analysis tools

### Phase 5: Test Coverage (MEDIUM PRIORITY)

**Effort**: 3-4 hours
**Impact**: Medium - Ensures logging quality

1. Create `tests/integration/test_logging_coverage.py`
2. Add tests for each command
3. Add tests for error scenarios
4. Add performance logging tests

### Phase 6: Log Analysis Tools (LOW PRIORITY)

**Effort**: 2-3 hours
**Impact**: Low - Improves operational debugging

1. Create `scripts/analyze_logs.py`
2. Add filtering capabilities
3. Add audit report generation
4. Add correlation ID tracing

---

## Summary Table

| Area | Coverage | Priority | Effort | Status |
|------|----------|----------|--------|--------|
| Infrastructure DB | 85% | - | - | ✅ Good |
| Application Services | 40% | Medium | 2h | ⚠️ Partial |
| CLI Commands | 5% | **High** | 5h | ❌ Critical Gap |
| Error Handling | 30% | **High** | 4h | ❌ Critical Gap |
| Performance Tracking | 0% | Medium | 3h | ❌ Missing |
| User Audit Trail | 0% | Medium | 3h | ❌ Missing |
| Archive/Cleanup | 0% | Medium | 2h | ❌ Missing |
| Log Analysis Tools | 0% | Low | 3h | ❌ Missing |
| Test Coverage | 40% | Medium | 4h | ⚠️ Partial |

**Total Effort to Complete**: ~26 hours across 6 phases

---

## Quick Wins (Can do in 1-2 hours)

1. **Add CLI command logging decorator** - Enables audit trail immediately
2. **Add error context logging** - Improves debugging for current operations
3. **Add timing to archive/restore** - Simple but valuable for new features
4. **Create basic audit test** - Ensures logging stays in place

---

## Questions to Consider

1. **Compliance**: Do you need logs for compliance (SOC2, etc.)?
2. **Retention**: How long should logs be retained?
3. **Sensitive Data**: Should we mask user identifiers or keep them?
4. **Real-time Alerts**: Do you want alerts for errors?
5. **Log Aggregation**: Will logs be sent to external service (Datadog, etc.)?
6. **Log Volume**: Are you concerned about log file size?
