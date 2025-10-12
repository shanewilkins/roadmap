---
id: ac64f265
title: Add project level template
priority: medium
status: done
issue_type: feature
milestone: ''
labels: []
github_issue: 4
created: '2025-10-11T19:03:58.235408'
updated: '2025-10-11T20:03:40.683135'
assignee: ''
estimated_hours: 2.0
depends_on: []
blocks: []
actual_start_date: '2025-10-11T19:07:12.400843'
actual_end_date: '2025-10-11T19:21:13.470728'
progress_percentage: 100.0
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
---

# Add project level template

## Description

Implement a comprehensive project-level template system that allows users to create and manage projects with proper metadata tracking, timeline management, and milestone integration.

## Acceptance Criteria

- [x] Create project template file with comprehensive metadata structure
- [x] Update core module to generate project template during initialization 
- [x] Add CLI command group for project management
- [x] Implement project creation command with full option support
- [x] Support multiple milestones per project
- [x] Include timeline tracking (start date, target end date, estimated hours)
- [x] Generate unique project IDs and proper file naming
- [x] Test template creation and project creation functionality

## Implementation Details

### ✅ Project Template Structure
- **File:** `.roadmap/templates/project.md`
- **Metadata:** ID, name, description, status, priority, owner, dates, milestones, hours
- **Timeline Tracking:** Start date, target end date, actual end date, estimated/actual hours
- **Milestone Integration:** Support for multiple milestones with links

### ✅ Core Module Integration
- **File:** `roadmap/core.py`
- **Function:** `_create_default_templates()` enhanced to include project template
- **Security:** Uses `create_secure_file` context manager for safe file creation

### ✅ CLI Implementation
- **Command Group:** `roadmap project` with subcommands
- **Create Command:** `roadmap project create [NAME]` with comprehensive options
- **Options:** description, owner, priority, start-date, target-end-date, estimated-hours, milestones
- **File Structure:** Creates `.roadmap/projects/` directory with pattern `{id}-{name}.md`

### ✅ Testing
- **Updated:** `tests/test_core.py` to verify project template creation
- **Verified:** Project creation functionality with real test cases

## Usage Examples

```bash
# Basic project creation
roadmap project create "My Project"

# Full project with all options  
roadmap project create "Advanced Project" \
  --description "Complex project with milestones" \
  --owner "johnsmith" \
  --priority "high" \
  --start-date "2025-01-01" \
  --target-end-date "2025-03-31" \
  --estimated-hours 120.0 \
  --milestones "Phase 1" \
  --milestones "Phase 2" \
  --milestones "Launch"
```

---
*Created by roadmap CLI*
Assignee: @shanewilkins