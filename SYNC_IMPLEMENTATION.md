# Sync Architecture Implementation

## Overview

We've implemented a production-ready, backend-agnostic sync architecture for the roadmap tool that separates concerns cleanly and provides comprehensive observability through structured logging.

## Core Components

### 1. Test Data Factories (`tests/factories/sync_data.py`)

**Purpose**: Fluent builders for constructing test data without hardcoding.

**Classes**:
- `IssueTestDataBuilder`: Builds `Issue` instances with configurable fields
- `SyncScenarioBuilder`: Constructs local/remote issue datasets
- `ConflictScenarioBuilder`: Creates conflict test scenarios

**Benefits**:
- DRY test code
- Clear, maintainable test scenarios
- Easy to extend with new test cases

### 2. Sync Conflict Resolver (`roadmap/core/services/sync_conflict_resolver.py`)

**Purpose**: Backend-agnostic conflict resolution logic.

**Key Classes**:
- `ConflictStrategy` enum: `KEEP_LOCAL`, `KEEP_REMOTE`, `AUTO_MERGE`
- `ConflictField`: Represents field-level conflicts
- `Conflict`: Represents all conflicts for a single issue
- `SyncConflictResolver`: Resolves conflicts using configured strategy

**Features**:
- Three resolution strategies with clear semantics
- Batch resolution with error handling
- Field-level conflict detection
- Structured logging with trace injection for debugging
- Auto-merge with timestamp comparison (prefer newer, fallback to local)

**Logging**:
```
resolve_conflict: Starts conflict resolution with strategy and field count
keeping_local_version / keeping_remote_version: Strategy decision
auto_merge_start: Begin merge process
local_is_newer_keeping_local: Timing-based decision
remote_is_newer_keeping_remote: Timing-based decision
field_conflict_detected: Individual field conflicts
batch_resolution_had_errors: Batch operation failures
```

### 3. Sync State Comparator (`roadmap/core/services/sync_state_comparator.py`)

**Purpose**: Backend-agnostic state comparison logic.

**Key Class**:
- `SyncStateComparator`: Compares local and remote states

**Methods**:
- `identify_conflicts()`: Issues that differ in both local and remote
- `identify_updates()`: Local issues to push (new or newer)
- `identify_pulls()`: Remote issues to fetch (new or newer)
- `identify_up_to_date()`: Issues identical in both

**Features**:
- Configurable fields to sync
- Timestamp-based comparison
- Handles missing/invalid timestamps gracefully
- Structured logging with detailed context
- Extraction of ISO format timestamps

**Logging**:
```
identify_conflicts_start/complete: Conflict detection lifecycle
conflict_identified: Individual conflicts found
identify_updates_start/complete: Update identification
local_is_newer_needs_update: Local version needs pushing
identify_pulls_start/complete: Pull identification
remote_is_newer_needs_pull: Remote version needs pulling
identify_up_to_date_start/complete: Up-to-date check
issue_is_up_to_date: Individual up-to-date issues
timestamp_extraction_error: Invalid timestamp handling
```

## Test Coverage

### Conflict Resolver Tests (22 tests)
- ConflictField detection and representation
- Conflict initialization and string output
- KEEP_LOCAL strategy verification
- KEEP_REMOTE strategy verification
- AUTO_MERGE with various timestamp scenarios
- Batch resolution with error handling
- Field conflict detection with edge cases
- Parametrized value conflict scenarios

### State Comparator Tests (31 tests)
- Initialization with defaults and custom fields
- Conflict identification (single, multiple, various scenarios)
- Update identification (new, newer, older issues)
- Pull identification (new remote, newer remote)
- Up-to-date identification (identical states)
- Timestamp extraction (ISO format, datetime objects, missing/invalid)
- Complex mixed scenarios with all operations
- Parametrized edge cases

## Architecture Decisions

### 1. Backend-Agnostic Design
- `Conflict` and `ConflictField` dataclasses work with any backend
- `SyncStateComparator` doesn't know about GitHub/Git specifics
- `SyncConflictResolver` applies same logic regardless of sync direction

### 2. Separation of Concerns
- **SyncConflictResolver**: Conflict detection and resolution
- **SyncStateComparator**: State comparison and identification
- **Backend adapters**: Only handle API calls (future implementation)
- **Orchestrator**: Coordinates the workflow (future implementation)

### 3. Structured Logging
- Uses `structlog` consistently with application
- Trace injection for debugging visibility
- Context-aware logging at each step
- Error paths logged with full context

### 4. Error Handling
- Graceful degradation (handles missing timestamps)
- Detailed error messages with context
- Batch operations continue on individual failures
- Proper exception chaining

## Data Structures

### Conflict Data

```python
@dataclass
class Conflict:
    issue_id: str
    local_issue: Issue
    remote_issue: dict[str, Any]
    fields: list[ConflictField]
    local_updated: datetime
    remote_updated: datetime | None
```

### Resolution Strategies

1. **KEEP_LOCAL**: Always use local version
2. **KEEP_REMOTE**: Always use remote version
3. **AUTO_MERGE**:
   - If local is newer → keep local
   - If remote is newer → use remote
   - If timestamps equal → keep local (prefer local on tie)

## Integration Points (Future)

The architecture is designed to integrate with:

1. **GenericSyncOrchestrator**: Will use these services to:
   - Get local and remote states
   - Compare states
   - Resolve conflicts
   - Apply resolved changes

2. **GitHub/Vanilla Git Backends**: Will implement:
   - `get_issues()`: Return remote issues
   - `push_issue(issue)`: Create/update single issue
   - `push_issues(issues)`: Batch push with progress
   - `pull_issues(remote_issues)`: Apply remote changes locally

## Testing Best Practices Implemented

- ✅ Test data factories instead of hardcoding
- ✅ Comprehensive edge case coverage
- ✅ Parametrized tests for value scenarios
- ✅ Clear test names describing intent
- ✅ Focused assertions with helpful messages
- ✅ No test interdependencies
- ✅ Structured logging in production code

## Performance Considerations

- Timestamp comparison is efficient (datetime objects)
- Batch operations with early termination on total failure
- ISO timestamp parsing cached where possible
- No unnecessary object allocations
- Logging with structured format (efficient filtering/processing)

## Next Steps for Implementation

1. Update `GenericSyncOrchestrator` to use these services
2. Simplify `GitHubSyncBackend` to just API calls
3. Implement remote-to-local conversion in backends
4. Add integration tests with actual sync workflows
5. Add CLI integration with progress bars and user prompts
