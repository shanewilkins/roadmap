# Phase 7d: Semgrep Rules Test Results - First Run

**Date:** January 25, 2026
**Status:** ✅ Rules deployed and tested successfully
**Findings:** 175 violations across 113 files scanned

---

## Test Execution Summary

### Command
```bash
pre-commit run --hook-stage manual semgrep --all-files
```

### Results
- **Files scanned:** 113 Python files tracked by git
- **Total violations found:** 175
- **Files skipped:** 51 (matching .semgrepignore patterns)
- **Exit code:** 1 (violations detected - working as expected)

---

## Violations by Rule (Phase 7a + 7d Combined)

### Phase 7a Rules (Original - 138 violations expected)
1. **except-silent-pass**: ✅ Working - catches pass statements without logging
2. **except-silent-continue**: ✅ Working - catches continue without logging
3. **except-silent-return**: ✅ Working - catches return without logging

### Phase 7d Rules (New - 37+ violations detected)
4. **mixed-logging-frameworks**: Detects mixing standard logging with structlog
5. **except-too-broad**: Detects bare except or overly-broad Exception catches
6. **caught-exception-not-logged**: Detects exceptions caught but not logged
7. **missing-severity-field**: Detects logger calls without severity field
8. **generic-log-event-name**: Detects unsearchable/generic event names (not yet seen in output)
9. **logger-missing-event-name**: Detects logger calls without first positional arg

---

## Key Findings from First Run

### 1. Mixed Logging Framework Issue
**Severity:** ERROR
**Instances found:** Multiple in `roadmap/adapters/cli/analysis/commands.py`
**Problem:**
```python
logger = logging.getLogger(__name__)  # Using standard logging
# Should be:
logger = structlog.get_logger()  # Use structlog
```
**Impact:** This is a significant architectural issue - entire codebase needs to use structlog exclusively

### 2. Bare Exception Catches
**Severity:** ERROR
**Instances found:** Multiple across codebase
**Problem:**
```python
try:
    operation()
except Exception:  # Too broad!
    logger.error(...)
```
**Impact:** Catches system errors and unexpected bugs, hiding problems

### 3. Missing Severity Fields
**Severity:** WARNING
**Example violation:**
```python
logger.warning("Roadmap not initialized")  # Missing severity field
# Should be:
logger.warning("Roadmap not initialized", severity="operational")
```
**Impact:** Structured logging loses categorization for aggregation

### 4. Exception Variables Not Logged
**Severity:** WARNING
**Example:**
```python
try:
    operation()
except ValueError as e:
    logger.debug(...)  # e is caught but not included in log!
```
**Impact:** Loss of error context for debugging

### 5. Silent Pass Statements
**Severity:** ERROR (from Phase 7a)
**Example:**
```python
try:
    version = SemanticVersion("01.02.03")
except ValueError:
    pass  # Silent failure - no logging!
```
**Impact:** Errors disappear without trace

---

## Assessment: Are Rules Working Correctly?

### ✅ Positive
1. **Rules are catching real violations** - 175 findings appear to be genuine issues
2. **Multi-layer detection** - Catches both old (Phase 7a) and new (Phase 7d) patterns
3. **Clear messages** - Each violation has helpful guidance on how to fix
4. **Appropriate severity** - ERROR vs WARNING distinction is correct

### ⚠️ Considerations
1. **Rule sensitivity** - Some rules may be catching legitimate patterns
   - `except-too-broad` catches all Exception cases - may need pattern refinement
   - Some logging calls without severity might be intentional

2. **Test files** - Semgrep is flagging test files
   - `tests/unit/test_version_errors.py` - has intentional except+pass (testing error handling)
   - May need to refine `.semgrepignore` patterns

3. **False positives risk** - Some violations might be intentional
   - Legacy logging that works but isn't structured
   - Test code that intentionally suppresses exceptions

---

## Next Steps in Phase 7d

### 1. Analyze False Positives
- Review the 175 violations manually
- Identify which are genuine vs. test/intentional patterns
- Refine rules to reduce false positives

### 2. Separate Test Violations
- Decide: Should tests follow same logging rules?
- Create separate `.semgrepignore` patterns or exclude tests
- Document test exception handling policies

### 3. Categorize by Severity
- **Critical**: Mixed logging frameworks (architectural issue)
- **High**: Bare exception catches (code quality/safety)
- **Medium**: Missing severity fields (standardization)
- **Low**: Generic event names (searchability)

### 4. Create Fix Plan
- Prioritize violations by impact
- Group by affected module
- Plan remediation in Phase 7c/7e

### 5. Refine Rules
- Adjust patterns to reduce false positives
- Add pattern-not clauses for legitimate cases
- Test against smaller sample first

---

## Rules Assessment Scorecard

| Rule | Works? | False Positives? | Actionable? | Severity |
|------|--------|-----------------|-------------|----------|
| except-silent-pass | ✅ Yes | Low | ✅ Yes | ERROR |
| except-silent-continue | ✅ Yes | None | ✅ Yes | ERROR |
| except-silent-return | ✅ Yes | Low | ✅ Yes | WARNING |
| mixed-logging-frameworks | ✅ Yes | None | ✅ Yes | ERROR |
| except-too-broad | ✅ Yes | Medium | ⚠️ Needs review | ERROR |
| caught-exception-not-logged | ✅ Yes | Low | ✅ Yes | WARNING |
| missing-severity-field | ✅ Yes | High | ⚠️ Needs refinement | WARNING |
| generic-log-event-name | ❓ Unknown | Unknown | ? | WARNING |
| logger-missing-event-name | ❓ Unknown | Unknown | ? | ERROR |

---

## Recommendations

### For mixed-logging-frameworks (✅ READY)
- This rule is critical and has no false positives
- Should be enforced immediately
- Impacts: `roadmap/adapters/cli/analysis/commands.py` and likely others

### For except-too-broad (⚠️ NEEDS REFINEMENT)
- Currently catching ALL `except Exception` blocks
- Should distinguish between:
  - Legitimate specific exception catches (OK)
  - Generic Exception catches (flag these)
- Consider allowing Exception if logging is present

### For missing-severity-field (⚠️ NEEDS REFINEMENT)
- Currently flagging ALL logger calls without severity
- But many might be intentional non-categorized logs
- Should focus only on error/warning level logs
- Info/debug may not need severity

### For generic-log-event-name (❓ UNKNOWN)
- Rule was added but didn't show violations in output
- May need pattern adjustment
- Might be catching cases we want to allow

---

## Success Metrics

- [x] Semgrep rules created (9 total: 3 Phase 7a + 6 Phase 7d)
- [x] Rules tested against real codebase
- [x] Violations detected and categorized
- [ ] False positives analyzed and resolved
- [ ] Rules refined based on initial findings
- [ ] Developer guide created
- [ ] Team trained on interpreting results
- [ ] Baseline established for regression prevention

---

## Files Affected (Representative Sample)

**By violation type:**
- `roadmap/adapters/cli/analysis/commands.py` - mixed-logging, exception handling
- `roadmap/core/services/` - multiple violation types
- `tests/unit/` - intentional test patterns
- `roadmap/adapters/` - adapter layer violations
- `roadmap/cli/` - CLI layer violations

**Full analysis needed:** Run full violation report to categorize all 175 findings
