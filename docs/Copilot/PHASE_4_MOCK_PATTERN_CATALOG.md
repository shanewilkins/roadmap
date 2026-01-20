# Phase 4: Mock Consolidation Pattern Catalog

## 📊 Executive Summary

**Total Mock Patterns to Consolidate**: 937 direct Mock() calls across 83 test files
**Phase 4 Scope (Tactical)**: Top 20-30 patterns (~300-400 calls)
**Focus Domain**: Sync-related services (highest priority)
**Estimated Impact**: 30-40% reduction in direct Mock() calls in Phase 4

---

## 🎯 Top 20 Mock Patterns by Frequency

### Tier 1: High Priority (50+ occurrences each)

| Rank | Pattern | Count | Type | Key Files |
|------|---------|-------|------|-----------|
| 1 | `mock_response` | 52 | HTTP/API Response | test_*_service.py (presenter, github) |
| 2 | `mock_console` | 50 | Rich Console I/O | test_*_presenter.py (all presenters) |
| 3 | `mock_get_connection` | 49 | DB Connection | test_*_repository.py, test_queries.py |
| 4 | `mock_transaction` | 48 | DB Transaction Context | test_*_repository.py (create, update ops) |
| 5 | `core` / `mock_core` | 48+9=57 | RoadmapCore Mock | test_initialization.py, test_services.py |

### Tier 2: Medium-High Priority (20-49 occurrences)

| Rank | Pattern | Count | Type | Key Files |
|------|---------|-------|------|-----------|
| 6 | `mock_git` | 46 | Git Operations | test_git_*.py, test_sync_*.py |
| 7 | `mock_git_integration` | 24 | GitHub Integration | test_github_*.py |
| 8 | `issue` / `mock_issue` | 32+21=53 | Issue Domain Object | test_*_service.py, test_health_*.py |
| 9 | `milestone` / `mock_milestone` | 19 | Milestone Domain Object | test_milestone_*.py, test_queries.py |
| 10 | `mock_executor` | 17 | Git/Shell Executor | test_git_*.py (sync domain) |

### Tier 3: Medium Priority (15-25 occurrences)

| Rank | Pattern | Count | Type | Key Files |
|------|---------|-------|------|-----------|
| 11 | `mock_func` | 16 | Generic Callable Mock | test_service.py (dispatch, handlers) |
| 12 | `mock_config` | 15 | Configuration Object | test_github_*.py, test_init.py |
| 13 | `project` | 13 | Project Domain Object | test_project_*.py, test_services.py |
| 14 | `mock_branch` | 13 | Git Branch Object | test_git_branch_*.py |
| 15 | `service` | 11 | Generic Service Mock | test_cli_*.py, test_command_*.py |

### Tier 4: Lower Priority (10-14 occurrences)

| Rank | Pattern | Count | Type | Key Files |
|------|---------|-------|------|-----------|
| 16 | `mock_manager` | 10 | Manager/Coordinator | test_github_*.py, test_sync_*.py |
| 17 | `mock_dep_issue` | 10 | Dependency-related Issue | test_dependency_*.py |
| 18 | `mock_query` | 9 | Query/Search Mock | test_queries_*.py |
| 19 | `mock_formatter_instance` | 9 | Formatter Instance | test_*_formatter.py |
| 20 | `commit` | 9 | Git Commit Object | test_git_commit_*.py |
| 21 | `mock_client` | 8 | HTTP/API Client | test_github_*.py, test_integration.py |
| 22 | `mock_report` | 7 | Report/Result Object | test_health_*.py, test_analysis.py |

---

## 🔄 Fixture Factory Design Patterns

### Pattern 1: Simple Response Mock
**Occurrence**: 52 (mock_response)
**Setup Pattern**:
```python
mock_response = Mock()
mock_response.status_code = 200
mock_response.json.return_value = {...}
mock_response.text = "..."
```

**Fixture Design**:
```python
@pytest.fixture
def mock_response_factory():
    def _factory(status_code=200, json_data=None, text="", headers=None):
        response = Mock()
        response.status_code = status_code
        response.json.return_value = json_data or {}
        response.text = text
        response.headers = headers or {}
        return response
    return _factory
```

**Files to Refactor**: test_github_integration_service.py, test_sync_backend_selection.py

---

### Pattern 2: Console/Output Mock
**Occurrence**: 50 (mock_console)
**Setup Pattern**:
```python
mock_console = Mock()
mock_console.print = Mock()
mock_console.rule = Mock()
mock_console.panel = Mock()
```

**Fixture Design**:
```python
@pytest.fixture
def mock_console_factory():
    def _factory(with_print=True, with_rule=True, with_panel=True):
        console = Mock()
        if with_print:
            console.print = Mock()
        if with_rule:
            console.rule = Mock()
        if with_panel:
            console.panel = Mock()
        return console
    return _factory
```

**Files to Refactor**: test_*_presenter.py (all 5 presenter test files)

---

### Pattern 3: Database Connection/Transaction
**Occurrence**: 48+48=96 (mock_get_connection + mock_transaction)
**Setup Pattern**:
```python
mock_transaction = Mock()
mock_conn = Mock()
mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
mock_transaction.return_value.__exit__ = Mock(return_value=False)
mock_get_connection = Mock(return_value=mock_conn)
```

**Fixture Design** (REUSE: mock_database_connection_factory already exists! ✅)
- Already created in Phase 2.1
- Can extend if needed for transaction context managers

**Files to Refactor**: test_*_repository.py (multiple), test_queries_state_operations.py

---

### Pattern 4: Git/VCS Operations Mock
**Occurrence**: 46 (mock_git)
**Setup Pattern**:
```python
mock_git = Mock()
mock_git.get_current_branch.return_value = "main"
mock_git.run.return_value = "output"
mock_git.get_commits.return_value = [...]
```

**Fixture Design**:
```python
@pytest.fixture
def mock_git_factory():
    def _factory(current_branch="main", run_output="", commits=None):
        git = Mock()
        git.get_current_branch.return_value = current_branch
        git.run.return_value = run_output
        git.get_commits.return_value = commits or []
        git.is_dirty.return_value = False
        return git
    return _factory
```

**Files to Refactor**: test_git_branch_manager.py (27 mocks), test_git_commit_analyzer.py (16 mocks)

---

### Pattern 5: Domain Object Mocks (Issue/Milestone/Project)
**Occurrence**: 32+19+13=64 (issue, milestone, project)
**Note**: We already have `mock_issue_factory`, `mock_milestone_factory` from Phase 2!
**Action**: Verify they're being used in all appropriate files

**Files to Refactor**: Audit all *_service.py and *_health.py files to ensure using factories

---

### Pattern 6: GitHub Integration Mock
**Occurrence**: 24 (mock_git_integration)
**Setup Pattern**:
```python
mock_git_integration = Mock()
mock_git_integration.authenticate.return_value = True
mock_git_integration.sync.side_effect = [...]
mock_git_integration.get_issues.return_value = [...]
```

**Fixture Design**:
```python
@pytest.fixture
def mock_github_integration_factory():
    def _factory(authenticated=True, sync_result=None, issues=None):
        integration = Mock()
        integration.authenticate.return_value = authenticated
        integration.sync.return_value = sync_result
        integration.get_issues.return_value = issues or []
        return integration
    return _factory
```

**Files to Refactor**: test_github_*.py (3-4 files), test_sync_orchestrator*.py

---

### Pattern 7: Git Executor Mock (Sync-Critical)
**Occurrence**: 17 (mock_executor) + 14 (monitor.git_executor.run)
**Setup Pattern**:
```python
mock_executor = Mock()
mock_executor.run.return_value = "commit_hash"
mock_executor.is_git_repository.return_value = True
mock_executor.get_current_branch.return_value = "main"
```

**Fixture Design**:
```python
@pytest.fixture
def mock_git_executor_factory():
    def _factory(run_output="", is_repo=True, current_branch="main"):
        executor = Mock()
        executor.run.return_value = run_output
        executor.is_git_repository.return_value = is_repo
        executor.get_current_branch.return_value = current_branch
        executor.commit.return_value = None
        return executor
    return _factory
```

**Files to Refactor**: test_sync_monitor.py (24 mocks), test_git_hooks_manager.py

---

## 📍 Sync Domain Focus Files (Phase 4 Priority)

### High Priority (Sync Domain - Most Impact)

1. **test_git_branch_manager.py** (27 mocks)
   - Patterns: mock_executor (6x), issue (6x), config (2x)
   - Refactor with: mock_git_executor_factory, mock_issue_factory, mock_config_factory

2. **test_sync_monitor.py** (24 mocks)
   - Patterns: monitor.git_executor.* (14x), monitor._get_changed_files (3x)
   - Refactor with: mock_git_executor_factory, custom monitor setup fixture

3. **test_git_commit_analyzer.py** (16 mocks)
   - Patterns: mock_executor (multiple), commit objects
   - Refactor with: mock_git_executor_factory

4. **test_sync_retrieval_orchestrator.py** (23 mocks)
   - Patterns: mock_git_integration, mock_executor, mock_transaction
   - Refactor with: mock_github_integration_factory, mock_git_executor_factory

### Medium Priority (Sync-Related Support)

5. **test_github_integration_service.py** (15+ mocks)
   - Patterns: mock_config, mock_manager, mock_response
   - Refactor with: mock_config_factory, mock_github_manager_factory, mock_response_factory

6. **test_sync_cache_orchestrator.py** (estimated 12-15 mocks)
   - Patterns: likely similar to retrieval orchestrator
   - Refactor with: existing sync factories

---

## 📋 Implementation Checklist

### Phase 4.1: Analysis ✅
- [x] Identify top 20-30 Mock patterns
- [x] Categorize by frequency and domain
- [x] Map to sync-related files

### Phase 4.2: Fixture Creation (Next)
- [ ] Create mock_response_factory
- [ ] Create mock_console_factory (all presenter mocks)
- [ ] Create mock_git_factory
- [ ] Create mock_github_integration_factory
- [ ] Create mock_git_executor_factory (SYNC PRIORITY)
- [ ] Create mock_config_factory
- [ ] Create mock_github_manager_factory
- [ ] Verify existing factories: mock_database_connection_factory, mock_issue_factory, mock_milestone_factory
- [ ] Export all to appropriate conftest.py files

### Phase 4.3: Refactoring (Sync-Priority)
- [ ] Refactor test_git_branch_manager.py (27 mocks)
- [ ] Refactor test_sync_monitor.py (24 mocks)
- [ ] Refactor test_git_commit_analyzer.py (16 mocks)
- [ ] Refactor test_sync_retrieval_orchestrator.py (23 mocks)
- [ ] Refactor test_github_integration_service.py (15+ mocks)

### Phase 4.4: Validation
- [ ] All 6567+ tests passing
- [ ] All linting passing
- [ ] No regressions
- [ ] Commit Phase 4 work

### Phase 4.5: Re-evaluation
- [ ] Measure reduction: 90 mocks → ~55 (expected ~60% reduction in targeted files)
- [ ] Assess Phase 5 effort based on remaining ~550-600 Mock() calls
- [ ] Decide: Continue Phase 5 or stop

---

## 📊 Expected Outcomes

**Phase 4 Success Metrics**:
- [ ] 8-12 new fixture factories created
- [ ] 90-100 direct Mock() calls eliminated from refactored files
- [ ] Sync domain test files refactored (90+ mocks consolidated)
- [ ] All tests passing with zero regressions
- [ ] Pattern catalog established for Phase 5+

**Efficiency Gains**:
- Sync test files: 75-90 mocks → ~20-25 fixtures (75% reduction)
- Presenter files: 50+ console mocks → 1 factory fixture
- Database files: 96 connection/transaction patterns → 1-2 factory fixtures

---

## 🔮 Phase 5 Decision Criteria

After Phase 4 completion, re-evaluate:
1. **Effort vs. Impact**: How much refactoring work remains vs. value gained?
2. **Pattern Consistency**: Are emerging patterns clear enough to apply systematically?
3. **Test Suite Stability**: Any issues encountered in Phase 4?
4. **Timeline**: How much time investment is reasonable?

**Go/No-Go Decision Points**:
- **GO to Phase 5** if: <15 hours estimated, >40% of remaining calls easily consolidatable
- **DEFER to Phase 6** if: >20 hours estimated or complex patterns require individual handling
- **SKIP Phase 5** if: Remaining calls are too diverse/specialized

---

## 📝 Notes

- **Already Completed**: mock_database_connection_factory (Phase 2.1), mock_issue_factory, mock_milestone_factory
- **REUSE Strategy**: Many factories already exist; focus is on adoption/refactoring
- **Domain Priority**: Sync services get first attention due to business impact
- **Incremental Approach**: Refactor file-by-file, validate thoroughly before moving to next
