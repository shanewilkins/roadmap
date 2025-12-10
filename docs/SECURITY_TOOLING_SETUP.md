# Security & Complexity Tooling Setup

## Overview

The roadmap project includes automated security scanning and complexity analysis as part of the pre-commit hook pipeline. This document describes the setup and how to work with these tools.

## Tools Included

### 1. Bandit - Security Vulnerability Scanner

**Purpose:** Detects common security issues in Python code including:
- SQL injection risks
- Hardcoded secrets/credentials
- Unsafe subprocess calls
- Insecure cryptographic functions

**Configuration:**
- **File:** `.bandit` (TOML format)
- **Severity Level:** HIGH (only fails on high-severity issues)
- **Scope:** All Python files in `roadmap/` directory (excludes tests, docs, scripts, future)

**Pre-commit Hook:**
```yaml
- repo: https://github.com/PyCQA/bandit
  rev: 1.7.6
  hooks:
    - id: bandit
      args: ['-r', '-c', '.bandit', '--severity-level=high']
      additional_dependencies: ['bandit[toml]']
      types: [python]
```

**Known Issues & False Positives:**

1. **B608: SQL Injection in f-string queries**
   - **Status:** SUPPRESSED (configured in `.bandit`)
   - **Reason:** Our codebase uses f-strings only for column names (from internal dict keys), while actual values use parameterized queries with `?` placeholders
   - **Example:** 
     ```python
     cursor = conn.execute(
         f"UPDATE projects SET {set_clause} WHERE id = ?",
         values  # Uses parameterized placeholders
     )
     ```
   - **Files Affected:** `project_repository.py`, `issue_repository.py`, `milestone_repository.py`

**Running Manually:**
```bash
# Full scan
poetry run bandit -r -c .bandit --severity-level=high roadmap

# Scan with all severity levels shown
poetry run bandit -r -c .bandit roadmap

# Scan specific file
poetry run bandit -c .bandit roadmap/file/path.py
```

### 2. Radon - Code Complexity Analysis

**Purpose:** Measures cyclomatic complexity to identify:
- Overly complex functions
- Functions that are hard to understand/maintain
- Refactoring candidates

**Complexity Grades:**
- **A:** 1-5 (simple, very low risk)
- **B:** 6-10 (moderate, low risk)
- **C:** 11-20 (complex, medium risk)
- **D:** 21-30 (very complex, high risk)
- **E:** 31-40 (too complex, very high risk)
- **F:** 41+ (unmaintainable, critical risk)

**Configuration:**
- **Pre-commit Hook:** Local hook using `poetry run radon cc`
- **Arguments:** `--exclude=tests -nb` (shows B and above only)
- **Scope:** All Python files in `roadmap/`

**Pre-commit Hook:**
```yaml
- repo: local
  hooks:
    - id: radon
      name: radon - complexity checking
      entry: poetry run radon cc roadmap --exclude=tests -nb
      language: system
      types: [python]
      pass_filenames: false
      always_run: true
```

**Current Status:**
- **3 functions with B complexity** (moderate, acceptable)
- **0 functions with C+ complexity** (none found)
- **Average complexity:** A (3.1335)

**Functions to Monitor:**
1. `roadmap/infrastructure/logging/audit_logging.py:14` - `get_current_user`
2. `roadmap/infrastructure/logging/decorators.py:21` - `get_current_user` (duplicate)
3. `roadmap/adapters/persistence/cleanup.py:357` - `_resolve_folder_issues`

**Running Manually:**
```bash
# Show all functions (even A complexity)
poetry run radon cc roadmap --exclude=tests

# Show complexity numbers instead of letters
poetry run radon cc roadmap --exclude=tests -n

# Show only B and above
poetry run radon cc roadmap --exclude=tests -nb

# Show detailed complexity metrics
poetry run radon cc roadmap --exclude=tests -a
```

### 3. Vulture - Dead Code Detection

**Purpose:** Finds unused code to keep codebase clean:
- Unused functions
- Unused variables
- Unused imports
- Unused exception handlers

**Configuration:**
- **File:** `.pre-commit-config.yaml`
- **Confidence Threshold:** 80% (reduces false positives)
- **Scope:** All Python files except tests

**Pre-commit Hook:**
```yaml
- repo: https://github.com/jendrikseipp/vulture
  rev: v2.11
  hooks:
    - id: vulture
      args: ['--min-confidence=80', '--exclude=tests', '--ignore-names=exc_*,method_name,Core']
      pass_filenames: true
      types: [python]
```

**False Positive Whitelist:** `.vultureignore`
- `except Exception as e:` (common pattern for error handling)
- `TYPE_CHECKING` imports (used by type annotations only)

**Running Manually:**
```bash
# Full scan with default confidence
poetry run vulture roadmap

# Scan with 60% confidence (more findings)
poetry run vulture --min-confidence=60 roadmap

# Generate whitelist
poetry run vulture roadmap --make-whitelist > .vultureignore
```

## Pre-commit Hook Execution Order

The security and complexity hooks run in this order:

1. **Fast file checks** (< 1 sec)
   - YAML/JSON/TOML syntax validation
   - Merge conflict detection
   - File size limits

2. **Code formatting** (< 1 sec)
   - Ruff formatter
   - Ruff linter

3. **Security scanning** (2-3 sec)
   - **Bandit** (detects security vulnerabilities)

4. **Complexity analysis** (2-3 sec)
   - **Radon** (measures cyclomatic complexity)

5. **Dead code detection** (1-2 sec)
   - **Vulture** (finds unused code)

6. **Type checking** (1-2 sec)
   - **Pyright** (static type analysis)

7. **Cosmetic fixes** (< 1 sec)
   - End-of-file fixers
   - Trailing whitespace removal

## Working with Pre-commit Hooks

### Run all hooks on changed files
```bash
pre-commit run
```

### Run all hooks on all files
```bash
pre-commit run --all-files
```

### Run specific hook
```bash
pre-commit run bandit --all-files
pre-commit run radon --all-files
pre-commit run vulture --all-files
```

### Skip hooks for a commit
```bash
# Skip all hooks
git commit --no-verify

# Still recommended to run manually:
poetry run bandit -r -c .bandit --severity-level=high roadmap
poetry run radon cc roadmap --exclude=tests -nb
poetry run vulture --min-confidence=80 roadmap
```

### Update hook repositories
```bash
pre-commit autoupdate
```

## Entropy Prevention Score

These tools contribute to preventing code entropy (degradation):

| Category | Tool | Coverage | Status |
|----------|------|----------|--------|
| Security | Bandit | 70% | ✅ Enabled |
| Complexity | Radon | 80% | ✅ Enabled |
| Dead Code | Vulture | 80% | ✅ Enabled |
| Documentation | pydocstyle | 20% | ⏸️ Deferred |
| Testing | Coverage enforcement | 0% | ❌ Not implemented |

**Overall Entropy Prevention:** 65% (after Phase 4d improvements)

## Future Improvements

1. **pydocstyle** - Add docstring validation (deferred - requires bulk docstring fixes)
2. **Coverage Enforcement** - Add pytest coverage check to prevent degradation
3. **Architectural Violations** - Detect import cycles and architectural boundary violations
4. **License Compliance** - Add license header validation
5. **Dependency Security** - Add `safety` check for vulnerable dependencies

## References

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Radon Documentation](https://radon.readthedocs.io/)
- [Vulture Documentation](https://github.com/jendrikseipp/vulture)
- [Pre-commit Documentation](https://pre-commit.com/)
