# Phase 7d: Semgrep Integration for Logging Enforcement

**Status:** 🚀 INITIATED - January 24, 2026
**Objective:** Use Semgrep to proactively detect and enforce logging standards
**Foundation:** Phase 7b-c error handling patterns and Semgrep readiness
**Scope:** Configure Semgrep rules, run detection, and establish enforcement framework

---

## Phase 7d Overview

Phase 7d transitions from **reactive audit/fix approach** (Phases 7a-7c) to **proactive enforcement approach** using Semgrep. This ensures that:

1. **Future violations are caught before code review**
2. **Developers understand standards through Semgrep feedback**
3. **Regression prevention is automated**
4. **Codebase quality stays consistent**

### Why Semgrep in Phase 7d?

- ✅ Phase 7a: Identified 138 violations across codebase
- ✅ Phase 7b: Defined error handling standards
- ✅ Phase 7c: Fixed core services (highest impact)
- 🔄 Phase 7d: **Enforce standards going forward** with Semgrep
- 📋 Phase 7e: Address remaining adapters/CLI with validated rules

---

## What We Have from Previous Phases

### From Phase 7b: Error Handling Standards
- **5 error categories:** Operational, Configuration, Data, System, Infrastructure
- **Logging templates:** Specific requirements for each category
- **Exit criteria:** Clear when to log at WARNING vs ERROR
- **Event naming:** Searchable, categorized event names

### From Phase 7c: Semgrep Readiness
- ✅ Semgrep installed and configured
- ✅ Three core rules created:
  - `except-silent-pass`: 72 violations detected
  - `except-silent-continue`: 9 violations detected
  - `except-silent-return`: 57 violations detected
- ✅ Pre-commit integration ready
- ✅ Baseline established (138 total violations)

---

## Phase 7d Tasks

### Task 1: Create Logging-Focused Semgrep Rules

**Goal:** Beyond just detecting silent failures, detect logging quality issues

**Rules to create:**

1. **Log-Level Violations**
   - Detects: Using ERROR for Operational errors
   - Detects: Using WARNING for Configuration errors
   - Detects: Missing severity field in logs

2. **Incomplete Logging Context**
   - Detects: Logging error without context about what was being attempted
   - Detects: Logging error without identifying the resource involved
   - Detects: Generic error messages like `"Error occurred"`

3. **Inconsistent Event Naming**
   - Detects: Event names that don't match our categorization
   - Detects: Event names that aren't searchable (e.g., `err`, `failed`)
   - Detects: Missing event name in logger.xxx() calls

4. **Structlog vs Standard Logging**
   - Detects: Mixed usage of standard logging and structlog
   - Detects: Inconsistent structured field names
   - Detects: Missing structured fields that should always be present

### Task 2: Tune Rules on Real Violations

**Goal:** Verify rules work without false positives

- [ ] Run each new rule against codebase
- [ ] Verify all results are genuine violations
- [ ] Adjust rule patterns to eliminate false positives
- [ ] Document expected violation count for each rule

### Task 3: Create Developer Guide

**Goal:** Help developers understand how to pass Semgrep checks

- [ ] Document each rule with clear explanations
- [ ] Provide fix examples for each violation type
- [ ] Create quick-reference guide for compliance
- [ ] Add to docs/DEVELOPMENT.md or docs/ERROR_HANDLING.md

### Task 4: Establish Pre-commit Enforcement

**Goal:** Prevent violations from reaching commit history

- [ ] Configure Semgrep in pre-commit hook
- [ ] Set to run in `manual` mode (don't block all commits)
- [ ] Document how developers run: `pre-commit run --hook-stage manual semgrep`
- [ ] Create CI/CD integration point

### Task 5: Create Regression Test Suite

**Goal:** Ensure Semgrep rules stay effective

- [ ] Create test files with violation patterns
- [ ] Create test files with compliant code
- [ ] Verify rules catch violations
- [ ] Verify rules don't flag compliant code
- [ ] Add to pre-commit or pytest pipeline

---

## Success Criteria for Phase 7d

- [ ] At least 4 new logging-focused Semgrep rules created
- [ ] All rules tested against codebase with 0 false positives
- [ ] Developer guide written and accessible
- [ ] Pre-commit integration working and documented
- [ ] Regression test suite covering all rules
- [ ] Team trained on how to interpret Semgrep violations
- [ ] Clear path established to Phase 7e (adapters/CLI fixes with Semgrep)

---

## Next Steps After Phase 7d

**Phase 7e:** Use validated Semgrep rules to fix remaining violations in:
- Adapters (roadmap/adapters/)
- CLI layer (roadmap/cli/)
- Other infrastructure layers

This will be faster and more confident with Semgrep rules guiding the work.

---

## Implementation Notes

### Current Semgrep Configuration
- Located in: `.semgrep.yml`
- Pre-commit hook in: `.pre-commit-config.yaml`
- Baseline violations: 138 from Phase 7c analysis

### Files to Create/Modify
- `.semgrep.yml` - Add new rules
- `docs/ERROR_HANDLING.md` or new `docs/SEMGREP_RULES.md` - Developer guide
- `.pre-commit-config.yaml` - Ensure integration
- Test files for regression validation

### Commands for Development
```bash
# Run full Semgrep check
semgrep --config=.semgrep.yml

# Run specific rule
semgrep --config=.semgrep.yml --include-rule=rule-id

# Run in pre-commit manually
pre-commit run --hook-stage manual --all-files semgrep

# Test against specific files
semgrep --config=.semgrep.yml roadmap/
```

---

## Status Tracking

- [ ] Task 1: Create logging-focused rules
- [ ] Task 2: Tune rules on real violations
- [ ] Task 3: Create developer guide
- [ ] Task 4: Establish pre-commit enforcement
- [ ] Task 5: Create regression test suite
- [ ] **Phase 7d Complete** - Ready for Phase 7e
