---
id: 7d4e6e84
title: 'Align CLI with GitHub terminology: rename roadmaps to projects'
priority: medium
status: closed
issue_type: other
milestone: v.0.2.0
labels:
- priority:high
- status:done
remote_ids:
  github: 51
created: '2026-01-02T19:20:51.896529+00:00'
updated: '2026-01-06T02:03:31.454465+00:00'
assignee: shanewilkins
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
github_issue: 51
---

# Align CLI with GitHub terminology: rename roadmaps to projects

## Description

Implement Option 1: Full GitHub Alignment - rename 'roadmap roadmap' commands to 'roadmap project' to match GitHub Projects model for better sync and user understanding.

This aligns our CLI terminology with GitHub's native project management concepts, improving user intuition and enabling better integration with GitHub Projects.

## Implementation Summary

### ✅ Completed Changes

1. **CLI Command Structure**:
   - Added new `roadmap project` command group with all subcommands (create, list, update, delete, overview)
   - Maintained backwards compatibility with `roadmap roadmap` commands but added deprecation warnings
   - Updated all help text and command descriptions to use "project" terminology

2. **File Operations**:
   - New project commands operate on `.roadmap/projects/` directory (existing structure maintained)
   - Updated internal logic to use "project" terminology in outputs and messages
   - Template processing updated to handle project vs roadmap content correctly

3. **Deprecation Strategy**:
   - Legacy `roadmap roadmap` commands show clear deprecation warnings
   - Warnings direct users to use `roadmap project` instead for GitHub alignment
   - Legacy commands delegate to new project commands to ensure consistency

4. **Test Updates**:
   - Updated critical CLI tests to use new `roadmap project` commands
   - Fixed assertions to expect "Created project" instead of "Created roadmap"
   - Tests now verify project files are created in correct locations

### 🔄 Testing Results

- ✅ `roadmap project create` - Creates projects successfully
- ✅ `roadmap project list` - Lists projects in clean table format
- ✅ `roadmap project --help` - Shows proper command structure
- ⚠️ `roadmap roadmap --help` - Shows deprecation warning as intended
- ✅ CLI tests updated and passing for new commands

## Acceptance Criteria

- [x] New `roadmap project` command group implemented with all subcommands
- [x] Backward compatibility maintained with deprecation warnings
- [x] Project terminology used consistently in CLI output
- [x] File operations work correctly with existing `.roadmap/projects/` structure
- [x] Help text and documentation updated to reflect GitHub alignment
- [x] Core CLI tests updated to use new command structure
- [ ] Full test suite passes (some legacy tests still need updates)
- [ ] Documentation files updated (README, docs/)

## GitHub Alignment Benefits

- **Conceptual Clarity**: Users understand "projects" from GitHub experience
- **API Consistency**: Matches GitHub's REST/GraphQL API terminology
- **Sync Simplification**: Direct 1:1 mapping with GitHub Projects
- **Industry Standard**: Aligns with established project management terminology

## Migration Path

Users can continue using `roadmap roadmap` commands but will see deprecation warnings encouraging migration to `roadmap project`. This provides a smooth transition path while encouraging adoption of GitHub-aligned terminology.
