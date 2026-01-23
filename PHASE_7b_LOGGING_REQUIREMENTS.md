# Phase 7b-3: Logging Standards & structlog Integration

**Status:** Phase 7b - Part 3 of 5
**Objective:** Define logging requirements and structlog format for error handling
**Usage:** Reference during Phase 7c-7e implementation

---

## Part 1: Structlog Configuration Overview

The roadmap project uses **structlog** for structured logging. This enables:
- Searchable error events (JSON format)
- Consistent field naming across codebase
- Better debugging and observability

**Current status:** Already integrated in project, used in ~58 files

---

## Part 2: Required Fields for All Error Logs

Every error log entry MUST include:

### Mandatory Fields
1. **Error event name** (first parameter) - Unique, searchable identifier
   ```python
   logger.error("github_api_timeout", ...)  # ✅ Good
   logger.error("error", ...)  # ❌ Bad - too generic
   ```

2. **operation** - What operation was happening
   ```python
   operation="fetch_github_issue"
   operation="sync_issues_to_database"
   ```

3. **error_type** or Exception class name
   ```python
   error_type=type(e).__name__
   # or inline
   error_type="Timeout" | "PermissionError" | "ValidationError"
   ```

4. **error** or **error_message** - Human-readable description
   ```python
   error="Connection timeout after 5 seconds"
   error_message="File /etc/config.yaml not found"
   ```

5. **severity** - What category from error hierarchy
   ```python
   severity="operational"  # User can fix
   severity="config"       # Setup issue
   severity="data"         # Corruption/validation
   severity="system"       # OS/resource
   severity="infrastructure"  # External service
   ```

### Context-Dependent Fields

Based on error type, include additional relevant fields:

**For file operations:**
```python
path="/path/to/file"
mode="write"  # if applicable
permissions="0644"
```

**For network operations:**
```python
endpoint="https://api.github.com/repos"
host="db.internal"
port=5432
timeout_seconds=5
status_code=403
```

**For database operations:**
```python
table="issues"
record_id=12345
database="roadmap_prod"
query="SELECT * FROM issues WHERE..."
```

**For user input/validation:**
```python
field="email"
provided_value=user_input
expected_type="string"
expected_format="user@domain.com"
```

---

## Part 3: Error Logging by Category

### Category 1: Operational Errors

```python
logger.warning(
    "operational_error_name",  # e.g., "file_not_found"
    operation="what_we_were_doing",
    resource="what_failed",  # file path, URL, etc.
    error="human_readable_message",
    user_action="what_user_should_do",
    severity="operational"
)
```

**Examples:**

```python
# Example 1: File not found
logger.warning(
    "config_file_not_found",
    operation="load_configuration",
    path="/etc/roadmap/config.yaml",
    error="Configuration file does not exist",
    user_action="Create config file at /etc/roadmap/config.yaml or use --config flag",
    severity="operational"
)

# Example 2: Validation failure
logger.warning(
    "email_validation_failed",
    operation="validate_user_input",
    field="email",
    provided_value=email_input,
    error="Email address format is invalid",
    expected_format="user@example.com",
    user_action="Please provide a valid email address",
    severity="operational"
)

# Example 3: Rate limiting
logger.warning(
    "github_rate_limit_exceeded",
    operation="fetch_github_issues",
    endpoint="https://api.github.com/repos/owner/repo/issues",
    error="GitHub API rate limit exceeded",
    limit=60,
    reset_time="2024-01-15T14:30:00Z",
    retry_after_seconds=300,
    user_action="Wait 5 minutes before retrying",
    severity="operational"
)
```

---

### Category 2: Configuration Errors

```python
logger.error(
    "config_error_name",  # e.g., "missing_api_key"
    operation="what_we_were_doing",
    config_key="GITHUB_TOKEN",  # or parameter name
    error="what_is_wrong",
    expected_value="example_format",
    hint="how_to_fix",
    severity="config_error"
)
```

**Examples:**

```python
# Example 1: Missing required key
logger.error(
    "missing_github_token",
    operation="initialize_github_client",
    config_key="GITHUB_TOKEN",
    error="Required GitHub API token not configured",
    expected_value="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    hint="Set environment variable: export GITHUB_TOKEN=<your_token>",
    hint_file_location=".env or .bashrc or CI configuration",
    severity="config_error"
)

# Example 2: Invalid configuration value
logger.error(
    "invalid_log_level",
    operation="configure_logging",
    config_key="LOG_LEVEL",
    provided_value=log_level,
    error="Invalid log level value",
    expected_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    hint="Set LOG_LEVEL to one of: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    severity="config_error"
)

# Example 3: Port in use
logger.error(
    "port_already_in_use",
    operation="start_server",
    requested_port=8000,
    error="Another process is listening on port 8000",
    hint="(1) Use different port: PORT=8001 ./run.sh",
    hint_kill_process="lsof -i :8000 | grep LISTEN",
    severity="config_error"
)
```

---

### Category 3: Data Errors

```python
logger.error(
    "data_error_name",  # e.g., "missing_required_field"
    operation="what_we_were_doing",
    resource_type="issues",  # table, entity, file, etc.
    resource_id=12345,  # record id, file path, etc.
    error="what_is_wrong_with_data",
    missing_fields=["title", "status"],  # if applicable
    action="what_we_did_about_it",  # skipped, aborted, etc.
    severity="data_error"
)
```

**Examples:**

```python
# Example 1: Missing required field
logger.error(
    "issue_missing_required_field",
    operation="deserialize_issue",
    resource_type="github_issue",
    resource_id="123",
    table="issues",
    missing_fields=["title"],
    error="Issue record is missing required field: title",
    action="Record skipped, manual review required",
    severity="data_error"
)

# Example 2: Type mismatch
logger.error(
    "invalid_data_type",
    operation="parse_api_response",
    resource_type="github_issue",
    field="id",
    error="Field has wrong data type",
    expected_type="integer",
    actual_type="string",
    actual_value=actual_id,
    action="Record skipped",
    severity="data_error"
)

# Example 3: Corruption detected
logger.error(
    "data_integrity_violation",
    operation="load_issue_from_database",
    table="issues",
    record_id=456,
    error="Foreign key constraint violated: assignee_id references non-existent user",
    constraint_name="fk_issues_assignee_id",
    foreign_key_id=789,
    action="Record flagged for manual review",
    severity="data_error"
)
```

---

### Category 4: System Errors

```python
logger.error(
    "system_error_name",  # e.g., "permission_denied"
    operation="what_we_were_doing",
    resource="what_failed",  # file, directory path, etc.
    error="what_went_wrong",
    current_user=os.getuid(),  # if applicable
    hint="how_to_fix",
    severity="system_error"
)
```

**Examples:**

```python
# Example 1: Permission denied
logger.error(
    "permission_denied_write",
    operation="save_report",
    path="/var/log/roadmap/report.txt",
    resource_type="file",
    error="Permission denied: unable to write to file",
    current_user=os.getuid(),
    file_owner=os.stat("/var/log/roadmap/report.txt").st_uid,
    file_permissions="0644",
    hint="Run with appropriate permissions or check directory ownership",
    action="Operation aborted",
    severity="system_error"
)

# Example 2: Disk space exhausted
logger.error(
    "disk_space_exhausted",
    operation="write_large_log",
    path="/var/log",
    resource_type="filesystem",
    error="No space left on device",
    available_bytes=0,
    required_bytes=file_size,
    total_disk_space=total_bytes,
    hint="Free up disk space or use different directory",
    severity="system_error"
)

# Example 3: Too many open files
logger.error(
    "too_many_open_files",
    operation="process_files_in_directory",
    directory="/tmp/roadmap",
    error="System limit exceeded: too many open files",
    current_file_limit=get_file_limit(),
    files_to_process=file_count,
    hint="Increase file descriptor limit: ulimit -n 10000",
    severity="system_error"
)
```

---

### Category 5: Infrastructure Errors

**First Attempt (Warning):**
```python
logger.warning(
    "infrastructure_error_name",  # e.g., "github_api_timeout"
    operation="what_we_were_doing",
    service="what_service_failed",  # github, database, etc.
    endpoint="service_endpoint",
    error="what_went_wrong",
    timeout_seconds=5,  # if applicable
    retry_attempt=1,
    max_retries=3,
    action="retrying_with_backoff",
    severity="infrastructure"
)
```

**After Retries Exhausted (Error):**
```python
logger.error(
    "infrastructure_error_name_final",  # e.g., "github_api_unreachable_final"
    operation="what_we_were_doing",
    service="what_service_failed",
    endpoint="service_endpoint",
    error="service_still_unavailable_after_retries",
    retry_attempt=3,
    total_attempts=3,
    action="operation_aborted",
    severity="infrastructure"
)
```

**Examples:**

```python
# Example 1: GitHub API timeout (first attempt)
logger.warning(
    "github_api_timeout",
    operation="fetch_github_issues",
    service="github",
    endpoint="https://api.github.com/repos/owner/repo/issues",
    error="Connection timeout",
    timeout_seconds=5,
    retry_attempt=1,
    max_retries=3,
    action="Retrying with exponential backoff",
    backoff_seconds=2,
    severity="infrastructure"
)

# Example 2: Database connection refused (final)
logger.error(
    "database_connection_unreachable",
    operation="load_issues_from_db",
    service="postgresql",
    endpoint="db.internal:5432",
    error="Connection refused",
    retry_attempt=5,
    total_retries=5,
    last_error="Connection refused by host",
    action="Operation failed, queue for retry later",
    severity="infrastructure"
)

# Example 3: Service temporarily unavailable (first attempt)
logger.warning(
    "external_service_unavailable",
    operation="sync_with_external_api",
    service="some_external_api",
    endpoint="https://api.external.com/sync",
    status_code=503,
    error="Service Unavailable",
    retry_after_seconds=60,
    retry_attempt=1,
    max_retries=3,
    action="Retrying with exponential backoff",
    severity="infrastructure"
)
```

---

## Part 4: Output Routing

### Rule: Errors Always Go to stderr

Use structlog configuration to route errors to stderr:

```python
# In your logging configuration
import structlog
import sys

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),  # ← ERROR LOGS TO STDERR
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# All errors logged via logger.error(), logger.warning() go to stderr
# Success output printed to stdout
```

### Guidelines:

```python
# ❌ DON'T - print errors to stdout
print(f"ERROR: Something failed")  # Wrong!
print(f"FATAL: Database down")     # Wrong!

# ✅ DO - use logger for all errors/warnings
logger.error("database_down", error=str(e))  # Goes to stderr
logger.warning("retry_attempt", attempt=1)   # Goes to stderr

# ✅ DO - use print for success output only
print("✅ Successfully synced 42 issues")  # Stdout OK
print("Generated report: /tmp/report.txt")  # Stdout OK
```

---

## Part 5: Logging Best Practices

### 1. Use Structured Fields, Not String Formatting

```python
# ❌ BAD - loses searchability
logger.error("Failed to fetch from " + url + " after " + str(retries) + " retries")

# ✅ GOOD - searchable fields
logger.error(
    "fetch_failed",
    url=url,
    retries=retries,
    error="Connection timeout"
)
```

### 2. Always Include Operation Context

```python
# ❌ BAD - unclear what was happening
logger.error("timeout", error=str(e))

# ✅ GOOD - full context
logger.error(
    "api_call_timeout",
    operation="fetch_github_issues",
    endpoint="https://api.github.com/repos/owner/repo/issues",
    timeout_seconds=5
)
```

### 3. Use Consistent Field Names Across Codebase

```python
# ✅ Consistent field naming
resource_id="issue_123"  # Use snake_case
operation="fetch_issue"  # Use snake_case
severity="infrastructure"  # Use lowercase
error_type="Timeout"  # Use PascalCase for class names
```

### 4. Include Actionable Information

```python
# ❌ BAD - tells us what failed, not what to do
logger.error("authentication_failed", error="Invalid credentials")

# ✅ GOOD - tells us what failed and how to fix
logger.error(
    "authentication_failed",
    operation="authenticate_with_github",
    error="Invalid credentials",
    hint="Check that GITHUB_TOKEN is set and valid",
    action="Please regenerate token at https://github.com/settings/tokens"
)
```

### 5. Use Appropriate Log Levels

```python
# ✅ Correct log levels
logger.info("operation_started", operation="sync")  # Normal operation
logger.warning("retry_attempt", attempt=1)  # Recoverable, expected
logger.error("database_connection_failed", ...)  # Failure, needs intervention
logger.debug("parsed_response", fields=["id", "title"])  # Dev debugging only
```

### 6. Include Raw Data When Helpful for Debugging

```python
# ✅ Include raw data for complex errors
logger.error(
    "json_parse_failed",
    operation="parse_api_response",
    raw_response=response_text,  # Full raw data
    error_line=e.lineno,
    error_message=str(e)
)
```

---

## Part 6: Quick Reference Template

Copy-paste template for each error category:

### Operational Error
```python
logger.warning(
    "REPLACE_WITH_EVENT_NAME",
    operation="...",
    resource="...",
    error="...",
    user_action="...",
    severity="operational"
)
```

### Configuration Error
```python
logger.error(
    "REPLACE_WITH_EVENT_NAME",
    operation="...",
    config_key="...",
    error="...",
    hint="...",
    severity="config_error"
)
```

### Data Error
```python
logger.error(
    "REPLACE_WITH_EVENT_NAME",
    operation="...",
    resource_type="...",
    resource_id="...",
    error="...",
    action="...",
    severity="data_error"
)
```

### System Error
```python
logger.error(
    "REPLACE_WITH_EVENT_NAME",
    operation="...",
    resource="...",
    error="...",
    hint="...",
    severity="system_error"
)
```

### Infrastructure Error (First)
```python
logger.warning(
    "REPLACE_WITH_EVENT_NAME",
    operation="...",
    service="...",
    endpoint="...",
    error="...",
    retry_attempt=1,
    max_retries=3,
    action="retrying",
    severity="infrastructure"
)
```

### Infrastructure Error (Final)
```python
logger.error(
    "REPLACE_WITH_EVENT_NAME_final",
    operation="...",
    service="...",
    endpoint="...",
    error="...",
    retry_attempt=3,
    total_retries=3,
    action="aborted",
    severity="infrastructure"
)
```

---

## Part 7: Implementation Checklist

For each exception handler during Phase 7c-7e:

- [ ] Choose error category (Operational/Config/Data/System/Infrastructure)
- [ ] Use appropriate log level (WARNING or ERROR)
- [ ] Include all mandatory fields: error_name, operation, error_type, error, severity
- [ ] Include relevant context fields (endpoint, path, timeout, etc.)
- [ ] Add user_action or hint for user-facing errors
- [ ] Verify error goes to stderr (via structlog)
- [ ] Test that log output is properly formatted
- [ ] Review for searchability (good event names, not generic)
