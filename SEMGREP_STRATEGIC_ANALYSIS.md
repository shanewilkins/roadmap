# Semgrep: Strategic Toolchain Integration Analysis

**Date:** January 22, 2026
**Status:** Analysis for Phase 7 and beyond

---

## What is Semgrep?

**Semgrep** is an **AST-based pattern matching engine** that detects bugs, security vulnerabilities, and enforces coding standards through declarative YAML rules.

**Key differentiators:**
- Works on Abstract Syntax Trees (AST), not regex - catches semantic issues our custom script misses
- 30+ languages supported (Python, JavaScript, Go, Java, C#, etc.)
- 2,000+ pre-built rules from Semgrep registry
- Rule-as-code (YAML) - easy to understand, review, modify
- Integrates with CI/CD, pre-commit, IDEs, and Slack
- Active maintenance with regular rule updates
- Free tier available for open source

---

## Current Roadmap Toolchain Analysis

### What We Have (8/10)
```
✅ Formatting:      ruff format
✅ Linting:         ruff check
✅ Type checking:   pyright
✅ Security:        bandit (focused)
✅ Complexity:      radon
✅ Dead code:       vulture
✅ Duplication:     jscpd
✅ Architecture:    import-linter
✅ Documentation:   pydocstyle
```

### What We're Missing (The Gap)
```
❌ Semantic bug detection (beyond syntax)
❌ Domain-specific pattern enforcement
❌ API misuse detection
❌ Anti-pattern detection
❌ Custom business logic validation
❌ Security beyond bandit scope
❌ Secrets detection
❌ Dependency vulnerability scanning
```

---

## What Semgrep Can Do for Roadmap

### 1. Error Handling & Logging (Phase 7a - PRIMARY)

**Rule: Except without logging**
```yaml
rules:
  - id: except-without-logging
    patterns:
      - pattern-either:
          - pattern: |
              try:
                  ...
              except $EXCEPTION:
                  pass
          - pattern: |
              try:
                  ...
              except $EXCEPTION:
                  continue
          - pattern: |
              try:
                  ...
              except $EXCEPTION:
                  return
    message: "Exception handler without logging - silent failure detected"
    severity: ERROR
```

**Catches:** All 121 violations we found in audit (83 files, 30 except+pass, 8 except+continue)

### 2. Logging Consistency (Phase 7b-7e)

**Rule: Structlog vs standard logging inconsistency**
```yaml
rules:
  - id: mixed-logging-frameworks
    pattern-either:
      - pattern: |
          import logging
          ...
          logger = structlog.get_logger()
      - pattern: |
          from logging import getLogger
          ...
          logger = structlog.get_logger()
    message: "Mixing standard logging and structlog imports"
    severity: WARNING
```

**Catches:** Framework inconsistency before it spreads

### 3. Error Context Quality (Phase 7f - Testing)

**Rule: Logger without context**
```yaml
rules:
  - id: logger-missing-context
    pattern-either:
      - pattern: logger.error($MSG)
      - pattern: logger.warning($MSG)
    message: "Logging without context - add error type and values"
    severity: WARNING
```

**Catches:** Low-quality error logs

### 4. CLI Error Routing (Phase 7d)

**Rule: Print to stdout in error handlers**
```yaml
rules:
  - id: print-in-exception-handler
    patterns:
      - pattern: |
          try:
              ...
          except:
              print(...)
    message: "Print in exception handler - use stderr or logger instead"
    severity: ERROR
```

**Catches:** Errors going to stdout instead of stderr

### 5. Async/Await Errors (Current Issues)

**Rule: Missing await in async functions**
```yaml
rules:
  - id: missing-await
    pattern: |
        async def $FUNC(...):
            ...
            $COROUTINE(...)
    message: "Coroutine called without await"
    severity: ERROR
```

**Catches:** Common async bugs

### 6. Configuration Validation

**Rule: Hardcoded secrets (Beyond bandit)**
```yaml
rules:
  - id: hardcoded-api-key
    pattern-either:
      - pattern: api_key = "sk_live_..."
      - pattern: PASSWORD = "..."
    message: "Hardcoded secret found"
    severity: CRITICAL
```

**Catches:** Secrets before they're committed

### 7. API Misuse (Custom Domain)

**Rule: Click decorator ordering**
```yaml
rules:
  - id: click-decorator-order
    pattern: |
        @click.option(...)
        @click.command()
        def $FUNC(...):
    message: "Click command decorator must be outermost (@click.command on top)"
    severity: WARNING
```

**Catches:** Common Click framework mistakes in our codebase

### 8. Data Validation (Custom Domain)

**Rule: Unvalidated external input**
```yaml
rules:
  - id: unvalidated-github-input
    pattern: |
        response = requests.get($URL)
        data = response.json()
        return data
    message: "GitHub API response not validated - add schema validation"
    severity: WARNING
```

**Catches:** Data integrity issues

### 9. Performance Anti-patterns

**Rule: N+1 database queries**
```yaml
rules:
  - id: n-plus-one-query
    pattern: |
        for $ITEM in $ITEMS:
            $RESULT = db.query(...)
    message: "Potential N+1 query pattern - consider batch query"
    severity: WARNING
```

**Catches:** Performance issues in sync operations

### 10. Testing Gaps

**Rule: Unimplemented tests**
```yaml
rules:
  - id: unimplemented-test
    pattern: |
        def test_$NAME(...):
            pass
    message: "Test not implemented"
    severity: WARNING
```

**Catches:** Empty test stubs

---

## Pre-built Rule Sets Available

### Semgrep Registry (Free)
- **Security:** 500+ rules for OWASP Top 10, CWE coverage
- **Code Quality:** 100+ rules for common bugs
- **Secrets:** 630+ types of credentials
- **Framework-specific:** Django, Flask, FastAPI, Click, etc.
- **Language-specific:** Python security rules, typing issues, etc.

### Relevant Pre-built Rules for Roadmap
```
p/security-audit          → OWASP vulnerabilities
p/python-best-practices   → Python anti-patterns
p/bandit                  → Similar to bandit, but better
p/owasp-top-ten          → Web framework security
p/django-best-practices  → If we used Django (we don't)
p/generic-patterns       → Generic code smells
```

---

## Integration Points for Roadmap

### 1. Pre-commit Hook (Immediate)
```yaml
- repo: https://github.com/returntocorp/semgrep
  rev: v1.45.0
  hooks:
    - id: semgrep
      args: ['--config=.semgrep.yml', '--error']
```

**Speed:** 3-5 seconds (acceptable)
**Blocks:** Commits with violations
**Cost:** Zero (open source tier)

### 2. CI/CD (GitHub Actions)
```yaml
- name: Run Semgrep
  run: semgrep --config=.semgrep.yml roadmap/ --json --output=semgrep-report.json

- name: Upload Results
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: semgrep-report.json
```

**Integration:** Native GitHub security tab
**Cost:** Free for open source

### 3. IDE Integration
**VSCode:** Semgrep VSCode extension
**Real-time:** Warnings appear as you type
**Cost:** Free

### 4. Slack Notifications
**Hook:** Semgrep app posts findings to Slack channel
**Cadence:** On new issues
**Cost:** Free

---

## Semgrep vs. Our Custom Audit Script

| Aspect | Custom Script | Semgrep |
|--------|---------------|---------|
| **Pattern Detection** | Regex (fragile) | AST (robust) |
| **Performance** | Fast (2-3s) | Fast (3-5s) |
| **Maintenance** | Us (burden) | Community |
| **Rule Quality** | What we wrote | 2,000+ vetted rules |
| **False Positives** | Higher | Lower (AST reduces FP) |
| **Extensibility** | Limited | Unlimited (YAML) |
| **IDE Integration** | None | VSCode, Sublime, JetBrains |
| **CI/CD Integration** | Custom | Native GitHub, GitLab |
| **Debugging** | Print statements | Built-in debugging tools |
| **Community** | Just us | 5,000+ users |
| **Documentation** | None yet | Comprehensive |
| **Long-term viability** | Uncertain | Backed by company, VC funded |

---

## Recommended Implementation: Phased Approach

### Phase 1: Foundation (This Week - Phase 7a)
```
1. Install semgrep: pip install semgrep
2. Create .semgrep.yml with error handling rules
3. Add to pre-commit hooks
4. Add to GitHub Actions
5. Verify it catches all 121 existing violations
6. Block commits with violations
```

**Deliverable:** Semgrep pre-commit integration
**Effort:** 2-3 hours
**Benefit:** Prevents future regressions during Phase 7b-7e refactoring

### Phase 2: Expand Rules (Phase 7b-7e)
```
1. Add structlog consistency rules
2. Add logging quality rules
3. Add CLI error routing rules
4. Add framework-specific rules
5. Add security rules from registry
```

**Deliverable:** Comprehensive custom rule set
**Effort:** 4-5 hours
**Benefit:** Catches domain-specific issues

### Phase 3: Optional - AppSec Platform (Post-Phase 7)
```
1. Connect to Semgrep managed service (free tier)
2. Enable GitHub integration
3. Get PR comments on findings
4. Track findings over time
5. Get AI explanations of issues
```

**Deliverable:** SaaS integration with analytics
**Effort:** 1 hour
**Benefit:** Team visibility, trend tracking

---

## Custom Rule Examples for Roadmap

### .semgrep.yml (Our Domain Rules)

```yaml
rules:
  # Error Handling - Phase 7a
  - id: except-silent-failure
    patterns:
      - pattern-either:
          - pattern: |
              try:
                  ...
              except $EXCEPTION:
                  pass
          - pattern: |
              try:
                  ...
              except $EXCEPTION:
                  continue
          - pattern: |
              try:
                  ...
              except $EXCEPTION:
                  return
    message: "Silent failure - exception handler must include logging"
    severity: ERROR
    languages: [python]

  # Structlog consistency - Phase 7b
  - id: structlog-consistency
    pattern-either:
      - pattern: |
          import logging
          ...
          logger = structlog.get_logger()
      - pattern: |
          from logging import getLogger
          ...
          logger = structlog.get_logger()
    message: "Mixing logging frameworks - use only structlog"
    severity: WARNING
    languages: [python]

  # Error context - Phase 7c
  - id: logger-insufficient-context
    pattern: logger.$METHOD($MSG)
    pattern-not: logger.$METHOD($MSG, $CONTEXT)
    message: "Log without context - add error details"
    severity: WARNING
    languages: [python]

  # CLI routing - Phase 7d
  - id: print-in-error-handler
    patterns:
      - pattern: |
          try:
              ...
          except:
              print(...)
    message: "Print in exception handler - use logger or sys.stderr"
    severity: ERROR
    languages: [python]

  # Architecture - Current
  - id: async-missing-await
    pattern: |
        async def $FUNC(...):
            ...
            $COROUTINE(...)
    message: "Coroutine called without await"
    severity: ERROR
    languages: [python]

  - id: click-decorator-order
    pattern: |
        @click.option(...)
        @click.command()
        def $FUNC(...):
    message: "@click.command() must be outermost decorator"
    severity: WARNING
    languages: [python]
```

---

## Why Semgrep is the Right Choice

1. **Future-proof** - Designed for exactly this use case
2. **Scalable** - Can add 100+ rules without performance hit
3. **Team-friendly** - Rules in YAML, not Python scripts
4. **Proven** - Used by thousands of companies
5. **Integrated** - Works with every tool in our pipeline
6. **Maintainable** - No custom code to maintain
7. **Extensible** - Community can contribute rules
8. **Debuggable** - Built-in rule debugging tools
9. **Cost-effective** - Free for open source
10. **Strategic** - Investment in tooling that pays dividends

---

## Migration Path from Custom Script

### Step 1: Replace pre-commit hook
```diff
- entry: python3 scripts/audit_error_handling.py
+ entry: semgrep --config=.semgrep.yml --error
```

### Step 2: Archive custom script
```bash
# Keep for reference, but no longer active
mv scripts/audit_error_handling.py scripts/audit_error_handling.py.archive
git rm scripts/audit_error_handling.py
```

### Step 3: Add .semgrep.yml
```bash
# Create new configuration
touch .semgrep.yml
# Add our custom rules
```

### Step 4: Test
```bash
semgrep --config=.semgrep.yml roadmap/ --json | jq '.results | length'
# Should show 121 violations (same as custom script)
```

---

## Conclusion

**Semgrep is the right tool for this job because:**

1. It's purpose-built for pattern detection (we're using the right tool)
2. It scales from Phase 7a (121 violations) → Phase 7f (1000+ custom rules)
3. It prevents future regressions through pre-commit integration
4. It provides industry-standard tooling (not a homegrown solution)
5. It enables team collaboration through shared rules

**Recommendation:** Replace custom audit script with Semgrep implementation before Phase 7b begins. This gives us a production-grade solution that will last through Phase 7 and beyond.
