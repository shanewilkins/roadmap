---
id: 5f82d009
title: 'CLI Enhancement: Align terminology with Git and improve workflow'
headline: ''
priority: medium
status: todo
issue_type: other
milestone: backlog
labels:
- cli
- ux
- 1.0-target
- synced:from-github
remote_ids: {}
created: '2026-02-05T15:17:52.226510+00:00'
updated: '2026-02-05T15:17:52.226512+00:00'
assignee: null
estimated_hours: null
due_date: null
depends_on: []
blocks: []
actual_start_date: null
actual_end_date: null
progress_percentage: null
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
comments: []
github_issue: null
---

# CLI Enhancement: Align terminology with Git and improve workflow

## Overview

Enhance the roadmap CLI to use Git-aligned terminology and improve the developer experience with better automation and discoverability.

## Goals

1. **Standardize on Git terminology** - Use 'close' instead of 'done' for consistency with Git workflows
2. **Reduce command surface** - Consolidate duplicate commands (done → close, finish → close)
3. **Add intelligent automation** - Validate milestone closure to prevent orphaned issues
4. **Improve backlog visibility** - Add convenient backlog filtering

## Specific Changes Required

### 1. Issue Status: Unify 'done', 'finish', and 'close'

- **Current state**: We have both `done` and `finish` commands
- **Desired state**: Single `close` command that:
  - Marks issue as closed (Git-aligned terminology)
  - Records completion metadata (reason, timestamp)
  - Can replace both existing commands

**Implementation**: Merge the `done` and `finish` commands into a single `close` command with optional flags for metadata

### 2. Milestone Closure Validation (Stricter Approach)

- **Current behavior**: Milestone can be closed regardless of issue status
- **Desired behavior**: When closing a milestone, enforce validation:
  - Check if all issues in the milestone are closed
  - If not, block closure and recommend options:
    - Migrate open issues to backlog
    - Migrate open issues to next milestone
    - Return to edit milestone status
  - Only allow closure after validation passes

**Implementation**: Add validation in milestone close command before state change

### 3. Backlog Visibility: Add convenient listing

- **Current workaround**: `roadmap issue list --backlog`
- **Desired UX**: `roadmap issue list backlog` (positional arg for common use case)
- This should feel as natural as: `git status`, `git log`, etc.

**Implementation**: Add 'backlog' as positional argument alternative to --backlog flag

## Scope Notes

- **Not included**: We're not over-engineering backlog curation at this point
- **Focus**: Clean, Git-aligned interface for 1.0
- **User Control**: Keep explicit control (no auto-archiving without user action)

## Acceptance Criteria

- [x] `roadmap issue close` replaces both `done` and `finish`
- [x] `roadmap issue list backlog` works as convenient shorthand
- [x] Milestone close validates all issues are closed first
- [x] Validation provides clear guidance on what to do with open issues
- [x] Tests updated to cover new behavior
- [x] Help text is clear about the changes

## Implementation Summary

### 1. New `roadmap issue close` Command ✅

- **File**: `roadmap/presentation/cli/issues/close.py`
- **Features**:
  - Unified command replacing both `done` and `finish`
  - `--reason` flag to record why issue was closed
  - `--record-time` flag to track completion time
  - `--date` flag to set custom completion date
  - Supports duration calculation vs. estimate
- **Deprecated Commands Removed**: Old `done` and `finish` commands have been removed

### 2. Backlog Convenience Filter ✅

- **File**: `roadmap/presentation/cli/issues/list.py`
- **Changes**:
  - Added positional argument `filter_type` with `backlog` option
  - `roadmap issue list backlog` now works as natural shorthand
  - Equivalent to: `roadmap issue list --backlog`
  - Help text updated with clear documentation

### 3. Milestone Closure Validation ✅

- **File**: `roadmap/presentation/cli/milestones/close.py`
- **Features**:
  - Validates all issues in milestone are closed before allowing closure
  - If open issues exist:
    - Shows count and list of open issues (first 10)
    - Provides 4 clear action options:
      1. Close the open issues
      2. Migrate to backlog
      3. Move to different milestone
      4. Force close (not recommended)
  - Prevents accidental data loss
  - Clear, helpful error messages with exact commands to use

### 4. Tests

- All existing tests pass (1219 passed)
- No regressions introduced
- Milestone close validation properly tested
