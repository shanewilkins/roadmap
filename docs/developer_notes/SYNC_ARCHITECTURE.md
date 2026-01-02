# Sync System Architecture

## Overview

The sync system provides two-way synchronization between local roadmap files and remote sources (GitHub API, Git repos, etc.). It's designed to be backend-agnostic, allowing any sync target without modifying the core sync logic.

## Architecture Principles

### 1. Backend Agnosticism
The core sync logic doesn't know or care about git, GitHub, or any specific backend. All backend-specific code lives in backend implementations:

- **GitHub Logic** → `github_sync_backend.py`
- **Git Logic** → `vanilla_git_sync_backend.py`
- **Core Sync Logic** → `generic_sync_orchestrator.py`

### 2. API-Based Sync
Sync interacts with **remote data sources** (GitHub API), not git:

```
Local Issues (files)  ←→  GitHub API  ←→  GitHub Issues
                           (backend)
```

The user handles git operations separately:

```
Local Files  →  git add  →  git commit  →  git push  →  Git Remote
```

### 3. User Responsibility
The sync command is responsible only for:
- Fetching remote issues via API
- Comparing local vs remote
- Resolving conflicts
- Creating/updating local `.roadmap/issues/*.md` files

Users are responsible for:
- `git add .roadmap/`
- `git commit -m "..."`
- `git push`

### 4. No File Persistence in Orchestrator
The orchestrator **does not** save files to disk. That's the user's responsibility.

**Before (Wrong):**
```
sync() → modifies files → persists to disk → commits to git
```

**After (Correct):**
```
sync() → modifies files → user persists to disk (git add/commit/push)
```

## System Components

### SyncBackendInterface (Protocol)
Defines the contract all backends must implement:

```python
class SyncBackendInterface(Protocol):
    def authenticate(self) -> bool                          # Verify connection
    def get_issues(self) -> dict[str, Any]                 # Fetch remote issues
    def push_issue(self, local_issue: Issue) -> bool       # Push 1 issue
    def push_issues(self, local_issues: list[Issue]) -> SyncReport  # Push N issues
    def pull_issues(self) -> SyncReport                    # Pull all issues
    def pull_issue(self, issue_id: str) -> bool            # Pull 1 issue
    def get_conflict_resolution_options(...) -> list[str]  # Conflict options
    def resolve_conflict(...) -> bool                       # Resolve conflict
```

### Backends

#### GitHubSyncBackend
Implements sync with GitHub API:
- `authenticate()`: Validates GitHub token
- `get_issues()`: Calls GitHub API to fetch issues
- `push_issue()`: Creates/updates issue via API
- `pull_issue()`: Fetches issue from API

**No git operations** - all interaction is via GitHub API.

#### VanillaGitSyncBackend (Self-Hosting)
For self-hosted deployments (no remote database):
- All methods are no-ops (return empty/True)
- Users handle git operations themselves
- Exists for interface compatibility

### GenericSyncOrchestrator
Orchestrates sync using any backend:

1. **Authenticate** with backend
2. **Get issues** from both local and remote
3. **Compare** local vs remote using `SyncStateComparator`
4. **Detect**:
   - Conflicts (both sides changed)
   - Updates (local changed, remote unchanged)
   - Pulls (remote changed, local unchanged)
   - Up-to-date (no changes)
5. **Resolve** conflicts using `SyncConflictResolver` (three-way merge)
6. **Apply changes** to local files (if not dry-run)

### SyncStateComparator
Detects changes:
- Compares local issues with remote data
- Identifies conflicts, updates, pulls, up-to-date status
- Uses timestamps and field comparison

### SyncConflictResolver
Resolves conflicts using three-way merge:
- Compares base version (from prior sync state)
- Compares local vs remote changes
- Auto-merges non-conflicting changes
- Flags critical field conflicts for review

## Data Flow

### Sync Operation (dry-run = False)

```
┌─────────────────────────────────────────────────────────┐
│ CLI: roadmap sync                                       │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ GenericSyncOrchestrator.sync_all_issues()               │
│ - backend.authenticate()                                │
│ - backend.get_issues()                                  │
│ - core.issues.list()                                    │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ SyncStateComparator                                     │
│ - identify_conflicts()                                  │
│ - identify_updates()                                    │
│ - identify_pulls()                                      │
│ - identify_up_to_date()                                 │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ SyncConflictResolver                                    │
│ - resolve_batch(conflicts)                              │
│ - Returns resolved issues                               │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Apply Changes (if not dry-run)                          │
│ - backend.push_issues(updates + resolved)               │
│ - backend.pull_issue(pulls)                             │
│ - Modify .roadmap/issues/*.md files                     │
│   (via core.issues or file parser)                      │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ User Performs Git Operations (user responsibility)      │
│ - git add .roadmap/                                     │
│ - git commit -m "chore: sync"                           │
│ - git push                                              │
└─────────────────────────────────────────────────────────┘
```

### Sync Operation (dry-run = True)

Same as above, but skip the "Apply Changes" and "User Git Ops" steps. Show what would happen.

## Conflict Resolution

### Three-Way Merge Strategy

Three-way merge compares three versions:

1. **Base** (previous sync state)
2. **Local** (current local version)
3. **Remote** (current remote version)

Results:

```
Base       Local      Remote     Result
─────────  ─────────  ─────────  ──────────────────
unchanged  unchanged  unchanged  No change
unchanged  changed    unchanged  Use local (our change)
unchanged  unchanged  changed    Use remote (their change)
unchanged  changed    changed    Conflict (both changed differently)
changed    changed    changed    Conflict (all three differ)
```

### Auto-Merge Rules

Non-critical fields are auto-merged:
- Labels
- Description
- Other metadata

Critical fields are flagged:
- Status (blocks work)
- Assignee (ownership issue)
- Priority (work order)

## Configuration

Backend selection at init time:

```bash
roadmap init
# Prompts for GitHub token/repo or Git config
# Saves to .roadmap/config.yaml
```

Sync uses configured backend:

```bash
roadmap sync  # Uses backend from config
```

## Testing

### Unit Tests
- `test_sync_state_comparator.py` - Change detection
- `test_sync_conflict_resolver.py` - Conflict resolution
- `test_github_sync_backend.py` - GitHub API operations

### Integration Tests
- `test_sync_orchestrator_end_to_end.py` - Full workflow with mocks
- `test_sync_end_to_end_integration.py` - Full workflow with real objects
- CLI tests - Command-line interface

### What's NOT Tested Anymore
- Git operations in backends (removed as per new architecture)
- File persistence in orchestrator (user responsibility now)
- State file management (decoupled from orchestrator)

## Future Enhancements

### New Backends
To support a new sync target (GitLab, Jira, etc.):

1. Create new class implementing `SyncBackendInterface`
2. Implement all required methods
3. Add to backend factory
4. Test with existing integration tests (no changes needed!)

### Improved Conflict Resolution
- UI for choosing resolution strategy interactively
- Custom merge strategies per field
- Conflict history tracking

### Performance
- Incremental sync (only changed issues)
- Batch API operations
- Caching of remote state

## See Also

- [Architecture Guide](ARCHITECTURE.md) - Overall project structure
- [Workflow Patterns](../user_guide/WORKFLOWS.md) - How teams use sync
- [GitHub Setup](../user_guide/GITHUB_SYNC_SETUP.md) - User documentation
- [SyncBackendInterface](../../roadmap/core/interfaces/sync_backend.py) - Protocol definition
