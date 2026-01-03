# Roadmap Sync Architecture: Git-Based State Management

## Executive Summary

This document describes the redesigned sync architecture for the roadmap tool. The architecture shifts from a database-heavy baseline state management system to a **file-as-source-of-truth** approach leveraging git history and frontmatter metadata. This enables backend-agnostic sync while maintaining atomic, versioned state and three-way merge conflict detection.

---

## 1. Architecture Overview

### Layers

```
┌─────────────────────────────────────────────────────────────┐
│                   User Workflow (CLI)                       │
│  roadmap sync → Fetch remote → Three-way merge → Commit     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│            Generic Sync Orchestrator                        │
│  • Detects changes (git diff + git history)                │
│  • Performs three-way merge                                │
│  • Handles conflict resolution                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         Backend-Agnostic Sync Interface                     │
│  • GitHub API Backend                                       │
│  • Vanilla Git Backend                                      │
│  • Future: Jira, Linear, GitLab adapters                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          Local File-Based Storage                           │
│  • Issues: .roadmap/projects/{project}/issues/             │
│  • YAML Frontmatter: sync_metadata embedded                │
│  • Git History: Baseline reconstruction via git log        │
│  • Database: Cache layer only (rebuilt on startup)         │
└─────────────────────────────────────────────────────────────┘
```

### Core Principle

**Files are the source of truth.** Everything else (database, git history, sync metadata) is derived from or supporting.

---

## 2. Sync Metadata Structure

Sync metadata is embedded in issue YAML frontmatter as a separate section. This ensures:
- **Atomic storage** with issue data
- **Git history integration** (part of committed file)
- **Backend agnostic** (applies to any syncing system)
- **User transparency** (they see all state in git)

### Metadata Format

```yaml
---
id: "gh-123"
title: "Implement feature X"
status: "in-progress"
assignee: "jane"
priority: "high"
labels:
  - "feature"
  - "backend"
content: "Description here"
milestone: "v1.0"

# Sync metadata - stored in YAML header for git tracking
sync_metadata:
  last_synced: "2026-01-03T10:30:45Z"
  last_updated: "2026-01-03T10:25:00Z"
  remote_state:
    status: "open"
    assignee: "bob"
    priority: "medium"
    labels: ["feature"]
    content: "Original description"
    milestone: null
---

Full markdown content and body here...
```

### Fields Explained

| Field | Purpose | Source |
|-------|---------|--------|
| `last_synced` | Timestamp of last successful sync | Set after sync completes |
| `last_updated` | Last update time from remote system | From remote API response |
| `remote_state` | Snapshot of remote issue at last sync | Captured from API response |

---

## 3. Baseline State Management via Git History

Instead of storing baseline state in a database, we reconstruct it from git history.

### How It Works

1. **User makes local changes** → Edit issue file directly
2. **User prepares to commit** → `roadmap sync`
3. **Sync reads local baseline**:
   ```python
   local_baseline = git_history.get_file_at_timestamp(
       issue_file_path,
       last_synced_timestamp
   )
   ```
4. **Sync reads remote baseline** → From `sync_metadata.remote_state`
5. **Three-way merge comparison**:
   - Local baseline → Local current = What user changed
   - Remote baseline → Remote current = What external system changed
   - Detects conflicts when both changed same field differently

### Git History Utilities

```python
# File: roadmap/adapters/persistence/git_history.py

def get_file_at_timestamp(file_path: str, timestamp: str) -> str:
    """Get file content as it existed at timestamp."""
    # Find git commit closest to timestamp
    # Return file content at that commit

def find_commit_at_time(timestamp: str, file_path: str = None) -> str:
    """Find commit SHA closest to given timestamp."""
    # git log --format="%H %aI" | find closest

def extract_yaml_header(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown file."""
    # Returns (metadata_dict, body_content)
```

### Benefits

✅ **No database needed** for baseline state
✅ **Full audit trail** in git
✅ **Atomic** (baseline + metadata in single commit)
✅ **Mergeable** (standard git conflicts if needed)
✅ **Recoverable** (can inspect any past commit)

---

## 4. Database as Cache Layer

The SQLite database (`~/.roadmap/roadmap.db`) remains, but only as a **query cache**:

### Tables Retained
- `projects` - Project metadata (name, description, status)
- `milestones` - Milestone data with foreign key to projects
- `issues` - Issue data with foreign key to milestones
- `issue_dependencies` - Issue relationship graph
- `issue_labels` - Many-to-many issue-label associations
- `comments` - Issue comments

### Tables Removed
- ❌ `sync_base_state` (replaced by git history)
- ❌ `sync_metadata` (replaced by YAML frontmatter)

### Rebuild Strategy

**On startup:**
```
1. Get list of changed files since last DB rebuild
   git diff --name-only <last_sync_commit> HEAD
2. For each changed .md file:
   - Parse YAML frontmatter
   - Update corresponding DB row
3. Full rebuild if needed (safety fallback)
   - Scan all .roadmap/projects/**/*.md
   - Rebuild entire projects/milestones/issues tables
   - ~50-100ms for typical projects
```

### Usage in List Commands

```python
# Old approach (file scan):
issues = [load_issue(f) for f in glob("**/*.md")]  # Slow

# New approach (DB):
issues = db.query("SELECT * FROM issues ORDER BY status")  # Fast
```

---

## 5. Backend-Agnostic Sync Interface

The `SyncBackendInterface` abstracts away backend details:

```python
class SyncBackendInterface(Protocol):
    """Contract all backends must implement."""

    def authenticate(self) -> bool:
        """Verify credentials and remote connectivity."""

    def get_issues(self) -> dict[str, Any]:
        """Fetch all issues from remote system."""

    def push_issue(self, issue: Issue) -> bool:
        """Push single local issue to remote."""

    def push_issues(self, issues: list[Issue]) -> SyncReport:
        """Push multiple issues with conflict reporting."""

    def pull_issues(self) -> SyncReport:
        """Pull and merge remote issues locally."""

    def get_conflict_resolution_options(self, conflict) -> list[str]:
        """Available strategies: 'use_local', 'use_remote', 'merge'."""

    def resolve_conflict(self, conflict, resolution: str) -> bool:
        """Apply conflict resolution."""
```

### Current Implementations

1. **GitHubSyncBackend** - GitHub REST API
   - Maps GitHub issue number to local issue ID
   - Syncs: status, assignee, labels, content, milestone

2. **VanillaGitSyncBackend** - Git push/pull
   - Works with any git hosting (GitHub, GitLab, Gitea, SSH)
   - No API calls - just git operations

### Adding New Backends

Implement the interface once, and `GenericSyncOrchestrator` handles everything else (conflict detection, merging, DB updates).

---

## 6. GitHub API Integration

### Metadata Compatibility

GitHub API provides these fields on issues:

| GitHub Field | Roadmap Field | Note |
|---|---|---|
| `state` | `status` | Maps: open↔in-progress, closed↔done |
| `assignee.login` | `assignee` | Single assignee (roadmap) |
| `labels[*].name` | `labels` | Array of label names |
| `body` | `content` | Issue description |
| `milestone.title` | `milestone` | Single milestone title |
| `created_at` | `created` | ISO 8601 timestamp |
| `updated_at` | `updated` | Last modification time |
| `closed_at` | `closed_at` | Closure timestamp |
| `comments` | `comment_count` | Number of comments |

### Not Supported by GitHub API

Fields the roadmap tool uses that GitHub doesn't provide natively:

- ❌ `priority` - Must be in milestone description or labels
- ❌ `estimated_hours` - Must be in issue body
- ❌ `dependencies` - No API support (could use labels like "blocks-#123")

**Workaround:** Roadmap stores these in issue content/body; sync skips them when syncing to GitHub.

---

## 7. Pre-Commit Sync Workflow

The user's sync happens **before** commit, not after:

```
User Branch
    ↓
User edits issues
    ↓
$ roadmap sync (before committing)
    │
    ├─ Fetch remote state via backend
    ├─ Load local baseline (git history at last_synced)
    ├─ Load remote baseline (sync_metadata.remote_state)
    ├─ Three-way merge
    ├─ Update issue files with merged state
    └─ Update sync_metadata with new remote baseline
    ↓
$ git add . && git commit "Feature X + sync"
    │
    └─ Single atomic commit with:
       - Feature changes
       - Sync metadata updates
       - Conflict resolutions
    ↓
$ git push
    │
    └─ If conflicts with master:
       - Standard git merge conflict
       - User resolves normally
       - Merged commit includes all state
```

### Benefits

✅ **Clean history** - No separate sync commits
✅ **Atomic** - Work + sync metadata in one commit
✅ **Conflict resolution at merge time** - Standard git workflow
✅ **Audit trail** - Every commit shows what user + remote changed
✅ **Project-as-code** - Everything versioned in git

---

## 8. Conflict Resolution Strategy

### Detection (Three-Way Merge)

```python
def detect_conflicts(local_baseline, local_current, remote_baseline, remote_current):
    """Find fields that both local and remote changed."""
    conflicts = {}
    for field in ['status', 'assignee', 'priority', 'labels', 'content']:
        local_changed = local_baseline[field] != local_current[field]
        remote_changed = remote_baseline[field] != remote_current[field]

        if local_changed and remote_changed:
            if local_current[field] != remote_current[field]:
                # Both changed differently - conflict
                conflicts[field] = {
                    'local': local_current[field],
                    'remote': remote_current[field],
                    'baseline': local_baseline[field]
                }
    return conflicts
```

### Resolution Options

1. **`use_local`** - Keep local version
2. **`use_remote`** - Accept remote version
3. **`merge`** - Try to combine (array fields like labels)

### Field-Level Conflicts

Because we store field-level baseline state in `remote_state`, we can offer smart merging:

```python
# Labels example:
baseline:  ['bug']
local:     ['bug', 'priority-high']  # Added priority-high
remote:    ['bug', 'documentation']  # Added documentation

# Smart merge result: ['bug', 'priority-high', 'documentation']
```

---

## 9. Data Flow Example

**Scenario:** User changes issue status locally; GitHub issue was reassigned

```yaml
# Local file at last_synced (git history)
status: "open"
assignee: "alice"

# Local file now (user edit)
status: "in-progress"
assignee: "alice"

# Remote baseline (sync_metadata.remote_state)
status: "open"
assignee: "jane"

# Remote now (GitHub API)
status: "open"
assignee: "bob"
```

**Three-Way Merge:**
- Local changed: status only (open → in-progress)
- Remote changed: assignee only (jane → bob)
- Result: Both changes merged
  ```yaml
  status: "in-progress"  # From local
  assignee: "bob"        # From remote
  ```

No conflict because they changed different fields.

---

## 10. Implementation Phases

### Phase 1: Foundation
- Create git history utilities module
- Update IssueFileStorage to read/write sync_metadata YAML
- Implement git-based baseline reconstruction

### Phase 2: Orchestration
- Update GenericSyncOrchestrator to use git baselines
- Remove database sync table queries
- Implement pre-commit sync workflow trigger

### Phase 3: Optimization
- Implement git diff-based DB cache invalidation
- Add DB rebuild on startup
- Performance testing with large projects

### Phase 4: Testing & Documentation
- Update all sync tests for new approach
- Integration tests with GitHub API
- User documentation for sync workflow

---

## 11. Appendix: Removed Infrastructure

### Why We Removed `sync_base_state` Table

**Old approach:**
```sql
-- sync_base_state table
CREATE TABLE sync_base_state (
    issue_id TEXT PRIMARY KEY,
    status TEXT,
    assignee TEXT,
    description TEXT,
    labels TEXT,  -- JSON array
    synced_at TIMESTAMP
);
```

**Problems:**
- ✗ Duplicate data (files + DB)
- ✗ Sync issues if DB and files diverged
- ✗ Lost history (only current baseline stored)
- ✗ Required cleanup/migration logic

**New approach:**
- ✓ Single source of truth (git + YAML)
- ✓ Complete history available
- ✓ No synchronization issues
- ✓ Mergeable via standard git

---

## 12. Glossary

| Term | Definition |
|---|---|
| **Baseline** | The state of an issue at the time of last sync |
| **Local Baseline** | What the file contained at `last_synced` (via git history) |
| **Remote Baseline** | What remote system had at `last_synced` (via sync_metadata) |
| **Three-Way Merge** | Comparing local_baseline→local_current vs remote_baseline→remote_current |
| **Sync Metadata** | YAML frontmatter tracking sync timestamps and remote state |
| **Backend** | Implementation of SyncBackendInterface (GitHub, Git, etc.) |
| **Source of Truth** | Files in `.roadmap/projects/` - the authoritative state |
