# Sync Implementation Plan

**Goal:** Make `roadmap sync` work reliably with intelligent conflict resolution and backend-agnostic design.

---

## 1. DESIRED STATE (What we want)

### 1.1 Command Structure
```bash
# Backend-agnostic top-level command
roadmap sync [OPTIONS]

# Respects backend from config (saved at init time)
# Options:
#   --dry-run       Preview changes without applying
#   --backend       Override default backend (github|git)
#   --force-local   Resolve all conflicts favoring local
#   --force-remote  Resolve all conflicts favoring remote
#   --interactive   Prompt on conflicts (not yet implemented)
```

### 1.2 GitHub Backend Sync Workflow

**PULL Phase** (Remote → Local):
1. Fetch all issues/comments from GitHub API
2. For each issue: compare `current local file` vs `GitHub API state`
3. Apply three-way merge (local vs base vs remote)
4. For unresolvable conflicts: flag for review or apply tiebreaker rules
5. Update local issue files
6. Commit changes: `git commit -m "Sync: pull from GitHub"`

**PUSH Phase** (Local → GitHub):
1. Detect changed issues (current files vs git HEAD)
2. For each changed issue: send updates to GitHub API
3. Handle conflicts detected by GitHub (e.g., concurrent edits)
4. Commit sync point: `git commit -m "Sync: push to GitHub"`

### 1.3 Git Backend Sync Workflow (Self-Hosted)

**PULL Phase:**
1. `git pull origin master`
2. Resolve any file conflicts using three-way merge (git's native)
3. Merge any conflicting issue state

**PUSH Phase:**
1. Commit any local changes
2. `git push origin master`

### 1.4 Conflict Resolution Strategy

**Three-way merge logic:**
```
Base State: previous agreed-upon state (from git history)
Local State: current file on disk
Remote State: GitHub API or git remote

For each field:
  if local == base:
    use remote  (only remote changed)
  elif remote == base:
    use local   (only local changed)
  elif local == remote:
    use either  (both made same change, no conflict)
  else:
    CONFLICT - both sides changed differently
```

**For conflicts:**
- **Status, Assignee, Milestone:** Flag for manual review (high-risk)
- **Comments, Description:** Merge both (append with source markers)
- **Metadata:** Use field-level rules (see 1.5)

### 1.5 Field-Level Tiebreaker Rules (for true conflicts)

| Field | Strategy | Rationale |
|-------|----------|-----------|
| `status` | Flag for review | Both sides changed intent → user decides |
| `assignee` | Flag for review | Both sides assigned differently → user decides |
| `milestone` | Flag for review | Different release targets → user decides |
| `labels` | Merge both (union) | Can have multiple labels |
| `description` | Merge both (append) | Preserve all content |
| `comments` | Merge both (append) | Preserve all feedback |
| `custom metadata` | Local wins | Local state is source of truth |
| `created_at`, `updated_at` | Remote wins | GitHub is authoritative |

---

## 2. CURRENT STATE (What we have)

### 2.1 Architecture
- `roadmap git sync` command exists (backend-specific naming)
- GitCoordinator, GitHubSyncOrchestrator classes exist
- Conflict detection happens but resolution is unclear
- Tests exist but focus on unit level, not integration

### 2.2 Command Location
```
roadmap git sync [OPTIONS]
```
**Problem:** Backend-specific naming; doesn't reflect that it should work for any backend

### 2.3 What's Implemented
- ✅ GitHub credentials stored/configured
- ✅ GitHub API connectivity
- ✅ Basic issue fetching from GitHub
- ✅ Some conflict detection (reports "18 conflicts")
- ✅ Dry-run preview mode
- ⚠️ Conflict resolution: Unclear/incomplete
- ❌ Three-way merge logic: Not implemented
- ❌ Field-level rules: Not implemented
- ❌ Manual conflict review: Not implemented
- ❌ Sync commit tracking: Not clear
- ❌ Backend selection from config: Not fully working
- ❌ Self-hosted (Git) backend: Partially implemented

### 2.4 Known Issues
1. **Backend selection:** `roadmap sync --backend github` required even though GitHub is configured
2. **Conflict handling:** All 18 issues show as conflicts; no intelligent resolution
3. **Uncertainty:** What is "base state"? How do we track it?
4. **Missing:** Base state storage (for three-way merge)
5. **Command structure:** `roadmap git sync` doesn't feel backend-agnostic

---

## 3. GAPS & PROBLEMS

| Issue | Impact | Root Cause |
|-------|--------|-----------|
| No three-way merge logic | 18 false conflicts reported | Not implemented |
| No base state tracking | Can't do three-way merge | No `.roadmap/.sync-state` or similar |
| Unclear conflict resolution | Can't resolve automatically | No rules defined for each field |
| Backend not auto-selected | User must pass `--backend` | Not loading from config in sync command |
| Command is `roadmap git sync` | Doesn't feel backend-agnostic | Architecture issue |
| All conflicts flagged as errors | Sync fails instead of prompting | Over-aggressive error handling |
| No manual conflict workflow | User can't resolve conflicts | Feature not built |
| Sync state not committed | Can't track sync history | No commit tracking |

---

## 4. IMPLEMENTATION PLAN

### Phase A: Foundation (Weeks 1-2)
**Goal:** Set up infrastructure for intelligent sync

#### A.1 Create Base State Tracking
- **File:** `.roadmap/.sync-state.json`
- **Content:** 
```json
{
  "last_sync": "2026-01-01T12:00:00Z",
  "backend": "github",
  "issues": {
    "issue-123": {
      "base_hash": "abc123...",
      "last_remote_sha": "def456...",
      "status": "in-progress",
      "assignee": "alice",
      "updated_at": "2026-01-01T10:00:00Z"
    }
  }
}
```
- **Update:** After each successful sync

#### A.2 Implement Three-Way Merge Service
```python
class ThreeWayMerger:
    def merge_field(self, base, local, remote, field_name) -> tuple[value, MergeStatus]:
        """
        Returns: (merged_value, "clean" | "conflict")
        """
        if local == base:
            return remote, "clean"  # only remote changed
        elif remote == base:
            return local, "clean"   # only local changed
        elif local == remote:
            return local, "clean"   # both made same change
        else:
            return None, "conflict" # both changed differently
```

#### A.3 Implement Field-Level Rules
```python
class ConflictResolver:
    RULES = {
        "status": "flag_for_review",
        "assignee": "flag_for_review", 
        "milestone": "flag_for_review",
        "labels": "merge_union",
        "description": "merge_append",
        "comments": "merge_append",
        # ... etc
    }
    
    def resolve_conflict(self, field, base, local, remote) -> value:
        rule = self.RULES.get(field, "flag_for_review")
        return apply_rule(rule, base, local, remote)
```

### Phase B: Command Restructuring (Week 2)
**Goal:** Make sync backend-agnostic

#### B.1 Create Top-Level Sync Command
- ✅ Created new `roadmap/adapters/cli/sync.py` with `sync` command
- ✅ Reads `sync_backend` from config automatically
- ✅ Passes to orchestrator
- ✅ Supports `--backend` override for manual selection
- ✅ Help text shows backend-agnostic options
- ⏳ Keep `roadmap git sync` as alias for backwards compatibility

#### B.2 Update Help/Docs
- ✅ `roadmap sync --help` shows clear backend-agnostic interface
- ✅ Documents auto-detection from config
- ✅ Lists all available options with descriptions

### Phase C: GitHub Backend Implementation (Weeks 3-4)
**Goal:** Make GitHub sync actually work with conflict resolution

#### C.1 PULL Phase
```
1. GitHubSyncOrchestrator.pull():
   - Fetch all issues from GitHub API
   - For each issue:
     - Load local file (if exists)
     - Load base state from .sync-state.json
     - Call ThreeWayMerger.merge_issue()
     - Collect conflicts
   - Return: MergeResult(merged_issues, conflicts)

2. ConflictResolver.resolve():
   - For each conflict:
     - Check field-level rules
     - Apply rule or flag for review
   - Return: resolved_issues, flagged_conflicts

3. Apply changes:
   - Write resolved issues to files
   - Update .sync-state.json
   - Commit: "Sync: pulled from GitHub"
```

#### C.2 PUSH Phase
```
1. GitCoordinator.get_local_changes():
   - Compare current files vs git HEAD
   - Return: list of Issue objects that changed

2. GitHubSyncOrchestrator.push():
   - For each changed issue:
     - Send to GitHub API
     - Handle GitHub API conflicts
   - Return: PushResult(succeeded, failed)

3. Commit:
   - "Sync: pushed to GitHub"
   - Update .sync-state.json with new remote SHA
```

#### C.3 Implement get_local_changes()
```python
class GitCoordinator:
    def get_local_changes(self) -> list[str]:
        """
        Returns list of issue IDs that changed since last sync.
        Compares current files vs git HEAD.
        """
        # Use: git diff HEAD --name-only --relative='\.roadmap/issues'
        # Parse filenames to extract issue IDs
```

### Phase D: Testing & Validation (Week 5)
**Goal:** Ensure sync works end-to-end

#### D.1 Integration Tests
- Create test repo with sample issues
- Mock GitHub API
- Test PULL phase with conflicts
- Test PUSH phase with conflicts
- Validate .sync-state.json is updated

#### D.2 Manual Testing
- Test with real GitHub repo (on test account)
- Create issue locally → sync → verify on GitHub
- Create issue on GitHub → sync → verify locally
- Concurrent edits → verify conflict detection & resolution

---

## 5. IMMEDIATE NEXT STEPS (This Week)

**Phase A Status:** ✅ COMPLETE
- ✅ Three-way merger implemented and tested (14 tests)
- ✅ Conflict resolver with field-level rules implemented (15 tests)  
- ✅ Sync state models implemented (11 tests)
- **Total:** 40 tests passing

**Phase B Status:** ✅ COMPLETE
- ✅ Top-level `roadmap sync` command created
- ✅ Backend auto-detection from config working
- ✅ Backend override via `--backend` option working
- ✅ Command registered in CLI (7 new tests passing)
- ✅ Help text documents all features

**Phase C: Next Steps**
1. Integrate ThreeWayMerger into GitHub sync orchestrator PULL phase
2. Integrate ConflictResolver into sync orchestrator
3. Update PULL phase to use three-way merge instead of reporting all as conflicts
4. Test end-to-end with real GitHub repo
5. Implement PUSH phase with conflict handling

---

## 6. SUCCESS CRITERIA

- [ ] `roadmap sync` works without `--backend` flag
- [ ] Sync completes without 18 false conflicts
- [ ] Three-way merge resolves ~80% of conflicts automatically
- [ ] True conflicts are flagged for review
- [ ] `.sync-state.json` tracks sync history
- [ ] Can sync with real GitHub repo
- [ ] Self-hosted (git) backend works
- [ ] Tests pass (unit + integration)
- [ ] No data loss on conflicts (always preserve both versions somewhere)

---

## 7. RISKS & MITIGATION

| Risk | Mitigation |
|------|-----------|
| Data loss during merge | Always keep both versions in flags; manual review required for critical fields |
| Sync divergence | Track base state in .sync-state.json; validate before each sync |
| GitHub API rate limits | Cache results; add exponential backoff |
| Concurrent team edits | Three-way merge handles most; flag true conflicts |
| Self-hosted backend incomplete | Implement in Phase E after GitHub works |

---

## 8. ARCHITECTURE DIAGRAM (Target State)

```
roadmap sync
    ↓
SyncCommand (backend-agnostic)
    ↓
(reads config)
    ↓
┌─────────────────────────────────┐
│  SyncOrchestrator               │
│  (backend-agnostic)             │
└─────────────────────────────────┘
    ↓                    ↓
GitHubSyncBackend   GitSyncBackend
    ↓                    ↓
├─ PULL Phase       └─ git pull
├─ PUSH Phase           git push
├─ ThreeWayMerger
└─ ConflictResolver
    ↓
.roadmap/.sync-state.json (base state)
```

---

## 9. FILES TO CREATE/MODIFY

**New:**
- `roadmap/core/services/sync/three_way_merger.py` - Merge logic
- `roadmap/core/services/sync/conflict_resolver.py` - Conflict rules
- `roadmap/adapters/cli/sync.py` - Top-level command
- `roadmap/core/models/sync_state.py` - State model

**Modify:**
- `roadmap/infrastructure/coordinator.py` - Add `get_local_changes()`
- `roadmap/adapters/cli/git/commands.py` - Ensure backend selection works
- `roadmap/core/services/github_sync_orchestrator.py` - Integrate merger
- `roadmap/infrastructure/github/github_client.py` - Handle API conflicts

**Testing:**
- `tests/unit/core/services/sync/test_three_way_merger.py`
- `tests/unit/core/services/sync/test_conflict_resolver.py`
- `tests/integration/test_sync_end_to_end.py`

