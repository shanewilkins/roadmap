# Architecture Analysis: Database vs File-Based Operations

## Executive Summary

Your instinct is correct: **the system is a "hodgepodge" rather than a unified architecture**. There are **two completely separate persistence layers** that don't talk to each other:

1. **YAML File Layer** (currently active)
   - Issues stored in `.roadmap/issues/` and `.roadmap/archive/issues/`
   - ALL user-facing operations use this layer
   - `list()`, `list_all_including_archived()`, sync operations all enumerate files

2. **SQLite Database Layer** (exists but unused)
   - Full schema with projects, milestones, issues, comments, sync metadata
   - Thread-safe connection pooling, transactions, migrations
   - BUT: **No read operations from core.py go through the database**
   - Only written to by `StateManager` and `SyncOrchestrator` (which are NOT called by main CLI)

---

## Current Data Flow

### How Issues Are Read (Actual)

```
User Command
    ↓
IssueCoordinator.list()
    ↓
IssueOperations.list_issues()
    ↓
IssueService.list_issues()
    ↓
YAMLIssueRepository.list()
    ↓
File Enumeration: scan .roadmap/issues/ and .roadmap/archive/issues/
    ↓
Load YAML frontmatter from each file
    ↓
Return Issue objects
```

**The database is never consulted.**

### How Issues Are Written (Actual)

```
User Command
    ↓
IssueCoordinator.create()
    ↓
IssueOperations.create_issue()
    ↓
IssueService.create_issue()
    ↓
YAMLIssueRepository.save()
    ↓
Write to file: .roadmap/issues/{id}.md or .roadmap/milestone/{name}/{id}.md
    ↓
Save YAML frontmatter
```

**The database is never updated.**

### How Sync Works (Current)

```
sync_retrieval_orchestrator.py
    ↓
core.issues.list_all_including_archived()  ← YOUR FIX
    ↓
YAMLIssueRepository.list_all_including_archived()
    ↓
File enumeration: .roadmap/issues/ + .roadmap/archive/issues/
    ↓
Three-way merge: (baseline, local, remote)
    ↓
Apply changes → sync_state_comparator.py
```

**The database is never accessed.**

### How Archive Works (Current)

```
archive command
    ↓
Move file from .roadmap/issues/{id}.md → .roadmap/archive/issues/{id}.md
    ↓
Mark `archived: true` in YAML frontmatter
```

**Archive status is tracked by FILE LOCATION, not in database.**

---

## The Database Layer (Unused)

There IS a complete database layer that exists but is **never called**:

### Database Schema (Implemented but Unused)

```sql
CREATE TABLE issues (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    milestone_id TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'medium',
    assignee TEXT,
    ... other fields ...
    FOREIGN KEY (project_id) REFERENCES projects (id),
    FOREIGN KEY (milestone_id) REFERENCES milestones (id)
);

CREATE TABLE sync_base_state (
    issue_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    assignee TEXT,
    milestone TEXT,
    ... baseline snapshot data ...
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sync_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE file_sync_state (
    file_path TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Database Infrastructure (Complete but Unused)

- **DatabaseManager**: SQLite connection pooling, thread-local connections, WAL mode, transactions
- **StateManager**: Orchestrates all database operations
- **Repository Classes**:
  - `roadmap/adapters/persistence/repositories/issue_repository.py` (database-backed)
  - `roadmap/adapters/persistence/repositories/milestone_repository.py` (database-backed)
  - `roadmap/adapters/persistence/repositories/project_repository.py` (database-backed)
  - `roadmap/adapters/persistence/repositories/sync_state_repository.py` (database-backed)

### The File Synchronizer (One-Way Only)

```python
# roadmap/adapters/persistence/file_synchronizer.py
class FileSynchronizer:
    """Synchronizes file changes TO database"""

    def sync_file_to_database(self, file_path):
        """Read file, write to DB"""
        ...

    # BUT: No sync_database_to_file() method!
```

**This is one-way**: files → database. Never database → files.

---

## The Incompatibility Problems

### Problem 1: Archive Status

**Files track it:**
- File location: `.roadmap/issues/` vs `.roadmap/archive/issues/`

**Database doesn't track it:**
- No `archived` column in issues table
- `archived: true` stored in YAML frontmatter
- Database doesn't know archived status

**Result:**
```python
# List commands work correctly (enumerate files)
issues = core.issues.list()  # ✓ Returns only active issues

# But if someone queries the DB directly:
# SELECT * FROM issues  ← Returns ALL issues, including "archived" ones (wrong!)
```

### Problem 2: Data Consistency

**What happens when you create an issue?**

```
1. File: ✓ Written to .roadmap/issues/{id}.md
2. Database: ✗ NOT written to issues table
3. Sync metadata: ✗ NOT created in sync_base_state

Result: List commands work. Database is out of sync.
```

**What happens if someone explicitly uses the database layer?**

```
state_manager = StateManager()
state_manager.issues.create(...)  # Creates in DB only
state_manager.issues.list()  # Returns DB issues

But: core.issues.list()  # Still enumerates files, misses the DB-created issue!
```

### Problem 3: Sync Operations

**Current sync operations:**
- Read from files via `core.issues.list_all_including_archived()`
- Compare baseline (from file git history or YAML metadata)
- Write results back to files

**What's NOT happening:**
- Never touches `sync_base_state` table
- Never updates `sync_metadata`
- Three-way merge baseline comes from files, not database `sync_base_state`

---

## The "Hodgepodge" Structure

```
┌─────────────────────────────────────┐
│  User CLI / Application Layer       │
└────────────────┬────────────────────┘
                 │
         ┌───────▼────────┐
         │ IssueCoordinator│
         │ IssueOperations │
         │ IssueService    │
         └───────┬────────┘
                 │
         ┌───────▼──────────────────────┐
         │ TWO COMPETING LAYERS:        │
         │                              │
         │ ├─ YAMLIssueRepository       │ ← ACTUALLY USED
         │ │  (.roadmap/issues/)        │
         │ │  List from files ✓         │
         │ │  List includes archived ✓  │
         │ │  Archive by moving files ✓ │
         │ │                            │
         │ └─ IssueRepository (DB)      │ ← NEVER USED
         │    (SQLite database)         │
         │    List from DB ✗            │
         │    Archive status ✗          │
         │    Sync metadata ✗           │
         └────────────────────────────────┘
```

---

## What Should Happen Instead

### Option A: File-Based as Source of Truth (Minimal Change)

**Decision:** Use YAML files as the persistent store. Database is cache/secondary.

```python
# Remove IssueRepository (DB version)
# Keep YAMLIssueRepository only

# For sync operations:
class SyncOrchestrator:
    def get_baseline(self):
        # Read from git history of file (current approach) ✓
        # OR: Build from file state (current approach) ✓
        pass

    def apply_changes(self):
        # Write to files (current approach) ✓
        pass

    # Optional: sync database FROM files as read-through cache
    def sync_to_cache_database(self):
        """One-way sync: files → database (optional)"""
        for issue in self.files.list_all_including_archived():
            database.issues.upsert(issue)
```

**Pros:**
- Minimal changes (already working)
- Files are source of truth
- No consistency issues

**Cons:**
- Database becomes dead code to remove
- Tests that use StateManager become irrelevant
- Can't leverage DB advantages (complex queries, transactions)

### Option B: Database as Source of Truth (Major Refactor)

**Decision:** Use SQLite database as source of truth. Files are export/representation.

```python
# Remove YAMLIssueRepository
# Use IssueRepository (database) everywhere

# Issue creation:
class IssueCoordinator:
    def create(self, ...):
        # Write to database
        issue = self.service.create_issue(params)

        # Also write to file (secondary)
        self.yaml_exporter.save_to_file(issue)

        return issue

# Issue listing:
class IssueCoordinator:
    def list(self):
        # Read from database
        return self.service.list_issues()
        # Files are just for backup/git history

# Archive:
class IssueCoordinator:
    def archive(self, issue_id):
        # Update DB: archived = True
        self.service.update(issue_id, {'archived': True})

        # Also move file for git history
        os.move('issues/{id}.md', 'archive/{id}.md')

# Sync operations:
class SyncOrchestrator:
    def get_baseline(self):
        # Load from database sync_base_state table
        return self.db.sync_base_state.get_by_issue_id(issue_id)

    def apply_changes(self):
        # Write to database
        self.db.issues.update(...)

        # Also update file for git history
        self.yaml_exporter.save_to_file(...)
```

**Pros:**
- Single source of truth
- Consistent archive tracking
- Can use database transactions for atomicity
- Sync metadata properly stored
- Complex queries become possible

**Cons:**
- Major refactoring required
- Need to handle file export consistently
- More complexity (dual writes)
- Git history still in files (split state)

### Option C: Hybrid - Explicit Layer Separation (Best Long-Term)

**Decision:** Keep both, but with explicit separation and synchronization.

```python
class IssueRepository(Protocol):
    """File-based repository (source of truth)"""
    def list(self) -> list[Issue]: ...
    def list_all_including_archived(self) -> list[Issue]: ...
    def save(self, issue: Issue) -> None: ...
    def delete(self, issue_id: str) -> bool: ...

class IssueCacheRepository(Protocol):
    """Database repository (read-through cache)"""
    def list(self) -> list[Issue]: ...
    def save(self, issue: Issue) -> None: ...

class IssueService:
    def __init__(self, file_repo: IssueRepository, cache_repo: IssueCacheRepository):
        self.file_repo = file_repo
        self.cache_repo = cache_repo

    def list_issues(self, ...):
        # Try cache first
        if cache_result := self.cache_repo.list(...):
            return cache_result

        # Fall back to files, populate cache
        issues = self.file_repo.list(...)
        for issue in issues:
            self.cache_repo.save(issue)

        return issues

    def create_issue(self, ...):
        # Write to files (source of truth)
        issue = self.file_repo.save(issue_data)

        # Populate cache
        self.cache_repo.save(issue)

        return issue

    def sync_file_to_cache(self):
        """Keep cache in sync"""
        for issue in self.file_repo.list_all_including_archived():
            self.cache_repo.save(issue)
```

**Pros:**
- Both layers work
- Files = source of truth (safe)
- Database = performance cache (optional)
- Gradual transition possible
- Can test DB layer independently

**Cons:**
- More code to maintain
- Cache invalidation complexity
- Still have data consistency issues

---

## Recommendations

### Immediate (Fix Consistency)

1. ✅ **Remove dead database code** (StateManager, DatabaseManager usage from CLI)
   - It's not connected to main code paths
   - Keep it for future use but remove from active codebase

2. ✅ **Document the architecture clearly**
   - This document

3. ✅ **Fix the "Pylance errors"** (done - added methods to expose files layer)
   - Your fix is correct for current design

### Medium-Term (Decide Architecture)

1. **Choose Option A, B, or C** based on project needs:
   - A: Keep files-only, remove database code
   - B: Migrate to database-first, export to files
   - C: Maintain both with explicit sync

2. **If Option A (Files-Only):**
   ```bash
   # Delete these files
   rm -rf roadmap/adapters/persistence/database_manager.py
   rm -rf roadmap/adapters/persistence/storage/
   rm -rf roadmap/adapters/persistence/repositories/
   ```

3. **If Option B or C:**
   - Add database read operations to main code paths
   - Create sync mechanisms between layers
   - Add archive tracking to database schema

### For Sync Specifically

**Current state is actually fine for sync:**
- Uses files as source (safe)
- Three-way merge from files/git history (works)
- All sync operations read/write files (consistent)

**To make it better:**
- Store `sync_base_state` in database instead of git history
- Store sync metadata in database instead of YAML frontmatter
- This would be a cleaner baseline system

---

## Your Three Questions Answered

### 1. How does database integrate with sync logic?

**Currently:** It doesn't. Sync is entirely file-based. The `sync_base_state` table exists but is never used. Baseline comes from git history or current file state.

### 2. Are all archived issues in the DB?

**Currently:** No. Archive status is tracked by file location only. Database would contain all issues with no way to know which are archived.

### 3. How are changes propagated back to DB after sync operations?

**Currently:** They're not. After resolving conflicts in sync, the resolved issues are written to files only. The database is never touched.

---

## Next Steps

1. **Decide** if database should exist at all
2. **If keeping it:** Choose integration model (A, B, or C)
3. **If removing it:** Clean up ~2000 lines of unused code
4. **For sync:** Consider whether to store baseline in database for cleaner architecture

Would you like me to help implement any of these options?
