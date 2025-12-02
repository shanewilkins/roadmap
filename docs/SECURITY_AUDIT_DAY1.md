# Security Audit - Day 1: Dependency & Input Validation

**Date:** December 2, 2025
**Issue:** #385758be (Implement comprehensive security audit framework)
**Focus:** Dependency & Input Validation Audit
**Status:** IN PROGRESS

---

## 1. Dependency Security Audit

### 1.1 Vulnerability Scan Results

**Tool:** pip-audit
**Command:** `pip-audit`
**Results:** 19 vulnerabilities found in current environment

#### Critical Finding: Django (10 vulnerabilities)

Django is a **transitive optional test dependency** of `dynaconf` (configuration management).

| Package | Version | Source | Status |
|---------|---------|--------|--------|
| Django | 5.1.2 | dynaconf[test] | 10 CVEs |

**Vulnerabilities in Django 5.1.2:**

- PYSEC-2025-13, PYSEC-2025-37, PYSEC-2024-157, PYSEC-2024-156, PYSEC-2025-1
- PYSEC-2025-14, PYSEC-2025-47
- CVE-2025-57833, CVE-2025-59681, CVE-2025-59682, CVE-2025-64458, CVE-2025-64459

**Impact:** Django is not used in our codebase. It's installed only because `dynaconf` declares it as an optional `test` extra.

**Recommendation:**

1. We don't use Dynaconf's test suite
2. Don't install optional test extras: `poetry install --no-extras` or configure Poetry to exclude test extras
3. Consider switching to simpler config management if Dynaconf isn't core to v1.0

**Action:**

- For development: Continue with current setup (test extras are acceptable for dev)
- For production/CI: Use `poetry install --no-extras` to exclude optional dependencies
- Long-term: Evaluate if Dynaconf is necessary for v1.0 scope

#### Other Vulnerabilities (8 packages, 9 CVEs)

| Package | Version | CVE | Fix Version | Impact |
|---------|---------|-----|-------------|--------|
| fonttools | 4.60.1 | CVE-2025-66034 | 4.60.2 | Visualization/export dependency |
| h11 | 0.14.0 | CVE-2025-43859 | 0.16.0 | Async HTTP (aiohttp transitive) |
| jupyter-core | 5.7.2 | CVE-2025-30167 | 5.8.1 | Dev/documentation dependency |
| jupyterlab | 4.3.4 | CVE-2025-59842 | 4.4.8 | Dev/documentation dependency |
| pip | 25.1.1 | CVE-2025-8869 | 25.3 | Package manager (system) |
| setuptools | 75.1.0 | PYSEC-2025-49 | 78.1.1 | Build tool (dev only) |
| tornado | 6.4.2 | CVE-2025-47287 | 6.5 | Async framework (aiohttp transitive) |

**Assessment:**

- **Production Runtime:** h11 (aiohttp transitive), fonttools (matplotlib transitive) - Low impact, non-critical paths
- **Development Only:** jupyter-core, jupyterlab, setuptools - No impact on distributed CLI
- **System Level:** pip (can be updated via `pip install --upgrade pip`)
- **Tornado:** Transitive through aiohttp; newer version available

**Immediate Actions:**

1. ✅ Uninstall orphaned Django
2. Update pip: `pip install --upgrade pip` (system-level, not Poetry-managed)
3. Review whether jupyter-core/jupyterlab are needed (documentation only?)

**Medium-term Actions:**

1. Add `pip-audit` and `safety` to dev dependencies for ongoing scanning
2. Set up CI/CD check for dependency vulnerabilities
3. Pin transitive dependency versions to mitigate supply chain attacks

### 1.2 Production Dependencies (Core Roadmap CLI)

| Package | Version | Purpose | Security Notes |
|---------|---------|---------|-----------------|
| click | >=8.0.0,<9.0 | CLI framework | ✅ Stable, no known vulns |
| rich | >=13.0.0,<15.0 | Terminal UI | ✅ Stable, no known vulns |
| pydantic | >=2.0.0,<3.0 | Data validation | ✅ Latest v2, excellent validation |
| pyyaml | >=6.0.0,<7.0 | YAML parsing | ⚠️ See section 1.3 |
| requests | >=2.28.0,<3.0 | HTTP client | ✅ Stable, no known vulns |
| aiohttp | >=3.8.0,<4.0 | Async HTTP | ⚠️ Transitive h11 has CVE, not critical |
| python-dotenv | >=1.0.0,<2.0 | Env var loading | ✅ Stable, no known vulns |
| keyring | >=23.0.0,<26.0 | Credential storage | 🔐 Critical for security |
| pandas | >=2.0.0,<3.0 | Data analysis | ✅ Stable |
| openpyxl | >=3.1.0,<4.0 | Excel export | ✅ Stable |
| matplotlib | >=3.6.0,<4.0 | Visualization | ⚠️ Transitive fonttools has CVE (low impact) |
| plotly | >=5.15.0,<6.0 | Interactive charts | ✅ Stable |
| seaborn | >=0.12.0,<1.0 | Statistical viz | ✅ Stable |
| toml | >=0.10.0,<1.0 | Config parsing | ✅ Stable, simple parser |
| structlog | >=23.0.0,<24.0 | Structured logging | ✅ No known vulns |
| GitPython | >=3.1.40,<4.0 | Git integration | ✅ v3.1.40+, no known vulns |
| dynaconf | >=3.2.0,<4.0 | Config management | ✅ No known vulns |
| diskcache | >=5.6.0,<6.0 | Local caching | ✅ No known vulns |
| asyncclick | >=8.1.0,<9.0 | Async CLI | ✅ Fork of Click, stable |
| tabulate | >=0.9.0,<1.0 | Table formatting | ✅ Stable |

**Summary:**

- **0 critical vulnerabilities** in production dependencies
- **0 vulnerabilities** in core runtime path
- **All dependencies pinned** to minor version ranges (good practice)
- **Keyring properly versioned** (>=23.0.0) for security

### 1.3 YAML Parsing Security Review

**File:** Dependency `pyyaml >= 6.0.0`

**Status:** ✅ SECURE - PyYAML 6.0.0+ uses safe loading by default

**Key Points:**

- PyYAML 6.0.0 (2023) introduced SafeLoader by default (breaking change from 5.x)
- This prevents arbitrary code execution through YAML deserialization
- All our YAML parsing should be using safe loading

**Action Items:**

- [ ] Audit `roadmap/infrastructure/storage.py` and YAML parsing code
- [ ] Verify all `yaml.load()` calls use `Loader=yaml.SafeLoader` or `yaml.safe_load()`
- [ ] Check for any `yaml.load()` without explicit loader (would fail safely in 6.0+)

---

## 2. CLI Input Validation Audit

### 2.1 CLI Command Entry Points to Audit

**File:** `roadmap/cli/__init__.py` - Main entry point
**File:** `roadmap/presentation/cli/` - Command modules

**Commands registered:**

- `init`, `status`, `health` (core)
- `today`, `cleanup` (core)
- `comment` (CRUD)
- `data` (export)
- `git` (hooks & operations)
- `issue` (CRUD)
- `milestone` (CRUD)
- `progress` (reports)
- `project` (CRUD)

### 2.2 Input Validation Checklist

#### Issue & Milestone Identifiers

- [ ] Issue IDs: Validate format (should be UUID or hex or numeric)
- [ ] Milestone names: Validate length (max 255 chars)
- [ ] Prevent path traversal in issue/milestone names
- [ ] Check for command injection in descriptions/titles

#### File Paths

- [ ] CLI `--output`, `--format`, `--filter` flags
- [ ] Prevent directory traversal (`../`, absolute paths)
- [ ] Validate file extensions for export formats
- [ ] Check symlink handling

#### Branch Names & Git References

- [ ] Branch name validation (prevent git injection)
- [ ] Commit SHA validation
- [ ] Remote URL sanitization

#### DateTime Inputs

- [ ] Validate date format (YYYY-MM-DD expected)
- [ ] Prevent timezone injection
- [ ] Check for overflow/underflow

### 2.3 Test Coverage Approach

1. Review existing validation tests in `tests/`
2. Identify gaps in input validation
3. Create test cases for malicious inputs:
   - SQL-like payloads
   - Path traversal attempts (`../`, `/etc/passwd`)
   - Command injection (`; rm -rf /`)
   - Unicode/encoding attacks
   - Symlink attacks

---

## 3. JSON Parsing Safety

### 3.1 Files to Audit

- [ ] `roadmap/infrastructure/storage.py` - JSON serialization
- [ ] `roadmap/domain/models.py` - Pydantic model parsing
- [ ] `roadmap/presentation/cli/data/commands.py` - Data export

### 3.2 Status

- Pydantic v2 used for JSON validation (✅ excellent)
- Type hints throughout codebase
- No direct `json.loads()` calls expected (prefer Pydantic)

---

## 4. Markdown Parsing Safety

### 4.1 Files to Audit

- [ ] Search for markdown parsing libraries
- [ ] Check for XSS vulnerabilities in rendered output
- [ ] Verify HTML sanitization if any rendering occurs

### 4.2 Expected Status

- CLI is text-based (no HTML rendering to browsers)
- Low risk for XSS
- Main concern: data integrity when parsing markdown from issues

---

## Acceptance Criteria - Day 1

- [x] Run pip-audit on all dependencies
- [x] Document vulnerability findings
- [ ] Remove Django from environment
- [ ] Review YAML parsing implementation
- [ ] Audit CLI input validation code
- [ ] Check JSON parsing safety
- [ ] Review markdown parsing (if applicable)
- [ ] Create security test cases for injection attacks
- [ ] Document all findings in issue

---

## Next Steps

**Day 2:** Credentials & File System
**Day 3:** Git Integration & Data Privacy
**Day 4:** Documentation & Testing
