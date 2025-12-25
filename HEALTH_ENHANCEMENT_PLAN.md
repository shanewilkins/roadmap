# Phase 5: Health Command Enhancement Implementation Plan

**Tracked in Issue:** `#b3343b67` (roadmap issue list view)

## Executive Summary
Consolidate health commands, add detailed diagnostics, implement hierarchical JSON output, and create an automated health fix command with dry-run capability.

## Current State Analysis

### Existing Checks (14 total)
**Infrastructure Checks:**
- roadmap_directory, state_file, issues_directory, milestones_directory
- git_repository, database_integrity

**Data Quality Checks:**
- duplicate_issues, folder_structure, data_integrity, orphaned_issues
- comment_integrity

**Informational Checks (never degrade health):**
- old_backups, archivable_issues, archivable_milestones

### Current Commands (REDUNDANT)
- `roadmap health` → runs checks (default)
- `roadmap health check` → same as above (redundant subcommand)
- `roadmap health scan` → entity-level diagnostics (different purpose)

## Proposed Architecture

### 1. Command Structure Consolidation
```
roadmap health                          # Default: run all checks
  ├── [no subcommand]                   # Show summary
  ├── --details                         # Show details + recommendations
  ├── --format json                     # Output as JSON
  ├── scan                              # KEEP: entity-level diagnostics (different tool)
  └── fix                               # NEW: auto-fix issues
        ├── --dry-run                   # Preview what would be fixed
        ├── --fix-type {all|backup|duplicate|orphaned|folder}
        └── --force                     # Skip confirmations

Remove: `health check` subcommand (make `roadmap health` do everything)
```

### 2. Enhanced Health Check Output Structure

#### Plain Text (--details flag)
```
✅ Health Check Results

Infrastructure:
  ✅ roadmap_directory    Accessible
  ✅ state_file           Valid (50MB)
  ✅ issues_directory     Accessible

Data Quality:
  ⚠️  duplicate_issues    Found 2 duplicates in recent issues
      → Fix: roadmap health fix --fix-type duplicate --dry-run
  ❌ orphaned_issues      Found 3 issues without milestones
      → Fix: roadmap health fix --fix-type orphaned --dry-run

Maintenance:
  ℹ️  old_backups         4 backups older than 90 days (not in use)
  ℹ️  archivable_issues   12 closed issues ready to archive

Overall: DEGRADED (1 error, 1 warning, see details above)
```

#### JSON (--format json)
```json
{
  "status": "degraded",
  "timestamp": "2025-12-25T...",
  "summary": {
    "healthy": 11,
    "degraded": 1,
    "unhealthy": 1,
    "total": 13
  },
  "checks": {
    "roadmap_directory": {
      "status": "healthy",
      "message": "Accessible",
      "severity": "critical",
      "fixable": false
    },
    "duplicate_issues": {
      "status": "degraded",
      "message": "Found 2 duplicates",
      "severity": "high",
      "fixable": true,
      "affected_entities": ["issue_5", "issue_12"],
      "fix_command": "roadmap health fix --fix-type duplicate --dry-run"
    },
    "orphaned_issues": {
      "status": "unhealthy",
      "message": "3 issues have no milestone",
      "severity": "high",
      "fixable": true,
      "affected_entities": ["issue_1", "issue_3", "issue_7"],
      "fix_command": "roadmap health fix --fix-type orphaned --dry-run"
    }
  },
  "recommendations": [
    {
      "priority": 1,
      "type": "critical",
      "message": "Fix orphaned issues - some entities are inconsistent",
      "action": "roadmap health fix --fix-type orphaned --dry-run"
    },
    {
      "priority": 2,
      "type": "high",
      "message": "Deduplicate issues - found 2 possible duplicates",
      "action": "roadmap health fix --fix-type duplicate --dry-run"
    },
    {
      "priority": 3,
      "type": "informational",
      "message": "Clean up old backups - 4 backups > 90 days old",
      "action": "roadmap health fix --fix-type backup --dry-run"
    }
  ]
}
```

### 3. Health Fix Command Design

#### Fixable Issues Categories

| Issue Type | Detection | Fix Strategy | Safety | Priority |
|-----------|-----------|--------------|--------|----------|
| **old_backups** | Backups >90 days old | Delete backup files | ✅ Safe | Low |
| **duplicate_issues** | Same title, same status | Merge into one (keep older) | ⚠️ Review | High |
| **orphaned_issues** | Issues with null milestones | Assign to "Backlog" milestone | ⚠️ Review | High |
| **folder_structure** | Issues in wrong folders | Move to correct folder | ✅ Safe | Medium |
| **corrupted_comments** | Malformed comment JSON | Remove/sanitize | ⚠️ Review | Medium |

#### Dry-Run Output Format
```
🔍 Health Fix Preview (--dry-run)

Would fix 6 issues:

[1] OLD BACKUPS (Safe to remove)
    Would delete: .roadmap/backups/backup_2024-01-15.tar.gz (2.3MB)
    Would delete: .roadmap/backups/backup_2024-02-10.tar.gz (2.1MB)
    Savings: 4.4MB

[2] DUPLICATE ISSUES (Review recommended)
    Issue #5 "Create user auth"  (created 2024-01-10)
    Issue #12 "Create user auth" (created 2024-01-15)
    → Would keep: #5, merge #12 into it, update all references

[3] ORPHANED ISSUES (Review recommended)
    Issue #1 "Setup database" → would assign to "Backlog"
    Issue #3 "API design"     → would assign to "Backlog"
    Issue #7 "Testing plan"   → would assign to "Backlog"

To apply fixes: roadmap health fix --fix-type all --force
To apply specific: roadmap health fix --fix-type duplicate --force
```

#### Fix Command Behavior
- `--dry-run` (default): Show preview, don't modify
- `--force`: Apply all fixes without prompts
- `--fix-type`: Fix only specific categories (backup|duplicate|orphaned|folder|all)

### 4. Implementation Phases

#### Phase 5A: Enhanced Health Check Output
**Files to create/modify:**
1. [roadmap/adapters/cli/health/health_enhancer.py](NEW) - Detailed check analysis
2. [roadmap/adapters/cli/health/formatters.py](MODIFY) - Add hierarchical JSON formatter
3. [roadmap/adapters/cli/status.py](MODIFY) - Add --details, --format json flags

**Tasks:**
- Create HealthEnhancer service to add details to checks
- Map each check to fixable issues + recommended actions
- Implement JSON formatter with hierarchical structure
- Update check_health command with new flags
- Remove `check` subcommand (make default behavior)

#### Phase 5B: Health Fix Infrastructure
**Files to create/modify:**
1. [roadmap/core/services/health_fixer.py](NEW) - Fix orchestrator
2. [roadmap/core/services/fixers/backup_fixer.py](NEW) - Old backups cleanup
3. [roadmap/core/services/fixers/duplicate_fixer.py](NEW) - Issue deduplication
4. [roadmap/core/services/fixers/orphaned_fixer.py](NEW) - Missing milestone assignment
5. [roadmap/core/services/fixers/folder_fixer.py](NEW) - Folder structure repair
6. [roadmap/adapters/cli/status.py](MODIFY) - Add `fix` subcommand

**Tasks:**
- Create HealthFixer orchestrator (delegates to specific fixers)
- Implement each fixer with rollback capability
- Add dry-run mode to all fixers
- Create fix preview output formatter
- Wire fix command to CLI with --dry-run, --fix-type, --force flags

#### Phase 5C: Testing & Validation
**Files to create:**
1. [tests/unit/services/test_health_fixer.py](NEW) - Fixer logic tests
2. [tests/integration/test_health_fix_command.py](NEW) - End-to-end fix tests
3. [tests/unit/cli/test_health_command_output.py](NEW) - Output format tests

**Tasks:**
- Unit tests for each fixer (dry-run behavior, edge cases)
- Integration tests for full fix workflow
- JSON output format validation
- Error recovery scenarios

## Key Design Decisions

### 1. Fixable vs Informational
- **Fixable with High Confidence**: old_backups, folder_structure
- **Fixable with Review**: duplicate_issues, orphaned_issues, corrupted_comments
- **Informational Only**: archivable_issues, archivable_milestones (users decide)

### 2. Safety First
- All fixes default to `--dry-run` (preview)
- Require explicit `--force` to apply
- Maintain backups before major fixes
- Log all changes for audit trail

### 3. JSON Structure
- Hierarchical: checks → affected_entities → fix_commands
- Recommendations separate from checks (actionable guidance)
- Include severity, fixability, and direct fix command for each issue

### 4. Command Consolidation
- `roadmap health` = infrastructure + data quality checks
- `roadmap health scan` = entity-level diagnostics (keep separate)
- Remove `roadmap health check` (redundant)

## Success Criteria

✅ **Feature Complete:**
- All 14 checks show details with --details flag
- JSON output with hierarchical structure and recommendations
- Health fix command with --dry-run, --fix-type, --force flags
- At least 5 fixable issue types automated

✅ **Code Quality:**
- All new code tested (unit + integration)
- No brittle regex patterns in output parsing
- Clean separation between check/fix concerns
- Error handling for all failure scenarios

✅ **User Experience:**
- Clear, actionable output from `health` command
- Preview first, apply second (--dry-run default)
- Explicit fix commands suggested in output
- Dry-run shows exactly what would change

## Timeline Estimate
- **Phase 5A** (Enhanced output): 4-6 hours
- **Phase 5B** (Fix infrastructure): 6-8 hours
- **Phase 5C** (Testing & validation): 4-6 hours
- **Total**: 14-20 hours

## Open Questions for Approval
1. Should `roadmap health fix` also include archivable items, or keep those manual?
2. For duplicate issue merging, preserve issue #1 or #2? (suggestion: older/lower ID)
3. For orphaned issue assignment, create new "Backlog" milestone if missing?
4. Should fix operations generate an archive/snapshot before applying?
