# Git-Diff Based Database Sync Architecture

## The Problem You Identified

Filesystem scans are expensive. Every command does this:

```
User runs: roadmap list
    ↓
Core reads files: enumerate .roadmap/issues/
    ↓
Open and parse YAML frontmatter for each file
    ↓
Build Issue objects
    ↓
Return to user
```

**Cost:** O(n) where n = number of issues.

For 1000 issues with git history, this is slow.

## The Solution: Database as Cheap Query Layer

**Key insight:** Files only change when git changes them. So we can:

1. **Keep database as the primary query cache**
   - `list()` queries database (fast)
   - Only update database when files change

2. **Know when files change via git diff** (cheap)
   - Don't scan filesystem, just check: `git diff --name-only`
   - Only reload changed files into database

3. **Files remain source of truth**
   - For git history (revert, blame, cherry-pick)
   - For reproducibility (anyone can clone and see full history)

## Data Flow (Proposed)

### Normal Operation

```
User: roadmap list
    ↓
IssueCoordinator.list()
    ↓
IssueService.list_issues()
    ↓
Check if DB is in sync with git
    ├─ git diff --name-only  (cheap, milliseconds)
    ├─ If no changes: return cached from DB (fast)
    └─ If changes detected:
        ├─ For each changed file: load from disk
        ├─ Update database
        └─ Return from database
```

### On File Change

```
Developer: git commit .roadmap/issues/{id}.md
    ↓
Pre-commit hook or git hook detects change
    ↓
Triggers: sync_database_from_git()
    ├─ Get list of changed issue files: git diff
    ├─ For each: read file, update database
    └─ Update sync state: last_git_hash
```

### On Sync Operation

```
User: roadmap sync
    ↓
SyncOrchestrator starts
    ├─ Get baseline: from database sync_base_state (fast)
    ├─ Get local issues: from database (cached, fast)
    ├─ Get remote issues: from API (expected cost)
    ├─ Three-way merge
    └─ Apply changes:
        ├─ Write to files: .roadmap/issues/{id}.md
        └─ Update database (in transaction)
```

## Implementation Architecture

### Layer 1: Git Sync Monitor

```python
# roadmap/adapters/git/sync_monitor.py

class GitSyncMonitor:
    """Detects changes between git and database."""

    def __init__(self, repo_path: Path, db_connection):
        self.repo = Repo(repo_path)
        self.db = db_connection
        self.last_synced_commit = self._get_last_synced_commit()

    def detect_changes(self) -> dict[str, str]:
        """Detect which .roadmap/issues files changed since last sync.

        Returns:
            {
                'modified': ['issue1.md', 'issue2.md'],
                'added': ['issue3.md'],
                'deleted': ['issue4.md']
            }
        """
        # Fast: just get list of changed files
        current_commit = self.repo.head.commit.hexsha

        if not self.last_synced_commit:
            # First sync: everything is "new"
            return self._get_all_roadmap_files()

        # Get diff between last_synced_commit and current
        diff = self.repo.commit(self.last_synced_commit).diff(
            self.repo.head.commit
        )

        changes = {'modified': [], 'added': [], 'deleted': []}
        for item in diff:
            if not item.a_path.startswith('.roadmap/issues/'):
                continue

            if item.change_type == 'M':
                changes['modified'].append(item.a_path)
            elif item.change_type == 'A':
                changes['added'].append(item.b_path)
            elif item.change_type == 'D':
                changes['deleted'].append(item.a_path)

        return changes

    def sync_to_database(self, changes: dict[str, str]):
        """Apply git changes to database."""
        # Load modified/added files
        for file_path in changes['modified'] + changes['added']:
            issue = self._load_issue_from_file(file_path)
            self.db.issues.upsert(issue)

        # Delete removed issues
        for file_path in changes['deleted']:
            issue_id = self._extract_id_from_path(file_path)
            self.db.issues.delete(issue_id)

        # Update sync state
        self._save_last_synced_commit()

    def _get_last_synced_commit(self) -> str | None:
        """Read from database sync_metadata table."""
        result = self.db.execute(
            "SELECT value FROM sync_metadata WHERE key = 'last_synced_commit'"
        ).fetchone()
        return result[0] if result else None

    def _save_last_synced_commit(self):
        """Write to database sync_metadata table."""
        current = self.repo.head.commit.hexsha
        self.db.execute(
            "INSERT OR REPLACE INTO sync_metadata (key, value) VALUES ('last_synced_commit', ?)",
            (current,)
        )
        self.db.commit()
```

### Layer 2: Service-Level Cache Checking

```python
# roadmap/core/services/issue_service.py (modified)

class IssueService:
    def __init__(self, file_repo: IssueRepository, cache_repo: IssueRepository, git_monitor: GitSyncMonitor):
        self.file_repo = file_repo      # For source-of-truth access
        self.cache_repo = cache_repo    # For fast queries
        self.git_monitor = git_monitor  # For detecting changes

    def list_issues(self, **filters):
        """List issues, using database cache when possible."""

        # Check if database is in sync with git (cheap operation)
        changes = self.git_monitor.detect_changes()

        if changes:
            # Sync database from git
            self.git_monitor.sync_to_database(changes)

        # Now database is guaranteed to be in sync
        # Return from cache (fast)
        return self.cache_repo.list(**filters)

    def create_issue(self, params: IssueCreateServiceParams):
        """Create issue in both file and database."""

        # Write to file (source of truth)
        issue = self.file_repo.create(params)

        # Update database cache
        self.cache_repo.save(issue)

        # Update sync state (no changes to sync since this is new)
        return issue

    def list_all_including_archived(self):
        """List all issues, including archived (for sync operations)."""

        # Check git for changes
        changes = self.git_monitor.detect_changes()
        if changes:
            self.git_monitor.sync_to_database(changes)

        # Return from database (which now includes archived)
        return self.cache_repo.list_all_including_archived()
```

### Layer 3: Coordinator-Level Integration

```python
# roadmap/infrastructure/issue_coordinator.py (modified)

class IssueCoordinator:
    def __init__(self, issue_ops: IssueOperations, git_monitor: GitSyncMonitor, core=None):
        self._ops = issue_ops
        self._git_monitor = git_monitor
        self._core = core

    def list(self, **filters):
        """List active issues with automatic database sync."""
        # Service handles git sync internally
        return self._ops.list_issues(**filters)
```

### Layer 4: Sync Operations

```python
# roadmap/adapters/sync/sync_retrieval_orchestrator.py (modified)

class SyncRetrievalOrchestrator(SyncMergeOrchestrator):
    def get_baseline(self) -> dict[str, SyncIssue] | None:
        """Get baseline from database sync_base_state table.

        This is much cleaner than parsing git history!
        """
        try:
            # Database has the exact baseline snapshot from last sync
            baseline_data = self.state_manager.get_sync_baseline()

            if not baseline_data:
                # No previous sync
                return None

            return {
                issue_id: SyncIssue(
                    id=issue_id,
                    status=data['status'],
                    title=data.get('title'),
                    # ... other fields
                )
                for issue_id, data in baseline_data.items()
            }
        except Exception as e:
            logger.error("Failed to load baseline", error=str(e))
            return None

    def apply_changes(self, changes: dict[str, Change]):
        """Apply sync changes: files + database."""
        for issue_id, change in changes.items():
            if change.action == 'update':
                # Write to file
                self._write_to_file(issue_id, change.resolved_state)

                # Update database cache
                self.core.issues._ops.issue_service.cache_repo.save(
                    change.resolved_state
                )

                # Update sync baseline for next sync
                self.state_manager.update_sync_baseline(issue_id, change.resolved_state)
```

## Benefits

### Performance
- **Before:** Every command scans ~1000 files, parses YAML
- **After:** Every command does git diff (50ms) + database query (5ms)
- **Result:** 10-20x faster for list operations

### Consistency
- Database is guaranteed in sync with files via git
- Three-way merge baseline stored in database (not git history)
- Archive status tracked in database

### Simplicity
- No filesystem scanning code
- Git already tracks what changed (don't reinvent)
- Database schema has purpose (caching, baseline)

### Reproducibility
- Files in git are still source of truth
- Can always rebuild database from files: `git checkout {ref} && sync_from_git`
- Git history shows exact changes to each issue

## Implementation Sequence

### Phase 1: Git Sync Monitor (1-2 days)
- [ ] Build `GitSyncMonitor` class
- [ ] Add git diff detection
- [ ] Write tests for change detection
- [ ] Handle edge cases (initial sync, rebases, etc.)

### Phase 2: Service Integration (1-2 days)
- [ ] Update `IssueService` to check git before queries
- [ ] Wire `GitSyncMonitor` into initialization
- [ ] Update `list_issues()` to sync on demand
- [ ] Update `create_issue()` to update both file and DB

### Phase 3: Sync Improvements (1 day)
- [ ] Move baseline to database `sync_base_state`
- [ ] Update `SyncRetrievalOrchestrator` to use DB baseline
- [ ] Simplify baseline retrieval (no more git history parsing)

### Phase 4: Testing & Validation (1-2 days)
- [ ] Test git change detection with various scenarios
- [ ] Benchmark performance improvements
- [ ] Test sync operations with DB baseline
- [ ] Integration tests

## Migration Path

**Can do incrementally:**

1. Add git monitor (non-breaking)
2. Keep file scanning as fallback
3. Gradually migrate commands to use git monitor
4. Eventually remove file scanning

```python
# Interim: both methods available
class IssueService:
    def list_issues_fast(self):  # New: uses git monitor
        ...

    def list_issues(self):  # Backward compat: falls back if needed
        try:
            return self.list_issues_fast()
        except:
            return self.file_repo.list()  # Fallback
```

## Testing Strategy

### Unit Tests

```python
# tests/unit/adapters/git/test_sync_monitor.py

def test_detect_changes_identifies_modified_files(repo):
    """git diff correctly identifies modified issue files"""

def test_detect_changes_identifies_new_files(repo):
    """git diff correctly identifies new issue files"""

def test_detect_changes_ignores_non_issue_files(repo):
    """git diff ignores non-.roadmap/issues/ changes"""

def test_sync_to_database_updates_modified_issues(git_monitor, db):
    """Modified files are updated in database"""

def test_sync_to_database_adds_new_issues(git_monitor, db):
    """New files are added to database"""

def test_sync_to_database_deletes_removed_issues(git_monitor, db):
    """Deleted files are removed from database"""
```

### Integration Tests

```python
# tests/integration/test_git_sync_performance.py

def test_list_performance_with_git_sync(large_repo):
    """Listing 1000 issues with git sync is faster than filesystem scan"""

    import time

    # Time filesystem scan (old way)
    start = time.time()
    yaml_repo.list_all_including_archived()
    fs_time = time.time() - start

    # Time git-based approach (new way)
    start = time.time()
    service.list_issues()  # Uses git monitor
    git_time = time.time() - start

    # Should be significantly faster
    assert git_time < fs_time * 0.3  # At least 3x faster
```

## Questions to Consider

1. **Should git sync be automatic or explicit?**
   - Automatic: every list() call checks git (seamless)
   - Explicit: user must call `roadmap sync-from-git` (safe)
   - **Recommendation:** Automatic, with fast path (memoization)

2. **What about detached HEAD or rebases?**
   - Need to handle: `git diff` fails in detached HEAD
   - Fallback to full filesystem scan in these cases
   - Log a warning to user

3. **Should sync state tracking be in database or git?**
   - Database: cleaner, faster, easier to test
   - Git: Reproducible, part of commit history
   - **Recommendation:** Database (sync state is runtime, not source)

4. **What about file locks during database updates?**
   - File sync and DB update must be atomic
   - Use git hooks to prevent concurrent changes
   - Use database transactions for consistency

## Expected Code Changes

### New Files
- `roadmap/adapters/git/sync_monitor.py` (~200 LOC)
- `tests/unit/adapters/git/test_sync_monitor.py` (~300 LOC)
- `tests/integration/test_git_sync_performance.py` (~200 LOC)

### Modified Files
- `roadmap/core/services/issue_service.py` (+30 lines)
- `roadmap/infrastructure/issue_coordinator.py` (+10 lines)
- `roadmap/adapters/sync/sync_retrieval_orchestrator.py` (+20 lines)
- `roadmap/infrastructure/core.py` (+5 lines for git monitor init)

### Deletable Code
- Filesystem scanning logic (can be removed after migration)
- ~500 lines of file enumeration code

## Timeline

- **Week 1:** Git monitor + service integration
- **Week 2:** Sync improvements + testing
- **Week 3:** Performance validation + cleanup

Total: ~1-2 weeks for full implementation

---

This approach gives you:
✓ Database for performance (caching)
✓ Files for reproducibility (source of truth)
✓ Git for change detection (cheap)
✓ No filesystem scanning (fast)
✓ Cleaner sync baseline (database)

Want to start building this?
