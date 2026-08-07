# Logging Guide

## Overview

Roadmap uses [structlog](https://www.structlog.org/) for structured logging with JSON output, correlation IDs, and performance tracking.

## Configuration

Logging is configured in `roadmap/shared/logging.py`:

- **Console output**: WARNING level, colored, human-readable
- **File output**: DEBUG level, JSON format, `~/.roadmap/logs/roadmap.log`
- **Rotation**: 10MB files, 5 backups
- **Processors**: Correlation IDs, sensitive data filtering, timing

## Features

### 1. Correlation IDs

Every CLI command gets a unique correlation ID for request tracing:

```python
from roadmap.shared.logging import set_correlation_id, get_correlation_id

# Automatically set by @handle_cli_errors decorator

# Or manually:

correlation_id = set_correlation_id()  # Generates UUID

logger.info("Processing request", user_id=123)  # ID automatically added

```text

Trace all logs for a single request:

```bash
python scripts/analyze_logs.py --correlation-id abc123

```text

### 2. Operation Timing

Track operation duration automatically:

```python
from roadmap.shared.logging import log_operation_timing

# Context manager approach

with log_operation_timing("sync_issues", repo="owner/repo"):
    sync_service.sync_all()

# Decorator approach

from roadmap.shared.logging import log_operation

@log_operation("create_issue", issue_type="bug")
def create_issue(title, body):
    ...

```text

Logs include `duration_ms` and `success` fields.

### 3. Sensitive Data Filtering

Automatically redacts sensitive information:

```python
logger.info("Authenticating", github_token="abc123", user="alice")

# Logged as: {"event": "Authenticating", "github_token": "***REDACTED***", "user": "alice"}

```text

Filtered keys: `token`, `password`, `secret`, `api_key`, `auth`, `credential`

### 4. Layer-Specific Loggers

Use standardized logger names by layer:

```python
from roadmap.shared.logging import (
    get_domain_logger,
    get_application_logger,
    get_infrastructure_logger,
    get_presentation_logger,
)

# Domain layer

logger = get_domain_logger("issue")  # roadmap.domain.issue

# Application layer

logger = get_application_logger("issue_service")  # roadmap.application.issue_service

# Infrastructure layer

logger = get_infrastructure_logger("github")  # roadmap.infrastructure.github

# Presentation layer

logger = get_presentation_logger("cli.issues")  # roadmap.presentation.cli.issues

```text

### 5. Per-Component Log Levels

Configure different log levels for different components:

```python
from roadmap.shared.logging import setup_logging

# Setup with custom levels

setup_logging(
    log_level="INFO",
    custom_levels={
        "infrastructure.github": "DEBUG",  # Verbose GitHub client logs

        "domain": "WARNING",                # Reduce domain noise

    }
)

```text

Or in settings:

```toml
[logging]
level = "INFO"

[logging.levels]
"infrastructure.github" = "DEBUG"
"domain" = "WARNING"

```text

### 6. CLI Error Handling

The `@handle_cli_errors` decorator provides comprehensive error handling:

```python
from roadmap.shared.cli_errors import handle_cli_errors

@click.command()
@handle_cli_errors(command_name="issue create", log_args=True)
def create(title, body):
    """Create a new issue."""
    # Automatically logs:

    # - Command invocation with correlation ID

    # - Filtered arguments (redacts tokens)

    # - Success/failure with timing

    # - Structured error context

    ...

```text

Features:
- Correlation ID generation
- Argument logging with sensitive data filtering
- Entry/exit logging with timing
- Keyboard interrupt handling
- Structured error logging

### 7. Sampling for High-Volume Operations

Reduce log volume for frequently called operations:

```python
from roadmap.shared.logging import should_sample

for item in large_dataset:
    process_item(item)

    # Log only 1% of iterations

    if should_sample(sample_rate=0.01):
        logger.debug("Processed item", item_id=item.id, progress=f"{i}/{total}")

```text

## Log Analysis

Use the log analysis script to examine logs:

```bash

# Overall summary

python scripts/analyze_logs.py

# Show only errors

python scripts/analyze_logs.py --errors-only

# Show slow operations (>1 second)

python scripts/analyze_logs.py --slow-ops --threshold 1000

# Filter by command

python scripts/analyze_logs.py --command create_issue

# Trace a specific request

python scripts/analyze_logs.py --correlation-id abc12345

# Recent entries only

python scripts/analyze_logs.py --recent 100

```text

## Structured Logging Patterns

### Creating an Issue

```python
logger = get_application_logger("issue_service")

logger.info(
    "Creating issue",
    title=title,
    assignee=assignee,
    labels=labels,
    repository=f"{owner}/{repo}",
)

try:
    issue = github_client.create_issue(...)
    logger.info(
        "Issue created successfully",
        issue_id=issue.id,
        issue_number=issue.number,
        url=issue.html_url,
    )
except Exception as e:
    logger.error(
        "Failed to create issue",
        error_type=type(e).__name__,
        error_message=str(e),
    )
    raise

```text

### Sync Operation

```python
logger = get_infrastructure_logger("sync")

with log_operation_timing("sync_issues", repo=f"{owner}/{repo}"):
    logger.info("Starting sync", local_issues=len(local), remote_issues=len(remote))

    for issue in issues_to_sync:
        sync_issue(issue)

    logger.info(
        "Sync completed",
        created=stats.created,
        updated=stats.updated,
        deleted=stats.deleted,
        duration_seconds=stats.duration,
    )

```text

### Error with Context

```python
try:
    result = risky_operation()
except ValidationError as e:
    logger.error(
        "Validation failed",
        error_type="ValidationError",
        field=e.field,
        value=e.value,
        constraints=e.constraints,
        user_id=user.id,
    )
    raise

```text

## Best Practices

1. **Use appropriate log levels**:
   - `DEBUG`: Detailed diagnostic information
   - `INFO`: General informational messages, business events
   - `WARNING`: Unexpected but handled situations
   - `ERROR`: Error events that still allow the application to continue
   - `CRITICAL`: Serious errors causing application failure

2. **Include context**: Add relevant structured data to all log messages
   ```python
   # Good

   logger.info("Issue created", issue_id=123, title=title, assignee=assignee)

   # Bad

   logger.info(f"Created issue {issue_id} with title {title}")
   ```

3. **Use layer-specific loggers**: Makes it easier to filter and configure logging
   ```python
   # Good

   logger = get_infrastructure_logger("github")

   # Bad

   logger = get_logger("roadmap")
   ```

4. **Log operation boundaries**: Log when operations start and complete
   ```python
   with log_operation_timing("complex_operation"):
       do_work()
   ```

5. **Don't log sensitive data**: The scrubbing processor helps, but be mindful
   ```python
   # Good - key name triggers automatic redaction

   logger.info("Authenticating", github_token=token)

   # Better - don't log it at all

   logger.info("Authenticating", user=username)
   ```

6. **Sample high-volume logs**: Don't overwhelm logs with repetitive information
   ```python
   if should_sample(0.01):  # 1% sampling

       logger.debug("Iteration progress", ...)
   ```

7. **Use correlation IDs**: Makes request tracing possible
   ```python
   # Automatically done by @handle_cli_errors

   # Or manually for background tasks:

   correlation_id = set_correlation_id()
   ```

## Troubleshooting

### Finding Errors

```bash
python scripts/analyze_logs.py --errors-only

```text

### Debugging Slow Operations

```bash
python scripts/analyze_logs.py --slow-ops --threshold 500

```text

### Tracing a Request

1. Find correlation ID in error output or logs
2. Trace all related logs:
   ```bash
   python scripts/analyze_logs.py --correlation-id abc12345
   ```

### Enabling Verbose Logging

```python

# Temporary debug mode

setup_logging(debug_mode=True)

# Or per-component

setup_logging(custom_levels={"infrastructure.github": "DEBUG"})

```text

## Migration Guide

### From Old Logging

Before:

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Created issue {issue_id}")

```text

After:

```python
from roadmap.shared.logging import get_application_logger

logger = get_application_logger("issue_service")

logger.info("Issue created", issue_id=issue_id, title=title)

```text

### From Manual Error Handling

Before:

```python
@click.command()
def create(title):
    try:
        issue = create_issue(title)
        click.echo(f"Created: {issue.id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

```text

After:

```python
from roadmap.shared.cli_errors import handle_cli_errors

@click.command()
@handle_cli_errors(command_name="issue create")
def create(title):
    issue = create_issue(title)
    click.echo(f"Created: {issue.id}")

```text

## See Also

- [structlog documentation](https://www.structlog.org/)
- [Python logging best practices](https://docs.python.org/3/howto/logging.html)
- `roadmap/shared/logging.py` - Implementation
- `scripts/analyze_logs.py` - Log analysis tool
