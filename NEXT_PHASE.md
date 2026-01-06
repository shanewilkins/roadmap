# Next Phase: GitSyncMonitor Implementation

## Quick Overview

You now have the architecture designed. Time to implement.

**What:** Build a `GitSyncMonitor` class that detects file changes via `git diff` and syncs them to the database.

**Why:** Current system scans 1000 files every command. New system checks git diff (50ms) + database (5ms).

**How:** 4 phases, 1-2 weeks total.

---

## Phase 1: Build GitSyncMonitor

**File:** `roadmap/adapters/git/sync_monitor.py`

**What it does:**
```python
class GitSyncMonitor:
    # Detect what changed: git diff --name-only
    def detect_changes() -> dict[str, str]

    # Load changed files into database
    def sync_to_database(changes)

    # Track what we've synced
    def _get_last_synced_commit() -> str
    def _save_last_synced_commit()
```

**Tests needed:**
- Unit tests for change detection
- Unit tests for database sync
- Integration tests with real git repo

**Time:** 1-2 days

**Acceptance criteria:**
- ✓ Detects modified/added/deleted files
- ✓ Ignores non-.roadmap/issues/ changes
- ✓ Syncs to database without errors
- ✓ Handles first sync (no previous commit)
- ✓ All tests passing

---

## Phase 2: Integrate with IssueService

**File:** `roadmap/core/services/issue_service.py`

**Changes:**
```python
class IssueService:
    def __init__(self, file_repo, cache_repo, git_monitor):
        # Add git_monitor

    def list_issues(self, **filters):
        # Check git before querying DB
        changes = self.git_monitor.detect_changes()
        if changes:
            self.git_monitor.sync_to_database(changes)

        # Now return from cache (fast)
        return self.cache_repo.list(**filters)

    def create_issue(self, params):
        # Write to file first
        issue = self.file_repo.create(params)

        # Sync to database
        self.cache_repo.save(issue)
        return issue
```

**Wire up:** `roadmap/infrastructure/core.py`
```python
class RoadmapCore:
    def __init__(self, ...):
        # Create git monitor
        self.git_monitor = GitSyncMonitor(self.root_path)

        # Pass to service
        self.issue_service = IssueService(
            file_repo, cache_repo, self.git_monitor
        )
```

**Time:** 1-2 days

**Acceptance criteria:**
- ✓ List commands use git monitor
- ✓ Performance test shows 10x improvement
- ✓ All existing tests still pass
- ✓ No breaking changes to API

---

## Phase 3: Improve Sync Operations

**File:** `roadmap/adapters/sync/sync_retrieval_orchestrator.py`

**Changes:**
```python
class SyncRetrievalOrchestrator:
    def get_baseline(self):
        # OLD: Parse git history
        # baseline = self.baseline_retriever.get_from_git()

        # NEW: Get from database
        baseline_data = self.state_manager.get_sync_baseline()
        return self._convert_to_sync_issues(baseline_data)

    def apply_changes(self, changes):
        # Write to file (source of truth)
        # Update database cache
        # Update sync baseline in database
```

**Time:** 1 day

**Acceptance criteria:**
- ✓ Baseline loads from database
- ✓ Baseline faster than git parsing
- ✓ All sync tests still pass
- ✓ Three-way merge still works

---

## Phase 4: Test & Validate

**Performance benchmarks:**
```python
# tests/integration/test_performance.py

def test_list_speed_with_1000_issues():
    # Should be <100ms for list()
    # Should be <10ms for cached query

def test_baseline_load_speed():
    # Should be <10ms (was 500ms with git parsing)
```

**Edge cases:**
```python
# tests/unit/adapters/git/test_sync_monitor.py

def test_detached_head_fallback()
def test_rebase_detection()
def test_first_sync_no_previous_commit()
def test_ignore_non_issue_files()
```

**Integration:**
```python
# tests/integration/test_git_sync_full.py

def test_create_issue_updates_database()
def test_modify_issue_via_git_syncs_to_db()
def test_delete_issue_removes_from_db()
```

**Time:** 1-2 days

**Acceptance criteria:**
- ✓ All benchmarks meet targets
- ✓ All edge cases handled
- ✓ 6500+ tests passing
- ✓ Performance improved 10-20x

---

## Current Code Reference

Start here to understand the structure:

**Database layer (target for caching):**
- `roadmap/adapters/persistence/storage/state_manager.py` - StateManager
- `roadmap/adapters/persistence/repositories/issue_repository.py` - DB-backed

**File layer (source of truth):**
- `roadmap/adapters/persistence/yaml_repositories.py` - YAMLIssueRepository

**Service layer (where sync happens):**
- `roadmap/core/services/issue_service.py` - IssueService
- `roadmap/infrastructure/issue_coordinator.py` - IssueCoordinator

**Current sync (to improve):**
- `roadmap/adapters/sync/sync_retrieval_orchestrator.py` - Gets baseline from git

---

## Files to Create

1. `roadmap/adapters/git/__init__.py` (new package)
2. `roadmap/adapters/git/sync_monitor.py` (main implementation)
3. `tests/unit/adapters/git/__init__.py` (new test package)
4. `tests/unit/adapters/git/test_sync_monitor.py` (unit tests)
5. `tests/integration/test_git_sync_full.py` (integration tests)

---

## Files to Modify

1. `roadmap/core/services/issue_service.py` - Add git monitor integration
2. `roadmap/infrastructure/issue_coordinator.py` - Maybe wire up git monitor
3. `roadmap/infrastructure/core.py` - Create and pass git monitor
4. `roadmap/adapters/sync/sync_retrieval_orchestrator.py` - Use DB baseline

---

## Estimated Timeline

- **Day 1:** Build GitSyncMonitor (4 hours)
- **Day 1-2:** Unit tests (4 hours)
- **Day 2:** Integrate with IssueService (4 hours)
- **Day 3:** Performance tests + fixes (4 hours)
- **Day 3-4:** Sync improvements + edge cases (8 hours)
- **Day 4:** Final validation + documentation (4 hours)

**Total:** ~1 week to full implementation

---

## Key Decisions to Make

1. **Auto-sync or manual?**
   - Auto: Every `list()` checks git (transparent, fast with memoization)
   - Manual: User calls `roadmap sync-from-git` (safe, explicit)
   - **Recommendation:** Auto with memoization (check git only once per command)

2. **Fallback behavior?**
   - Detached HEAD: Fall back to filesystem scan + warn user
   - Git command fails: Use cached database if available
   - Database corrupted: Fall back to files (always safe)

3. **Git hooks?**
   - Pre-commit: Could validate sync state
   - Post-commit: Could auto-sync database
   - **Recommendation:** Start without hooks, add later if needed

---

## Success Looks Like

```
Before:
$ time roadmap list
  1.2s

After:
$ time roadmap list
  0.08s

That's 15x faster. ✓
```

And in the code:
- ✓ No filesystem scanning (removed or unused)
- ✓ Git diff used for change detection
- ✓ Database cache always in sync
- ✓ Files remain source of truth
- ✓ All tests passing
- ✓ Performance benchmarks documented

---

## Questions Before Starting?

1. Should git sync be automatic or explicit?
2. How to handle git hook failures?
3. Should we version the sync state format?
4. How aggressive should caching be?

Ready to start? Pick Phase 1 and go! 🚀
