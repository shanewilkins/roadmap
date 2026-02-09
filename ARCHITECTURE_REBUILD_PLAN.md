# Roadmap Sync Architecture Rebuild Plan

**Document Relationships**:
- **Primary Context**: [SYNC_IMPROVEMENTS_ROADMAP.md](SYNC_IMPROVEMENTS_ROADMAP.md) - Comprehensive sync system improvement strategy (Tasks 1-12)
- **Architecture Analysis**: [docs/developer_notes/SYNC_ARCHITECTURE_ANALYSIS.md](docs/developer_notes/SYNC_ARCHITECTURE_ANALYSIS.md) - Technical review and issues
- **This Document**: Rebuild plan for ~300 deleted lines of implementation code (enables Tasks 5-6+)

---

## Summary of Current Broken State

**What Was Deleted**: Approximately 300 lines of implementation code from:
- `SyncMergeOrchestrator._sync_*` methods (initialization, deduplication, analysis, apply, metrics)
- `GitHubSyncBackend` push/pull/delete operation implementations  
- Supporting helper methods across both files

**Why It's Broken**: The orchestrator calls methods that exist but the underlying implementation was gutted. The structure that decides WHAT to do (orchestrator) is intact, but the HOW (backend operations and sync phases) is incomplete.

**Additional Breakages Discovered**:
- `SyncPlanExecutor` is marked a scaffold and does not fully implement applying actions, yet it is used in the critical apply path.
- `SyncPlanExecutor` expects backend methods to return a report, but `GitHubSyncBackend.push_issues()` and `pull_issues()` return `Result[SyncReport, SyncError]`, causing runtime mis-handling of results and errors.
- `DeduplicateService` calls `backend.delete_issues()`, but `GitHubSyncBackend` does not implement it, so remote duplicate deletion is skipped.
- Documentation drift: [GRAPHQL_DELETION_VERIFICATION.md](GRAPHQL_DELETION_VERIFICATION.md) claims GraphQL deletion is implemented, but the backend lacks the method.

**Connection to Improvements Roadmap**: This rebuild unblocks Tasks 5-6 in the [SYNC_IMPROVEMENTS_ROADMAP.md](SYNC_IMPROVEMENTS_ROADMAP.md):
- **Task 5** (Duplicate Resolution Persistence ✅) - Requires: functional backend push/pull/delete operations
- **Task 6** (Comprehensive Observability) - Requires: working sync pipeline to collect metrics
- **Task 7+** (Pre-flight, Health Checks, etc.) - Require: complete backend implementation

---

## Current Architecture State & Foundation From Improvements Roadmap

### Established Patterns (From Completed Tasks)

#### ✅ Task 1: Result<T, E> Pattern (Completed)
**Reference**: [SYNC_IMPROVEMENTS_ROADMAP.md → Task 1](SYNC_IMPROVEMENTS_ROADMAP.md#task-1-result-type-pattern)

All operations use `Result[SuccessType, SyncError]` pattern (in `roadmap/common/result.py`):
- Ensures explicit error handling throughout rebuild
- **All methods being implemented must return Result types**
- No exceptions leaked from backend operations
- SyncError enum (from `common/errors.py`) defines error categories

**Impact on Rebuild**: 
- `push_issues()` → `Result[SyncReport, SyncError]`
- `pull_issues()` → `Result[SyncReport, SyncError]`
- `delete_remote_duplicates()` → `Result[dict, SyncError]`

#### ✅ Task 2: Retry + Circuit Breaker (Completed)
**Reference**: [SYNC_IMPROVEMENTS_ROADMAP.md → Task 2](SYNC_IMPROVEMENTS_ROADMAP.md#task-2-retry--circuit-breaker)

GitHub API calls already wrapped with:
- `@retry_with_backoff` decorator (in `roadmap/common/services/retry.py`)
- CircuitBreaker class for persistent failures
- Automatic retry with exponential backoff

**Impact on Rebuild**:
- GitHubClientWrapper._make_request() already handles retries
- No need to add retry logic in backend methods themselves
- Focus on proper error handling and propagation

#### ✅ Task 3: Backend Registry Pattern (Completed)
**Reference**: [SYNC_IMPROVEMENTS_ROADMAP.md → Task 3](SYNC_IMPROVEMENTS_ROADMAP.md#task-3-backend-registry--repository-pattern)

Backend discovery already implemented:
- `roadmap/adapters/sync/backend_factory.py` - SyncBackendFactory
- `roadmap/infrastructure/sync_gateway.py` - centralized gateway
- Multiple backends (GitHub, Vanilla Git, etc.)

**Impact on Rebuild**:
- No changes needed to how backends are accessed
- Just implement the missing methods
- Backend interface is protocol-based (SyncBackendInterface in `core/interfaces/sync_backend.py`)

#### ✅ Task 4: Duplicate Detection System (Completed)
**Reference**: [SYNC_IMPROVEMENTS_ROADMAP.md → Task 4](SYNC_IMPROVEMENTS_ROADMAP.md#task-4-duplicate-detection-system)

Duplicate infrastructure already in place:
- `roadmap/common/union_find.py` - O(α(n)) disjoint set algorithm
- `roadmap/core/services/sync/duplicate_detector.py` - detection engine
- Detects: ID collisions, exact title matches, fuzzy matches (>90%)

**Impact on Rebuild**:
- Backend `delete_issues()` needed by dedup service
- Phase B of rebuild plan ensures proper integration
- Metrics recorded in SyncObservability (Task 6)

#### ✅ Task 5: Duplicate Resolution Persistence (Completed Feb 6)
**Reference**: [SYNC_IMPROVEMENTS_ROADMAP.md → Task 5](SYNC_IMPROVEMENTS_ROADMAP.md#task-5-duplicate-resolution-persistence)

Deduplication is currently implemented with:
- `roadmap/core/services/sync/duplicate_resolver.py` - resolution strategies
- Orchestrator method: `_execute_duplicate_resolution()` - applies results
- IssueService methods: `merge_issues()`, `archive_issue()`
- Hybrid deletion/archive strategy with audit trail

**Impact on Rebuild**:
- Duplicate resolution DEPENDS on working backend push/pull/delete
- Current implementation returns "link" actions during analysis phase
- Actual merge/delete happens in execution phase
- This rebuild enables Task 5 to fully execute

### Service Layer & Orchestrator

#### Established Services (Fully Functional)
From improvements roadmap, these services are **complete and working**:
- `SyncAuthenticationService` - manages GitHub token and credentials
- `SyncDataFetchService` - fetches issues from remote backend
- `SyncAnalysisService` - three-way merge analysis
- `SyncReportService` - generates sync reports
- `DeduplicateService` - coordinates duplicate detection/resolution

#### SyncMergeOrchestrator Structure
- **File**: `roadmap/adapters/sync/sync_merge_orchestrator.py`
- **Status**: ~90% complete, main loop intact
- **Main Orchestration Method**: `sync_all_issues()`
  1. Phase 0: Pre-flight checks *(Task 7 adds this)*
- Phase A + B complete → **Task 5 fully works** (Duplicate Resolution Persistence ✅)
- Phase A + C complete → **Task 6 can measure** (Comprehensive Observability)
- Phase A + B + C complete → **Task 7 can validate** (Pre-flight Validation)
- Phase D complete → **Tasks 8-12 can proceed** (Testing & Documentation)

### Phase A: Contract Alignment (HIGHEST PRIORITY)
**Timeline**: 2-4 hours
**Unblocks**: Task 5 execution, Task 6 metrics collection

This phase makes the apply path coherent by aligning the executor with backend Result types and ensuring the sync plan is actually executed correctly.

#### A1. Align Executor With Result Pattern
**File**: `roadmap/core/services/sync/sync_plan_executor.py`

**What to Implement**:
- When calling `transport_adapter.push_issues()` or `pull_issues()`, unwrap `Result` and handle `Err` explicitly.
- Merge per-issue errors from `SyncReport` into executor error accumulation.
- Propagate fatal errors into `SyncReport.error` (and stop if `stop_on_error=True`).

**Success Criteria**:
- Sync apply uses the Result pattern correctly.
- `issues_pushed` and `issues_pulled` reflect actual counts.
- Errors are surfaced in `SyncReport.errors` and `SyncReport.error`.

#### A2. Verify SyncMergeEngine Apply Path
**File**: `roadmap/adapters/sync/sync_merge_engine.py` → `_apply_plan()`

**What to Verify**:
- Ensure counts from `SyncPlanExecutor` are applied to `SyncReport` consistently.
- Ensure errors are merged into report (and not dropped).

### Phase B: Remote Deletion (GraphQL Only)
**Timeline**: 3-4 hours
**Unblocks**: Task 5 duplicate deletion execution

This phase implements the missing GraphQL batch deletion used by deduplication.

#### B1. Implement `delete_issues()` in GitHub Backend
**File**: `roadmap/adapters/sync/backends/github_sync_backend.py`

**What to Implement**:
```python
def delete_issues(self, issue_numbers: list[int]) -> int | Result[dict, SyncError]:
  """
  Delete issues from GitHub via GraphQL.
  - Resolve node IDs in batches (50)
  - Execute deleteIssue mutations in batches
  - Track per-issue success/failure
  - Return deleted count (or Result with details)
  """
```

**Success Criteria for Phase B**:
- ✅ GraphQL mutations execute successfully
- ✅ Issues deleted from GitHub
- ✅ Batch size respected (50 issues max per call)
- ✅ Per-issue error tracking works
- ✅ Rate limiting handled gracefully

### Phase C: Telemetry + Error Handling (Mandatory)
**Timeline**: 2-3 hours
**Unblocks**: Task 6 observability and reliable diagnostics

This phase ensures the most important signal: accurate metrics and explicit errors for every sync operation.

**What to Implement**:
- Record push/pull durations and counts in `SyncObservability` after apply.
- Record dedup deletion metrics (deleted count, failed count, duration).
- Record Result errors as structured observability events (error type, message).
- Ensure `SyncReport.metrics` is populated for completed runs.

### Phase D: Tests + Validation
**Timeline**: 3-5 hours
**Validates**: Phases A-C

This phase proves correctness with targeted tests and manual validation.

#### D1. Unit Tests (Per-Method)
**Files**: `tests/unit/adapters/sync/backends/test_github_sync_backend.py`

```python
class TestGitHubSyncBackend:
    def test_push_issues_creates_new(self):
        # Mock API, call push_issues with new issue
        # Assert POST called, issue created
        # Assert Result.ok returned with SyncReport
    
    def test_push_issues_updates_existing(self):
        # Mock API, call push_issues with existing issue (has backend_id)
        # Assert PATCH called, issue updated
        # Assert Result.ok returned

    def test_pull_issues_fetches_and_creates(self):
        # Mock API, call pull_issues with issue IDs
        # Assert GET called
        # Assert Issue created locally
        # Assert Result.ok returned
    
    def test_delete_issues_via_graphql(self):
        # Mock GraphQL, call delete_issues
        # Assert mutation executed
        # Assert per-issue status tracked
        # Assert Result.ok returned
    
    def test_error_handling_returns_err(self):
        # Mock API error, verify Result.err returned
        # Assert SyncError populated correctly
```

#### D2. Integration Tests (Full Pipeline)
**Files**: `tests/integration/sync/test_end_to_end_sync.py`

```python
class TestEndToEndSync:
    @pytest.mark.integration
    def test_sync_all_issues_happy_path(self):
        # Setup fake backend with test issues
        # Call orchestrator.sync_all_issues()
        # Assert sync phases complete successfully
        # Assert SyncReport has success data
    
    @pytest.mark.integration
    def test_sync_with_duplicates(self):
        # Setup: 99 canonical, 1728 duplicates across local+remote
        # Call orchestrator.sync_all_issues() with --detect-duplicates
        # Assert: Duplicates detected
        # Assert: Deleted from GitHub
        # Assert: Only 99 issues remain in sync
        # Assert: Second sync shows "no changes"
    
    @pytest.mark.integration
    def test_sync_with_conflicts(self):
        # Setup: Issue edited locally AND remotely (conflict)
        # Call orchestrator.sync_all_issues()
        # Assert: Conflict detected
        # Assert: Resolution applied (local, remote, or manual)
        # Assert: Sync completes successfully
```

#### D3. Manual Validation

**Pre-sync Validation**:
1. Create test GitHub repo
2. Create test issues (10-20 issues)
3. Edit some locally
4. Edit some on GitHub
5. Create duplicates (same title)

**Run Sync**:
```bash
export GITHUB_TOKEN=<test-token>
roadmap config --repo tests/resources/test-repo --backend github
roadmap sync --verbose --dry-run  # Should show all changes
roadmap sync  # Execute sync
```

**Post-sync Validation**:
- ✅ Local issues match GitHub
- ✅ Duplicates removed
- ✅ Conflicts resolved
- ✅ No errors in output
- ✅ Re-run sync shows "everything up-to-date"

**Success Criteria for Phase D**:
- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ Manual validation successful
- ✅ No pyright type errors
- ✅ Code review ready

---

## Key Files & Implementation Checklist

| File | Current Status | Need to Add | References |
|------|---|---|---|
| `SyncMergeOrchestrator` | 90% complete | Verify all phase methods return/handle Result types | Improvements: Task 1 (Result), Task 6 (observability) |
| `GitHubSyncBackend.push_issues()` | Implemented but Result mismatch in executor | Ensure Result is unwrapped/handled in executor | Phase A, Task 1 (Result pattern) |
| `GitHubSyncBackend.pull_issues()` | Implemented but Result mismatch in executor | Ensure Result is unwrapped/handled in executor | Phase A, Task 1 (Result pattern) |
| `GitHubGraphQLService` | Optional | Only add if backend deletion grows too large | Phase B, Task 2 (retry via GitHubClientWrapper) |
| `GitHubSyncBackend.delete_issues()` | **Missing** | Implement GraphQL batch delete | Phase B, Task 5 (duplicate deletion) |
| `DeduplicateService` | ~80% complete | Ensure backend delete integration, Result handling | Phase B/D, Task 4 (detection), Task 5 (resolution) |
| `SyncBackendInterface` | 100% complete | No changes | Inherent - abstract protocol |
| Issue conversion helpers | Unknown | May need to add/restore for push_issues | Phase A |
| Error mapping | May exist | Map GitHub API errors to SyncError enum | Task 1 (Result + SyncError) |

---

## Critical Decision Points (With Improvements Roadmap Context)

### 1. Where Should GraphQL Live?
**Reference**: Single Responsibility Principle (from [SYNC_ARCHITECTURE_ANALYSIS.md](docs/developer_notes/SYNC_ARCHITECTURE_ANALYSIS.md))

Options:
- **Option A**: `GitHubSyncBackend` directly (simple, all GitHub code together) ✅ RECOMMENDATION
- **Option B**: Separate `GitHubGraphQLService` in services layer (cleaner separation, more testable)

**Decision**: Start with **Option A** (GraphQL in backend), refactor to Option B if it grows beyond 500 lines.

**Rationale**: 
- GraphQL is GitHub-specific implementation detail
- Belongs in platform layer with other GitHub operations
- Keeps service layer focused on business logic (dedup, analysis, etc.)
- Can extract later without breaking contracts

### 2. REST vs GraphQL for Push/Pull?

**Context**: Task 2 (Retry + Circuit Breaker) already handles HTTP retries

Options:
- **REST API**: Single issue operations, simpler implementation, GitHub rate limits
- **GraphQL**: Batch operations, fewer API calls, but mutations are more complex

**Decision**:
- Use **REST** for push/pull (stable, already integrated via `GitHubSyncOps`).
- Use **GraphQL** only for batch deletion (dedup) and future batch reads if needed.

**Rationale**:
- REST push/pull unblocks Tasks 5-6 quickly
- GraphQL delete is genuinely more efficient for batch ops
- Phased approach reduces risk
- Matches [SYNC_IMPROVEMENTS_ROADMAP.md Task 2](SYNC_IMPROVEMENTS_ROADMAP.md#task-2-retry--circuit-breaker) - retry layer already built

### 3. Error Handling Strategy?

**Context**: Task 1 Result pattern already established throughout codebase

**Strategy**:
```python
# Per-issue errors tracked in detail
Result[SyncReport, SyncError]
# SyncReport includes per-issue status:
# - issue_number: str
# - success: bool
# - error_message: str | None
# - error_type: SyncErrorType
```

**Decision**: Keep Result pattern everywhere, no exceptions

**Rationale**:
- Matches Task 1 design
- Makes async/batch operations composable
- Enables proper retry logic (Task 2)
- Enables observability metrics (Task 6)

### 4. Synchronous vs Async?
**Context**: Current backend methods are synchronous and the orchestrator does not `await` them.

**Decision**: Keep **synchronous** method signatures for now.

**Rationale**:
- Matches existing backend method signatures and call sites.
- Avoids partial async migration that would widen the mismatch.
- Concurrency can be handled internally (e.g., ThreadPoolExecutor) without changing API.

---

## Success Criteria

After complete implementation of Phases A-D:

1. ✅ `roadmap sync` completes without crashes or exceptions
2. ✅ Issues are created in GitHub when pushed
3. ✅ Issues are updated in GitHub when changed
4. ✅ Issues are pulled from GitHub and created locally
5. ✅ Duplicates are detected before sync
6. ✅ Duplicates are deleted from GitHub via GraphQL
7. ✅ Conflicts are detected and resolved correctly
8. ✅ All pyright type errors are fixed (0 errors)
9. ✅ All integration tests pass (end-to-end scenarios)
10. ✅ Sync metrics are recorded (Task 6 observability)
11. ✅ Second sync run shows "everything synced, no changes"
12. ✅ Manual validation with test GitHub repo succeeds

**Comprehensive Validation** (From [SYNC_IMPROVEMENTS_ROADMAP.md](SYNC_IMPROVEMENTS_ROADMAP.md)):
- ✅ Task 5 Tollgate passes: Duplicates properly merged/archived
- ✅ Task 6 Phase 1: Metrics collected for all operations
- ✅ Pre-cursor for Task 7: Pre-flight validation can now test real sync

---

## Relationship to Improvements Roadmap

This rebuild plan is the **critical path** for the improvements roadmap:

| Task | Status | Depends On This Rebuild | Notes |
|------|--------|---|---|
| Task 1: Result Pattern | ✅ Complete | No | Foundation - already established |
| Task 2: Retry/Circuit | ✅ Complete | No | Foundation - already established |
| Task 3: Backend Registry | ✅ Complete | No | Foundation - already established |
| Task 4: Duplicate Detection | ✅ Complete | No | Foundation - already established |
| **Task 5: Duplicate Resolution** | 🚀 **BLOCKED** | **YES - This Rebuild** | Waiting for push/pull/delete ops |
| **Task 6: Observability** | ⏳ **BLOCKED** | **YES - This Rebuild** | Needs working sync to measure |
| **Task 7: Pre-flight Validation** | ⏳ **BLOCKED** | **YES - Phase A/B/C** | Needs working sync to validate |
| Task 7b: Health Checks | ⏳ **BLOCKED** | **YES - Phase A/B** | Needs working dedup |
| Task 8-12: Testing/Docs | ⏳ **BLOCKED** | **YES - Phase D** | Can't test what doesn't work |

**Critical Path Analysis**:
```
Task 1-4 (Foundation) ✅
    ↓
This Rebuild (Phase A-C) → Unblocks Task 5 & 6 → Enables Task 7+ → Completes Task 8-12
```

---

## Timeline Estimate

*Based on [SYNC_IMPROVEMENTS_ROADMAP.md](SYNC_IMPROVEMENTS_ROADMAP.md) complexity assessment*

- **Phase A (Contract Alignment)**: 2-4 hours
  - Align `SyncPlanExecutor` with Result pattern
  - Ensure report/error propagation is consistent
  - Unblocks: Immediate progress on Tasks 5-6

- **Phase B (GraphQL Batch Delete)**: 3-4 hours
  - Implement `GitHubSyncBackend.delete_issues()`
  - Add node ID resolution + delete mutations
  - Unblocks: Full duplicate deletion

- **Phase C (Telemetry + Error Handling)**: 2-3 hours
  - Record push/pull timings and counts
  - Record dedup deletion metrics and errors
  - Unblocks: Task 6 observability completion

- **Phase D (Testing & Validation)**: 3-5 hours
  - Unit tests for executor/result handling
  - Integration tests for full sync pipeline
  - Manual validation with test GitHub repo
  - Unblocks: Tasks 6-12 can proceed safely

**Total: 10-16 hours of focused implementation**

**Why This Timeline Aligns With Improvements Roadmap**:
- [Task 6: Comprehensive Observability](SYNC_IMPROVEMENTS_ROADMAP.md#task-6-comprehensive-observability) estimated at 2-3 days (includes metrics infrastructure which already exists)
- This rebuild is the critical prerequisite, not added to Task 6 timeline
- Completion enables parallel work on Tasks 5-7

---

## Implementation Constraints & Guidelines

### From Copilot Instructions (`.github/copilot-instructions.md`)
- ✅ Use `uv` for command execution
- ✅ Follow semantic versioning in commits  
- ✅ Include comprehensive tests alongside implementation
- ✅ Use type hints throughout (pyright must pass)
- ✅ Maintain POSIX compatibility
- ❌ Cannot force push to main branch
- ❌ Cannot run full test suite without approval (run targeted tests only)

### From SYNC Design (Architecture Analysis)
- Follow separation of concerns (Task 1 established)
- Backend = API-specific implementation ONLY
- Orchestrator = decision logic and phase sequencing
- Services = multi-concern coordination
- All operations return Result types (Task 1)

### From This Rebuild Plan
- Do NOT modify orchestrator structure
- Do NOT add business logic to backend methods
- Do NOT create new service layers
- Do NOT change the SyncBackendInterface protocol
- Keep error handling consistent (Result + SyncError)
- Every method must have clear purpose and boundaries

---

## Pre-Rebuild Checklist

Before starting Phase A, verify:

- [ ] Sync infrastructure in place (services, orchestrator, backend interface)
  - Check: `roadmap/adapters/sync/sync_merge_orchestrator.py` exists and loads
  - Check: `roadmap/core/interfaces/sync_backend.py` has complete protocol
  - Check: `roadmap/adapters/sync/backends/github_sync_backend.py` loads without import errors

- [ ] Result pattern available
  - Check: `roadmap/common/result.py` exports `Ok` and `Err`
  - Check: `roadmap/common/errors.py` has `SyncError` enum

- [ ] GitHub client available
  - Check: `GitHubClientWrapper` available in github backend module
  - Check: Methods: `get()`, `post()`, `patch()`, `delete()` exist

- [ ] Services available
  - Check: `DeduplicateService` can be imported
  - Check: `SyncAuthenticationService`, `SyncDataFetchService`, etc. available

- [ ] Dependencies in pyproject.toml
  - Check: `gql` or GraphQL client library listed
  - Check: `structlog` for logging (already used)

- [ ] Tests framework ready
  - Check: `pytest` and `pytest-asyncio` configured
  - Check: Can run `uv run pytest tests/unit/` successfully

---

## Next Steps

1. **Read this document thoroughly** 
  - Understand Phases A-D requirements
   - Review success criteria
   - Understand constraints

2. **Validate pre-rebuild checklist**
   - All infrastructure and dependencies present
   - Can import backend and orchestrator

3. **Start Phase A implementation**
  - Focus: Align executor with Result handling
  - Verify: No crashes, errors surfaced, metrics can be recorded

4. **Post-Phase A**:
  - Begin Phase B (GraphQL delete)
  - Phase B unlocks Task 5 duplicate deletion

5. **After Phase C**:
  - Task 6 (Observability) can collect real metrics
  - Task 7+ (Pre-flight, Health, Testing) can proceed

---

## Reference Documents

**Improvements Roadmap Context**:
- [SYNC_IMPROVEMENTS_ROADMAP.md](SYNC_IMPROVEMENTS_ROADMAP.md) - Master strategy (Tasks 1-12)
  - Task 1: Result pattern ✅
  - Task 2: Retry/circuit breaker ✅  
  - Task 3: Backend registry ✅
  - Task 4: Duplicate detection ✅
  - Task 5: Duplicate resolution 🚀 (blocked by this rebuild)
  - Task 6: Observability ⏳ (blocked by this rebuild)
  - Task 7+: Pre-flight, health, testing ⏳

**Design & Architecture**:
- [docs/developer_notes/SYNC_ARCHITECTURE_ANALYSIS.md](docs/developer_notes/SYNC_ARCHITECTURE_ANALYSIS.md) - Comprehensive architecture review
  - Grade: B+ (sound, with identified issues)
  - 6 issues with full remediation plan
  - This rebuild addresses Issue #1 (incomplete backend implementation)

- [docs/developer_notes/SYNC_ENTITY_BREAKDOWN_PROPOSAL.md](docs/developer_notes/SYNC_ENTITY_BREAKDOWN_PROPOSAL.md) - UI improvements (independent of this rebuild)

**Code References**:
- `roadmap/adapters/sync/sync_merge_orchestrator.py` (orchestrator - 90% complete)
- `roadmap/adapters/sync/backends/github_sync_backend.py` (GitHub backend - 60% complete)
- `roadmap/core/interfaces/sync_backend.py` (protocol definition - 100% complete)
- `roadmap/application/services/deduplicate_service.py` (dedup service - 80% complete)
- `roadmap/core/services/sync/duplicate_detector.py` (detection - 100% complete)
- `roadmap/core/services/sync/duplicate_resolver.py` (resolution - 100% complete)

---

**Status**: Ready to begin Phase A implementation
**Last Updated**: February 7, 2026
**Document Supersedes**: Initial ARCHITECTURE_REBUILD_PLAN.md
**Next Action**: Start Phase A focused on executor Result alignment and error/metrics propagation
