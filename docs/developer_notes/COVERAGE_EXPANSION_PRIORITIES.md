# Coverage Expansion Priorities - Phase 8 Tier 2+

**Current Coverage**: 77% (6616 tests passing)
**Goal**: 85%
**Gap**: 8 percentage points (~800 lines to cover)

---

## Priority Tiers

### 🔴 CRITICAL (10-40% coverage) - Highest Impact

These files have severe undercoverage and are likely causing significant gaps:

| File | Lines | Coverage | Uncovered | Priority |
|------|-------|----------|-----------|----------|
| [roadmap/adapters/sync/services/local_change_filter.py](roadmap/adapters/sync/services/local_change_filter.py) | 48 | 10% | 43 | 🔴 CRITICAL |
| [roadmap/adapters/sync/services/pull_result_processor.py](roadmap/adapters/sync/services/pull_result_processor.py) | 40 | 12% | 35 | 🔴 CRITICAL |
| [roadmap/adapters/sync/backends/github_backend_helpers.py](roadmap/adapters/sync/backends/github_backend_helpers.py) | 120 | 12% | 106 | 🔴 CRITICAL |
| [roadmap/adapters/cli/sync_validation.py](roadmap/adapters/cli/sync_validation.py) | 115 | 13% | 100 | 🔴 CRITICAL |
| [roadmap/core/services/utils/remote_fetcher.py](roadmap/core/services/utils/remote_fetcher.py) | 92 | 15% | 78 | 🔴 CRITICAL |
| [roadmap/adapters/persistence/repositories/remote_link_repository.py](roadmap/adapters/persistence/repositories/remote_link_repository.py) | 121 | 17% | 100 | 🔴 CRITICAL |
| [roadmap/core/services/sync/sync_state_manager.py](roadmap/core/services/sync/sync_state_manager.py) | 127 | 19% | 103 | 🔴 CRITICAL |
| [roadmap/core/services/utils/remote_state_normalizer.py](roadmap/core/services/utils/remote_state_normalizer.py) | 45 | 20% | 36 | 🔴 CRITICAL |
| [roadmap/adapters/cli/git/handlers/git_connectivity_handler.py](roadmap/adapters/cli/git/handlers/git_connectivity_handler.py) | 43 | 16% | 36 | 🔴 CRITICAL |
| [roadmap/adapters/cli/git/handlers/git_hooks_handler.py](roadmap/adapters/cli/git/handlers/git_hooks_handler.py) | 45 | 22% | 35 | 🔴 CRITICAL |

**Total Uncovered**: ~570 lines
**Estimated Coverage Gain**: +2.1%

---

### 🟠 HIGH (30-45% coverage) - High Impact, Medium Complexity

| File | Lines | Coverage | Uncovered | Notes |
|------|-------|----------|-----------|-------|
| [roadmap/adapters/cli/output_manager.py](roadmap/adapters/cli/output_manager.py) | 94 | 40% | 56 | Output formatting |
| [roadmap/adapters/sync/sync_merge_engine.py](roadmap/adapters/sync/sync_merge_engine.py) | 220 | 40% | 131 | Core merge logic |
| [roadmap/adapters/sync/services/remote_issue_creation_service.py](roadmap/adapters/sync/services/remote_issue_creation_service.py) | 29 | 38% | 18 | Remote issue creation |
| [roadmap/settings.py](roadmap/settings.py) | 74 | 38% | 46 | Configuration |
| [roadmap/core/services/github/github_change_detector.py](roadmap/core/services/github/github_change_detector.py) | 52 | 29% | 37 | Change detection |
| [roadmap/adapters/cli/sync.py](roadmap/adapters/cli/sync.py) | 121 | 34% | 80 | Sync command |
| [roadmap/adapters/cli/issues/comment.py](roadmap/adapters/cli/issues/comment.py) | 74 | 34% | 49 | Comment command |
| [roadmap/adapters/cli/projects/close.py](roadmap/adapters/cli/projects/close.py) | 55 | 31% | 38 | Project close |
| [roadmap/adapters/cli/issues/unlink.py](roadmap/adapters/cli/issues/unlink.py) | 40 | 32% | 27 | Issue unlinking |
| [roadmap/adapters/cli/presentation/cleanup_presenter.py](roadmap/adapters/cli/presentation/cleanup_presenter.py) | 94 | 32% | 64 | Cleanup output |

**Total Uncovered**: ~546 lines
**Estimated Coverage Gain**: +2.0%

---

### 🟡 MEDIUM (45-60% coverage) - Medium Impact, Medium Complexity

| File | Lines | Coverage | Uncovered | Notes |
|------|-------|----------|-----------|-------|
| [roadmap/adapters/cli/git/commands.py](roadmap/adapters/cli/git/commands.py) | 206 | 46% | 111 | Git commands |
| [roadmap/adapters/sync/sync_merge_orchestrator.py](roadmap/adapters/sync/sync_merge_orchestrator.py) | 210 | 48% | 110 | Sync orchestration |
| [roadmap/core/services/baseline/baseline_retriever.py](roadmap/core/services/baseline/baseline_retriever.py) | 20 | 35% | 13 | Baseline retrieval |
| [roadmap/adapters/cli/health/fixers/orphaned_issues_fixer.py](roadmap/adapters/cli/health/fixers/orphaned_issues_fixer.py) | 92 | 33% | 62 | Health fixing |
| [roadmap/common/utils/file_utils.py](roadmap/common/utils/file_utils.py) | 137 | 58% | 58 | File operations |
| [roadmap/common/logging/utils.py](roadmap/common/logging/utils.py) | 77 | 56% | 34 | Logging utilities |

**Total Uncovered**: ~388 lines
**Estimated Coverage Gain**: +1.4%

---

## Recommended Tier 2 Strategy

### Phase 8 Tier 2A: Quick Wins (SYNC Layer - Critical)
**Target Coverage Gain**: +1.5% (120 lines)
**Estimated Time**: 3-4 hours

**Focus**: Core sync functionality that's completely untested

1. **[roadmap/adapters/sync/services/local_change_filter.py](roadmap/adapters/sync/services/local_change_filter.py)** (10% → 80%)
   - 48 lines, 43 uncovered
   - Tests: Filter logic, edge cases
   - Time: ~45 minutes

2. **[roadmap/core/services/sync/sync_state_manager.py](roadmap/core/services/sync/sync_state_manager.py)** (19% → 70%)
   - 127 lines, 103 uncovered
   - Tests: State transitions, updates
   - Time: ~90 minutes

3. **[roadmap/core/services/utils/remote_fetcher.py](roadmap/core/services/utils/remote_fetcher.py)** (15% → 75%)
   - 92 lines, 78 uncovered
   - Tests: Fetch logic, error handling
   - Time: ~75 minutes

### Phase 8 Tier 2B: Infrastructure (Git/Settings - High Value)
**Target Coverage Gain**: +1.0% (80 lines)
**Estimated Time**: 2-3 hours

1. **[roadmap/settings.py](roadmap/settings.py)** (38% → 85%)
   - 74 lines, 46 uncovered
   - Tests: Configuration loading, validation
   - Time: ~60 minutes

2. **[roadmap/adapters/cli/git/handlers/git_connectivity_handler.py](roadmap/adapters/cli/git/handlers/git_connectivity_handler.py)** (16% → 80%)
   - 43 lines, 36 uncovered
   - Tests: Connectivity checks, error scenarios
   - Time: ~50 minutes

---

## Expected Impact

| Tier | Files | Current | Target | Gain |
|------|-------|---------|--------|------|
| Current | 6616 tests | 77% | — | — |
| 2A (Sync) | 3 files | 15% avg | 75% avg | +1.5% |
| 2B (Infrastructure) | 2 files | 27% avg | 82% avg | +1.0% |
| **Total with Tier 2A+2B** | — | **77%** | **79.5%** | **+2.5%** |

To reach 85%, would need:
- Tier 2C: CLI commands (git, sync, issues) → +1.5%
- Tier 2D: Health/cleanup fixers → +1.5%
- Tier 2E: Presentation/output → +0.5%

---

## Test Pattern Recommendations

### For Sync Services
Use mocking and parametrization:
```python
@pytest.mark.parametrize("change_type,expected", [
    ("local_only", True),
    ("remote_only", False),
    ("conflict", None),
])
def test_filter_changes(change_type, expected, sync_factory):
    """Test change filtering logic."""
```

### For Remote Fetcher
Mock GitHub API, test error paths:
```python
@pytest.fixture
def remote_fetcher_mock():
    with patch("roadmap.core.services.utils.remote_fetcher.GitHubAPI") as mock:
        yield mock

def test_fetch_with_retry(remote_fetcher_mock):
    """Test fetch retry mechanism."""
```

### For Settings
Use isolated filesystem:
```python
def test_settings_loading(tmp_path):
    """Test loading configuration from file."""
    config_file = tmp_path / "config.toml"
    # Create test config
    result = load_settings(config_file)
```

---

## Next Steps

1. **Start with Tier 2A** (Sync layer - most critical)
2. **Use factories** from TEST_INDEPENDENCE_PATTERNS.md
3. **Follow parametrization** patterns from Phase 8 Tier 1
4. **Run tests** frequently to validate coverage gains
5. **Commit regularly** with clear coverage metrics

---

## References

- [TEST_INDEPENDENCE_PATTERNS.md](docs/developer_notes/TEST_INDEPENDENCE_PATTERNS.md)
- [FLAKINESS_INVESTIGATION_SUMMARY.md](docs/developer_notes/FLAKINESS_INVESTIGATION_SUMMARY.md)
- [GLOBAL_SINGLETON_AUDIT.md](docs/developer_notes/GLOBAL_SINGLETON_AUDIT.md)
- [PHASE_9_IMPLEMENTATION.md](PHASE_9_IMPLEMENTATION.md)
