# Semgrep Quick Reference Card

**Status:** ✅ All violations fixed (0 findings)
**Last Updated:** January 26, 2026
**Print this out** or keep it handy as a reference guide for maintaining standards

---

## One-Line Summary Per Rule

| Rule | What It Catches | Quick Fix |
|------|---|---|
| **except-silent-pass** | `except: pass` | Add `logger.error(...)` before pass |
| **except-silent-return** | `except: return` | Add `logger.error(...)` before return |
| **except-silent-continue** | `except: continue` in loop | Add `logger.warning(...)` before continue |
| **mixed-logging-frameworks** | `import logging` | Change to `from structlog import get_logger` |
| **caught-exception-not-logged** | Exception caught but not in log | Add exception to log: `error=str(e)` |
| **missing-severity-field** | `logger.error()` without severity | Add field: `severity="appropriate_type"` |
| **logger-missing-event-name** | `logger.error()` with no arg | Add event name: `logger.error("operation_failed", ...)` |
| **except-too-broad** | Bare `except:` | Specify exception type: `except ValueError as e:` |

---

## Quick Fixes (Copy-Paste Templates)

### except-silent-pass
```python
# FIX THIS:
except ValueError:
    pass

# DO THIS:
except ValueError as e:
    logger.error(
        "operation_failed",
        operation="current_operation",
        error=str(e),
        severity="data_error"  # or config_error, operational, etc.
    )
    pass
```

### except-silent-return
```python
# FIX THIS:
except KeyError:
    return None

# DO THIS:
except KeyError as e:
    logger.error(
        "operation_failed",
        operation="current_operation",
        error=str(e),
        severity="data_error"
    )
    return None
```

### except-silent-continue
```python
# FIX THIS:
for item in items:
    try:
        process(item)
    except ValueError:
        continue

# DO THIS:
for item in items:
    try:
        process(item)
    except ValueError as e:
        logger.warning(
            "item_skipped",
            operation="batch_process",
            item_id=item.id,
            error=str(e),
            severity="operational"
        )
        continue
```

### mixed-logging-frameworks
```python
# FIX THIS:
import logging
logger = logging.getLogger(__name__)

# DO THIS:
from structlog import get_logger
logger = get_logger()
```

### caught-exception-not-logged
```python
# FIX THIS:
except ValueError as e:
    logger.error("operation_failed")

# DO THIS:
except ValueError as e:
    logger.error("operation_failed", error=str(e))
```

### missing-severity-field
```python
# FIX THIS:
logger.error("operation_failed", operation="...")

# DO THIS:
logger.error("operation_failed", operation="...", severity="data_error")
# severity options: config_error, data_error, system_error, operational (WARNING only)
```

### logger-missing-event-name
```python
# FIX THIS:
logger.error()

# DO THIS:
logger.error("operation_failed", operation="...", error=str(e))
```

### except-too-broad
```python
# FIX THIS:
except:
    pass

# DO THIS:
except ValueError as e:
    logger.error("operation_failed", error=str(e), severity="data_error")
```

---

## Severity Field Quick Lookup

| Error Type | Log Level | Severity Value | Example |
|---|---|---|---|
| Expected, user can retry | WARNING | `"operational"` | file_not_found, timeout |
| Setup needed before run | ERROR | `"config_error"` | missing_api_key |
| Bad/corrupt data | ERROR | `"data_error"` | validation_failed |
| OS/resource problem | ERROR | `"system_error"` | permission_denied |
| External service down | WARNING→ERROR | `"infrastructure"` | api_timeout |

---

## Priority Order

**Fix these FIRST (Phase 7c - Reliability):**
1. except-silent-pass (52 violations) ← START HERE
2. except-silent-return (37 violations)
3. except-silent-continue (4 violations)
4. mixed-logging (6 violations)

**Fix these SECOND (Phase 7e - Standardization):**
5. caught-exception-not-logged (62 violations)
6. missing-severity-field (124 violations)

---

## Commands

```bash
# Check all files
pre-commit run --hook-stage manual semgrep --all-files

# Check your file (after fixing)
pre-commit run --hook-stage manual semgrep --all-files -- roadmap/your/file.py

# Check specific rule
pre-commit run --hook-stage manual semgrep --all-files -- --include-rule=except-silent-pass

# See line numbers
pre-commit run --hook-stage manual semgrep --all-files 2>&1 | grep "\.py"
```

---

## Common Questions

**Q: Which errors are most critical?**
A: except-silent-pass (52) - errors disappear completely

**Q: Should I fix all violations at once?**
A: No - fix by rule, prioritize silent failures first

**Q: What severity for my error?**
A: See table above. When in doubt: data_error

**Q: Can I ignore some violations?**
A: Only test files and documented exceptions

**Q: How long does each fix take?**
A: 30 seconds to 5 minutes depending on complexity

---

## Need More Help?

- **Full documentation:** `docs/SEMGREP_RULES.md`
- **Error categories:** `PHASE_7b_REMEDIATION_CHECKLIST.md`
- **Design decisions:** `PHASE_7d_LOGGING_RULES_DESIGN.md`

---
