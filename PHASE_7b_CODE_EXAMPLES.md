# Phase 7b-4: Code Examples - Before/After

**Status:** Phase 7b - Part 4 of 5
**Objective:** Show real-world before/after examples to guide Phase 7c-7e
**Usage:** Reference when implementing fixes in actual codebase

---

## Example 1: Silent Exception (Operational Error)

### ❌ BEFORE (Bad) - From Audit Findings
```python
# roadmap/adapters/cli/commands/create.py (simplified)
def create_issue_from_file(file_path: str) -> Issue:
    """Create issue from YAML file."""

    try:
        with open(file_path) as f:
            data = yaml.safe_load(f)

        issue = Issue.from_dict(data)
        return issue

    except FileNotFoundError:
        pass  # Silent failure - Problem! ❌

    except yaml.YAMLError:
        pass  # Silent failure - Problem! ❌
```

**Problems:**
- Callers don't know if operation succeeded or failed
- No context for debugging
- User sees nothing, assumes it worked
- Exception swallowed with no logging

### ✅ AFTER (Good) - Using Error Hierarchy
```python
# roadmap/adapters/cli/commands/create.py
import structlog
from pathlib import Path

logger = structlog.get_logger()

def create_issue_from_file(file_path: str) -> Optional[Issue]:
    """Create issue from YAML file.

    Args:
        file_path: Path to YAML file containing issue data

    Returns:
        Issue if successful, None if file not found or invalid format
    """

    try:
        with open(file_path) as f:
            data = yaml.safe_load(f)

        issue = Issue.from_dict(data)
        return issue

    except FileNotFoundError:
        # Operational error - expected, user-recoverable
        logger.warning(
            "issue_file_not_found",
            operation="create_issue_from_file",
            path=file_path,
            error="Issue file not found",
            user_action=f"Please create {file_path} or specify valid file path",
            severity="operational"
        )
        return None

    except yaml.YAMLError as e:
        # Operational error - user provided invalid file format
        logger.warning(
            "issue_file_invalid_yaml",
            operation="create_issue_from_file",
            path=file_path,
            error=f"Invalid YAML format: {str(e)}",
            line=e.problem_mark.line if hasattr(e, 'problem_mark') else None,
            user_action="Check YAML syntax in file",
            severity="operational"
        )
        return None

    except Exception as e:
        # Unexpected error
        logger.error(
            "issue_file_parse_failed",
            operation="create_issue_from_file",
            path=file_path,
            error_type=type(e).__name__,
            error=str(e),
            severity="system_error"
        )
        raise
```

**Improvements:**
- ✅ Operational errors logged at WARNING level
- ✅ Clear error messages for each failure mode
- ✅ User gets actionable suggestion
- ✅ Unexpected errors still raised
- ✅ Caller can check return value

---

## Example 2: Bare Except with Continue (Loop Anti-pattern)

### ❌ BEFORE (Bad) - From Audit Findings
```python
# roadmap/core/services/sync_service.py (simplified)
def sync_all_issues(repo_list: List[str]) -> None:
    """Sync issues from all repositories."""

    for repo in repo_list:
        try:
            issues = fetch_github_issues(repo)
            save_to_database(issues)

        except:  # Bare except - Problem! ❌
            continue  # Silent continue - Problem! ❌
```

**Problems:**
- Catches ALL exceptions including KeyboardInterrupt, SystemExit
- No logging - we don't know which repos failed
- Loop continues silently - data inconsistency
- Impossible to debug failures

### ✅ AFTER (Good) - Using Error Hierarchy
```python
# roadmap/core/services/sync_service.py
import structlog
from typing import Optional

logger = structlog.get_logger()

def sync_all_issues(repo_list: List[str]) -> dict:
    """Sync issues from all repositories.

    Args:
        repo_list: List of repository names (owner/repo format)

    Returns:
        Dictionary with stats: {synced: N, skipped: N, failed: N}
    """

    results = {"synced": 0, "skipped": 0, "failed": 0}

    for repo in repo_list:
        try:
            logger.info("syncing_repo", operation="sync_all_issues", repo=repo)

            issues = fetch_github_issues(repo)
            save_to_database(issues)

            results["synced"] += 1
            logger.info(
                "repo_synced",
                operation="sync_all_issues",
                repo=repo,
                issue_count=len(issues)
            )

        except requests.Timeout as e:
            # Infrastructure error - service temporarily unavailable
            logger.warning(
                "github_api_timeout_syncing_repo",
                operation="sync_all_issues",
                repo=repo,
                service="github",
                endpoint=f"https://api.github.com/repos/{repo}/issues",
                timeout_seconds=5,
                error="API timeout",
                action="Skipping repo, will retry in next sync cycle",
                severity="infrastructure"
            )
            results["skipped"] += 1

        except (requests.ConnectionError, requests.HTTPError) as e:
            # Infrastructure error - API unavailable
            logger.error(
                "github_api_failed_syncing_repo",
                operation="sync_all_issues",
                repo=repo,
                service="github",
                error_type=type(e).__name__,
                error=str(e),
                action="Skipping repo, will retry in next sync cycle",
                severity="infrastructure"
            )
            results["failed"] += 1

        except Exception as e:
            # Unexpected error
            logger.error(
                "sync_repo_failed",
                operation="sync_all_issues",
                repo=repo,
                error_type=type(e).__name__,
                error=str(e),
                severity="system_error"
            )
            results["failed"] += 1

    logger.info(
        "sync_complete",
        operation="sync_all_issues",
        repos_synced=results["synced"],
        repos_skipped=results["skipped"],
        repos_failed=results["failed"]
    )

    return results
```

**Improvements:**
- ✅ Specific exception types caught (not bare except)
- ✅ Each error type logged appropriately
- ✅ Loop continues but we track what failed
- ✅ Results returned to caller
- ✅ Clear audit trail of what happened
- ✅ Different handling for infrastructure vs system errors

---

## Example 3: Return Without Logging (Silent Exit)

### ❌ BEFORE (Bad) - From Audit Findings
```python
# roadmap/adapters/github/github_adapter.py (simplified)
def validate_github_credentials() -> bool:
    """Validate GitHub credentials."""

    try:
        # Try to use credentials
        response = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}"}
        )

        if response.status_code == 401:
            return False  # Silent failure - Problem! ❌

        return True

    except Exception as e:
        return False  # Silent failure - Problem! ❌
```

**Problems:**
- No logging - we don't know WHY validation failed
- Caller only gets True/False, no context
- Impossible to debug authentication issues
- Different failure modes all look the same

### ✅ AFTER (Good) - Using Error Hierarchy
```python
# roadmap/adapters/github/github_adapter.py
import structlog

logger = structlog.get_logger()

def validate_github_credentials(token: str) -> bool:
    """Validate GitHub API credentials.

    Args:
        token: GitHub API token

    Returns:
        True if credentials are valid, False otherwise
    """

    try:
        response = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}"},
            timeout=5
        )

        if response.status_code == 401:
            # Configuration error - credentials invalid
            logger.error(
                "invalid_github_credentials",
                operation="validate_github_credentials",
                error="GitHub token is invalid or expired",
                status_code=401,
                hint="Generate new token at https://github.com/settings/tokens",
                severity="config_error"
            )
            return False

        if response.status_code == 403:
            # Configuration error - insufficient permissions
            logger.error(
                "insufficient_github_permissions",
                operation="validate_github_credentials",
                error="GitHub token has insufficient permissions",
                status_code=403,
                required_scopes=["repo", "read:org"],
                hint="Regenerate token with required scopes",
                severity="config_error"
            )
            return False

        if response.status_code != 200:
            # Unexpected HTTP error
            logger.error(
                "github_validation_request_failed",
                operation="validate_github_credentials",
                error="GitHub API returned unexpected status",
                status_code=response.status_code,
                response_body=response.text[:200],  # First 200 chars
                severity="infrastructure"
            )
            return False

        logger.info("github_credentials_valid", operation="validate_github_credentials")
        return True

    except requests.Timeout:
        # Infrastructure error - API not responding
        logger.warning(
            "github_validation_timeout",
            operation="validate_github_credentials",
            error="GitHub API timeout",
            timeout_seconds=5,
            action="Cannot validate credentials now, will retry later",
            severity="infrastructure"
        )
        return False

    except requests.ConnectionError as e:
        # Infrastructure error - network issue
        logger.warning(
            "github_validation_connection_failed",
            operation="validate_github_credentials",
            error=str(e),
            action="Cannot validate credentials now, will retry later",
            severity="infrastructure"
        )
        return False

    except Exception as e:
        # Unexpected error
        logger.error(
            "github_validation_failed",
            operation="validate_github_credentials",
            error_type=type(e).__name__,
            error=str(e),
            severity="system_error"
        )
        return False
```

**Improvements:**
- ✅ Each failure mode logged separately
- ✅ Configuration errors clearly identified
- ✅ Infrastructure errors distinguished from auth errors
- ✅ Caller still gets True/False but now we have full audit trail
- ✅ Different error types suggest different recovery actions

---

## Example 4: Missing Error Context in Data Processing

### ❌ BEFORE (Bad) - From Audit Findings
```python
# roadmap/core/models/issue.py (simplified)
def deserialize_issue(data: dict) -> Issue:
    """Load issue from dictionary."""

    try:
        return Issue(
            id=data["id"],
            title=data["title"],
            state=data["state"],
            created_at=datetime.fromisoformat(data["created_at"])
        )
    except Exception:
        pass  # Silent - Problem! ❌
```

**Problems:**
- No logging - which field failed? Why?
- Callers don't know if operation succeeded
- Impossible to find bad data records
- Silent corruption spreading through database

### ✅ AFTER (Good) - Using Error Hierarchy
```python
# roadmap/core/models/issue.py
import structlog
from typing import Optional
from datetime import datetime

logger = structlog.get_logger()

def deserialize_issue(data: dict) -> Optional[Issue]:
    """Load issue from dictionary.

    Args:
        data: Dictionary from API or database

    Returns:
        Issue object if successful, None if data is invalid
    """

    try:
        # First validate required fields exist
        required_fields = ["id", "title", "state", "created_at"]
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            logger.error(
                "issue_missing_required_fields",
                operation="deserialize_issue",
                issue_id=data.get("id", "unknown"),
                missing_fields=missing_fields,
                error="Required fields missing from issue data",
                action="Record will be skipped",
                severity="data_error"
            )
            return None

        # Validate field types
        if not isinstance(data["id"], int):
            logger.error(
                "issue_invalid_id_type",
                operation="deserialize_issue",
                issue_id=data.get("id"),
                field="id",
                expected_type="int",
                actual_type=type(data["id"]).__name__,
                severity="data_error"
            )
            return None

        if not isinstance(data["title"], str):
            logger.error(
                "issue_invalid_title_type",
                operation="deserialize_issue",
                issue_id=data["id"],
                field="title",
                expected_type="str",
                actual_type=type(data["title"]).__name__,
                severity="data_error"
            )
            return None

        # Parse timestamp with error handling
        try:
            created_at = datetime.fromisoformat(data["created_at"])
        except (ValueError, TypeError) as e:
            logger.error(
                "issue_invalid_timestamp",
                operation="deserialize_issue",
                issue_id=data["id"],
                field="created_at",
                provided_value=data["created_at"],
                error=f"Invalid timestamp format: {str(e)}",
                expected_format="ISO 8601 (e.g., 2024-01-15T14:30:00Z)",
                severity="data_error"
            )
            return None

        # Create issue
        return Issue(
            id=data["id"],
            title=data["title"],
            state=data["state"],
            created_at=created_at
        )

    except Exception as e:
        # Unexpected error
        logger.error(
            "issue_deserialization_failed",
            operation="deserialize_issue",
            error_type=type(e).__name__,
            error=str(e),
            data=data,
            severity="system_error"
        )
        return None
```

**Improvements:**
- ✅ Missing fields detected and logged
- ✅ Type validation with specific error messages
- ✅ Timestamp parsing errors caught with context
- ✅ Full data available for debugging if unexpected error
- ✅ Caller knows what failed and why

---

## Example 5: Configuration Validation at Startup

### ❌ BEFORE (Bad) - Configuration Applied Later
```python
# roadmap/cli.py (simplified)
def main():
    """Main CLI entry point."""

    token = os.getenv("GITHUB_TOKEN")  # Returns None silently

    # ... lots of code ...

    # Crashes later when actually used
    headers = {"Authorization": f"token {token}"}  # "token None"
```

**Problems:**
- Missing config not detected at startup
- Crashes much later with cryptic error
- User doesn't know what to fix
- Wastes time with misleading error messages

### ✅ AFTER (Good) - Fail Fast at Startup
```python
# roadmap/cli.py
import structlog
import sys
from pathlib import Path

logger = structlog.get_logger()

class ConfigurationError(Exception):
    """Raised when required configuration is missing."""
    pass

def validate_configuration():
    """Validate all required configuration at startup."""

    errors = []

    # Check GitHub token
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        errors.append({
            "key": "GITHUB_TOKEN",
            "error": "Required environment variable not set",
            "fix": "export GITHUB_TOKEN=<your_token>"
        })

    # Check database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        errors.append({
            "key": "DATABASE_URL",
            "error": "Required environment variable not set",
            "fix": "export DATABASE_URL=postgres://..."
        })

    # Check output directory
    output_dir = os.getenv("OUTPUT_DIR", "./output")
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    except PermissionError:
        errors.append({
            "key": "OUTPUT_DIR",
            "error": f"Permission denied: cannot write to {output_dir}",
            "fix": f"Check directory permissions"
        })

    # Report all errors at once (better UX)
    if errors:
        for err in errors:
            logger.error(
                "missing_configuration",
                config_key=err["key"],
                error=err["error"],
                hint=err["fix"],
                severity="config_error"
            )

        raise ConfigurationError(
            f"Missing {len(errors)} required configuration settings. "
            "Check logs above for details."
        )

def main():
    """Main CLI entry point."""

    try:
        validate_configuration()
    except ConfigurationError as e:
        logger.error("startup_configuration_failed", error=str(e))
        sys.exit(1)

    # Now we know configuration is valid
    run_application()
```

**Improvements:**
- ✅ Configuration validated at startup (fail fast)
- ✅ All errors reported together (better UX)
- ✅ Clear error messages with fixes
- ✅ Exit with non-zero code on failure
- ✅ No cryptic errors later during execution

---

## Example 6: External Service Call with Retry

### ❌ BEFORE (Bad) - No Retry Logic
```python
# roadmap/adapters/github/issues.py (simplified)
def fetch_github_issues(owner: str, repo: str) -> List[dict]:
    """Fetch issues from GitHub."""

    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/issues"
    )

    return response.json()  # Crashes on timeout
```

**Problems:**
- No retry logic - transient failures kill the operation
- No logging - we don't know what happened
- No timeout - can hang indefinitely
- Network blips cause cascading failures

### ✅ AFTER (Good) - Retry with Backoff and Logging
```python
# roadmap/adapters/github/issues.py
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import requests

logger = structlog.get_logger()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    reraise=True
)
def fetch_github_issues(owner: str, repo: str) -> Optional[List[dict]]:
    """Fetch issues from GitHub with retry logic.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        List of issues if successful, None on permanent failure
    """

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
            operation="fetch_github_issues",
            owner=owner,
            repo=repo,
            timeout_seconds=5,
            action="Retrying with exponential backoff",
            severity="infrastructure"
        )
        raise  # Let @retry decorator handle it

    except requests.ConnectionError as e:
        logger.warning(
            "github_api_unreachable",
            operation="fetch_github_issues",
            owner=owner,
            repo=repo,
            error=str(e),
            action="Retrying with exponential backoff",
            severity="infrastructure"
        )
        raise  # Let @retry decorator handle it

    except requests.HTTPError as e:
        if response.status_code == 403:
            # Rate limited - don't retry immediately
            logger.error(
                "github_api_rate_limited",
                operation="fetch_github_issues",
                owner=owner,
                repo=repo,
                status_code=403,
                reset_time=response.headers.get("X-RateLimit-Reset"),
                error="GitHub API rate limit exceeded",
                action="Wait and retry later",
                severity="infrastructure"
            )
        elif response.status_code == 401:
            # Unauthorized - auth issue
            logger.error(
                "github_api_unauthorized",
                operation="fetch_github_issues",
                status_code=401,
                error="GitHub API returned 401 Unauthorized",
                hint="Check GITHUB_TOKEN is valid",
                severity="config_error"
            )
        else:
            logger.error(
                "github_api_error",
                operation="fetch_github_issues",
                owner=owner,
                repo=repo,
                status_code=response.status_code,
                error=str(e),
                severity="infrastructure"
            )
        return None

    except Exception as e:
        logger.error(
            "fetch_issues_failed",
            operation="fetch_github_issues",
            owner=owner,
            repo=repo,
            error_type=type(e).__name__,
            error=str(e)
        )
        return None
```

**Improvements:**
- ✅ Automatic retry with exponential backoff for transient errors
- ✅ Different handling for permanent (auth) vs transient (timeout) errors
- ✅ Rate limiting detected and reported
- ✅ Timeout prevents hanging
- ✅ Clear logging at each retry attempt
- ✅ Caller gets None on permanent failure instead of exception

---

## How to Use These Examples

### During Phase 7c (Core Services)
1. Find exception handlers in `roadmap/core/services/*.py`
2. Match pattern to error type
3. Apply "After" pattern structure
4. Update logging to match hierarchy

### During Phase 7d (CLI Handling)
1. Find exception handlers in `roadmap/adapters/cli/commands/*.py`
2. Look for silent failures (except with pass/return)
3. Add logging context
4. Ensure user gets helpful message

### During Phase 7e (Adapters)
1. Find exception handlers in adapter files (github, git, persist)
2. Add retry logic if external service call
3. Classify error type
4. Log appropriate level and context

---

## Common Patterns to Look For

- [ ] `except: pass` → Add logging, return None
- [ ] `except Exception: return` → Log error, return None
- [ ] Multiple except blocks with same body → Consolidate, add specific logging
- [ ] No timeout on network calls → Add timeout + logging
- [ ] No retry on transient errors → Add @retry decorator
- [ ] Error message only in exception → Add context fields
- [ ] Using print for errors → Change to logger
- [ ] Catching bare Exception → Catch specific types
