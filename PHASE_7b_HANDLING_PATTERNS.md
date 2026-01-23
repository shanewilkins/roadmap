# Phase 7b-2: Handling Patterns by Error Type

**Status:** Phase 7b - Part 2 of 5
**Objective:** Provide reusable patterns for each error category
**Usage:** Reference during Phase 7c-7e implementation

---

## Pattern 1: Operational Errors (User/External Factors)

### Pattern Template
```python
def operation_that_can_fail():
    """Operation that might fail for expected reasons."""
    try:
        # Attempt operation that might fail
        result = external_call_or_user_input()
    except ExpectedException as e:
        # Log with context
        logger.warning(
            "operational_error_code",  # e.g., "file_not_found"
            operation="describe_operation",
            resource=str(e.resource),
            error=str(e),
            user_action="Tell user what to do",
            severity="operational"
        )
        # Return controlled response
        return None
    except Exception as e:
        # Unexpected error - rethrow or handle as System/Data error
        logger.error("unexpected_error", error=str(e))
        raise

    return result
```

### Real Example: File Input Validation
**Before (Bad):**
```python
def load_config(path):
    with open(path) as f:
        return json.load(f)  # Crashes if file missing/invalid
```

**After (Good):**
```python
def load_config(path: str) -> Optional[Dict]:
    """Load config file with user-friendly error handling."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(
            "config_file_not_found",
            operation="load_config",
            path=path,
            error="Configuration file not found",
            user_action=f"Please create {path} or provide via --config flag",
            severity="user_error"
        )
        return None
    except json.JSONDecodeError as e:
        logger.warning(
            "config_invalid_json",
            operation="load_config",
            path=path,
            error=str(e),
            line=e.lineno,
            column=e.colno,
            user_action="Check JSON syntax in config file",
            severity="user_error"
        )
        return None
    except Exception as e:
        # Unexpected error
        logger.error(
            "config_load_failed",
            operation="load_config",
            path=path,
            error_type=type(e).__name__,
            error=str(e)
        )
        raise
```

### Real Example: API Validation
**Before (Bad):**
```python
def validate_github_url(url):
    assert "github.com" in url  # Silent assertion failure
```

**After (Good):**
```python
def validate_github_url(url: str) -> bool:
    """Validate GitHub URL format with helpful error message."""
    if not url:
        logger.warning(
            "github_url_empty",
            operation="validate_github_url",
            error="URL is empty",
            user_action="Provide a GitHub URL",
            severity="user_error"
        )
        return False

    if "github.com" not in url:
        logger.warning(
            "github_url_invalid_format",
            operation="validate_github_url",
            provided_url=url,
            error="URL does not contain github.com",
            user_action="Provide valid GitHub URL (e.g., https://github.com/owner/repo)",
            severity="user_error"
        )
        return False

    return True
```

---

## Pattern 2: Configuration Errors (Setup/Deployment Issue)

### Pattern Template
```python
def get_required_config(key: str, default=None) -> str:
    """Get configuration value, fail fast if missing required key."""
    value = os.getenv(key)

    if not value:
        if default is not None:
            logger.info(f"Using default for {key}")
            return default
        else:
            # Required config missing - fail immediately
            logger.error(
                "missing_required_config",
                operation="get_required_config",
                config_key=key,
                error=f"Required configuration '{key}' not set",
                expected_format="describe format/example",
                hint=f"Set environment variable: export {key}=<value>",
                severity="config_error"
            )
            raise ConfigurationError(f"Missing required config: {key}")

    return value
```

### Real Example: API Key Configuration
**Before (Bad):**
```python
def get_github_token():
    return os.getenv("GITHUB_TOKEN")  # Returns None silently

# Later crashes with cryptic error
token = get_github_token()
headers = {"Authorization": f"token {token}"}  # Sends "token None"
```

**After (Good):**
```python
def get_github_token() -> str:
    """Get GitHub token from config with clear error if missing."""
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        logger.error(
            "missing_github_token",
            operation="get_github_token",
            config_key="GITHUB_TOKEN",
            error="Required GitHub token not configured",
            hint="Set environment variable: export GITHUB_TOKEN=<your_token>",
            severity="config_error"
        )
        raise ConfigurationError(
            "GitHub token not configured. "
            "Set GITHUB_TOKEN environment variable."
        )

    return token
```

### Real Example: Port Already in Use
**Before (Bad):**
```python
def start_server(port=8000):
    app.run(port=port)  # Crashes with generic error
```

**After (Good):**
```python
def start_server(port: int = 8000) -> None:
    """Start server with helpful error if port in use."""
    try:
        app.run(port=port)
    except OSError as e:
        if e.errno == 48:  # Address already in use
            logger.error(
                "port_in_use",
                operation="start_server",
                requested_port=port,
                error=f"Port {port} is already in use",
                hint=f"Either: (1) Use different port (PORT={port+1}), "
                     f"or (2) Kill process: lsof -i :{port}",
                severity="config_error"
            )
            raise ConfigurationError(
                f"Port {port} already in use"
            )
        raise
```

---

## Pattern 3: Data Errors (Corruption/Inconsistency)

### Pattern Template
```python
def process_data_record(record: Dict) -> Optional[DataModel]:
    """Process record with validation and corruption detection."""
    try:
        # Validate required fields
        required_fields = ["id", "created_at", "status"]
        missing_fields = [f for f in required_fields if f not in record]

        if missing_fields:
            logger.error(
                "data_missing_fields",
                operation="process_data_record",
                record_id=record.get("id", "unknown"),
                table="records",
                missing_fields=missing_fields,
                error="Required fields missing from record",
                action="Record will be skipped, manual review needed",
                severity="data_error"
            )
            return None

        # Process and validate
        model = DataModel(**record)
        return model

    except (KeyError, ValueError, TypeError) as e:
        logger.error(
            "data_deserialization_failed",
            operation="process_data_record",
            record_id=record.get("id", "unknown"),
            error_type=type(e).__name__,
            error=str(e),
            raw_record=record,
            action="Record skipped",
            severity="data_error"
        )
        return None
```

### Real Example: Database Record Validation
**Before (Bad):**
```python
def load_issue(row):
    return Issue(
        id=row["id"],
        title=row["title"],
        state=row["state"]
    )  # Crashes if any field is None/missing
```

**After (Good):**
```python
def load_issue(row: Dict) -> Optional[Issue]:
    """Load issue with data validation."""
    try:
        # Validate required fields exist
        required = ["id", "title", "state"]
        missing = [f for f in required if f not in row or row[f] is None]

        if missing:
            logger.error(
                "issue_missing_required_fields",
                operation="load_issue",
                issue_id=row.get("id", "unknown"),
                missing_fields=missing,
                error="Issue record missing required fields",
                action="Record skipped, requires manual review",
                severity="data_error"
            )
            return None

        # Validate field types
        if not isinstance(row["id"], int):
            logger.error(
                "issue_invalid_field_type",
                operation="load_issue",
                issue_id=row.get("id"),
                field="id",
                expected_type="int",
                actual_type=type(row["id"]).__name__,
                error="Issue id must be integer",
                severity="data_error"
            )
            return None

        return Issue(
            id=row["id"],
            title=row["title"],
            state=row["state"]
        )

    except Exception as e:
        logger.error(
            "issue_deserialization_failed",
            operation="load_issue",
            error_type=type(e).__name__,
            error=str(e),
            raw_row=row
        )
        return None
```

### Real Example: API Response Validation
**Before (Bad):**
```python
def parse_github_response(data):
    return {
        "id": data["id"],
        "title": data["title"],
        "status": data["state"]
    }  # Crashes if API returns different structure
```

**After (Good):**
```python
def parse_github_response(data: Dict) -> Optional[Dict]:
    """Parse GitHub API response with structure validation."""
    try:
        # Validate expected structure
        expected_fields = ["id", "title", "state"]
        missing = [f for f in expected_fields if f not in data]

        if missing:
            logger.error(
                "github_response_incomplete",
                operation="parse_github_response",
                expected_fields=expected_fields,
                missing_fields=missing,
                error="GitHub API response missing expected fields",
                actual_response=data,
                action="This API response cannot be processed",
                severity="data_error"
            )
            return None

        return {
            "id": data["id"],
            "title": data["title"],
            "status": data["state"]
        }

    except (KeyError, TypeError) as e:
        logger.error(
            "github_response_parse_failed",
            operation="parse_github_response",
            error=str(e),
            response=data
        )
        return None
```

---

## Pattern 4: System Errors (OS/Resource Issues)

### Pattern Template
```python
def perform_operation_needing_resource():
    """Operation that might fail due to system constraints."""
    try:
        # Attempt operation
        result = operation_requiring_resources()
        return result

    except PermissionError as e:
        logger.error(
            "permission_denied",
            operation="perform_operation_needing_resource",
            path=str(e.filename),
            error="Permission denied",
            current_user=os.getuid(),
            hint="Check file permissions or run with appropriate privileges",
            severity="system_error"
        )
        raise

    except FileNotFoundError as e:
        logger.error(
            "file_not_found",
            operation="perform_operation_needing_resource",
            path=str(e.filename),
            error="File not found",
            severity="system_error"
        )
        raise

    except OSError as e:
        if e.errno == 28:  # No space left on device
            logger.error(
                "disk_space_exhausted",
                operation="perform_operation_needing_resource",
                error="No space left on device",
                severity="system_error"
            )
        raise
```

### Real Example: File Writing
**Before (Bad):**
```python
def save_report(data, path):
    with open(path, "w") as f:
        f.write(data)  # Crashes silently if permission denied
```

**After (Good):**
```python
def save_report(data: str, path: str) -> bool:
    """Save report with permission/space error handling."""
    try:
        with open(path, "w") as f:
            f.write(data)
        return True

    except PermissionError:
        logger.error(
            "report_save_permission_denied",
            operation="save_report",
            path=path,
            error="Permission denied writing to file",
            hint=f"Check permissions on {path} or parent directory",
            severity="system_error"
        )
        return False

    except OSError as e:
        if e.errno == 28:  # No space left on device
            logger.error(
                "report_save_disk_full",
                operation="save_report",
                path=path,
                error="No space left on device",
                severity="system_error"
            )
        else:
            logger.error(
                "report_save_failed",
                operation="save_report",
                path=path,
                error_code=e.errno,
                error=str(e),
                severity="system_error"
            )
        return False
```

---

## Pattern 5: Infrastructure Errors (External Services)

### Pattern Template
```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def call_external_service(endpoint: str):
    """Call external service with automatic retry."""
    try:
        response = requests.get(endpoint, timeout=5)
        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        logger.warning(
            "service_timeout",
            operation="call_external_service",
            endpoint=endpoint,
            timeout_seconds=5,
            retry_attempt=call_external_service.retry.statistics.get("attempt_number", 1),
            action="Retrying with exponential backoff"
        )
        raise

    except requests.ConnectionError as e:
        logger.warning(
            "service_unreachable",
            operation="call_external_service",
            endpoint=endpoint,
            error=str(e),
            action="Retrying with exponential backoff"
        )
        raise

    except Exception as e:
        logger.error(
            "service_call_failed",
            operation="call_external_service",
            endpoint=endpoint,
            error_type=type(e).__name__,
            error=str(e)
        )
        raise
```

### Real Example: GitHub API with Backoff
**Before (Bad):**
```python
def get_github_issues(owner, repo):
    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/issues"
    )
    return response.json()  # Crashes on timeout, rate limit, etc.
```

**After (Good):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def get_github_issues(owner: str, repo: str) -> Optional[List[Dict]]:
    """Fetch GitHub issues with retry on transient failures."""
    try:
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            timeout=5
        )
        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        logger.warning(
            "github_api_timeout",
            operation="get_github_issues",
            endpoint=f"{owner}/{repo}/issues",
            timeout_seconds=5,
            action="Retrying with exponential backoff"
        )
        raise

    except requests.HTTPError as e:
        if response.status_code == 403:
            logger.error(
                "github_api_rate_limited",
                operation="get_github_issues",
                endpoint=f"{owner}/{repo}/issues",
                status_code=403,
                error="API rate limit exceeded",
                action="Wait and retry later"
            )
        else:
            logger.error(
                "github_api_error",
                operation="get_github_issues",
                endpoint=f"{owner}/{repo}/issues",
                status_code=response.status_code,
                error=str(e)
            )
        raise

    except requests.ConnectionError as e:
        logger.warning(
            "github_api_unreachable",
            operation="get_github_issues",
            error=str(e),
            action="Retrying with exponential backoff"
        )
        raise
```

### Real Example: Database Connection with Retry
**Before (Bad):**
```python
def get_db_connection():
    return psycopg2.connect(
        host="db.internal",
        port=5432
    )  # Crashes if database down
```

**After (Good):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=20),
    reraise=True
)
def get_db_connection():
    """Connect to database with retry for transient failures."""
    try:
        conn = psycopg2.connect(
            host="db.internal",
            port=5432,
            connect_timeout=5
        )
        logger.info("database_connected", operation="get_db_connection")
        return conn

    except psycopg2.OperationalError as e:
        logger.warning(
            "database_connection_failed",
            operation="get_db_connection",
            host="db.internal",
            port=5432,
            error=str(e),
            action="Retrying with exponential backoff"
        )
        raise
```

---

## Quick Reference: Error Pattern Selector

**Choose your pattern based on error type:**

| Error Type | When | Pattern | Logging | Recovery |
|-----------|------|---------|---------|----------|
| **Operational** | Expected failures | Catch → Log WARNING | Operation + resource | Continue/Retry |
| **Configuration** | Setup issues | Check early → Log ERROR | Config key + hint | Exit(1) |
| **Data** | Corrupted/invalid | Validate → Log ERROR | Record id + detail | Skip/Abort |
| **System** | OS/resource | Catch specific → Log ERROR | Resource + limits | Fail or fix |
| **Infrastructure** | External service | @retry decorator → Log WARN/ERR | Service + endpoint | Retry w/backoff |

---

## Implementation Checklist

For each exception handler during Phase 7c-7e:

- [ ] Identify exception type
- [ ] Determine error category using hierarchy
- [ ] Choose appropriate pattern from this document
- [ ] Add required logging fields
- [ ] Verify error goes to stderr
- [ ] Add appropriate retry logic (if infrastructure error)
- [ ] Test error path (Phase 7f)
