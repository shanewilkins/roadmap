---
id: 98e87e57
title: 'Architecture: Enable Git-Only Self-Hosting Without GitHub Coupling'
headline: '# Architecture: Enable Git-Only Self-Hosting Without GitHub Coupling'
priority: medium
status: closed
archived: false
issue_type: other
milestone: backlog
labels:
- synced:from-github
remote_ids:
  github: 3721
created: '2026-02-05T15:17:52.429165+00:00'
updated: '2026-02-11T19:55:16.921216+00:00'
assignee: null
estimated_hours: null
due_date: null
depends_on: []
blocks: []
actual_start_date: null
actual_end_date: null
progress_percentage: 100.0
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
comments: []
github_issue: 3721
---

# Architecture: Enable Git-Only Self-Hosting Without GitHub Coupling

## Description

Currently, the sync architecture is tightly coupled to GitHub. Teams who want to self-host roadmaps through vanilla Git repositories (GitLab, Gitea, vanilla Git over SSH, etc.) should have that option without requiring GitHub integration.

This issue addresses the architectural refactoring needed to support multiple sync backends and ensure GitHub is *optional*, not mandatory.

## Current State

- ✅ GitHub sync orchestrator implemented and working
- ✅ Interface abstraction created (SyncBackendInterface Protocol)
- ✅ GitHub-specific code extracted into GitHubSyncBackend
- ❌ Cannot sync to vanilla Git-only repos yet (Phase 3 in progress)
- ❌ Backend selection not yet wired into CLI/config

## Acceptance Criteria

- [x] Create `SyncBackendInterface` in `roadmap/core/interfaces/` defining sync contract
  - **Phase 1 Complete**: Protocol defined in `roadmap/core/interfaces/sync_backend.py`
  - Includes SyncConflict and SyncReport supporting classes
  - 13 unit tests validating interface contract

- [x] Extract GitHub-specific code into `GitHubSyncBackend` implementing the interface
  - **Phase 2 Complete**: Implementation in `roadmap/adapters/sync/backends/github_sync_backend.py`
  - All 7 core methods implemented
  - 22 unit tests covering full functionality
  - Graceful error handling without raising exceptions

- [x] Implement `VanillaGitSyncBackend` for vanilla Git (git push/pull) sync
  - **Phase 3 Complete**: Implementation in `roadmap/adapters/sync/backends/vanilla_git_sync_backend.py`
  - All 7 core methods implemented using subprocess git commands
  - 25 unit tests covering full functionality (all passing ✅)
  - Supports any Git hosting: GitHub, GitLab, Gitea, vanilla SSH, etc.

- [x] Update `GitHubSyncOrchestrator` to use abstracted backend interface
  - **Phase 4 Complete**: Orchestrator updated in `roadmap/adapters/sync/generic_sync_orchestrator.py`

- [x] CLI supports selecting backend: `roadmap init --sync-backend=[github|git]`
  - **Phase 4 Complete**: CLI option added to init/commands.py with proper enum conversion

- [x] Configuration stores selected backend in `.roadmap/config.json`
  - **Phase 4 Complete**: Config schema extended in common/config_schema.py
  - Backend selection persists and reloads correctly

- [x] Documentation: SELF_HOSTING.md with setup instructions
  - **Phase 4 Complete**: Comprehensive guide in `docs/SELF_HOSTING.md`

- [x] Unit tests for both backends with interface contract tests
  - **Complete**: Interface contract tests ✅ (13 passing)
  - **Complete**: GitHub backend tests ✅ (22 passing)
  - **Complete**: Vanilla Git backend tests ✅ (25 passing)
  - **Complete**: Integration tests ✅ (4 passing for backend selection)
  - **Total**: 64 unit tests across all phases
  - **Full test suite**: 5885 tests passing ✅

- [x] Ensure GitHub integration gracefully degrades when not configured
  - **Phase 4 Complete**: Backend factory has fallback logic
  - Non-fatal error handling with structured logging

## Progress Summary

✅ **ISSUE COMPLETED - ALL ACCEPTANCE CRITERIA MET**

**Phase 1 (25%)**: Interface & Contract Definition ✅ COMPLETE
**Phase 2 (50%)**: GitHub Backend Extraction ✅ COMPLETE
**Phase 3 (75%)**: Vanilla Git Backend Implementation ✅ COMPLETE
**Phase 4 (100%)**: Integration & CLI Wiring ✅ COMPLETE

### Summary of Completion

**Total Implementation Time:** ~8 hours
**Total Tests:** 5885 passing (including 64 new tests for this feature)
**Code Quality:** All pre-commit hooks passing, zero violations

**Key Deliverables:**
1. ✅ SyncBackendInterface Protocol with full contract definition
2. ✅ GitHubSyncBackend implementation with 22 unit tests
3. ✅ VanillaGitSyncBackend implementation with 25 unit tests
4. ✅ Backend factory with detection and fallback logic
5. ✅ CLI integration: `roadmap init --sync-backend=[github|git]`
6. ✅ Config persistence for backend selection
7. ✅ SELF_HOSTING.md documentation
8. ✅ 4 integration tests verifying backend selection persistence
9. ✅ Structured logging for observability and debugging
10. ✅ Graceful error handling and fallback mechanisms

**Architecture Achievement:**
- ✅ GitHub is now optional, not mandatory
- ✅ Users can choose vanilla Git hosting without GitHub dependency
- ✅ Extensible design allows future backends (GitLab, Jira, etc.)
- ✅ Non-breaking changes to existing GitHub functionality
- ✅ Full backward compatibility maintained

## Technical Design

### Backend Interface (Location: `roadmap/core/interfaces/sync_backend.py`)

```python
class SyncBackendInterface(Protocol):
    """Abstract sync backend for two-way sync operations"""

    def authenticate(self) -> bool:
        """Verify credentials and connectivity"""

    def get_issues(self) -> List[Dict]:
        """Fetch all issues from remote"""

    def push_issue(self, local_issue: Issue) -> bool:
        """Push local issue to remote"""

    def push_issues(self, local_issues: List[Issue]) -> Dict:
        """Batch push with conflict reporting"""

    def pull_issues(self) -> Dict:
        """Pull remote issues to local"""
```

### Backends to Implement

1. **GitHubSyncBackend** (refactored from current code)
   - Uses GitHub REST API
   - Supports all GitHub-specific features (labels, milestones, etc.)
   - Requires authentication token

2. **VanillaGitSyncBackend** (new)
   - Syncs through git push/pull only
   - Treats issues as files in a known directory structure
   - No external API dependency
   - Works with any Git hosting (GitHub, GitLab, Gitea, vanilla SSH, etc.)

## Implementation Plan

1. **Phase 1: Define Interface** (2-4 hrs)
   - Create `SyncBackendInterface` protocol
   - Document sync contract and error handling

2. **Phase 2: Refactor GitHub Sync** (4-6 hrs)
   - Extract current GitHub sync into `GitHubSyncBackend`
   - Update CLI to use abstracted interface
   - Ensure all tests still pass

3. **Phase 3: Implement Vanilla Git Backend** (6-8 hrs)
   - Create `VanillaGitSyncBackend`
   - Implement push/pull logic using git commands
   - Handle merge conflicts gracefully

4. **Phase 4: Integration & Testing** (2-4 hrs)
   - Update `roadmap init` to support backend selection
   - Write comprehensive tests for both backends
   - Update CLI help and documentation

## Benefits

- **Flexibility**: Teams choose their hosting solution
- **No Vendor Lock-in**: Never forced to use GitHub
- **Offline Support**: Git-only mode works fully offline
- **Compliance**: On-premise Git hosting available
- **Extensibility**: New backends can be added (GitLab, Jira, etc.)

## Implementation Status

### Files Created (Phase 1-2)

**Core Interface:**
- `roadmap/core/interfaces/sync_backend.py` - SyncBackendInterface Protocol (7 methods)
- `roadmap/core/interfaces/__init__.py` - Updated exports

**GitHub Backend:**
- `roadmap/adapters/sync/backends/github_sync_backend.py` - GitHubSyncBackend class
- `roadmap/adapters/sync/backends/__init__.py` - Module initialization
- `roadmap/adapters/sync/__init__.py` - Sync module initialization

**Tests:**
- `tests/unit/core/interfaces/test_sync_backend.py` - Interface contract tests (13 tests) ✅
- `tests/unit/adapters/sync/test_github_sync_backend.py` - GitHub backend tests (22 tests) ✅

### Pending Implementation (Phase 3-4)

**Phase 3 (Vanilla Git Backend):**
- `roadmap/adapters/sync/backends/vanilla_git_sync_backend.py` - New
- `tests/unit/adapters/sync/test_vanilla_git_sync_backend.py` - New tests

**Phase 4 (Integration & CLI):**
- Update `roadmap/adapters/cli/git/commands.py` - Accept backend parameter
- Create backend factory/selector
- Update `roadmap init` command for `--sync-backend` option
- Documentation: `docs/SELF_HOSTING.md`

## Related Issues

- Depends on: GitHub Authentication implementation (needs working sync first)
- Unblocks: Teams wanting to self-host without GitHub dependency
