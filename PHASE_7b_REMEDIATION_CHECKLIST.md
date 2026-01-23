# Phase 7b-5: Remediation Checklist

**Status:** Phase 7b - Part 5 of 5 (FINAL)
**Objective:** Provide step-by-step checklist for Phase 7c-7e implementation
**Usage:** Copy for each file being remediated in Phase 7c-7e

---

## Master Checklist for Exception Handler Remediation

Use this checklist for EVERY exception handler found in the 83 flagged files.

### Step 1: Identify Exception Type
- [ ] Is this a specific exception type? (e.g., `FileNotFoundError`, `KeyError`)
- [ ] Or is it a generic `Exception`?
- [ ] Or bare `except:` (catch-all)?

### Step 2: Classify Error Category

Ask: "What caused this error?"

- [ ] **Operational** - Expected during normal operation, user can fix/retry
  - File not found, validation failure, rate limit
  - User can retry with different input
  - Log level: `WARNING`

- [ ] **Configuration** - Setup/deployment issue, must fix before running
  - Missing API key, invalid config, port in use
  - Requires administrator intervention
  - Log level: `ERROR` + exit(1)

- [ ] **Data** - Corrupted/invalid/inconsistent data
  - Missing required field, wrong type, foreign key broken
  - May require data cleanup
  - Log level: `ERROR`

- [ ] **System** - OS/resource issue
  - Permission denied, disk full, too many open files
  - Infrastructure fix needed
  - Log level: `ERROR`

- [ ] **Infrastructure** - External service failure
  - Database down, API timeout, network unreachable
  - Usually transient, retry may help
  - Log level: `WARNING` → `ERROR` after retries exhausted

### Step 3: Check Current Implementation

**Current bad patterns (fix these):**

- [ ] `except: pass` - Silent failure
- [ ] `except Exception: pass` - Catches too much
- [ ] `except SomeError: return` - Silent return
- [ ] `except SomeError: continue` - Loop continues silently
- [ ] No logging anywhere - No audit trail
- [ ] Error message only - Missing context

### Step 4: Add Logging

Choose template based on error category:

#### Operational Error Template
```python
logger.warning(
    "EVENT_NAME",  # e.g., "file_not_found"
    operation="current_function_name",
    resource="what_failed",
    error="human_readable_message",
    user_action="what_user_should_do",
    severity="operational"
)
```
- [ ] Event name is specific and searchable
- [ ] Operation describes what was happening
- [ ] Resource identifies what failed
- [ ] Error message is user-friendly
- [ ] user_action tells them how to fix
- [ ] severity="operational"

#### Configuration Error Template
```python
logger.error(
    "EVENT_NAME",
    operation="current_function_name",
    config_key="SETTING_NAME",
    error="what_is_wrong",
    hint="how_to_fix",
    severity="config_error"
)
```
- [ ] Event name specific (missing_key, invalid_value, etc.)
- [ ] Operation describes what was happening
- [ ] config_key names the setting
- [ ] Error explains what's wrong
- [ ] hint tells them how to fix
- [ ] severity="config_error"

#### Data Error Template
```python
logger.error(
    "EVENT_NAME",
    operation="current_function_name",
    resource_type="entity_type",  # e.g., "issue"
    resource_id="entity_id",
    error="what_is_wrong",
    action="what_we_did",  # skipped, aborted, etc.
    severity="data_error"
)
```
- [ ] Event name specific (missing_field, invalid_type, etc.)
- [ ] Operation describes what was happening
- [ ] resource_type identifies entity (issue, user, etc.)
- [ ] resource_id identifies specific record
- [ ] Error describes validation failure
- [ ] action says what we did (skip/abort/etc.)
- [ ] severity="data_error"

#### System Error Template
```python
logger.error(
    "EVENT_NAME",
    operation="current_function_name",
    resource="what_failed",  # file path, etc.
    error="os_error_message",
    hint="how_to_fix",
    severity="system_error"
)
```
- [ ] Event name specific (permission_denied, disk_full, etc.)
- [ ] Operation describes what was happening
- [ ] resource identifies what OS resource failed
- [ ] Error message from OS/exception
- [ ] hint suggests fix if possible
- [ ] severity="system_error"

#### Infrastructure Error Template (First Attempt)
```python
logger.warning(
    "EVENT_NAME",
    operation="current_function_name",
    service="external_service",  # github, database, etc.
    endpoint="service_endpoint",
    error="connection_error",
    retry_attempt=1,
    max_retries=3,
    action="retrying",
    severity="infrastructure"
)
```
- [ ] Event name specific (timeout, unreachable, etc.)
- [ ] Operation describes what was happening
- [ ] service names the external system
- [ ] endpoint specifies what we called
- [ ] Error message from network call
- [ ] retry_attempt indicates attempt number
- [ ] max_retries shows total attempts
- [ ] action="retrying"
- [ ] severity="infrastructure"

#### Infrastructure Error Template (Final)
```python
logger.error(
    "EVENT_NAME_final",
    operation="current_function_name",
    service="external_service",
    endpoint="service_endpoint",
    error="still_unavailable",
    retry_attempt=3,
    total_attempts=3,
    action="aborted",
    severity="infrastructure"
)
```
- [ ] Event name indicates final attempt (add "_final")
- [ ] retry_attempt matches max attempts
- [ ] total_attempts shows we retried
- [ ] action="aborted"

### Step 5: Implement Error Recovery

Choose recovery strategy based on error type:

#### Operational Error Recovery
- [ ] Return None or default value
- [ ] Caller can decide what to do next
- [ ] Provide user with actionable message
- [ ] Don't exit process

#### Configuration Error Recovery
- [ ] Log error with fix instructions
- [ ] Raise ConfigurationError exception
- [ ] OR exit(1) immediately
- [ ] Early failure is better (fail fast)

#### Data Error Recovery
- [ ] Skip corrupted record
- [ ] Log record ID for manual review
- [ ] Continue processing other records
- [ ] Return count of skipped records

#### System Error Recovery
- [ ] Log OS error with context
- [ ] Suggest infrastructure fix if known
- [ ] May retry or fail depending on situation
- [ ] Document what operator should do

#### Infrastructure Error Recovery
- [ ] Use @retry decorator with exponential backoff
- [ ] Log each retry attempt
- [ ] Return None after max retries
- [ ] Consider queue for retry later

### Step 6: Test Error Path

- [ ] Create unit test for error case
- [ ] Verify logging output appears
- [ ] Verify log contains all required fields
- [ ] Verify error goes to stderr (not stdout)
- [ ] Verify error message is helpful
- [ ] Verify recovery action works
- [ ] Mark test for Phase 7f error path coverage

### Step 7: Verify Searchability

Each error log entry should be findable:

- [ ] Event name is specific: ✅ "github_api_timeout" NOT ❌ "error"
- [ ] Event name is consistent across codebase
- [ ] Can search by error type: e.g., grep "severity=infrastructure"
- [ ] Can search by operation: e.g., grep 'operation="sync'
- [ ] Can search by resource: e.g., grep 'resource_id=123'

---

## File-Specific Checklist

For each of the 83 flagged files:

### Before Starting
- [ ] Read file and locate all exception handlers
- [ ] Note number of handlers found
- [ ] Identify error categories for each handler

### For Each Exception Handler
- [ ] Determine error category (Ops/Config/Data/System/Infra)
- [ ] Choose appropriate error handling pattern
- [ ] Add logging with required fields
- [ ] Implement recovery strategy
- [ ] Verify error routing (stderr)
- [ ] Create test case
- [ ] Review for searchability

### After All Handlers
- [ ] No more `except: pass` in file
- [ ] No more silent `return` statements
- [ ] All exceptions logged with context
- [ ] All error messages are user-friendly
- [ ] Error categories are consistent
- [ ] Tests added for error paths

### Verification
- [ ] Run ruff on file: `ruff check <file>`
- [ ] Run pylint on file: `pylint <file>`
- [ ] Run Semgrep on file: `semgrep --config=.semgrep.yml <file>`
- [ ] Run tests for file: `pytest tests/<file>`
- [ ] All checks pass with no new warnings

---

## Phase 7c Checklist (Core Services)

Files to remediate: ~7 files in `roadmap/core/services/`

- [ ] roadmap/core/services/sync_service.py
- [ ] roadmap/core/services/issue_service.py
- [ ] roadmap/core/services/workspace_service.py
- [ ] roadmap/core/services/settings_service.py
- [ ] [Other core service files]

For each file:
1. [ ] Locate all exception handlers
2. [ ] Classify errors (most will be infrastructure or data)
3. [ ] Add appropriate logging
4. [ ] Test error paths
5. [ ] Verify all tests pass

---

## Phase 7d Checklist (CLI Handling)

Files to remediate: ~35 files in `roadmap/adapters/cli/commands/`

Examples:
- [ ] roadmap/adapters/cli/commands/create.py
- [ ] roadmap/adapters/cli/commands/list.py
- [ ] roadmap/adapters/cli/commands/update.py
- [ ] roadmap/adapters/cli/commands/delete.py
- [ ] roadmap/adapters/cli/commands/sync.py
- [ ] roadmap/adapters/cli/commands/view.py
- [ ] roadmap/adapters/cli/commands/assign.py
- [ ] roadmap/adapters/cli/commands/close.py
- [ ] [Other CLI command files]

For each command file:
1. [ ] Locate all exception handlers
2. [ ] Most will be operational errors (user input validation)
3. [ ] Add logging with user_action field
4. [ ] Ensure error messages are user-friendly
5. [ ] Test with invalid input

---

## Phase 7e Checklist (Adapters)

Files to remediate: ~41 files across adapter modules

### GitHub Adapter (~15 files)
- [ ] roadmap/adapters/github/issues.py
- [ ] roadmap/adapters/github/pull_requests.py
- [ ] roadmap/adapters/github/comments.py
- [ ] [Other GitHub adapter files]

Each should have:
- [ ] @retry decorators for transient failures
- [ ] Infrastructure error logging
- [ ] Timeout configuration
- [ ] Rate limit handling

### Git Adapter (~8 files)
- [ ] roadmap/adapters/git/git_adapter.py
- [ ] [Other Git adapter files]

Each should have:
- [ ] System error handling (permissions, etc.)
- [ ] Process error handling
- [ ] Repository validation

### Persistence Adapter (~10 files)
- [ ] roadmap/adapters/persistence/*.py

Each should have:
- [ ] Data error handling
- [ ] Database connection errors with retry
- [ ] Transaction error handling

### Sync Adapter (~8 files)
- [ ] roadmap/adapters/sync/*.py

Each should have:
- [ ] Infrastructure errors with retry
- [ ] Data conflict resolution
- [ ] State consistency checks

---

## Quick Stats Template

For tracking progress during Phase 7c-7e:

```
Phase 7c: Core Services
- Total files: 7
- Handlers remediated: __/7
- Tests added: __/7
- All tests passing: [ ] Yes [ ] No

Phase 7d: CLI Handling
- Total files: 35
- Handlers remediated: __/35
- Tests added: __/35
- All tests passing: [ ] Yes [ ] No

Phase 7e: Adapters
- Total files: 41
- Handlers remediated: __/41
- Tests added: __/41
- All tests passing: [ ] Yes [ ] No

TOTAL
- Files remediated: __/83
- Tests added: __/83
- Coverage increase: __%
- All tests passing: [ ] Yes [ ] No
```

---

## Semgrep Validation

Before moving to Phase 7f, run Semgrep to verify patterns:

```bash
# Run Semgrep with our custom rules
pre-commit run semgrep --all-files

# Check for remaining violations
semgrep --config=.semgrep.yml roadmap/ --error
```

Expected output:
- [ ] No "except-silent-pass" violations
- [ ] No "except-silent-continue" violations
- [ ] No "except-silent-return" violations
- [ ] All violations have been fixed or are false positives (document if any)

---

## Phase 7f Preparation

As you complete Phases 7c-7e, prepare for Phase 7f (Error Path Testing):

For each error scenario:
- [ ] Unit test exists
- [ ] Test covers error path (not just happy path)
- [ ] Test verifies logging output
- [ ] Test verifies recovery behavior
- [ ] Coverage metric tracked

Target: 85%+ error path coverage

---

## Final Acceptance Criteria for Phase 7b-7e

Before marking Phase 7 complete:

- [ ] All 83 flagged files have been remediated
- [ ] All exception handlers have appropriate logging
- [ ] All error messages are user-friendly
- [ ] All errors route to stderr (not stdout)
- [ ] Error categories are consistent across codebase
- [ ] Semgrep reports no violations
- [ ] All unit tests passing (6,558+ tests)
- [ ] Error path coverage at 85%+
- [ ] No new warnings from ruff/pylint/bandit
- [ ] Pre-commit checks all passing

---

## Reference Materials

When implementing fixes, reference these documents:

1. **PHASE_7b_ERROR_HIERARCHY.md** - Which category is this error?
2. **PHASE_7b_HANDLING_PATTERNS.md** - What pattern to use?
3. **PHASE_7b_LOGGING_REQUIREMENTS.md** - What fields to include?
4. **PHASE_7b_CODE_EXAMPLES.md** - Show me an example!
5. **PHASE_7a_AUDIT_FINDINGS.md** - Which files are flagged?
6. **PHASE_7_REMEDIATION_LIST.md** - Which module is this in?
