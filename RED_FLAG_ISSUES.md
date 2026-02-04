# RED FLAG FINDINGS - Confirmed Issues

**Status**: These are likely the ROOT CAUSES of app breakage. Each one represents incomplete refactoring.

---

## 1. ❌ CONFLICT_DETECTOR - Unused Attribute
**File**: `roadmap/adapters/sync/backends/github_sync_backend.py`
**Lines**: 87-89
**Issue**: Initialized but never used

```python
# Line 87: Set to None
self.conflict_detector = None

# Line 89: Conditionally initialized
if hasattr(core, "github_service") and core.github_service is not None:
    self.conflict_detector = self._safe_init(...)
```

**Problem**: This attribute is created but never referenced anywhere in the class.

**Impact**: GitHub conflict detection is not active during sync.

**Action**: Remove lines 87-89 unless external code depends on it.

---

## 2. ❌ _PUSH_SERVICE - Never Lazily Initialized
**File**: `roadmap/adapters/sync/backends/github_sync_backend.py`
**Line**: 112
**Issue**: Set to None but never actually initialized

```python
self._fetch_service = None  # Initialized lazily after auth (WORKS - lines 174-183)
self._push_service = None   # Initialized lazily after auth (NEVER HAPPENS - LINE 112 ONLY)
```

**Pattern**: `_fetch_service` IS lazily initialized (see lines 174-183), but `_push_service` is not.

**Problem**: Unlike fetch, push never gets initialized. There's a `GitHubIssuePushService` class that exists but is never instantiated.

**Impact**: If push operations require the service (currently they use individual `push_issue` calls), this could cause issues.

**Action**: Implement lazy initialization like `_fetch_service` or determine if it's needed at all.

---

## 3. ❌ _SYNC_STATE_TRACKER - Duplicate Initialization (Wrong Place)
**File**: `roadmap/adapters/persistence/storage/state_manager.py`
**Line**: 68
**Issue**: Initialized but never used here - ALSO initialized elsewhere

```python
# Line 68 in state_manager.py (NEVER USED)
self._sync_state_tracker = SyncStateTracker(self._db_manager._get_connection)
```

**But also**:
```python
# Line 30 in sync_orchestrator.py (ACTUALLY USED)
self._state_tracker = SyncStateTracker(get_connection)
```

**Problem**:
- `SyncStateTracker` is the sync metadata tracker (tracks which files have been synced)
- It's properly initialized and used in `sync_orchestrator.py`
- But ALSO initialized in `state_manager.py` where it's never used
- This is a symptom of incomplete refactoring - code was moved but old initialization wasn't removed

**Impact**: Dead initialization in state_manager, but the functionality IS available through sync_orchestrator.

**Root Cause**: Incomplete refactor - state_manager probably had sync responsibilities that were moved to sync_orchestrator, but cleanup wasn't finished.

**Action**: Remove lines 68 from state_manager (it's already properly initialized in sync_orchestrator where it's actually used).

---

## 4. ❌ _CONFLICT_RESOLVER - Duplicate Initialization (Wrong Place)
**File**: `roadmap/adapters/persistence/storage/state_manager.py`
**Line**: 69-70
**Issue**: Initialized but never used here - should probably be elsewhere

```python
# Line 69-70 in state_manager.py (NEVER USED)
self._conflict_resolver = ConflictResolver(
    self.db_path.parent
)  # data_dir is parent of db file
```

**Problem**:
- `ConflictResolver` detects and resolves git merge conflicts in `.roadmap` files
- It has methods: `detect_conflicts()`, `resolve_conflict()`, `auto_resolve_conflicts()`
- It's created but never called in state_manager
- Never found in use anywhere else in codebase

**Impact**: Git conflict detection is not running. If files have merge conflict markers, they won't be detected or resolved.

**Root Cause**: Likely intended for `sync_orchestrator` (which manages `.roadmap` directory sync) but was mistakenly placed in state_manager.

**Action**: Either:
- Move to `sync_orchestrator` and actually use it for conflict detection
- Remove if conflict resolution is handled elsewhere
- Investigate if this is why conflicts aren't being detected

---

## Summary: Incomplete Refactoring Pattern

All four of these follow the same pattern:

1. **Code exists but isn't initialized**: `_push_service`
2. **Code is initialized but not used**: `conflict_detector`, `_sync_state_tracker`, `_conflict_resolver`
3. **Similar code exists in the right place**: `_sync_state_tracker` in sync_orchestrator, `_fetch_service` properly initialized

This is textbook incomplete refactoring - likely during an architectural redesign, code was moved from state_manager to sync_orchestrator, but:
- The old initialization in state_manager wasn't removed
- The new initialization in sync_backend wasn't finished

---

## Critical Questions for App Breakage

1. **Is git conflict detection running?** If `_conflict_resolver` is not being used, conflicts won't be detected.
2. **Is sync metadata being tracked?** If `_sync_state_tracker` in state_manager is used instead of sync_orchestrator's version, tracking might be broken.
3. **Are push operations working?** If `_push_service` was supposed to be initialized, push might be partially broken.
4. **Is GitHub integration working?** If `conflict_detector` was supposed to run conflict detection during GitHub sync, that's missing.

These unused initializations could very well be why the app is currently broken.
