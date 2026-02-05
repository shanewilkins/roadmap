# Sync System Improvements - Implementation Roadmap

**Created**: February 5, 2026
**Status**: Planning Complete - Ready for Implementation
**Estimated Duration**: 4-6 weeks (1 developer)

---

## 📍 Current State

### ✅ Completed (All 27 Milestone Sync Tasks)
- [x] Tasks 1-12: Core sync infrastructure (GitHub, Git, three-way merge, conflict detection)
- [x] Task 13: Progress indicators (SyncProgressTracker - partially integrated)
- [x] Tasks 14-17: Documentation, verbose mode, retry logic, sync history
- [x] Task 18: Performance optimization (SyncCache, IssueIndexer - created, needs integration)
- [x] Task 19: Batch processing (BatchProcessor, AsyncBatchProcessor - created)
- [x] Task 20: Configuration options (retry, batch, conflict, filtering)
- [x] Task 21: Integration test framework (structure exists, needs responses library)
- [x] Task 22: Error recovery (checkpoint/rollback with --resume flag)
- [x] Task 23: Interactive conflict resolution (--interactive flag)
- [x] Task 24: Enhanced dry-run mode (detailed tables)
- [x] Task 25: Sync status dashboard (health metrics, error trends)
- [x] Task 26: Milestone filtering (name, state, date range)
- [x] Task 27: Auto-detect GitHub config

### 🔍 Design Documents Created
1. **SYNC_ENTITY_BREAKDOWN_PROPOSAL.md** - UI improvements with 5-category system
   - Status rows × entity columns format
   - Categories: Up-to-date, Needs Push, Needs Pull, Conflicts, Errors
   - Applies to both dry-run and post-sync reports

2. **SYNC_ARCHITECTURE_ANALYSIS.md** - Comprehensive architectural review
   - Current Grade: B+ (fundamentally sound)
   - 6 issues identified (2 critical, 3 medium, 1 low)
   - Full implementation plan (this roadmap)

### 🧪 Quality Status
- All 7600+ tests passing
- Type checking (pyright) passes
- Code complexity (radon) acceptable
- Security scanning (bandit, semgrep) passes

---

## 🎯 Implementation Plan

### **Phase 1: Critical Fixes (Weeks 1-2)**

#### Week 1: Error Handling & Duplicate Detection

**Task 1.1: Result<T, E> Pattern** (2-3 days)
- [ ] Create `roadmap/common/result.py`
  ```python
  @dataclass
  class Ok(Generic[T]):
      value: T

  @dataclass
  class Err(Generic[E]):
      error: E

  Result = Union[Ok[T], Err[E]]
  ```
- [ ] Update `SyncBackendInterface` methods to return `Result`
- [ ] Migrate error handling in `SyncMergeOrchestrator`
- [ ] Update `GitHubSyncBackend` and `VanillaGitSyncBackend`
- [ ] Update CLI commands to handle Result types

**Task 1.2: Duplicate Detection System** (2-3 days)
- [ ] Create `roadmap/core/services/sync/duplicate_detector.py`:
  - `DuplicateMatch` dataclass (local_issue, remote_issue, match_type, confidence, recommended_action)
  - `DuplicateDetector` class with methods:
    - `detect_all()` - run all detection strategies
    - `_detect_id_collisions()` - same GitHub number, different content
    - `_detect_title_duplicates()` - exact match or >90% similarity
    - `_detect_content_duplicates()` - >85% text similarity using SequenceMatcher
- [ ] Create `roadmap/core/services/sync/duplicate_resolver.py`:
  - `DuplicateResolver` class
  - `resolve_automatic(match)` - high-confidence matches (>95% similarity)
  - `resolve_interactive(matches)` - CLI prompts with Rich UI
- [ ] Integrate into `SyncMergeOrchestrator.analyze_all_issues()`:
  - Run detection before main sync analysis
  - Auto-resolve high-confidence matches
  - Warn about manual-resolution cases
- [ ] Add CLI flags to `roadmap/adapters/cli/sync.py`:
  - `--detect-duplicates / --no-detect-duplicates` (default: on)
  - `--interactive-duplicates`
- [ ] Add tests for duplicate detection and resolution

#### Week 2: Retry Logic & Error Classification

**Task 1.3: Retry + Circuit Breaker** (2 days)
- [ ] Create `roadmap/common/retry.py`:
  - `CircuitBreaker` class:
    - `failure_threshold=5`, `timeout=60.0`
    - States: closed, open, half-open
    - `call(func)` method with state management
  - `@retry_with_backoff` decorator:
    - Exponential backoff: 1s, 2s, 4s, 8s, 16s
    - Max retries: 5
    - Configurable exceptions to retry
- [ ] Apply to `GitHubClientWrapper._make_request()`
- [ ] Handle rate limit errors (429 responses, parse Retry-After header)
- [ ] Add circuit breaker state tracking and logging
- [ ] Add tests for retry behavior and circuit breaker

**Task 1.4: Enhanced Error Classification** (1-2 days)
- [ ] Extend `ErrorClassifier` with new categories:
  - Rate limit errors (with retry-after info)
  - Duplicate detection errors
  - Circuit breaker open errors
  - Retry exhausted errors
- [ ] Add error recovery recommendations to messages
- [ ] Update `display_error_summary()` in `apply_ops.py`
- [ ] Add structured error context (operation_id, backend_type, retry_count)

---

### **Phase 2: Architecture Improvements (Weeks 3-4)**

#### Week 3: Backend Registry & Repository Pattern

**Task 2.1: Backend Registry** (2-3 days)
- [ ] Create `roadmap/adapters/sync/backend_registry.py`:
  ```python
  class BackendRegistry:
      _backends: dict[str, type[SyncBackendInterface]] = {}

      @classmethod
      def register(cls, name: str, backend_class):
          cls._backends[name] = backend_class

      @classmethod
      def get_backend(cls, name: str, core, config):
          return cls._backends[name](core, config)

      @classmethod
      def auto_detect(cls, core) -> str | None:
          # Check git remote, return "github" or "git"
  ```
- [ ] Add `can_handle(config)` class method to all backends
- [ ] Register backends:
  ```python
  BackendRegistry.register("github", GitHubSyncBackend)
  BackendRegistry.register("git", VanillaGitSyncBackend)
  ```
- [ ] Update `roadmap/adapters/cli/sync.py` to use registry
- [ ] Remove direct backend imports from CLI
- [ ] Add tests for registry and auto-detection

**Task 2.2: Repository Pattern** (2 days)
- [ ] Create `roadmap/core/repositories/sync_repository.py`:
  ```python
  class SyncRepository(Protocol):
      def fetch_issues(self) -> Result[dict[str, SyncIssue], SyncError]
      def push_issues(self, issues) -> Result[SyncReport, SyncError]
      def pull_issues(self, issues) -> Result[SyncReport, SyncError]
  ```
- [ ] Create `roadmap/adapters/sync/backend_sync_repository.py`:
  - Adapter wrapping `SyncBackendInterface`
  - Add middleware support (caching, logging, metrics)
- [ ] Integrate `SyncCache` as caching middleware
- [ ] Update `SyncMergeOrchestrator` to use repository
- [ ] Add tests for repository pattern

#### Week 4: Observability Layer

**Task 2.3: Comprehensive Observability** (2-3 days)
- [ ] Create `roadmap/core/observability/sync_metrics.py`:
  ```python
  @dataclass
  class SyncMetrics:
      operation_id: str
      backend_type: str
      start_time: datetime
      duration_seconds: float
      issues_fetched: int
      issues_pushed: int
      issues_pulled: int
      conflicts_detected: int
      duplicates_detected: int
      errors_count: int
      cache_hit_rate: float
      circuit_breaker_state: str

  class SyncObservability:
      def start_operation(self, backend_type) -> str  # returns operation_id
      def record_fetch(self, operation_id, count, duration)
      def record_push(self, operation_id, count, duration)
      def record_conflict(self, operation_id)
      def record_duplicate(self, operation_id)
      def record_error(self, operation_id, error_type)
      def finalize(self, operation_id) -> SyncMetrics
  ```
- [ ] Integrate with `SyncProgressTracker` for real-time display
- [ ] Instrument `SyncMergeOrchestrator`:
  - Fetch duration and counts
  - Push/pull operation timing
  - Conflict detection
  - Duplicate detection
  - Cache statistics
  - Circuit breaker state changes
- [ ] Add structured logging with context (operation_id, user_id, backend_type)
- [ ] Create `roadmap/adapters/cli/commands/sync_metrics.py` - view historical metrics
- [ ] Store metrics in database (use SyncMetadataService pattern)
- [ ] Add tests for metrics collection

---

### **Phase 3: Testing & Documentation (Weeks 5-6)**

#### Week 5: Test Infrastructure

**Task 3.1: Contract Tests** (2 days)
- [ ] Create `tests/contracts/test_sync_backend_contract.py`:
  ```python
  class SyncBackendContractTests:
      @pytest.fixture
      def backend(self):
          raise NotImplementedError

      def test_authenticate_returns_result(self, backend)
      def test_get_issues_returns_result(self, backend)
      def test_push_issues_returns_result(self, backend)
      def test_error_handling_returns_err(self, backend)
  ```
- [ ] Implement `TestGitHubBackendContract(SyncBackendContractTests)`
- [ ] Implement `TestVanillaGitBackendContract(SyncBackendContractTests)`
- [ ] Ensure all backends pass contract tests

**Task 3.2: Property-Based Tests** (2 days)
- [ ] Add `hypothesis` to dev dependencies
- [ ] Create `tests/property/test_three_way_merge.py`:
  ```python
  @given(baseline=st.builds(Issue), local=st.builds(Issue), remote=st.dictionaries(...))
  def test_three_way_merge_categorization(baseline, local, remote):
      # Test: all changes must be categorized
      # Test: conflicts must have both local and remote changes
  ```
- [ ] Create `tests/property/test_duplicate_detection.py`:
  ```python
  @given(issues=st.lists(st.builds(Issue)))
  def test_duplicate_detection_accuracy(issues):
      # Test: no false positives
      # Test: detection is symmetric
      # Test: confidence scoring is consistent
  ```
- [ ] Test edge cases (empty strings, special characters, unicode)

#### Week 6: Integration Tests & Documentation

**Task 3.3: Integration Test Suite** (2 days)
- [ ] Create `tests/integration/sync/fake_backend.py`:
  ```python
  class FakeSyncBackend(SyncBackendInterface):
      def __init__(self):
          self.issues = {}
          self.push_calls = []
          self.should_fail = False
  ```
- [ ] Create end-to-end test scenarios:
  - [ ] Happy path: push local → pull remote → no conflicts
  - [ ] Network failures → retry → success
  - [ ] Conflicts → interactive resolution → success
  - [ ] Duplicates → detection → automatic resolution
  - [ ] Circuit breaker → repeated failures → fast fail → recovery
- [ ] Test checkpoint/resume functionality with interruptions
- [ ] Test interactive modes (mock user input with pytest-mock)

**Task 3.4: Duplicate Resolution Tests** (1 day)
- [ ] Create `tests/unit/services/sync/test_duplicate_detector.py`:
  - Test ID collision detection
  - Test title exact match
  - Test title fuzzy match (90% threshold)
  - Test content similarity (85% threshold)
  - Test confidence scoring accuracy
- [ ] Create `tests/unit/services/sync/test_duplicate_resolver.py`:
  - Test automatic resolution strategies
  - Test interactive resolution (mock prompts)
  - Test edge cases (same ID different content, abandoned duplicates)

**Task 3.5: Architecture Decision Records** (1 day)
- [ ] Create `docs/architecture/` directory
- [ ] Write `ADR-001-protocol-based-interfaces.md`
- [ ] Write `ADR-002-result-type-error-handling.md`
- [ ] Write `ADR-003-repository-pattern.md`
- [ ] Update `SYNC_ARCHITECTURE_ANALYSIS.md` with implementation notes

---

## 📊 Success Metrics

After implementation, measure and verify:

1. **Error Rate**: < 1% of syncs fail due to transient errors
2. **Test Coverage**: > 90% for sync module (check with `pytest --cov`)
3. **Unhappy Path Coverage**: > 80% of error scenarios tested
4. **MTTR**: Circuit breaker reduces mean time to recovery by 50%
5. **Duplicate Prevention**: 0 duplicate issues created during failed sync recovery
6. **Developer Experience**: New backend added in < 4 hours (vs ~2 days currently)

---

## 🚨 Important Notes

### Files Already Created (Ready for Integration)
- `roadmap/core/services/sync/performance.py` - SyncCache and IssueIndexer
- `roadmap/core/services/sync/batch_processor.py` - BatchProcessor and AsyncBatchProcessor
- `roadmap/core/services/sync/sync_checkpoint.py` - Checkpoint/rollback system
- `roadmap/adapters/cli/sync_handlers/interactive_resolver.py` - Interactive conflict resolution
- `roadmap/adapters/cli/sync_handlers/progress_tracker.py` - Progress indicators
- `roadmap/adapters/cli/commands/sync_status.py` - Status dashboard

### Policy Directives (MUST FOLLOW)
- ❌ Do NOT commit, reset, or force push to main branch without approval
- ❌ Do NOT revert changes to main branch without approval
- ❌ Do NOT create new branches without approval
- ❌ Do NOT run full test suite without approval
- ❌ Do NOT deploy to production without approval
- ❌ Do NOT decide that a failing test is acceptable without approval
- ❌ Do NOT merge pull requests without approval
- ✅ Use CLI git, not MCP

### Development Guidelines
- Use `uv` for Python environment management
- Use Poetry for dependency management
- Follow semantic versioning
- Maintain POSIX compatibility throughout
- Use type hints everywhere
- Check code quality: `uv run radon cc --min D roadmap/` (no D/E/F grades)
- Run tests: `uv run pytest`

---

## 📦 Pending Work: Entity Breakdown UI

**Note**: The entity breakdown UI improvements (from `SYNC_ENTITY_BREAKDOWN_PROPOSAL.md`) are separate from architectural improvements and can be implemented independently.

**Summary**: Add 5-category status breakdown × entity columns format:
- Categories: Up-to-date, Needs Push, Needs Pull, Conflicts, Errors
- Entities: Issues, Milestones, Projects, TOTAL
- Apply to both dry-run analysis and post-sync reports

**Estimated Time**: 9-12 hours (can be done in parallel or after Phase 1)

---

## 🔄 How to Resume Work

1. **Read this roadmap** to understand current state and plan
2. **Read `SYNC_ARCHITECTURE_ANALYSIS.md`** for detailed technical context
3. **Start with Phase 1, Task 1.1** (Result<T,E> pattern)
4. **Follow the task list sequentially** - each task builds on previous
5. **Run tests after each task** to ensure no regressions
6. **Commit frequently** with clear, descriptive messages

---

## 📚 Reference Documents

- `docs/developer_notes/SYNC_ENTITY_BREAKDOWN_PROPOSAL.md` - UI improvements design
- `docs/developer_notes/SYNC_ARCHITECTURE_ANALYSIS.md` - Comprehensive architecture review
- `docs/.github/copilot-instructions.md` - Project-specific guidelines
- `roadmap/adapters/sync/sync_merge_orchestrator.py` - Main sync coordinator
- `roadmap/adapters/sync/backends/github_sync_backend.py` - GitHub backend implementation

---

**Last Updated**: February 5, 2026
**Next Action**: Begin Phase 1, Task 1.1 - Implement Result<T,E> pattern
