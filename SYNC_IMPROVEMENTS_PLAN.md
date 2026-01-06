ok,# Sync Improvements Implementation Plan

## Sprint 1: Foundation (Manual Linking)

### 1.1 Update Issue Domain Model
- [ ] Add `remote_ids: dict[str, str | int] = Field(default_factory=dict)` to Issue
- [ ] Add `@property github_issue` getter/setter for backwards compat
- [ ] Update Issue serialization/deserialization for YAML

**Files**: `roadmap/core/domain/issue.py`

### 1.2 Update SyncBackendInterface
- [ ] Add `get_backend_name() -> str` method
- [ ] Update protocol definition and docstrings

**Files**: `roadmap/core/interfaces/sync_backend.py`

### 1.3 Update Backends
- [ ] Update `GitHubBackend.get_backend_name()` → returns "github"
- [ ] Update `VanillaGitSyncBackend.get_backend_name()` → returns "git"
- [ ] Ensure backends work with new interface

**Files**: `roadmap/adapters/sync/backends/*.py`

### 1.4 Add Manual Link/Unlink Commands to CLI
- [ ] Add `--link <remote-id>` flag to `roadmap sync` command
- [ ] Add `--unlink` flag to `roadmap sync` command
- [ ] Implement link logic: set `issue.remote_ids[backend_name] = remote_id`
- [ ] Implement unlink logic: remove `issue.remote_ids[backend_name]`
- [ ] Add validation and user feedback

**Files**: `roadmap/adapters/cli/sync.py`

**Usage**:
```bash
roadmap sync --link 7e99d67b 42              # Link local issue to GitHub #42
roadmap sync --unlink 7e99d67b               # Remove GitHub link
```

### 1.5 Update Tests
- [ ] Update `IssueTestDataBuilder` to use `with_remote_id()` for setting remote_ids
- [ ] Ensure existing tests still pass with property accessor
- [ ] Add tests for link/unlink commands

**Files**: `tests/factories/sync_data.py`, `tests/unit/adapters/cli/test_sync.py`

**Validation**: All existing tests pass with new Issue model

---

## Sprint 2: Comparator Awareness

### 2.1 Update SyncStateComparator
- [ ] Add `backend: SyncBackendInterface` parameter to `__init__`
- [ ] Implement `_normalize_local_to_remote_keys()` method
- [ ] Update `analyze_three_way()` to normalize keys before comparison
- [ ] Handle new issues (no remote_id) with `__new__{uuid}` prefix

**Files**: `roadmap/core/services/sync_state_comparator.py`

### 2.2 Update SyncMergeOrchestrator
- [ ] Pass `backend` instance to `SyncStateComparator` constructor
- [ ] Update comparator instantiation in `sync_all_issues()`

**Files**: `roadmap/adapters/sync/sync_merge_orchestrator.py`

### 2.3 Verify Matching Logic
- [ ] Test: Local issue with remote_ids["github"]=42 matches GitHub issue #42
- [ ] Test: New local issue (no remote_id) treated as push
- [ ] Test: New remote issue (no matching local) treated as pull
- [ ] Test: Three-way merge uses correct keys for conflict detection

**Validation**: Integration tests show proper matching and no false duplicates

---

## Sprint 3: Smart Matching (Future)

### 3.1 Implement Smart Matching
- [ ] Add `smart_match_issues()` function
- [ ] Exact title matching with confidence scoring
- [ ] User confirmation for ambiguous cases

### 3.2 First-Sync Detection
- [ ] Detect if no issues have remote_ids yet
- [ ] Run smart matching before comparison
- [ ] Auto-link confident matches

### 3.3 Auto-Link on Push/Pull
- [ ] After pushing new issue to remote, auto-set remote_ids
- [ ] After pulling new issue from remote, auto-set remote_ids

---

## Acceptance Criteria

### Phase 1 (Manual Linking)
- ✓ `remote_ids` field stores and persists correctly
- ✓ `issue.github_issue` property works for backwards compat
- ✓ `roadmap sync --link <local-id> <remote-id>` works
- ✓ `roadmap sync --unlink <local-id>` works
- ✓ All existing tests pass
- ✓ No breaking changes to CLI or API

### Phase 2 (Comparator)
- ✓ Comparator receives backend instance
- ✓ Keys normalized before comparison
- ✓ Issues matched correctly using remote_ids
- ✓ No more false "new issue" duplicates
- ✓ Integration tests verify correct matching behavior

### Phase 3 (Smart Matching - Future)
- ✓ First sync with existing issues shows matches
- ✓ User can confirm/reject matches
- ✓ Auto-linking works on push/pull operations
- ✓ Zero user intervention for typical workflows

## Success Metrics

- [ ] Sync no longer treats matched issues as new
- [ ] Local UUID consistency maintained
- [ ] Multiple backends can coexist with different remote_ids
- [ ] Test suite passes (6000+ tests)
- [ ] Manual link/unlink commands work correctly
- [ ] No data loss during migration
