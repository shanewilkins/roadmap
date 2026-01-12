# Git Hooks Implementation Plan

## Current State

### What's Working (80% Complete)
- **Hook Installation/Uninstall**: `GitHookManager`, `HookInstaller` fully functional
- **Hook Registry**: 4 hooks available (post-commit, post-checkout, pre-push, post-merge)
- **Hook Script Generation**: Bash wrapper auto-generates Python handlers
- **Auto-Sync Service**: `GitHookAutoSyncService` with configuration framework
- **Logging**: Activity logs to `.git/roadmap-hooks.log`
- **CLI Commands**: `git hooks-install`, `hooks-uninstall`, `hooks-status`, `hooks-config` exist

### What's NOT Working
1. **Configuration**: `GitHookAutoSyncConfig` class exists but isn't wired to CLI
   - Users cannot enable/disable auto-sync per event without code changes
   - No persistence of hook configuration

2. **Backend Agnosticism**: GitHub-hardcoded in `GitHookAutoSyncService`
   - Imports `GitHubIntegrationService` and `GitHubSyncOrchestrator` directly
   - No backend selection logic
   - No support for vanilla Git sync via hooks

3. **Issue Status Auto-Update**: Partially implemented
   - `_update_issue_from_commit()` method exists but never called
   - No automatic status progression (TODO → IN_PROGRESS)
   - No commit reference attachment to issues

4. **Visibility**: No way to see hook configuration or behavior
   - `hooks-config` command exists but is empty/incomplete
   - No command to show what hooks will do or their configuration

---

## Implementation Phases

### Phase 1: Wire Configuration (2-3 hours)
**Goal**: Users can configure auto-sync behavior via CLI

**Tasks**:
1. **Implement `roadmap git hooks-config` command**
   - Show current configuration: `roadmap git hooks-config --show`
   - Set options: `roadmap git hooks-config --enable-sync-on-commit`
   - Set options: `roadmap git hooks-config --disable-sync-on-merge`
   - Confirm before sync: `roadmap git hooks-config --confirm-before-sync`
   - Force resolution: `roadmap git hooks-config --force-local` (or --force-remote)

2. **Persist configuration**
   - Store in `.roadmap/.hook-config.json` or similar
   - Load configuration on hook execution
   - Validate configuration on load

3. **Tests**
   - Test all config get/set operations
   - Test persistence and reload
   - Test validation

**Files to modify**:
- `roadmap/adapters/cli/git/hooks_config.py` (likely already exists, expand it)
- `roadmap/adapters/git/git_hooks_manager.py` (add config persistence)
- Tests: Create/expand `tests/unit/adapters/cli/git/test_hooks_config.py`

---

### Phase 2: Backend Agnosticism (1-2 hours)
**Goal**: Hooks work with any sync backend (GitHub or Git)

**Tasks**:
1. **Refactor GitHookAutoSyncService**
   - Replace hardcoded GitHub imports
   - Auto-detect backend from config (like sync.py does)
   - Use `GenericSyncOrchestrator` instead of `GitHubSyncOrchestrator`

2. **Update hook trigger logic**
   - `_trigger_auto_sync_on_commit()` → Use generic orchestrator
   - `_trigger_auto_sync_on_checkout()` → Use generic orchestrator
   - `_trigger_auto_sync_on_merge()` → Use generic orchestrator

3. **Tests**
   - Test auto-sync with GitHub backend
   - Test auto-sync with Git backend
   - Test backend detection logic

**Files to modify**:
- `roadmap/core/services/git_hook_auto_sync_service.py` (~30 line changes)
- Tests: Expand existing auto-sync tests

---

### Phase 3: Issue Auto-Update (1-2 hours)
**Goal**: Commits automatically update issue status and attach metadata

**Tasks**:
1. **Activate issue status updates**
   - Call `_update_issue_from_commit()` from hook handlers
   - Extract issue ID from branch name or commit message
   - Auto-update status: TODO → IN_PROGRESS on first commit
   - Update progress_percentage based on commit count

2. **Track commit references**
   - Attach commit hash, message, timestamp to issue
   - Store in issue's git_commits field
   - Display in issue view

3. **Smart parsing**
   - Support "Closes #123" / "Fixes #456" in commit messages
   - Support "ISSUE-123" format from branch names
   - Fallback to branch-to-issue mapping if message doesn't specify

4. **Tests**
   - Test status update on first commit
   - Test commit tracking
   - Test issue ID extraction from various formats

**Files to modify**:
- `roadmap/adapters/git/git_hooks_manager.py` (wire update_issue calls)
- Potentially add commit message parser utility

---

### Phase 4: Improved Visibility (1 hour)
**Goal**: Users understand what hooks are doing

**Tasks**:
1. **Enhance `hooks-status` output**
   - Show which hooks are installed and executable
   - Show current configuration (sync-on-commit: enabled, etc.)
   - Show last activity from `.git/roadmap-hooks.log`

2. **Add `hooks-test` command**
   - Test hook execution without making changes
   - Verify Python environment and imports
   - Verify roadmap is initialized
   - Verify Git repo connectivity

3. **Improve logging**
   - More detailed logs with outcomes (what changed)
   - Summary at end of hook execution

**Files to modify**:
- `roadmap/adapters/cli/git/commands.py` (enhance hooks_status, add hooks_test)
- `roadmap/adapters/git/status_display.py` (if hook status display exists)

---

## Critical Decisions

### Decision 1: Configuration Storage Location
**Question**: Where should hook configuration be stored?

**Options**:
- **A) `.roadmap/.hook-config.json`** (isolated, clean)
  - ✅ Separate from other config
  - ✅ Easy to version control
  - ❌ One more file in .roadmap

- **B) Inside `config.yaml` under `hooks` section**
  - ✅ Single source of truth
  - ✅ Already using YAML
  - ❌ Mixes concerns (GitHub config + hooks config)

- **C) Inside `.github/config.json` (if exists)**
  - ✅ Already exists if GitHub is configured
  - ❌ Doesn't work for vanilla Git sync only
  - ❌ GitHub-specific naming

**Recommendation**: **Option A** - Clean separation, easier to understand

### Decision 2: Auto-Sync Opt-In vs Opt-Out
**Question**: Should auto-sync be on by default or require explicit enable?

**Options**:
- **A) Opt-In (default OFF)** - Users must enable
  - ✅ Safer, no surprises
  - ✅ Clear user intent
  - ❌ Requires extra step for new users

- **B) Opt-Out (default ON)** - Auto-sync enabled after `hooks install`
  - ✅ More convenience
  - ✅ Hooks immediately useful
  - ❌ May surprise users with auto syncs

**Recommendation**: **Option A** - Auto-sync is a power feature, should be explicit

### Decision 3: Issue Status Update Thresholds
**Question**: When should issue status automatically change?

**Options**:
- **A) First commit triggers TODO → IN_PROGRESS**
  - ✅ Simple, obvious signal
  - ❌ May be premature (just started work)

- **B) Require N commits or time threshold**
  - ✅ More deliberate
  - ❌ Complex, harder to explain

- **C) No automatic status change, just track commits**
  - ✅ Safest, no surprises
  - ❌ Less value from hooks

**Recommendation**: **Option A** - Simplest and aligns with Git workflow

### Decision 4: Hook Blocking on Error
**Question**: Should a hook error block the Git operation?

**Current**: Silent fail (hook errors don't stop Git)

**Options**:
- **A) Always silent fail** (current)
  - ✅ Never blocks developer workflow
  - ❌ Issues silently fail to sync

- **B) Warn but don't block**
  - ✅ User sees the error
  - ✅ Doesn't block Git
  - ❌ Noisy for minor issues

- **C) Block on critical errors, silent on non-critical**
  - ✅ Balance safety and UX
  - ❌ Complex, need to define "critical"

**Recommendation**: **Option B** - Warn but don't block (can be tuned later)

---

## Effort Estimate

| Phase | Work | Estimate | Notes |
|-------|------|----------|-------|
| Phase 1 | Config wiring | 2-3h | Most complex part |
| Phase 2 | Backend agnosticism | 1-2h | Straightforward refactor |
| Phase 3 | Issue auto-update | 1-2h | Mostly plumbing |
| Phase 4 | Visibility | 1h | Polish |
| Testing | All phases | 2-3h | Integration tests |
| **Total** | | **8-11h** | **Span 2-3 days** |

---

## Implementation Order

1. **Start with Phase 2** (backend agnosticism) - Prerequisite for rest
2. **Then Phase 1** (config) - Foundation for behavior
3. **Then Phase 3** (auto-update) - Main value-add
4. **Finally Phase 4** (visibility) - Polish

**Why this order**: Phase 2 unblocks Phase 1 (so auto-sync can work with any backend), Phase 1 unblocks Phase 3 (so config actually works), Phase 4 is last because it's optional polish.

---

## Next Steps

1. **Today**: Return to Phase C of sync implementation (GitHub backend integration)
2. **Later today or tomorrow**: Start Phase 1 (hooks config wiring)
3. **Follow-up**: Complete remaining hook phases to full completion

---

## Related Work

- Current sync implementation status: Phase B complete (top-level sync command)
- Next: Phase C (GitHub backend integration using ThreeWayMerger)
- Hooks provide complementary automation that will be more valuable once Phase C is done
