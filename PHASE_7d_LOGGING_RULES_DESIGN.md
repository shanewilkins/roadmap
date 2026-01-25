# Phase 7d: Logging-Focused Semgrep Rules Design

**Status:** Design phase
**Goal:** Create rules that enforce Phase 7b logging standards
**Foundation:** Error handling patterns from Phase 7b remediation checklist

---

## Rule 1: Incorrect Log Level for Error Category

**Objective:** Prevent using wrong log level for error type

**Anti-patterns to catch:**
```python
# ❌ Using ERROR for Operational error (should be WARNING)
except FileNotFoundError as e:
    logger.error("file_not_found", ...)  # Should be WARNING

# ❌ Using WARNING for Configuration error (should be ERROR)
except ConfigError as e:
    logger.warning("missing_api_key", ...)  # Should be ERROR

# ❌ Using WARNING for Data error (should be ERROR)
except ValueError as e:
    logger.warning("validation_failed", ...)  # Should be ERROR
```

**Detection logic:**
- Detects: Errors containing "not_found", "timeout", "rate_limit" with ERROR level
- Detects: Errors containing "missing", "invalid_config", "key_error" with WARNING level
- Detects: Errors containing "validation", "missing_field", "invalid_type" with WARNING level

**Semgrep pattern:** Multiple pattern-either for each category

---

## Rule 2: Missing Severity Field in Logging

**Objective:** Ensure all log calls include severity field for structured logging

**Anti-patterns to catch:**
```python
# ❌ Missing severity field
logger.error("operation_failed", operation="...", error="...")
# Missing: severity="config_error" or severity="data_error" etc.

# ❌ Empty severity
logger.warning("file_not_found", severity="")

# ❌ Invalid severity value
logger.error("operation_failed", severity="unknown_type")
```

**Valid severity values:**
- `operational` - for WARNING level errors
- `config_error` - for Configuration errors
- `data_error` - for Data errors
- `system_error` - for System errors
- `infrastructure` - for Infrastructure errors

**Semgrep pattern:** Detects logger calls without severity= or with empty/invalid values

---

## Rule 3: Missing Essential Logging Context

**Objective:** Ensure error logs include required context fields

**Anti-patterns to catch:**

For Operational errors (should have):
```python
# ❌ Missing user_action (what should user do?)
logger.warning("file_not_found", operation="...", error="...")
# Missing: user_action="..."
```

For Configuration errors (should have):
```python
# ❌ Missing config_key (which setting is wrong?)
logger.error("missing_setting", operation="...", error="...")
# Missing: config_key="SETTING_NAME"
```

For Data errors (should have):
```python
# ❌ Missing resource_type (what entity failed?)
logger.error("validation_failed", operation="...", error="...")
# Missing: resource_type="issue" and resource_id="..."
```

For System errors (should have):
```python
# ❌ Missing hint (how to fix?)
logger.error("permission_denied", operation="...", error="...")
# Missing: hint="..."
```

**Detection strategy:** Pattern-based detection of logger calls checking for specific required fields

---

## Rule 4: Generic or Unsearchable Event Names

**Objective:** Enforce specific, searchable event naming conventions

**Anti-patterns to catch:**
```python
# ❌ Too generic - not searchable
logger.error("error", ...)
logger.error("failed", ...)
logger.error("operation_error", ...)

# ❌ Too vague - doesn't indicate what happened
logger.error("err", ...)
logger.error("fail", ...)
logger.error("problem", ...)

# ❌ Not snake_case
logger.error("FileNotFound", ...)
logger.error("invalidConfig", ...)
```

**Valid event names must:**
- Be specific (not "error", "failed", "problem")
- Be in snake_case
- Describe WHAT happened: "file_not_found", "validation_failed", "api_timeout"
- Be searchable across logs: `grep "file_not_found"` should find all instances

**Semgrep pattern:** Detects logger calls with event names that are too short, not snake_case, or in generic list

---

## Rule 5: Mixing Standard Logging and Structlog

**Objective:** Ensure consistent use of structlog across codebase

**Anti-patterns to catch:**
```python
# ❌ Mixed imports in same file
import logging
from structlog import get_logger

# ❌ Mixing logger types
logger = logging.getLogger(__name__)
structured_logger = structlog.get_logger()

# ❌ Using standard logging instead of structlog
logging.warning("something")  # Should use structlog
```

**Expected pattern:**
```python
# ✅ Consistent structlog usage
from structlog import get_logger
logger = get_logger()

logger.warning("event_name", **context_dict)
```

**Semgrep pattern:** Detects standard logging imports/calls when structlog is available

---

## Rule 6: Exception Messages Not Included in Log Context

**Objective:** Ensure exception details are captured in logs

**Anti-patterns to catch:**
```python
# ❌ Exception caught but not included in log
try:
    operation()
except ValueError as e:
    logger.error("validation_failed", operation="...")  # Missing e!

# ❌ Exception converted to string poorly
except ValueError as e:
    logger.error("validation_failed", error=str(e))  # OK, but raw_exception better

# ❌ Exception ignored entirely
except ValueError:
    logger.error("validation_failed", operation="...")  # Missing exception
```

**Expected pattern:**
```python
# ✅ Include exception in structured log
try:
    operation()
except ValueError as e:
    logger.error(
        "validation_failed",
        operation="...",
        error=str(e),
        exc_info=True  # Includes traceback if needed
    )
```

**Semgrep pattern:** Detects `except ... as e:` followed by logger call that doesn't reference `e`

---

## Rule 7: Bare Except or Catching Too-Broad Exception

**Objective:** Catch unsafe exception handling patterns

**Anti-patterns to catch:**
```python
# ❌ Bare except catches everything (including KeyboardInterrupt)
try:
    operation()
except:
    logger.error("operation_failed", ...)

# ❌ Catching too broad (Exception catches ours + unexpected)
try:
    operation()
except Exception as e:
    logger.error("operation_failed", ...)
    # This catches MemoryError, SystemExit, etc. - DON'T DO THIS
```

**Expected pattern:**
```python
# ✅ Catch specific exceptions
try:
    operation()
except ValueError as e:
    logger.error("validation_failed", ...)
except FileNotFoundError as e:
    logger.warning("file_not_found", ...)
```

**Semgrep pattern:** Detects bare `except:` or `except Exception:` - flag as ERROR for manual review

---

## Implementation Plan

### Step 1: Create Extended .semgrep.yml
- Add rules 1-7 above
- Each rule has:
  - Clear id (e.g., `log-level-incorrect`)
  - Multiple patterns for variations
  - Message with fix example
  - Severity (ERROR for critical, WARNING for important)
  - Languages: [python]

### Step 2: Test Rules Against Codebase
```bash
# Test each rule individually
semgrep --config=.semgrep.yml --include-rule=log-level-incorrect
semgrep --config=.semgrep.yml --include-rule=missing-severity-field
# ... etc
```

### Step 3: Create Developer Reference
- Document each rule in `docs/SEMGREP_RULES.md`
- Provide fix examples
- Link to Phase 7b remediation checklist

### Step 4: Integrate with Pre-commit
- Add Semgrep to `.pre-commit-config.yaml`
- Configure to run in `manual` mode
- Document in DEVELOPMENT.md

### Step 5: Establish Baseline
```bash
# Create violation baseline
semgrep --config=.semgrep.yml --json > phase-7d-baseline.json
```

---

## Challenges & Solutions

### Challenge 1: False Positives from Generic Patterns
**Solution:**
- Test each rule thoroughly before enabling
- Use pattern-not to exclude known legitimate cases
- Start with ERROR severity, reduce to WARNING if too noisy

### Challenge 2: Incomplete Exception Type Information
**Solution:**
- Some rules (like log level) need to know exception type
- Will need to map common exceptions to categories
- May need to start with manual review category

### Challenge 3: Structlog Context Dict Validation
**Solution:**
- Structlog uses `**context_dict` which is hard to analyze statically
- Will focus on detecting structured calls vs unstructured
- Manual review for completeness of context

---

## Success Metrics for Phase 7d

- [ ] 7 new Semgrep rules created and tested
- [ ] 0 false positives on existing codebase
- [ ] Each rule has clear developer documentation
- [ ] Rules integrated with pre-commit
- [ ] Developer guide published
- [ ] Team trained on reading Semgrep output
- [ ] Baseline established for regression tracking
