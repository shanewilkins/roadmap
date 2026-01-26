# Semgrep Rules Developer Guide

**Last Updated:** January 26, 2026
**Status:** ✅ COMPLETE - All 115 violations fixed (0 findings)
**Audience:** All roadmap developers
**Purpose:** Reference guide for Semgrep rules and compliance standards

---

## Status Update

🎉 **All Semgrep violations have been fixed!** (115 → 0 violations over January 2026)

**Session Progress:**
- ✅ Fixed 36 event-name violations (f-strings → static names with context fields)
- ✅ Fixed 15 silent-pass/silent-return violations (added logging)
- ✅ Fixed 12 remaining violations (event naming, exc_info, severity fields)
- ✅ Final semgrep run: 0 findings across all 12 rules

This document now serves as a **reference guide** for maintaining compliance with our Semgrep standards.

---

## Quick Start

When you see a Semgrep violation in your code:

1. **Find the rule name** - Look for the rule ID in the Semgrep output (e.g., `except-silent-pass`)
2. **Go to the section below** - Find the rule in this guide
3. **Understand what's wrong** - Read the description and violation example
4. **Apply the fix** - Use the provided fix template for your error type
5. **Verify** - Run `pre-commit run --hook-stage manual semgrep --all-files` to confirm

---

## Rules at a Glance

| Rule | Severity | Count | Type | Status |
|------|----------|-------|------|--------|
| [except-silent-pass](#except-silent-pass) | 🔴 ERROR | ✅ 0 | Silent failures | Complete |
| [except-silent-return](#except-silent-return) | 🟠 WARNING | ✅ 0 | Unlogged exits | Complete |
| [except-silent-continue](#except-silent-continue) | 🔴 ERROR | ✅ 0 | Loop skipping | Complete |
| [mixed-logging-frameworks](#mixed-logging-frameworks) | 🔴 ERROR | ✅ 0 | Architecture | Complete |
| [caught-exception-not-logged](#caught-exception-not-logged) | 🟠 WARNING | ✅ 0 | Missing context | Complete |
| [missing-severity-field](#missing-severity-field) | 🟠 WARNING | ✅ 0 | Categorization | Complete |
| [logger-missing-event-name](#logger-missing-event-name) | 🔴 ERROR | ✅ 0 | Missing event | Complete |
| [except-too-broad](#except-too-broad) | 🔴 ERROR | ✅ 0 | Code smell | Complete |

---

## Detailed Rule Explanations

### except-silent-pass

**Severity:** 🔴 ERROR (Highest Priority)
**Count:** 52 violations
**Category:** Silent failures - errors disappearing without trace

#### What It Catches

Exception handlers with `pass` statement and no logging before it:

```python
try:
    parse_config()
except ValueError:
    pass  # ❌ VIOLATION: Error disappears!
```

#### Why It's a Problem

- Errors are swallowed silently
- No audit trail of what went wrong
- Makes debugging nearly impossible
- User has no feedback that something failed

#### How to Fix It

**Pattern:** Add logging BEFORE the `pass` statement

```python
# BEFORE (violation):
try:
    parse_config()
except ValueError as e:
    pass

# AFTER (fixed):
try:
    parse_config()
except ValueError as e:
    logger.error(
        "config_parse_failed",
        operation="load_config",
        error=str(e),
        severity="config_error"
    )
    pass  # Now it's OK - error is logged
```

**Or better:** Don't use `pass`, use a return or raise:

```python
try:
    parse_config()
except ValueError as e:
    logger.error("config_parse_failed", error=str(e), severity="config_error")
    return False  # Better than pass
```

#### Related Patterns

- If loop: Use `except SomeError as e:` with `continue` - still needs logging
- If returning: Use `except SomeError as e:` with `return None/False` - still needs logging
- See [except-silent-return](#except-silent-return) and [except-silent-continue](#except-silent-continue)

#### Error Category from Phase 7b

This depends on WHAT failed:
- **Operational error** (file not found): Use `WARNING` level
- **Configuration error** (invalid config): Use `ERROR` level
- **Data error** (invalid data type): Use `ERROR` level

---

### except-silent-return

**Severity:** 🟠 WARNING (High Priority)
**Count:** 37 violations
**Category:** Unlogged function exits

#### What It Catches

Exception handlers that return without logging:

```python
def process_item(item):
    try:
        transform(item)
    except KeyError:
        return  # ❌ VIOLATION: Silent exit
```

#### Why It's a Problem

- Function exits without explaining why
- Caller doesn't know if return is success or error
- No way to distinguish between:
  - Success: `return None`
  - Failure: `except ... return None` (unlogged)

#### How to Fix It

**Pattern:** Add logging BEFORE return

```python
# BEFORE:
def process_item(item):
    try:
        transform(item)
    except KeyError as e:
        return None

# AFTER:
def process_item(item):
    try:
        transform(item)
    except KeyError as e:
        logger.warning(
            "item_transform_failed",
            operation="transform_item",
            item_id=item.get("id"),
            error=str(e),
            severity="operational"
        )
        return None
```

**If returning different values:**

```python
def process_item(item):
    try:
        result = transform(item)
        return result  # Success
    except KeyError as e:
        logger.warning(
            "item_transform_failed",
            operation="transform_item",
            item_id=item.get("id"),
            error=str(e),
            severity="operational"
        )
        return None  # Failure - now logged
```

#### Context Clues

- Look at what the function returns on success
- If success returns a value, failure should log + return same/different value
- If success returns None, failure should still log + return None

---

### except-silent-continue

**Severity:** 🔴 ERROR
**Count:** 4 violations
**Category:** Silently skipping items in loops

#### What It Catches

Loop exception handlers with `continue` and no logging:

```python
for item in items:
    try:
        process(item)
    except ValueError:
        continue  # ❌ VIOLATION: Item silently skipped
```

#### Why It's a Problem

- Items are skipped with no indication
- User doesn't know some items failed
- No audit trail of what was skipped
- May mask systematic data issues

#### How to Fix It

**Pattern:** Always log when skipping loop items

```python
# BEFORE:
for item in items:
    try:
        process(item)
    except ValueError as e:
        continue

# AFTER:
for item in items:
    try:
        process(item)
    except ValueError as e:
        logger.warning(
            "item_skipped",
            operation="batch_process",
            item_id=item.get("id"),
            error=str(e),
            action="skipped",
            severity="operational"
        )
        continue
```

**Better approach:** Collect and summarize skipped items

```python
skipped_items = []
for item in items:
    try:
        process(item)
    except ValueError as e:
        logger.debug(
            "item_failed",
            item_id=item.get("id"),
            error=str(e)
        )
        skipped_items.append((item, e))

if skipped_items:
    logger.warning(
        "batch_processing_incomplete",
        operation="batch_process",
        total_items=len(items),
        skipped_count=len(skipped_items),
        severity="operational"
    )
```

---

### mixed-logging-frameworks

**Severity:** 🔴 ERROR (Architectural)
**Count:** 6 violations
**Category:** Inconsistent logging frameworks

#### What It Catches

Files that import or use standard `logging` instead of `structlog`:

```python
import logging  # ❌ VIOLATION: Should use structlog

logger = logging.getLogger(__name__)
logger.error("something")
```

#### Why It's a Problem

- Breaks log aggregation consistency
- Standard logging outputs different format than structlog
- Makes filtering/searching logs harder
- Difficult to parse and analyze at scale

#### How to Fix It

**Replace standard logging with structlog:**

```python
# BEFORE:
import logging
logger = logging.getLogger(__name__)
logger.error("operation_failed")

# AFTER:
from structlog import get_logger
logger = get_logger()
logger.error("operation_failed", operation="...", error="...")
```

**Key changes:**
1. Replace `import logging` with `from structlog import get_logger`
2. Replace `logging.getLogger(__name__)` with `get_logger()`
3. Pass structured data as keyword arguments, not format strings

**Structlog example:**

```python
from structlog import get_logger

logger = get_logger()

# ❌ Old way (standard logging):
logger.error("Error occurred: %s", str(e))

# ✅ New way (structlog):
logger.error("operation_failed", operation="load_file", error=str(e))
```

#### Type Annotations

When using logger in type hints, use structlog types:

```python
# BEFORE:
def handler(logger: logging.Logger | None = None):
    self.logger = logger or logging.getLogger(__name__)

# AFTER:
from structlog.typing import FilteringBoundLogger
from structlog import get_logger

def handler(logger: FilteringBoundLogger | None = None):
    self.logger = logger or get_logger()
```

---

### caught-exception-not-logged

**Severity:** 🟠 WARNING
**Count:** 62 violations
**Category:** Missing exception context in logs

#### What It Catches

Exception caught and logged, but exception details not included in log:

```python
try:
    operation()
except ValueError as e:
    logger.error("operation_failed", operation="...")  # Missing e!
```

#### Why It's a Problem

- Exception details are lost
- Stack trace not captured
- Original error message unavailable for debugging
- Log aggregation can't correlate related failures

#### How to Fix It

**Pattern:** Include exception in log context

```python
# BEFORE:
try:
    operation()
except ValueError as e:
    logger.error("operation_failed", operation="load_config")

# AFTER - Option 1 (error string):
try:
    operation()
except ValueError as e:
    logger.error(
        "operation_failed",
        operation="load_config",
        error=str(e)
    )

# AFTER - Option 2 (with stack trace):
try:
    operation()
except ValueError as e:
    logger.error(
        "operation_failed",
        operation="load_config",
        error=str(e),
        exc_info=True  # Includes full stack trace
    )

# AFTER - Option 3 (exception object):
try:
    operation()
except ValueError as e:
    logger.error(
        "operation_failed",
        operation="load_config",
        exception=e
    )
```

**When to use which:**
- **error=str(e)**: Quick fixes, known error types
- **exc_info=True**: For unexpected errors, need full context
- **exception=e**: When structlog handles exception serialization

#### False Positive Cases

This rule sometimes flags code where exception is handled separately:

```python
# This is OK - exception context extracted separately:
try:
    result = get_data()
except ValueError as e:
    context = extract_context(e)  # Using e, just not in logger call
    logger.error("failed", context=context)  # Context passed separately
```

If you get a false positive, it's usually because exception is processed before logging.

---

### missing-severity-field

**Severity:** 🟠 WARNING (Standardization)
**Count:** 124 violations
**Category:** Missing error categorization

#### What It Catches

`error()` or `warning()` calls without `severity` field:

```python
logger.error("operation_failed", operation="...")  # Missing severity field
```

#### Why It's a Problem

- Logs can't be filtered by error category
- Can't distinguish operational vs. data vs. config errors
- Log aggregation systems need this for grouping
- Makes incident response harder

#### How to Fix It

**Pattern:** Add severity field matching error type

```python
# BEFORE:
logger.error("config_parse_failed", operation="load_config", error=str(e))

# AFTER - Choose correct severity:

# For Configuration errors:
logger.error(
    "config_parse_failed",
    operation="load_config",
    error=str(e),
    severity="config_error"  # ← REQUIRED
)

# For Data errors:
logger.error(
    "validation_failed",
    field="email",
    value=provided_value,
    severity="data_error"  # ← REQUIRED
)

# For System errors:
logger.error(
    "permission_denied",
    operation="write_file",
    path="/protected/file",
    severity="system_error"  # ← REQUIRED
)
```

**For WARNING level (Operational errors):**

```python
# For Operational errors:
logger.warning(
    "file_not_found",
    operation="load_config",
    filename=path,
    user_action="Please provide valid file path",
    severity="operational"  # ← REQUIRED
)
```

#### Severity Field Values

From Phase 7b standards:

| Severity Value | Log Level | When to Use | Examples |
|---|---|---|---|
| `operational` | WARNING | Expected, user can retry | file_not_found, timeout, rate_limit |
| `config_error` | ERROR | Setup issue, must fix | missing_api_key, invalid_setting |
| `data_error` | ERROR | Bad/corrupt data | missing_field, invalid_type |
| `system_error` | ERROR | OS/resource issue | permission_denied, disk_full |
| `infrastructure` | WARNING→ERROR | External service down | api_timeout, database_unreachable |

#### Exception

Info/Debug logs DON'T need severity:

```python
# These are OK (no severity needed):
logger.info("operation_started", operation="sync", user_id="123")
logger.debug("batch_processing", items=100, timeout=30)
```

Only `error()` and `warning()` calls need severity field.

---

### logger-missing-event-name

**Severity:** 🔴 ERROR (Code Quality)
**Count:** 0 violations (rare)
**Category:** Incomplete logger calls

#### What It Catches

Logger calls without the required event name (first positional argument):

```python
logger.error()  # ❌ VIOLATION: No event name
```

#### Why It's a Problem

- Event name is required for log aggregation
- Can't search or filter logs without event name
- Violates structured logging principles

#### How to Fix It

**Pattern:** Always provide event name as first positional argument

```python
# BEFORE:
logger.error()

# AFTER:
logger.error(
    "operation_failed",  # ← Event name (first positional arg)
    operation="sync",
    error=str(e)
)
```

#### Event Name Conventions

Event names should be:
- **Specific:** What happened (not just "error")
- **Snake case:** all_lowercase_with_underscores
- **Searchable:** Can grep `"operation_failed"` and find all instances
- **Categorized:** Should match error type

**Good event names:**
- `config_parse_failed`
- `file_not_found`
- `validation_failed`
- `api_timeout`
- `database_connection_lost`

**Bad event names:**
- `error` (too generic)
- `failed` (too vague)
- `err` (abbreviation)
- `Error` (not snake_case)

---

### except-too-broad

**Severity:** 🔴 ERROR (Code Smell)
**Count:** 0 violations (not found)
**Category:** Dangerous exception handling

#### What It Catches

Bare `except:` statements (catch-all with no exception type):

```python
try:
    operation()
except:  # ❌ VIOLATION: Catches everything!
    pass
```

#### Why It's a Problem

- Catches `KeyboardInterrupt`, `SystemExit` (shouldn't be caught)
- Catches own programming bugs (should be fixed, not caught)
- Makes debugging extremely difficult
- Only safe use case: cleanup code, not error handling

#### How to Fix It

**Pattern:** Always specify exception types

```python
# BEFORE (bad):
try:
    operation()
except:
    logger.error("operation_failed")

# AFTER (good):
try:
    operation()
except (ValueError, KeyError) as e:
    logger.error(
        "operation_failed",
        error=str(e),
        severity="data_error"
    )
```

**For different exception types:**

```python
try:
    operation()
except FileNotFoundError as e:
    logger.warning("file_not_found", filename=path, severity="operational")
except PermissionError as e:
    logger.error("permission_denied", filename=path, severity="system_error")
except Exception as e:
    # Only catch Exception if you log it!
    logger.error("unexpected_error", error=str(e), exc_info=True, severity="data_error")
```

#### Exception

If you must catch all exceptions (rare), name them and log:

```python
# This is OK if you log:
try:
    operation()
except Exception as e:  # Broad, but acceptable if logged
    logger.error("unexpected_error", error=str(e), severity="data_error")
```

Bare `except:` is NEVER acceptable.

---

## How to Run Semgrep

### Manually Check All Files

```bash
pre-commit run --hook-stage manual semgrep --all-files
```

### Check Specific Rule

```bash
pre-commit run --hook-stage manual semgrep --all-files -- --include-rule=except-silent-pass
```

### Check Specific File

```bash
pre-commit run --hook-stage manual semgrep --all-files -- roadmap/core/services/
```

### See Detailed Output

```bash
pre-commit run --hook-stage manual semgrep --all-files -- --verbose
```

---

## Severity Levels Explanation

### 🔴 ERROR (Blocking)

These violations prevent code from being reliable. Must be fixed:
- `except-silent-pass` - Errors disappear
- `except-silent-return` - Unlogged exits (WARNING actual, but high priority)
- `except-silent-continue` - Items silently skipped
- `mixed-logging-frameworks` - Breaks consistency
- `except-too-broad` - Catches system errors

### 🟠 WARNING (Important)

These reduce code quality but may be acceptable in some cases:
- `caught-exception-not-logged` - Missing debugging info
- `missing-severity-field` - Can't filter logs
- `logger-missing-event-name` - Can't search logs

---

## Common Questions

### Q: Why does my code flag even though I log before pass?

**A:** You must have the logging BEFORE the pass statement:

```python
# ❌ Still violates:
except ValueError:
    pass
    logger.error("...")  # After pass - doesn't help!

# ✅ Fixed:
except ValueError as e:
    logger.error("operation_failed", error=str(e))
    pass  # Now it's OK
```

### Q: Can I disable a rule for my file?

**A:** Not recommended. But if necessary, use Semgrep comments:

```python
# semgrep: disable=except-silent-pass
try:
    operation()
except ValueError:
    pass  # Exception disabled just for this block
# semgrep: enable=except-silent-pass
```

Better approach: Fix the violation properly.

### Q: What if I don't know what error category applies?

**A:** Check Phase 7b remediation checklist:
- **Operational:** User can retry or fix input
- **Configuration:** Admin must fix setting before running
- **Data:** Data is corrupted/invalid
- **System:** OS/resource problem
- **Infrastructure:** External service down

Most application errors are Operational or Data.

### Q: I caught Exception, is that OK?

**A:** Only if you log it:

```python
try:
    operation()
except Exception as e:  # Broad catch
    logger.error("unexpected_error", error=str(e), severity="data_error")  # But logged!
    # Now acceptable
```

Bare `except:` is NEVER OK.

---

## How to Test Your Fixes

1. **Run Semgrep:** `pre-commit run --hook-stage manual semgrep --all-files`
2. **Check your file:** See if violations are gone
3. **Check the log:** Verify logging is actually being called
4. **Check severity:** Ensure correct severity field for error type
5. **Check event name:** Verify event name is searchable and specific

---

## Getting Help

- **Phase 7b Remediation Checklist:** `PHASE_7b_REMEDIATION_CHECKLIST.md` - Templates for each error type
- **Error Standards:** `roadmap/common/errors/error_standards.py` - See error categories
- **Structlog Documentation:** `roadmap/common/logging/` - See how logging is configured
- **Slack:** Ask in #dev-tools or #roadmap-squad

---

## Summary: Fix Priority

**Fix these first (blocks reliability):**
1. `except-silent-pass` (52 violations) - Errors disappear
2. `except-silent-return` (37 violations) - Unlogged exits

**Fix next (architectural consistency):**
3. `mixed-logging-frameworks` (6 violations) - Use structlog everywhere

**Fix after (code quality):**
4. `caught-exception-not-logged` (62 violations) - Add error context
5. `missing-severity-field` (124 violations) - Add error categories

---
