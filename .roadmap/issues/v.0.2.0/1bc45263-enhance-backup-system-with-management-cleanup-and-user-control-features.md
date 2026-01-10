---
id: 1bc45263
title: Enhance backup system with management, cleanup, and user control features
headline: '# Enhance backup system with management, cleanup, and user control features'
priority: medium
status: closed
issue_type: feature
milestone: v.0.2.0
labels:
- priority:medium
- status:done
- backup
- data-management
- cleanup
remote_ids:
  github: '41'
created: '2026-01-09T21:31:44.497736+00:00'
updated: '2026-01-10T00:09:39.980171+00:00'
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
github_issue: '41'
---

# Enhance backup system with management, cleanup, and user control features

## Description

Enhance the existing automatic backup system (`.roadmap/backups/`) with comprehensive management, cleanup policies, and user control features to make backup operations more efficient and user-friendly.

## Current State Analysis

The current backup system provides:
- ✅ Automatic backup creation before file modifications
- ✅ Timestamped naming (`{filename}_{YYYYMMDD_HHMMSS}.backup.md`)
- ✅ YAML recovery and validation features
- ✅ Restoration from most recent backup

## Problems to Address

### 1. **Backup Accumulation**

- No cleanup of old/stale backups leads to `.roadmap/backups/` growth
- Test-generated invalid issue backups clutter the directory
- No retention policies or size limits

### 2. **Limited User Control**

- No manual backup creation on-demand
- No interactive backup browsing/selection interface
- No way to exclude certain operations from auto-backup

### 3. **Missing Management Features**

- No backup metadata (what triggered the backup, operation context)
- No compression for space efficiency
- No backup verification or integrity checks

## Requirements

### Backup Management Commands

- `roadmap backup create [path]` - Manual backup creation
- `roadmap backup list [--filter-by-date] [--filter-by-type]` - Browse backups
- `roadmap backup restore <backup-id> [--preview]` - Interactive restoration
- `roadmap backup clean [--older-than] [--dry-run]` - Cleanup old backups
- `roadmap backup status` - Show backup directory health and statistics

### Cleanup Policies

- **Retention policies**: Keep last N backups per file
- **Age-based cleanup**: Remove backups older than X days
- **Size limits**: Compress or remove when directory exceeds threshold
- **Test artifact cleanup**: Remove test-generated invalid backups

### Enhanced Features

- **Backup compression**: Optional gzip compression for older backups
- **Backup verification**: Validate backup integrity and restorability
- **Operation context**: Track what operation triggered each backup
- **Diff preview**: Show changes before restoration
- **Batch operations**: Backup entire project directories

## Acceptance Criteria

- [ ] Add new CLI command group `roadmap backup` with subcommands
- [ ] Implement retention policy configuration (default: keep last 10 per file)
- [ ] Add automatic cleanup on backup creation (remove old backups)
- [ ] Implement manual backup creation for any file or directory
- [ ] Add backup listing with filtering (by date, type, size)
- [ ] Create interactive restoration with diff preview
- [ ] Add backup directory statistics and health reporting
- [ ] Implement compression option for space efficiency
- [ ] Add configuration for backup policies in `.roadmap/config.yaml`
- [ ] Clean up existing test-generated invalid issue backups
- [ ] Add backup verification and integrity checking
- [ ] Support project-wide backup operations

## Technical Implementation Notes

- Extend existing `YAMLRecoveryManager` class with new methods
- Add backup metadata storage (JSON sidecar files or embedded metadata)
- Use configurable retention policies via settings
- Implement background cleanup on CLI operations
- Add backup compression using gzip for older files
- Create backup index for faster listing and searching

## Configuration Example

```yaml
backup:
  retention:
    max_backups_per_file: 10
    max_age_days: 30
  compression:
    enabled: true
    compress_after_days: 7
  cleanup:
    auto_cleanup: true
    cleanup_test_artifacts: true

```text
