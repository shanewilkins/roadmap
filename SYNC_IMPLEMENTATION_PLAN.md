# Sync Architecture Implementation Plan

## Overview

This document is a concise, phase-by-phase guide for implementing the new git-based sync architecture with YAML frontmatter metadata and pre-commit sync workflow.

---

## Phase 1: Foundation (Git History Utilities)

### Objective
Create utilities to access file history from git and parse YAML metadata.

### Tasks

**1.1 Create `roadmap/adapters/persistence/git_history.py`**
- `get_file_at_timestamp(file_path, timestamp)` → Returns file content as it existed at timestamp
- `find_commit_at_time(timestamp, file_path=None)` → Finds commit SHA closest to given time
- `get_file_at_commit(file_path, commit_sha)` → Returns file at specific commit
- Error handling for git operations (no git repo, detached HEAD, etc.)

**1.2 Update `roadmap/adapters/persistence/issue_file_storage.py`**
- Modify `load_issue()` to extract and parse `sync_metadata` from YAML header
- Modify `save_issue()` to accept and write `sync_metadata` to YAML header
- Ensure `_parse_yaml_header()` preserves all frontmatter keys including `sync_metadata`
- Ensure `_build_yaml_header()` writes `sync_metadata` if present

**1.3 Unit Tests**
- Test `get_file_at_timestamp()` with various commit scenarios
- Test YAML parsing/writing with embedded sync_metadata
- Test edge cases (file doesn't exist, no git history, malformed YAML)

---

## Phase 2: Sync State Manager & Metadata

### Objective
Refactor SyncStateManager to use git history and YAML metadata instead of DB tables.

### Tasks

**2.1 Refactor `roadmap/core/services/sync_state_manager.py`**
- Remove DB-backed save/load methods (`save_sync_state_to_db`, `load_sync_state_from_db`)
- Add `get_local_baseline(issue_id)` → Calls git history utilities
- Add `get_remote_baseline(issue_id)` → Reads from issue's `sync_metadata.remote_state`
- Add `save_issue_sync_metadata(issue_id, metadata)` → Writes to issue YAML
- Keep `sync_state.json` for global metadata (last_sync_time, backend type, etc.)

**2.2 Create Metadata Migration Script**
- `roadmap/scripts/migrate_sync_state_to_yaml.py`
- Reads old `sync_base_state` table
- For each issue: Extracts baseline and writes to issue YAML `sync_metadata`
- Backs up old database
- Verifies migration completeness

**2.3 Unit Tests**
- Test baseline reconstruction from git history
- Test sync_metadata read/write for issues
- Test migration script on sample data

---

## Phase 3: Sync Orchestration

### Objective
Update sync orchestrator to use git-based baselines and support pre-commit workflow.

### Tasks

**3.1 Update `roadmap/adapters/sync/generic_sync_orchestrator.py`**
- Replace `sync_state_repository.get_base_state()` calls with `git_history` calls
- Update `_detect_changes_with_baselines()` to use:
  - Local baseline from git history
  - Remote baseline from sync_metadata
  - Three-way merge logic (unchanged)
- Remove database queries for baseline state
- Add `update_sync_metadata_after_sync()` to save remote state post-sync

**3.2 Implement Changed-File Detection**
- Add `get_changed_files_since_last_sync()` utility
- Uses `git diff --name-only HEAD~1`
- Falls back to full scan if git diff fails
- Used by DB cache invalidation

**3.3 Update Database Cleanup**
- Remove `sync_base_state` table creation from `database_manager.py`
- Remove `sync_metadata` table creation
- Remove any sync-related indexes and triggers
- Database now holds only: projects, milestones, issues, issue_dependencies, issue_labels, comments

**3.4 Unit Tests**
- Mock git history for baseline tests
- Test three-way merge with various scenarios
- Test sync_metadata updates post-sync
- Test with GitHub and vanilla git backends

---

## Phase 4: Database Cache Optimization

### Objective
Implement smart cache invalidation and rebuild strategy.

### Tasks

**4.1 Create `roadmap/adapters/persistence/db_cache_manager.py`**
- `rebuild_from_changed_files(files: list[str])` → Update DB for changed .md files only
- `full_rebuild()` → Scan all files and rebuild DB
- Should be called on app startup
- Tracks last rebuild time

**4.2 Integrate into App Startup**
- Call `db_cache_manager.rebuild_from_changed_files()` on init
- Measure startup time (should be <100ms)
- Add optional `--no-rebuild` flag for server mode

**4.3 Update List Commands**
- Audit all list operations to use DB queries instead of file scans
- Ensure consistency with file-based source of truth
- Performance test: list commands should be fast

**4.4 Unit Tests**
- Test partial rebuild from changed files
- Test full rebuild and consistency
- Performance tests for large project sets

---

## Phase 5: Pre-Commit Sync Integration

### Objective
Implement pre-commit sync workflow and user messaging.

### Tasks

**5.1 Update Sync CLI Command**
- Add `--pre-commit` flag (or make it default for `sync` command)
- Before sync: List files with local changes
- After sync: Show sync_metadata updates
- Clear messaging about conflicts detected
- Exit code indicates success/conflict/error

**5.2 Git Hook Integration (Optional)**
- Create `.git/hooks/pre-commit` template that runs `roadmap sync`
- User can install via `roadmap init --install-hooks`
- Prevents commit if sync fails

**5.3 Conflict Display**
- When conflicts detected, show field-level diff
- Indicate resolution strategy (local/remote/merge)
- Provide option to review before proceeding

**5.4 Update Documentation**
- Document pre-commit sync workflow in CLI help
- Add examples showing sync + commit cycle
- Explain conflict resolution strategies

**5.5 Unit Tests**
- Test sync command with `--pre-commit` flag
- Test conflict detection and display
- Test error handling

---

## Phase 6: Testing & Migration

### Objective
Validate all changes and migrate existing user data.

### Tasks

**6.1 Integration Tests**
- End-to-end sync with GitHub backend
- End-to-end sync with vanilla git backend
- Test three-way merge scenarios (no conflict, field-level conflict, resolution)
- Test with multiple issues and milestones

**6.2 Run Full Test Suite**
- All existing tests should pass (may need updates for removed DB tables)
- No regressions in other features

**6.3 Migration Testing**
- Test migration script on real user databases
- Verify sync_metadata correctly populated
- Test old workflow still works before migration
- Document migration steps for users

**6.4 Performance Benchmarks**
- Measure startup time with new DB rebuild
- Measure sync time with various project sizes (100, 1000+ issues)
- Ensure no significant regression

---

## Phase 7: Documentation & Release

### Objective
Document new architecture and prepare for release.

### Tasks

**7.1 Update User Documentation**
- Add "Sync Workflow" section to user guide
- Document pre-commit sync pattern
- Show conflict resolution examples
- Add troubleshooting for common sync issues

**7.2 Update Developer Documentation**
- Add architecture document (SYNC_ARCHITECTURE.md) ✓ (already created)
- Document git_history utilities API
- Document SyncBackendInterface for future backends
- Provide example of adding new sync backend

**7.3 Update CHANGELOG**
- Document architectural changes
- Note removed database tables
- Note migration required for existing users
- Highlight benefits (git history, pre-commit workflow)

**7.4 Prepare Release Notes**
- Summary of sync improvements
- Migration instructions
- Known issues or limitations
- Breaking changes (if any)

---

## Implementation Timeline

| Phase | Effort | Duration | Dependencies |
|-------|--------|----------|--------------|
| 1: Git History | 1-2 days | 2 days | None |
| 2: Sync Manager | 1-2 days | 2 days | Phase 1 |
| 3: Orchestration | 2-3 days | 3 days | Phase 1, 2 |
| 4: DB Cache | 1 day | 1 day | Phase 3 |
| 5: Pre-Commit | 1 day | 1 day | Phase 3 |
| 6: Testing | 2-3 days | 3 days | Phase 1-5 |
| 7: Documentation | 1 day | 1 day | All phases |
| **Total** | **9-14 days** | **~2 weeks** | Sequential |

---

## Success Criteria

- [ ] All 6440+ tests pass
- [ ] Git history utilities work reliably
- [ ] Sync metadata correctly stored in YAML
- [ ] Three-way merge detects all conflicts
- [ ] Pre-commit sync workflow documented and working
- [ ] DB rebuilds in <100ms on startup
- [ ] List commands use DB (fast)
- [ ] Migration script works for existing users
- [ ] GitHub and vanilla git backends fully functional
- [ ] No sync idempotency issues (no spurious pushes/pulls)

---

## Rollback Plan

If issues arise:

1. **Database tables still exist** - Can revert to DB-based approach
2. **YAML metadata backwards compatible** - Existing code can ignore sync_metadata
3. **Git history never changes** - Safe to revert code changes
4. **Migration is optional** - Users don't have to migrate immediately

---

## Notes

- **Git dependency**: Requires git in PATH (already required for vanilla git backend)
- **Backward compatibility**: Existing projects work without YAML metadata (no baseline conflicts)
- **Performance**: Git history lookups cached in memory to avoid repeated subprocess calls
- **Future backends**: New backends only need to implement interface; everything else works
