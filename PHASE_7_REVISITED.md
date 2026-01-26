# Phase 7 Revisited: Standardized Structured Logging

**Status:** Planning & Scope Clarification  
**Started:** Phase 7d (except-silent violations)  
**Current Focus:** Root cause analysis & comprehensive standard definition  
**Estimated Completion:** 6-8 additional hours after scope alignment

---

## Executive Summary

Phase 7 is NOT primarily about fixing individual violations. It's about establishing a **standardized, machine-enforceable logging pattern** across the entire application codebase.

**Root Problem:** The codebase has inconsistent logging practices:
- Event names are sometimes f-strings (not greppable)
- Severity fields missing or inconsistent
- Exception context sometimes absent
- Parameter order varies
- No enforcement mechanism beyond manual review

**Root Cause:** Phase 7 was approached as "fix violations one by one" rather than "establish a standard then enforce it comprehensively."

**Goal:** 
- Define canonical logging pattern
- Build Semgrep rules that enforce it
- Systematically fix ALL application code to conform
- Document for developers and future AI assistants
- Make future fixes scriptable/automated

---

## Canonical Logging Pattern

### The Standard Form

```python
# In normal code (no exception):
logger.error(
    "event_name",  # ← Static string, snake_case, specific
    field1=value1,
    field2=value2,
    severity="category",  # ← Always required for error/warning
)

# In except blocks:
except SomeException as e:
    logger.error(
        "operation_failed",  # ← Static string, snake_case
        operation="sync",    # ← Context fields
        error=str(e),        # ← Exception as string (ERROR level)
        severity="operational",  # ← Always required
        exc_info=True,       # ← Only for ERROR, not WARNING
    )
```

### Key Rules

1. **Event Name (first positional argument)**
   - MUST be a static string literal
   - MUST be snake_case (all lowercase, underscores)
   - MUST be specific to the error ("operation_failed", not "error")
   - MUST be greppable - `grep "operation_failed"` finds all instances
   - Pattern: `{operation}_{result}` (e.g., "file_read_failed", "sync_completed_with_errors")

2. **Context Fields (kwargs before error)**
   - Any contextual data about what was being done
   - Examples: `operation="sync"`, `filepath="/path/to/file"`, `user_id=123`
   - Order: Logical/semantic (related fields grouped)

3. **Error Context (if exception present)**
   - ERROR level: Include `error=str(e)` AND `exc_info=True`
   - WARNING level: Include `error=str(e)` only (no exc_info for recoverable errors)
   - NEVER interpolate exception into message or event name (defeats searchability)

4. **Severity Field (always required for error/warning)**
   - Categories: `config_error`, `data_error`, `system_error`, `infrastructure`, `operational`
   - Placement: After context fields, before exc_info
   - See severity mapping below

5. **Message String**
   - MUST be the event name only, OR
   - Can use message parameter: `logger.error("event_name", msg="User-facing description")`
   - NEVER f-string the event name: ❌ `logger.error(f"{op}_failed")`

### Severity Categories

| Category | Use Case | Log Level | Examples |
|---|---|---|---|
| `config_error` | Setup/configuration missing or invalid | ERROR | Missing API key, invalid config file, credentials not set |
| `data_error` | Data is corrupt, malformed, or fails validation | ERROR | Parse error, validation failed, corrupt file |
| `system_error` | OS/resource problem, permissions, disk space | ERROR | Permission denied, file not found, no disk space |
| `infrastructure` | External service/network issue | ERROR or WARNING | API timeout, database connection lost, network unreachable |
| `operational` | Expected runtime error, user can retry | WARNING or ERROR | Retry failed, cache miss, operation timeout |

### When to Use exc_info

- ✅ `exc_info=True`: ERROR level, unexpected exceptions, need full debugging context
- ❌ `exc_info=False/omit`: WARNING level, expected/recoverable errors, verbose trace not needed
- 📋 Rationale: Full traces are verbose; most operational errors don't need them

---

## Root Causes & What Went Wrong

### 1. Inconsistent Event Name Practices
**Problem:** Event names sometimes dynamic (f-strings), not greppable
```python
# ❌ WRONG - can't grep for this
logger.error(f"{operation}_failed", error=str(e))

# ✅ RIGHT - greppable static string
logger.error("operation_failed", operation=operation, error=str(e))
```

**Root cause:** No early enforcement; developers naturally took shortcuts

### 2. Missing Severity Fields
**Problem:** 112+ logger.error/warning calls lack severity
**Root cause:** Rule exists but isn't enforced before code review; caught after merge

### 3. Inconsistent Exception Context
**Problem:** 158 violations of exceptions caught but not logged structurally
**Root cause:** Rule was too broad (matched all loggers in try/except); refined but violations still present

### 4. Parameter Order Chaos
**Problem:** Same call structured differently across codebase
```python
# ❌ Different developers, different orders
logger.error("failed", error=str(e), context=x, severity="op")
logger.error("failed", severity="op", error=str(e), context=x)
logger.error("failed", context=x, error=str(e), severity="op")
```

**Root cause:** No documented standard; no automated enforcement

### 5. No Automation Path
**Problem:** Fixes are manual, one-by-one; can't script corrections
**Root cause:** Inconsistency is too severe; no target state to script toward

---

## Semgrep Rules to Enforce This

### Current State
- `caught-exception-not-logged`: Requires error=/exception=/exc_info in except blocks ✓
- `missing-severity-field`: Requires severity field on error/warning calls ✓

### Gaps to Add
Need new rules or refinements:

1. **event-name-must-be-static** (NEW)
   - Reject f-strings as first argument
   - Reject string concatenation
   - Reject variables

2. **event-name-must-be-snake-case** (NEW)
   - Reject camelCase, PascalCase, UPPERCASE
   - Reject spaces or special chars

3. **logger-parameter-order** (NEW)
   - Enforce: event_name, context_fields, error/exception/exc_info, severity
   - Or accept structured order via pattern matching

4. **exc-info-only-on-error** (NEW)
   - Reject `exc_info=True` on logger.warning
   - Allow only on logger.error

5. **refined-caught-exception-not-logged**
   - Current: Requires exception context in except blocks ✓
   - Needs: Ensure it's passed structurally (error= or exception=), not just in message

---

## Scope: What Gets Fixed

### Phase 7 Files (Already Modified)
- Phases 7d, 7e: ~20 files touched for except-silent fixes
- Phases 7f onwards: Any file modified for logging

**Action:** Audit these first for conformity to new standard

### Entire Application Code
- All `roadmap/` files (exclude tests)
- All logger.error() and logger.warning() calls
- Approximately 200-300 violations to fix across codebase

**Rationale:** If we're establishing a standard, it should apply everywhere for consistency

### NOT Included
- Test code (tests log for debugging, different purpose)
- Third-party dependencies
- Generated code

---

## Execution Plan

### Phase 7g: Standardization (This Phase - 6-8 hours)

**Step 1: Inventory & Categorization (1-2 hours)**
- Audit all Phase 7 modified files
- List current violations with context
- Categorize by error type (for appropriate severity values)
- Identify event names that need static conversion

**Step 2: Build Comprehensive Semgrep Rules (1-2 hours)**
- Create rules for all 5 gaps above
- Test on sample files
- Validate they don't produce false positives

**Step 3: Systematic Code Fixes (3-4 hours)**
- Build Python script to:
  - Read all files with violations
  - Determine correct severity for each error
  - Convert f-string event names to static + context parameter
  - Reorder parameters correctly
  - Generate file modifications
- Apply fixes in batches of 20-30 files
- Run pre-commit, fix any lint issues
- Commit per batch

**Step 4: Documentation (1 hour)**
- Create `docs/developer_notes/LOGGING_STANDARD.md`
- Examples of correct vs incorrect patterns
- Severity mapping quick reference
- Common mistakes and fixes
- How to write good event names
- Semgrep rules reference

---

## Future: Making It Scriptable

Once phase complete, future corrections can be:
- **Automated via script** if pattern is consistent
- **Pre-commit hook** to auto-fix before commit
- **AI assistant** can fix new violations using documented pattern
- **Code review** focuses on severity categorization, not formatting

This is the payoff for establishing a strict standard now.

---

## Open Questions for Clarification

1. Should parameter order be strictly enforced by Semgrep, or just documented?
   - Strict = more rules, less flexibility
   - Documented = more flexibility, but requires discipline

2. Should we auto-fix parameter order, or require manual review?
   - Auto-fix = faster, lower risk for reordering
   - Manual = slower but ensures developer understands

3. For event names currently using f-strings, should we:
   - Convert to static + extract variables to context? (Recommended)
   - Leave as-is for now? (Not recommended)

4. Should tests be included after all, for consistency?
   - Current stance: No
   - Reconsider: Tests might benefit from same pattern for clarity

---

## Success Criteria

✅ Phase 7 is complete when:
- [ ] All application logger.error/warning calls follow canonical pattern
- [ ] No f-strings in event names
- [ ] All error/warning calls have severity field
- [ ] All except blocks log exception context structurally
- [ ] All parameter order consistent (context → error → severity → exc_info)
- [ ] Semgrep rules enforce this automatically
- [ ] Documentation written for developers
- [ ] Pre-commit hooks validate before commit
- [ ] CI passes
- [ ] Script exists to fix future violations

---

## Time Estimate Breakdown

- **Inventory & Categorization:** 1-2 hours
- **Semgrep Rule Development:** 1-2 hours
- **Code Fixes (scripted batches):** 3-4 hours
- **Testing & Pre-commit Fixes:** 1 hour
- **Documentation:** 1 hour

**Total: 7-10 hours** (more realistic than initial 5-6 hour estimate)

This is a full afternoon + evening of focused work, but creates a foundation for years of maintainable logging.

---

## Related Documentation

- [`docs/developer_notes/LOGGING_STANDARD.md`](./docs/developer_notes/LOGGING_STANDARD.md) - Detailed pattern guide (to be created)
- [`docs/developer_notes/SEMGREP_QUICK_REFERENCE.md`](./docs/developer_notes/SEMGREP_QUICK_REFERENCE.md) - Rule reference
- [`.semgrep.yml`](./.semgrep.yml) - Enforcement rules
- [`PHASE_7_REMEDIATION_LIST.md`](./PHASE_7_REMEDIATION_LIST.md) - Violation tracking (existing)
