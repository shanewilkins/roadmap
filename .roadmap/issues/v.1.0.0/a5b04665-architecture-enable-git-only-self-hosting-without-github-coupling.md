---
id: a5b04665
title: 'Architecture: Enable Git-Only Self-Hosting Without GitHub Coupling'
priority: high
status: in-progress
issue_type: feature
milestone: v.1.0.0
labels: []
github_issue: null
created: '2026-01-01T14:13:50.213803+00:00'
updated: '2026-01-01T15:35:12.106422+00:00'
assignee: shanewilkins
estimated_hours: 16.0
due_date: null
depends_on:
- ecf9851a
blocks: []
actual_start_date: '2026-01-01T08:23:50.620033+00:00'
actual_end_date: null
progress_percentage: 75.0
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
comments: []
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
  - **Phase 4**: Refactor orchestrator to accept backend as dependency

- [x] CLI supports selecting backend: `roadmap init --sync-backend=[github|git]`
  - **Phase 4**: Add CLI option and backend factory

- [x] Configuration stores selected backend in `.roadmap/config.json`
  - **Phase 4**: Extend config schema to include backend selection

- [x] Documentation: SELF_HOSTING.md with setup instructions
  - **Phase 4**: Create comprehensive self-hosting guide

- [x] Unit tests for both backends with interface contract tests
  - **Complete**: Interface contract tests ✅ (13 passing)
  - **Complete**: GitHub backend tests ✅ (22 passing)
  - **Complete**: Vanilla Git backend tests ✅ (25 passing)
  - **Total**: 60 unit tests across all three phases

- [ ] Ensure GitHub integration gracefully degrades when not configured
  - **Phase 4**: Add fallback and degradation logic

## Progress Summary

**Phase 1 (25%)**: Interface & Contract Definition ✅
**Phase 2 (50%)**: GitHub Backend Extraction ✅
**Phase 3 (75%)**: Vanilla Git Backend Implementation ✅
**Phase 4 (100%)**: Integration & CLI Wiring 🔄 (Next)

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
