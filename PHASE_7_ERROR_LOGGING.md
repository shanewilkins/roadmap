# Phase 7: Error Handling & Logging

## Goal
Improve observability and robustness by standardizing error handling and logging patterns across the codebase.

## Current State
- structlog is partially used throughout the codebase
- Various error handling patterns exist (some with silent failures)
- No unified error taxonomy
- Inconsistent output routing (stdout/stderr)

## Phase 7 Objectives

### 1. Standardize structlog Usage
**Target:** All application logging uses structlog consistently.

Key areas:
- CLI commands (adapters/cli/*)
- Core services (core/services/*)
- Infrastructure components (infrastructure/*)
- Adapters (adapters/*)

Requirements:
- Use `structlog.get_logger()` consistently
- Structured logs with stable, descriptive keys
- Appropriate log levels (debug, info, warning, error)
- Context binding for request/operation tracking

### 2. Implement Error Taxonomy
**Target:** Clear error classification and handling.

Error categories to define:
1. **Operational Errors** (user-recoverable)
   - Missing configuration
   - Invalid input
   - File not found
   - Network timeout

2. **Configuration Errors** (setup issues)
   - Invalid setup parameters
   - Missing dependencies
   - Permission denied

3. **Data Errors** (data integrity)
   - Corrupt data
   - Constraint violations
   - State inconsistencies

4. **System Errors** (infrastructure)
   - Database connection failed
   - Filesystem errors
   - External service failures

### 3. Route Output Correctly
**Target:** Clear separation of concerns.

Conventions:
- **stdout:** Primary CLI output (tables, lists, formatted results)
- **stderr:** All logs, warnings, errors, diagnostics
- Exit codes: 0 = success, 1 = error, 2 = usage error

### 4. Eliminate Silent Failures
**Target:** Every exception has a user-facing message.

Patterns to replace:
- Bare `except: pass`
- `except: continue` without logging
- Swallowed exceptions in callbacks

## Implementation Strategy

### Phase 7a: Audit Current State (Day 1)
1. Search for all exception handlers
2. Count silent failures
3. Identify inconsistent logging patterns
4. Document error-prone areas

### Phase 7b: Define Error Hierarchy (Day 1)
1. Create custom exception classes
2. Map to appropriate HTTP/exit codes
3. Define structured log format
4. Document error messages

### Phase 7c: Standardize Core Services (Day 2-3)
1. Update services in `roadmap/core/services/`
2. Add context binding for operation tracking
3. Replace generic exceptions with typed ones
4. Add validation logging

### Phase 7d: Standardize CLI Handlers (Day 3-4)
1. Update all CLI commands
2. Add error presenters for user feedback
3. Ensure consistent exit codes
4. Add progress logging for long operations

### Phase 7e: Standardize Adapters (Day 4-5)
1. Update adapter layers
2. Add retry logic with logging
3. Ensure boundary errors are caught/logged
4. Add tracing for multi-step operations

### Phase 7f: Validation & Testing (Day 5)
1. Run full test suite
2. Verify error messages are user-friendly
3. Check log output for structured format
4. Validate exit codes
5. Test error scenarios

## Acceptance Criteria

✅ **No Silent Failures**
- Every exception caught and logged
- User receives feedback (or graceful degradation)
- Logs include context (operation, affected resource, error type)

✅ **Consistent Structured Logs**
- All logs use structlog with stable keys
- Standard keys: `operation`, `error_type`, `error_msg`, `context_*`
- Appropriate log levels used throughout
- Debug logs include implementation details

✅ **Clear Error Handling**
- Custom exception hierarchy defined
- Error taxonomy documented
- Error messages are actionable
- Exit codes follow conventions (0, 1, 2)

✅ **Testing**
- Error paths have test coverage
- Error messages validated in tests
- Exit codes verified
- Log output verified (sampling)

## Related Files to Audit

### Core Services
- `roadmap/core/services/initialization/`
- `roadmap/core/services/sync/`
- `roadmap/core/services/health/`
- `roadmap/core/services/issue_helpers/`

### CLI Commands
- `roadmap/adapters/cli/init/`
- `roadmap/adapters/cli/sync.py`
- `roadmap/adapters/cli/status.py`
- `roadmap/adapters/cli/commands/`

### Adapters
- `roadmap/adapters/persistence/`
- `roadmap/adapters/git/`
- `roadmap/adapters/github/`

### Infrastructure
- `roadmap/infrastructure/coordination/`
- `roadmap/infrastructure/hooks/`

## Metrics
- Silent failures eliminated: Baseline TBD → 0
- Structured log coverage: Baseline TBD → 90%+
- Error test coverage: Baseline TBD → 85%+
- Type-safe error handling: Baseline TBD → 95%+

## Success Indicators
1. All exception handlers have logging
2. No `except: pass` patterns without justification
3. Structured logs in all CLI output
4. Error messages are actionable
5. Tests verify error behavior
6. Exit codes are meaningful
