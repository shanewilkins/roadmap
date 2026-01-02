# Phase 6: File Persistence Architecture

## Overview

File persistence in the sync system follows the **Repository Pattern**. The sync orchestrator doesn't directly write files - instead, it returns sync results and relies on the caller to persist changes.

## Architecture

### Before (Wrong - Phase 1-4)
```
sync() → modifies issues → persists to disk → returns report
```

### After (Correct - Phase 6+)
```
sync() → modifies issues in memory → returns report
caller → uses report → persists to disk via repository
```

## The Flow

### For Local Updates (Push)

```
Local Issue (in memory)
    ↓
sync.push_issue()
    ↓
backend.push_issue() (no-op or API call)
    ↓
Issue object remains in memory
    ↓
Issue Service → Repository → File Saved
(automatic when issue is modified)
```

### For Remote Updates (Pull)

```
Remote Issue (GitHub API)
    ↓
backend.pull_issue()
    ↓
Issue data returned to orchestrator
    ↓
Create/Update Issue via IssueService
    ↓
IssueRepository saves to disk
```

## Responsibility Model

| Component | Responsibility |
|-----------|-----------------|
| Sync Orchestrator | Detect changes, resolve conflicts, coordinate flow |
| Backend | Fetch/push via API/git, no file operations |
| IssueRepository | Persist issues to disk (.roadmap/issues/*.md) |
| CLI | Call sync, handle user display |
| User | `git add`, `git commit`, `git push` |

## Current Implementation Status

✅ **Phase 6 Complete**

The system now correctly separates concerns:

1. **Sync** - Orchestrates remote/local comparison and conflict resolution
2. **Repository** - Handles file persistence automatically
3. **User** - Handles git operations

The repository pattern automatically saves files when issues are created or updated, so sync doesn't need explicit persistence code.

## Future Enhancements

### Explicit Persistence API

If needed, we could add an explicit method:

```python
class SyncPersistenceService:
    def persist_sync_results(self, report: SyncReport) -> None:
        """Persist sync results to disk using repository pattern."""
        # This would be explicit and optional
        # Currently implicit through IssueService
```

### Transaction Support

For atomic sync operations:

```python
def sync_all_issues(self, ...) -> SyncReport:
    with transaction():
        # All changes persist together
        # If any step fails, roll back all
        pass
```

### Conflict State Tracking

Track conflicting issues separately:

```python
class ConflictTracker:
    def track_conflict(self, issue_id: str, conflict: SyncConflict) -> None:
        """Record conflicting issue for later review."""
        # Save to .roadmap/.conflicts/
```

## Testing

The implicit persistence is tested through:

1. **Integration Tests** - Create issues → sync → verify files exist
2. **End-to-End Tests** - Full workflow including file verification
3. **Repository Tests** - Verify files are saved correctly

## Documentation

- [Sync Architecture](SYNC_ARCHITECTURE.md) - Full sync system design
- [User Guide: Sync Workflow](../user_guide/GITHUB_SYNC_SETUP.md) - How users interact
- [Workflows Guide](../user_guide/WORKFLOWS.md) - Team patterns
