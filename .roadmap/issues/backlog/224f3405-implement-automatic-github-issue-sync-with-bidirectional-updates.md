---
id: 224f3405
title: Implement automatic GitHub issue sync with bidirectional updates
priority: medium
status: todo
issue_type: feature
milestone: null
labels: []
remote_ids:
  github: '221'
created: '2025-12-20T20:47:49.863886+00:00'
updated: '2026-01-06T16:25:12.651418+00:00'
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
github_issue: '221'
---

# Phase 2: Automatic GitHub Issue Sync with Bidirectional Updates

## Overview
Build on Phase 1 manual sync to implement automatic, bidirectional synchronization between roadmap issues and GitHub issues. This includes periodic syncing, webhook support, and GitHub API health monitoring.

## Phase 2 Features

### 1. Automatic Sync Scheduling
- Background sync job that runs periodically (configurable interval, default: every 30 minutes)
- Syncs all linked issues (where github_issue is set)
- Tracks last sync timestamp per issue
- Respects GitHub API rate limits
- Batches API calls for efficiency

### 2. Bidirectional Updates
- **Roadmap → GitHub**: Update GitHub issue when roadmap issue changes
- **GitHub → Roadmap**: Pull updates from GitHub when issue changes there
- Conflict resolution: Last-write-wins or user prompt (TBD)
- Update supported fields: title, description, labels, milestones, assignees

### 3. GitHub Webhook Support (Optional)
- Receive GitHub webhooks for real-time updates
- Webhook handler endpoint
- Signature verification
- Fallback to polling if webhooks unavailable

### 4. GitHub API Health Monitoring
**Important for health scan integration:**
- Add GitHub API connectivity check to infrastructure health monitoring
- Monitor: API availability, rate limit status, authentication validity
- Include in `roadmap health check` output
- Alert if GitHub API is unreachable (don't block roadmap operations)
- Track health metrics: last successful sync, last error, consecutive failures

**Note on Health Scan**: The entity-level health scan (Phase 1 issue 681e4fe2) should NOT depend on GitHub API. However, the health check command should monitor GitHub connectivity as optional infrastructure health.

### 5. Sync Error Handling
- Graceful handling of GitHub API errors
- Retry logic with exponential backoff
- Error logging and notifications
- Skip syncing for broken links (missing GitHub ID)
- Recover from partial sync failures

### 6. Sync Status & History
- Track sync status per issue (synced, pending, error)
- Maintain sync history (last sync time, what changed)
- Display in issue view: last synced timestamp, pending changes

### 7. Configuration
- Sync interval (env var: ROADMAP_GITHUB_SYNC_INTERVAL_MINUTES, default: 30)
- Auto-sync enabled/disabled flag (env var: ROADMAP_GITHUB_AUTO_SYNC_ENABLED)
- Webhook secret (env var: GITHUB_WEBHOOK_SECRET)
- Health check interval (env var: ROADMAP_GITHUB_HEALTH_CHECK_MINUTES, default: 5)

## Implementation Details

### GitHub Health Check Component
- Separate from entity health scan
- Runs independently on configured interval
- Checks:
  - Token validity (attempt minimal API call)
  - Current rate limit status
  - Connection availability
  - Authentication (401 errors)
- Cached results (don't spam API on each command)
- Add to `roadmap health check` output under "Infrastructure" section

### Sync Execution Strategy
- Background thread or async task runner
- Single sync queue to avoid concurrent updates
- Locking mechanism for issue updates during sync
- Heartbeat/health check for background process

### Conflict Resolution Strategy
Two options to implement:
1. **Last-write-wins**: GitHub change overwrites roadmap, or vice versa (configurable)
2. **User Prompt**: Alert user to conflict, require manual resolution

### Database Schema Updates
- Add sync_status column (enum: synced, pending, error)
- Add last_sync_timestamp column
- Add last_sync_error column
- Add pending_github_changes column (JSON of diff)

## Success Criteria
- [ ] Background sync job runs on configured interval
- [ ] Syncs both directions (roadmap → GitHub and GitHub → roadmap)
- [ ] Handles conflicts gracefully (chosen strategy)
- [ ] GitHub API health monitored independently
- [ ] Health check includes GitHub status (doesn't fail if unavailable)
- [ ] Rate limiting respected (batch API calls)
- [ ] Sync history tracked (last sync time, changes)
- [ ] All existing tests passing
- [ ] 100% test coverage for new sync code
- [ ] Configuration via environment variables
- [ ] Clear error messages and logging

## Testing Strategy
- Mock GitHub API for CI
- Test rate limit handling
- Test conflict scenarios
- Test health check with API down
- Test background sync with concurrent updates
- Integration tests: full sync cycle
- Performance tests: batch sync of many issues

## Related Issues
- **Phase 1 (a13292a4)**: Manual sync, GitHub ID linking - prerequisite
- **Health Check (681e4fe2)**: Completed, but note: doesn't depend on GitHub

## Future Enhancements
- Webhook support (real-time sync instead of polling)
- Sync statistics dashboard
- Audit trail of all sync changes
- Bidirectional label/milestone mapping
- GitHub Projects integration
