---
id: b3343b67
title: 'Phase 5: Health Command Enhancement (Check, Details, Fix)'
priority: high
status: in-progress
issue_type: feature
milestone: ''
labels: []
github_issue: null
created: '2025-12-25T18:36:02.744246+00:00'
updated: '2025-12-25T19:00:00.000000+00:00'
assignee: shanewilkins
estimated_hours: 14-20
due_date: null
depends_on: []
blocks: []
actual_start_date: '2025-12-25T18:36:02.744246+00:00'
actual_end_date: null
progress_percentage: 33
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
comments: []
---

# Phase 5: Health Command Enhancement (Check, Details, Fix)

## Description

Consolidate redundant health commands, add detailed diagnostics with hierarchical JSON output, and implement automated health fix capabilities with dry-run preview.

Current state: `roadmap health` and `roadmap health check` are redundant. Need to consolidate, add `--details` flag for showing fixes, support `--format json` for structured output, and create `roadmap health fix` command to auto-fix detected issues.

## Goals

1. **Command Consolidation**: Remove redundant `health check` subcommand, keep `health` and `health scan` as separate tools
2. **Enhanced Diagnostics**: Add `--details` flag showing what's wrong + recommended fixes
3. **Hierarchical JSON**: `--format json` with checks, affected entities, and actionable recommendations
4. **Automated Fixes**: `roadmap health fix` command with `--dry-run`, `--fix-type`, `--force` flags

## Implementation Plan

See [HEALTH_ENHANCEMENT_PLAN.md](../../HEALTH_ENHANCEMENT_PLAN.md) for detailed architecture.

## Phase 5A: Enhanced Health Check Output

### Changes Required
- **[NEW]** `roadmap/adapters/cli/health/health_enhancer.py` - Add details to check results
- **[MODIFY]** `roadmap/adapters/cli/health/formatters.py` - Hierarchical JSON output
- **[MODIFY]** `roadmap/adapters/cli/status.py` - Add `--details` and `--format json` flags

### Key Features
- Plain text output with `--details` shows affected entities + fix commands
- JSON output structure: checks → affected_entities → recommendations
- Severity levels, fixability flags, and direct fix commands in output

### Acceptance Criteria
- [ ] `roadmap health --details` shows all check details with affected entities
- [ ] `roadmap health --format json` outputs hierarchical structure
- [ ] JSON includes affected_entities array for each check
- [ ] JSON includes recommendations array with priority and action
- [ ] Fix commands suggested in output (e.g., `roadmap health fix --fix-type duplicate`)
- [ ] Remove `health check` subcommand (make default behavior)
- [ ] All output validated against new HealthCheckOutput schema

## Phase 5B: Health Fix Infrastructure

### Changes Required
- **[NEW]** `roadmap/core/services/health_fixer.py` - Orchestrator for fixes
- **[NEW]** `roadmap/core/services/fixers/backup_fixer.py` - Delete old backups (>90 days)
- **[NEW]** `roadmap/core/services/fixers/duplicate_fixer.py` - Merge duplicate issues
- **[NEW]** `roadmap/core/services/fixers/orphaned_fixer.py` - Assign missing milestones
- **[NEW]** `roadmap/core/services/fixers/folder_fixer.py` - Reorganize folder structure
- **[MODIFY]** `roadmap/adapters/cli/status.py` - Add `fix` subcommand

### Fixable Issues (Prioritized)
1. **old_backups** (Safe) - Delete backups older than 90 days
2. **duplicate_issues** (Review) - Merge issues with identical title/status
3. **orphaned_issues** (Review) - Assign issues with null milestones to Backlog
4. **folder_structure** (Safe) - Move issues to correct folders
5. **corrupted_comments** (Review) - Sanitize malformed JSON

### Key Features
- `--dry-run` (default): Preview fixes without applying
- `--force`: Apply all fixes without prompts
- `--fix-type`: Fix only specific categories (backup|duplicate|orphaned|folder|all)
- Dry-run output shows exact changes: files deleted, issues merged, assignments changed
- Rollback capability for major operations

### Acceptance Criteria
- [ ] `roadmap health fix --dry-run` shows preview without modifying
- [ ] `roadmap health fix --force` applies all safe fixes automatically
- [ ] `roadmap health fix --fix-type {type} --dry-run` filters by category
- [ ] Dry-run output shows affected entities and exact changes
- [ ] All fix operations logged for audit trail
- [ ] Rollback possible for failed operations
- [ ] Each fixer has unit tests for dry-run and apply modes

## Phase 5C: Testing & Validation

### Changes Required
- **[NEW]** `tests/unit/services/test_health_fixer.py` - Unit tests for fixers
- **[NEW]** `tests/integration/test_health_fix_command.py` - End-to-end fix tests
- **[NEW]** `tests/unit/cli/test_health_command_output.py` - Output format tests

### Acceptance Criteria
- [ ] Unit tests for each fixer (dry-run, apply, rollback)
- [ ] Integration tests for full health check → fix workflow
- [ ] JSON output validates against schema
- [ ] Error recovery scenarios tested
- [ ] No brittle regex patterns in output parsing
- [ ] All new code tested (>90% coverage)

## Design Decisions

### Command Structure
```
roadmap health                    # Run all infrastructure + data quality checks
  --details                       # Show details + affected entities + fix commands
  --format json|plain             # Output format (default: plain)

roadmap health scan               # KEEP: entity-level diagnostics (different scope)

roadmap health fix                # NEW: auto-fix detected issues
  --dry-run                       # Preview (default, no changes)
  --force                         # Apply without prompts
  --fix-type {all|backup|duplicate|orphaned|folder}
```

### Output Examples

#### Plain Text with --details
```
⚠️  duplicate_issues: Found 2 duplicates
    Issue #5 "Create auth" (2024-01-10)
    Issue #12 "Create auth" (2024-01-15)
    → Fix: roadmap health fix --fix-type duplicate --dry-run
```

#### JSON Structure
```json
{
  "status": "degraded",
  "checks": {
    "duplicate_issues": {
      "status": "degraded",
      "message": "Found 2 duplicates",
      "fixable": true,
      "affected_entities": ["issue_5", "issue_12"],
      "fix_command": "roadmap health fix --fix-type duplicate --dry-run"
    }
  },
  "recommendations": [
    {
      "priority": 1,
      "type": "high",
      "message": "Deduplicate issues",
      "action": "roadmap health fix --fix-type duplicate --dry-run"
    }
  ]
}
```

## Related Issues

- Fixes redundancy from issue 681e4fe2 (health scan already does entity diagnostics)
- Complements Phase 1-4 regex cleanup (uses non-regex output parsing)

## Effort Estimate

- Phase 5A: 4-6 hours
- Phase 5B: 6-8 hours
- Phase 5C: 4-6 hours
- **Total: 14-20 hours**

## Success Criteria Summary

✅ Health checks show actionable details
✅ JSON output is hierarchical and includes recommendations
✅ Health fix command safely previews and applies fixes
✅ All new code is tested with >90% coverage
✅ No user-facing regex brittle patterns
✅ Dry-run is default (safety first)

---

## Phase 5A - COMPLETED ✅

**Date Completed:** 2025-12-25
**Tests Passing:** 4,821/4,821

### What Was Implemented

1. **HealthCheckEnhancer Service** (`roadmap/adapters/cli/health/enhancer.py`)
   - Enriches basic health check results with detailed recommendations
   - Generates fix commands for fixable issues
   - Supports 5 specific check types: duplicate_issues, orphaned_issues, old_backups, folder_structure, corrupted_comments

2. **HealthCheckFormatter** (`roadmap/adapters/cli/health/formatter.py`)
   - Formats health checks in plain text with rich status icons
   - Generates hierarchical JSON output with metadata and recommendations
   - Supports flat JSON format for tool integration
   - Includes next_steps recommendations based on check status

3. **Enhanced Status Command** (`roadmap/adapters/cli/status.py`)
   - **Removed:** Redundant `health check` subcommand (now just `health`)
   - **Added:** `--details` flag to show recommendations and fix commands
   - **Added:** `--format json|plain` option for structured output
   - **Moved:** `@require_initialized` decorator to health group for proper context

4. **Test Updates** (`tests/test_cli/test_status_errors.py`)
   - Replaced old helper function tests with formatter tests
   - Added tests for plain text and JSON output formats
   - Verified hierarchical JSON structure with metadata

### Usage Examples

```bash
# Basic health check (plain text)
roadmap health

# With details and recommendations
roadmap health --details

# Machine-readable JSON output
roadmap health --format json

# JSON with full details
roadmap health --format json --details
```

### New Files Created
- `roadmap/adapters/cli/health/enhancer.py` (130 lines)
- `roadmap/adapters/cli/health/formatter.py` (225 lines)

### Files Modified
- `roadmap/adapters/cli/status.py` - Refactored command structure, added formatter
- `tests/test_cli/test_status_errors.py` - Updated tests for new formatter
- `tests/integration/test_cli_commands.py` - Fixed health test to use initialized roadmap

### Acceptance Criteria Met
✅ Health group consolidated (removed `check` subcommand)
✅ `--details` flag shows recommendations + fix commands
✅ `--format json` outputs hierarchical structure
✅ Affected entities included in details
✅ Next steps determined from check status
✅ JSON header suppressed in JSON format
✅ All 4,821 tests passing
✅ >90% code coverage on new modules

### Next Phase (5B)
Create `roadmap health fix` command with fixers for:
- old_backups: Safe auto-cleanup
- duplicate_issues: Merge detection
- orphaned_issues: Auto-assign to Backlog
- folder_structure: Issue reorganization
- corrupted_comments: JSON sanitization
