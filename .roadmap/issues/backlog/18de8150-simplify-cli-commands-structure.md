---
id: 18de8150
title: Simplify CLI Commands Structure
headline: ''
priority: medium
status: todo
issue_type: other
milestone: backlog
labels:
- synced:from-github
remote_ids: {}
created: '2026-02-05T15:17:51.826454+00:00'
updated: '2026-02-05T15:17:51.826454+00:00'
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

## Overview

## Overview

Refactor CLI commands across issues, milestones, and projects to achieve consistency, remove redundancy, and align with GitHub naming conventions. The goal is to establish a clean, predictable command structure with:

1. Consistent CRUD operations across all entity types (create, read, update, delete, archive, restore)
2. Elimination of redundant commands (done.py, finish.py, deprecated wrappers)
3. Strategic command consolidation using a hybrid approach: monolithic `update` command with convenience wrappers for common operations
4. GitHub alignment in terminology and field naming
5. Finalized API foundation for v1.0 release

### Core Principle: Update-Centric Architecture

All state changes route through a unified `update` command, with convenience wrappers (close, block, start, etc.) as syntactic sugar that internally call `update` with appropriate flags. This reduces code duplication while maintaining excellent UX.

## Description

Refactor CLI commands across issues, milestones, and projects to achieve consistency, remove redundancy, and align with GitHub naming conventions. The goal is to establish a clean, predictable command structure with:

1. Consistent CRUD operations across all entity types (create, read, update, delete, archive, restore)
2. Elimination of redundant commands (done.py, finish.py, deprecated wrappers)
3. Strategic command consolidation using a hybrid approach: monolithic `update` command with convenience wrappers for common operations
4. GitHub alignment in terminology and field naming
5. Finalized API foundation for v1.0 release

### Core Principle: Update-Centric Architecture

All state changes route through a unified `update` command, with convenience wrappers (close, block, start, etc.) as syntactic sugar that internally call `update` with appropriate flags. This reduces code duplication while maintaining excellent UX.

## Architecture

### CRUD Pattern (All Entity Types)

All entities (issues, milestones, projects) support:

- **create** - Create new entity
- **read** - `list` and `view` commands for retrieval
- **update** - Unified command for any field modifications
- **delete** - Hard delete for orphaned/malformed entities
- **archive** - Soft delete (standard workflow)
- **restore** - Unarchive/recover archived entities

### Issue Commands

**Core CRUD:**

- `roadmap issue create` - Create new issue
- `roadmap issue list` - List issues with filters
- `roadmap issue view <ID>` - View issue details
- `roadmap issue update <ID> [OPTIONS]` - Update any field (status, priority, assignee, due_date, etc.)
- `roadmap issue delete <ID>` - Hard delete (malformed/duplicates)
- `roadmap issue archive <ID>` - Soft delete (standard)
- `roadmap issue restore <ID>` - Restore archived issue

**Convenience Wrappers (call update internally):**

- `roadmap issue close <ID>` → `update <ID> --status closed`
- `roadmap issue start <ID>` → `update <ID> --status in-progress --actual-start-date now`
- `roadmap issue block <ID> --reason TEXT` → `update <ID> --status blocked`
- `roadmap issue unblock <ID>` → `update <ID> --status todo`
- `roadmap issue progress <ID> <PERCENT>` → `update <ID> --progress <PERCENT>`
- `roadmap issue assign <ID> <USER>` → `update <ID> --assignee <USER>`

**Queries & Dependencies:**

- `roadmap issue deps <ID>` - Manage dependencies (complex enough to keep separate)

**Items to Decide Later:**

- Kanban visualization (view feature, not CRUD)

**Items to Remove:**

- ❌ `done.py` - Redundant with `close`
- ❌ `finish.py` - Redundant with `close`

### Milestone Commands

**Core CRUD:**

- `roadmap milestone create` - Create new milestone
- `roadmap milestone list` - List milestones with filters
- `roadmap milestone view <ID>` - View milestone details
- `roadmap milestone update <ID> [OPTIONS]` - Update any field
- `roadmap milestone delete <ID>` - Hard delete
- `roadmap milestone archive <ID>` - Soft delete
- `roadmap milestone restore <ID>` - Restore archived

**Convenience Wrappers:**

- `roadmap milestone close <ID>` → `update <ID> --status closed`

**Special Operations:**

- `roadmap milestone kanban <ID>` - Keep (visualization, not CRUD)
- `roadmap milestone assign <ID> --issue ISSUE_ID` - Keep or refactor to query?
- `roadmap milestone recalculate` - Keep (batch calculation, not CRUD)

### Project Commands

**Core CRUD:**

- `roadmap project create` - Create new project
- `roadmap project list` - List projects with filters
- `roadmap project view <ID>` - View project details
- `roadmap project update <ID> [OPTIONS]` - Update any field
- `roadmap project delete <ID>` - Hard delete
- `roadmap project archive <ID>` - Soft delete
- `roadmap project restore <ID>` - Restore archived

## GitHub Alignment

**Terminology (no changes needed):**

- `title` - matches GitHub
- `status` / `state` - "open", "closed", "draft" align with GitHub
- `priority` - custom field (GitHub: custom fields)
- `labels` - matches GitHub
- `assignee` - matches GitHub
- `milestone` - matches GitHub

**Status Values:**

- Issues: `todo`, `in-progress`, `blocked`, `closed`
- Milestones: `open`, `closed`
- Projects: `open`, `closed`, `archived`

## Acceptance Criteria

- [ ] Remove `done.py` and `finish.py` - consolidate functionality into `close` command
- [ ] Refactor `close`, `block`, `unblock`, `progress`, `start`, and `assign` commands as thin wrappers around `update`
- [ ] Verify all convenience wrappers pass existing tests without modification to test code
- [ ] Update CLI help text to show proper usage and routing to `update`
- [ ] Ensure `update` command handles all field modifications consistently
- [ ] Remove deprecated command registrations from `__init__.py` files
- [ ] Add integration tests verifying wrapper commands work identically to direct `update` calls
- [ ] Document the wrapper pattern for future command additions
- [ ] Verify all 1300+ tests pass after refactoring
- [ ] Create or update CLI documentation reflecting simplified command structure

## Implementation Notes

### Wrapper Pattern Example

Instead of duplicate implementations, wrappers delegate to update:

```python
@click.command("close")
@click.argument("issue_id")
@click.pass_context
def close_issue(ctx, issue_id):
    """Close an issue (syntactic sugar for: issue update --status closed)"""
    # Delegate to update with status flag
    ctx.invoke(update_issue, issue_id=issue_id, status="closed")
```

This ensures:

- Single source of truth for business logic
- Consistent error handling
- No test duplication
- Easy to add more wrappers

### Consolidation Scope

**Phase 1 (this issue):**

- Remove done.py, finish.py
- Refactor close, block, unblock, progress, start as wrappers
- Update command registration

**Phase 2 (future):**

- Evaluate kanban visualization approach
- Consider milestone-specific commands
- Assess deps complexity

## Related Issues

- e8445ada: Eliminated redundant sync functions (database layer)
- This issue: Eliminate redundant CLI commands (API layer)
