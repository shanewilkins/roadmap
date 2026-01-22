# Phase 7a Tooling Assessment: Error Handling & Logging Detection

## Executive Summary

**Recommendation: HYBRID APPROACH (Option C)**
- Use existing tools (ruff, pylint, bandit) for structural validation
- Supplement with custom script for semantic error handling analysis
- This balances automation with comprehensive coverage

---

## Existing Tool Capabilities

### ✅ Already Installed & Available

#### **Ruff (v0.6.9)** - Currently in use
- **E722**: `bare-except` - Detects bare `except:` clauses ✓
- **Fast execution** - Excellent for CI integration
- **Status**: Already configured in ruff.lint.select

**Result when run:**
```
ruff check roadmap/ --select E722
# Returns: 0 findings (clean codebase)
```

---

#### **Pylint (v3.3.9)** - Currently in use
- **W0702**: `bare-except` - Bare except clause catches all exceptions including system ✓
- **E0702**: `bad-except-order` - Except clauses not in correct order (specific→generic) ✓
- **E0703**: `bare-raise` - Bare raise outside except clause ✓
- **E0704**: `misplaced-bare-raise` - Bare raise in wrong context ✓
- **E0705**: `bad-exception-cause` - Bad exception cause in raise...from ✓
- **E0710**: `raising-non-exception` - Raising non-BaseException class ✓
- **E0712**: `catching-non-exception` - Catching non-Exception type ✓
- **E1200**: `logging-unsupported-format` - Unsupported logging format characters ✓

**Result when run:**
```
pylint roadmap/ --enable=W0702,E0702,E0703,E0704,E0705,E0710,E0712 --exit-zero
# Returns: 10.00/10 rating (no violations found)
```

---

#### **Bandit (v1.9.2)** - Currently in use (security-focused)
- **B101**: `assert_used` - Detects assert statements (skipped for tests)
- **B110**: `try_except_pass` - Detects try/except/pass pattern (intentional skips)
- Can detect some silent failure patterns
- **Limitation**: Not comprehensive for logging detection

---

#### **Flake8 (v7.3.0)** - Currently in use
- **pycodestyle**: PEP 8 compliance
- **pyflakes**: Logical errors
- **mccabe**: Complexity (radon plugin)
- **Limitation**: No built-in rules for exception logging

---

### ❌ Not Installed / Limited

#### **Semgrep** - NOT installed
- **Capability**: Advanced pattern matching for custom rules
- **Use case**: Could write custom rules for "except without logging"
- **Decision**: Overkill for current needs, custom script sufficient

#### **Flake8 Plugins** - Not currently in use
- `flake8-exceptions` - Doesn't exist (unmaintained)
- `flake8-logging` - Focuses on logging format, not error handling
- `pylint-logging` - Limited scope

---

## What Existing Tools Cover ✅

| Issue | Tool | Rule | Status |
|-------|------|------|--------|
| Bare except clauses | ruff | E722 | ✅ Covered |
| Bare except clauses | pylint | W0702 | ✅ Covered |
| Except clause ordering | pylint | E0702 | ✅ Covered |
| Bare raise misplacement | pylint | E0704 | ✅ Covered |
| Invalid exception types | pylint | E0710/E0712 | ✅ Covered |
| Invalid exception cause | pylint | E0705 | ✅ Covered |
| Logging format errors | pylint | E1200 | ✅ Covered |

---

## What Existing Tools DON'T Cover ❌

| Issue | Why Important | Why Tools Can't Detect |
|-------|---------------|------------------------|
| **Except blocks without logging** | Silent failures hide errors | Requires semantic analysis of handler body |
| **Except + pass pattern** | Data loss and debugging blindness | Need context analysis, not just syntax |
| **Except + continue pattern** | Silently skips errors in loops | Would require control flow analysis |
| **Except + return without logging** | Function exits silently | Need semantic tracking of error path |
| **Inconsistent logging frameworks** | Maintenance nightmare (structlog vs logging) | Tools don't understand domain conventions |
| **Missing error context in logs** | Insufficient debugging information | Requires semantic analysis of log content |
| **Swallowed SystemExit/KeyboardInterrupt** | Hard to interrupt programs | Complex flow analysis needed |

---

## Hybrid Approach (Recommended)

### **Phase 7a.1: Use Existing Tools** (Quick Win)
```bash
# Validate structural exception handling
ruff check roadmap/ --select E722
pylint roadmap/ --disable=all --enable=W0702,E0702,E0703,E0704,E0705,E0710,E0712

# Result: 0 violations (codebase already clean)
```

### **Phase 7a.2: Run Custom Audit Script** (Semantic Analysis)
- Use existing `scripts/audit_error_handling.py` for:
  - Exception handlers without logging (primary concern)
  - Except...pass, except...continue patterns
  - Inconsistent logging framework usage
  - Error context quality

### **Phase 7a.3: Document Findings** (Comprehensive Report)
- Combine tool + custom script results
- Create prioritized remediation plan
- Identify architectural patterns to standardize

---

## Why Not Just Existing Tools?

1. **E722/W0702 only catch bare except syntax** - They don't validate that exceptions are actually logged
2. **No tool detects "except + pass" pattern** - We need custom logic to find silent failures
3. **No tool validates logging framework consistency** - Tools don't understand domain conventions
4. **No tool analyzes error context quality** - Tools can't judge log message sufficiency

---

## Why Not Just Custom Script?

1. **We're already running ruff + pylint in CI** - Why duplicate work?
2. **Existing tools are battle-tested** - Better than custom regex patterns
3. **Tools integrate with editor/IDE** - Developers see issues in real-time
4. **Tools have performance advantages** - Especially ruff for large codebases
5. **Standard tools = maintainability** - Easier for team to understand

---

## Decision Matrix

| Approach | Pro | Con |
|----------|-----|-----|
| **Tool-only (A)** | Fast, integrated | Misses semantic issues |
| **Script-only (B)** | Comprehensive | Maintenance burden, no CI integration |
| **Hybrid (C)** | ✓ Best coverage ✓ Maintainable ✓ CI-friendly | Requires coordination |

---

## Next Steps

1. **Run existing tools** (confirm they pass)
   ```bash
   poetry run ruff check roadmap/
   poetry run pylint roadmap/
   ```

2. **Execute custom audit script**
   ```bash
   python3 scripts/audit_error_handling.py > audit_report.txt
   ```

3. **Merge findings** into unified report
4. **Create remediation tasks** for Phase 7b-7e
5. **Add tool checks to pre-commit** if gaps found

---

## Tool Configuration Summary

**Current pyproject.toml Status:**
- ✅ ruff: Configured with E722 (bare-except)
- ✅ pylint: Available but not pre-configured for exception rules
- ✅ bandit: Configured with B101/B110 skips
- ✅ flake8: Available (7.3.0 with mccabe, pycodestyle, pyflakes, radon)

**Recommendation:** Keep current configuration. Add manual pylint run with exception rules during Phase 7a.
