---
id: e5603e6a
title: Add view commands for issues, milestones, and projects
priority: high
status: done
issue_type: other
milestone: v.0.5.0
labels: []
github_issue: null
created: '2025-11-21T17:42:18.538326+00:00'
updated: '2025-11-21T17:46:58.316726+00:00'
assignee: shanewilkins
estimated_hours: 6.0
due_date: null
depends_on: []
blocks: []
actual_start_date: '2025-11-21T11:42:49.528904+00:00'
actual_end_date: null
progress_percentage: 100.0
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
---

# Add view commands for issues, milestones, and projects

## Description

Implement `view` commands for issues, milestones, and projects to provide detailed, formatted inspection of individual items. This addresses a common user need discovered during development where attempting `roadmap issue view <id>` resulted in "No such command" errors.

**Current Problem:**
- Users need to open markdown files directly to see full issue/milestone/project details
- The `list` commands only show tabular summaries without full context
- No quick way to inspect dependencies, git branches, acceptance criteria, or full descriptions

**Solution:**
Implement three new view commands following CRUD patterns (view = Read operation):
1. `roadmap issue view <issue_id>` - Display full issue details
2. `roadmap milestone view <milestone_name>` - Display milestone details with progress
3. `roadmap project view <project_id>` - Display project details with milestones

**Benefits:**
- Quick inspection without opening files or parsing markdown
- Consistent with CLI UX patterns (list = overview, view = detail)
- Helpful for debugging (dependencies, git branches, timestamps)
- Better user experience for daily workflows

## Acceptance Criteria

### Issue View Command

- [ ] Create `roadmap/presentation/cli/issues/view.py` with `view_issue` command
- [ ] Accept issue ID as argument (required)
- [ ] Display formatted output using Rich panels/tables with sections:
  - Header: ID, title, status badge, priority, type
  - Metadata: Assignee, milestone, created/updated dates
  - Timeline: Estimated/actual hours, progress percentage, due date
  - Dependencies: depends_on and blocks lists
  - Git integration: branches, commits
  - Description section (full markdown)
  - Acceptance criteria checklist
- [ ] Handle missing issue ID with helpful error message
- [ ] Register command in `roadmap/presentation/cli/issues/__init__.py`

### Milestone View Command

- [ ] Create `roadmap/presentation/cli/milestones/view.py` with `view_milestone` command
- [ ] Accept milestone name as argument (required)
- [ ] Display formatted output with sections:
  - Header: Name, status badge, due date
  - Progress: X/Y issues complete, percentage, progress bar
  - Statistics: Total estimated time, breakdown by status
  - Issues table: Mini-table of issues in milestone (ID, title, status, progress)
  - Description section (full markdown)
  - Goals/success criteria
- [ ] Show overdue warning if milestone past due date
- [ ] Handle missing milestone with helpful error message
- [ ] Register command in `roadmap/presentation/cli/milestones/__init__.py`

### Project View Command

- [ ] Create `roadmap/presentation/cli/projects/view.py` with `view_project` command
- [ ] Accept project ID as argument (required)
- [ ] Display formatted output with sections:
  - Header: ID, name, status, priority
  - Metadata: Owner, start/end dates, estimated/actual hours
  - Milestones: Table of associated milestones with progress
  - Objectives checklist
  - Description section
- [ ] Handle missing project with helpful error message
- [ ] Register command in `roadmap/presentation/cli/projects/__init__.py`

### Testing & Documentation

- [ ] Add integration tests for all three view commands
- [ ] Test error handling (missing items, invalid IDs)
- [ ] Update CLI help documentation
- [ ] Add examples to README or user guide
- [ ] Verify commands work with real roadmap data
