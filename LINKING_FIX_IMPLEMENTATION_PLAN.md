# Linking Fix Implementation Plan

**Goal:** Make sync reports accurate and prevent repeated pulls

**Architecture:**
- YAML files (`.roadmap/issues/*.md`) = source of truth with `remote_ids` field
- Database = fast query cache for linking lookups
- GitSyncMonitor = keeps DB cache in sync with YAML

---

## Phase 1: Auto-Linking on Pull/Push

### Task 1.1: Find Pull Handler
**File:** Locate where pulled issues are created locally
- Search for: `pull_issue()`, `create_from_remote()`, issue creation after sync
- Likely locations:
  - `roadmap/adapters/sync/sync_merge_orchestrator.py`
  - `roadmap/adapters/sync/sync_retrieval_orchestrator.py`
  - `roadmap/core/services/github_issue_client.py`

**Action:**
- [ ] Identify the exact function that creates/updates local Issue after pulling
- [ ] Add logging to see when this happens
- [ ] Verify Issue object has `remote_ids` field accessible

### Task 1.2: Add Auto-Linking to Pull Handler
**Implementation:**
```python
# After pulling issue #150 from GitHub, before saving:
if pulled_remote_issue:
    # Extract remote ID (e.g., "150" from GitHub issue)
    remote_id = pulled_remote_issue.get("id")  # or .number

    # Auto-link in local issue
    if not local_issue.remote_ids:
        local_issue.remote_ids = {}
    local_issue.remote_ids["github"] = remote_id

    # Save the updated issue (YAML will include remote_ids)
    issue_service.update(local_issue)
```

**Tests needed:**
- [ ] After pull, check that `remote_ids["github"]` is set
- [ ] Verify YAML file contains the linking data
- [ ] Test with multiple backends (github, gitlab, etc.)

### Task 1.3: Find Push Handler
**File:** Locate where local issues are pushed to remote
- Search for: `push_issue()`, `create_on_remote()`, after sync push
- Likely locations:
  - `roadmap/adapters/sync/sync_merge_orchestrator.py`
  - Backend implementation files

**Action:**
- [ ] Identify exact function
- [ ] Check if backend returns remote ID after push
- [ ] Verify we capture the returned ID

### Task 1.4: Add Auto-Linking to Push Handler
**Implementation:**
```python
# After pushing local issue to GitHub and getting back response:
if push_response and push_response.get("id"):
    remote_id = push_response.get("id")

    # Auto-link in local issue
    local_issue.remote_ids["github"] = remote_id

    # Save the updated issue
    issue_service.update(local_issue)

    # Also update database (see Phase 2)
    state_manager.link_issue_to_remote(
        local_issue_id=local_issue.id,
        backend="github",
        remote_id=remote_id
    )
```

**Tests needed:**
- [ ] After push, check that `remote_ids["github"]` is set
- [ ] Verify correct ID is captured
- [ ] Test error cases (push fails, no ID returned)

---

## Phase 2: Database Sync for Linking

### Task 2.1: Add Database Schema
**File:** `roadmap/adapters/persistence/database_manager.py` or migrations

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS issue_remote_links (
    id TEXT PRIMARY KEY,
    issue_uuid TEXT NOT NULL,
    backend_name TEXT NOT NULL,
    remote_id TEXT NOT NULL,
    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(issue_uuid, backend_name),
    FOREIGN KEY(issue_uuid) REFERENCES issues(id)
);

-- Index for fast lookups during sync
CREATE INDEX IF NOT EXISTS idx_remote_id
ON issue_remote_links(backend_name, remote_id);
```

**Action:**
- [ ] Create migration file for new table
- [ ] Add table creation to schema initialization
- [ ] Handle migration for existing installations

### Task 2.2: Add Repository for Remote Links
**File:** Create `roadmap/adapters/persistence/repositories/remote_link_repository.py`

**Methods:**
```python
class RemoteLinkRepository:
    def link_issue(self, issue_uuid: str, backend: str, remote_id: str) -> bool:
        """Link local issue to remote ID"""

    def unlink_issue(self, issue_uuid: str, backend: str) -> bool:
        """Remove link between local and remote"""

    def get_remote_id(self, issue_uuid: str, backend: str) -> str | None:
        """Get remote ID for a local issue"""

    def get_issue_uuid(self, backend: str, remote_id: str) -> str | None:
        """Get local UUID for a remote ID (reverse lookup)"""

    def get_all_links_for_issue(self, issue_uuid: str) -> dict[str, str]:
        """Get all backend links for an issue: {"github": "150", "gitlab": "42"}"""

    def get_all_links_for_backend(self, backend: str) -> dict[str, str]:
        """Get all issue→remote mappings for a backend"""

    def validate_link(self, issue_uuid: str, backend: str, remote_id: str) -> bool:
        """Check if link exists and is valid"""

    def bulk_import_from_yaml(self, issues: list[Issue]) -> int:
        """Import all remote_ids from YAML files into DB"""
```

**Action:**
- [ ] Create file with repository class
- [ ] Implement all methods with proper error handling
- [ ] Add unit tests for each method

### Task 2.3: Update StateManager to Use Remote Links
**File:** `roadmap/adapters/persistence/storage/state_manager.py`

**Changes:**
```python
class StateManager:
    def __init__(self, ...):
        # ... existing code ...
        self._remote_link_repo = RemoteLinkRepository(...)

    def sync_remote_links_from_yaml(self, issues: list[Issue]) -> int:
        """Load remote_ids from YAML and sync to database"""
        count = 0
        for issue in issues:
            if issue.remote_ids:
                for backend, remote_id in issue.remote_ids.items():
                    self._remote_link_repo.link_issue(
                        issue.id, backend, str(remote_id)
                    )
                    count += 1
        return count
```

**Action:**
- [ ] Add `_remote_link_repo` field
- [ ] Add `sync_remote_links_from_yaml()` method
- [ ] Call this during initialization to load existing links

### Task 2.4: Update GitSyncMonitor to Sync Remote Links
**File:** `roadmap/adapters/git/sync_monitor.py`

**Changes:**
```python
class GitSyncMonitor:
    def sync_to_database(self, changes: dict[str, str]) -> bool:
        """Sync detected changes to database cache."""
        # ... existing code ...

        # NEW: Sync remote_ids changes
        for changed_file in changes.keys():
            if self._is_issues_file(changed_file):
                # Load the changed issue
                issue = self._load_issue_from_file(changed_file)
                if issue and issue.remote_ids:
                    # Sync remote_ids to database
                    self.state_manager.sync_remote_links_from_yaml([issue])
```

**Action:**
- [ ] Add method to load issue from file
- [ ] Add remote_ids sync to database in `sync_to_database()`
- [ ] Handle deletions (remove links when file deleted)

### Task 2.5: Update SyncStateComparator to Use Database Links
**File:** `roadmap/core/services/sync_state_comparator.py`

**Changes:**
```python
class SyncStateComparator:
    def __init__(self, ..., remote_link_repo=None):
        # ... existing code ...
        self.remote_link_repo = remote_link_repo

    def _normalize_remote_keys(self, local: dict, remote: dict) -> tuple:
        """Use database for fast linking lookups"""
        if not self.remote_link_repo:
            # Fallback to old method
            return self._normalize_remote_keys_from_yaml(local, remote)

        backend_name = self.backend.get_backend_name()
        normalized_remote = {}

        # Build reverse mapping using database (faster than parsing YAML)
        for remote_key, remote_issue in remote.items():
            remote_key_str = str(remote_key)

            # Fast database lookup
            local_uuid = self.remote_link_repo.get_issue_uuid(
                backend_name, remote_key_str
            )

            if local_uuid:
                normalized_remote[local_uuid] = remote_issue
            else:
                # New remote issue
                prefixed_key = f"_remote_{remote_key}"
                normalized_remote[prefixed_key] = remote_issue

        return local, normalized_remote
```

**Action:**
- [ ] Add `remote_link_repo` parameter to constructor
- [ ] Rewrite `_normalize_remote_keys()` to use DB lookups
- [ ] Keep fallback for when DB unavailable
- [ ] Add logging to show when DB is used vs fallback

---

## Phase 3: One-Time Validation and Fixing

### Task 3.1: Create Validation Command
**File:** Create `roadmap/adapters/cli/sync/validate_links.py`

**Command:**
```
roadmap sync --validate-links
```

**Implementation:**
```python
def validate_links() -> LinkValidationReport:
    """
    Scan all YAML files and validate remote_ids:
    1. Check that all issues with remote_ids exist on remote
    2. Check that all remote issues have corresponding local issues
    3. Report any mismatches
    4. Option to auto-fix
    """
    report = LinkValidationReport()

    # Load all local issues
    local_issues = core.issues.list_all_including_archived()

    # For each local issue with remote_ids
    for issue in local_issues:
        if not issue.remote_ids:
            continue

        for backend, remote_id in issue.remote_ids.items():
            # Verify remote still exists
            remote = backend_service.get_issue(remote_id)
            if not remote:
                report.add_error(
                    f"Local {issue.id} linked to {backend}#{remote_id} but remote doesn't exist"
                )
                continue

            # Verify database link exists
            db_uuid = state_manager.remote_link_repo.get_issue_uuid(backend, remote_id)
            if db_uuid != issue.id:
                report.add_warning(
                    f"Database link mismatch for {backend}#{remote_id}"
                )
                # Fix it
                if auto_fix:
                    state_manager.remote_link_repo.link_issue(
                        issue.id, backend, remote_id
                    )

    # Report unlinked remotes
    remote_issues = backend_service.get_all_issues()
    for remote_id, remote_issue in remote_issues.items():
        local_uuid = state_manager.remote_link_repo.get_issue_uuid(
            backend, remote_id
        )
        if not local_uuid:
            report.add_warning(
                f"Remote {backend}#{remote_id} '{remote_issue.title}' not linked locally"
            )

    return report
```

**Output:**
```
🔍 Validating Remote Links

Local Issues:
  ✓ 123 issues with valid links
  ⚠ 5 issues with database mismatches (fixed)
  ✗ 2 issues linked to non-existent remotes
  → 29 issues without any remote links

Remote Issues:
  ✓ 120 issues have local counterparts
  ⚠ 10 orphaned remote issues (not linked locally)

Summary:
  Total issues validated: 152 local, 100 remote
  Mismatches found: 17
  Auto-fixes applied: 5
  Requires attention: 12
```

**Action:**
- [ ] Create CLI command file
- [ ] Implement validation logic
- [ ] Add `--auto-fix` option
- [ ] Add `--report-only` option
- [ ] Generate detailed output

### Task 3.2: Run Validation on Next Sync
**File:** `roadmap/adapters/sync/sync_merge_orchestrator.py`

**Implementation:**
```python
def sync_all_issues(self, dry_run=False):
    # NEW: Validate links before sync
    if not hasattr(self, '_links_validated'):
        report = validate_links(auto_fix=True)
        if report.has_errors:
            logger.warning("Link validation found issues", report=report)
        self._links_validated = True

    # Continue with normal sync...
```

**Action:**
- [ ] Add validation call to sync workflow
- [ ] Only run once per session
- [ ] Log any issues found

---

## Implementation Sequence

### Day 1: Auto-Linking (Phase 1)
1. [ ] Task 1.1: Find pull handler
2. [ ] Task 1.2: Add auto-linking to pull
3. [ ] Task 1.3: Find push handler
4. [ ] Task 1.4: Add auto-linking to push
5. [ ] Test: Run sync and verify `remote_ids` set in YAML

### Day 2: Database Schema (Phase 2)
1. [ ] Task 2.1: Create schema migration
2. [ ] Task 2.2: Create RemoteLinkRepository
3. [ ] Task 2.3: Update StateManager
4. [ ] Test: Verify links stored in database

### Day 3: GitSync Integration + Comparator (Phase 2)
1. [ ] Task 2.4: Update GitSyncMonitor
2. [ ] Task 2.5: Update SyncStateComparator
3. [ ] Test: Verify DB lookups work during sync

### Day 4: Validation (Phase 3)
1. [ ] Task 3.1: Create validation command
2. [ ] Task 3.2: Integrate with sync
3. [ ] Run one-time validation: `roadmap sync --validate-links`
4. [ ] Verify sync report now shows correct counts

---

## Testing Strategy

### Unit Tests
- [ ] RemoteLinkRepository CRUD operations
- [ ] SyncStateComparator with database lookups
- [ ] Auto-linking logic on pull/push
- [ ] GitSyncMonitor remote_ids syncing

### Integration Tests
- [ ] Full sync workflow with auto-linking
- [ ] Validation command with various link states
- [ ] Multi-backend linking (github + gitlab)

### End-to-End
- [ ] Run sync with `--dry-run`
- [ ] Verify sync report shows correct numbers
- [ ] Run with `--apply`
- [ ] Verify no duplicate pulls on next sync

---

## Success Criteria

- ✓ Sync report shows ~125 up-to-date (not 2)
- ✓ No duplicate pulls in repeated syncs
- ✓ `remote_ids` correctly set in YAML after pull/push
- ✓ Database has all links from YAML
- ✓ Validation command runs successfully
- ✓ All 6,455 tests still pass
