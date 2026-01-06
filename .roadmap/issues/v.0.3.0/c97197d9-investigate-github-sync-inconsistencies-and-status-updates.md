---
id: c97197d9
title: Investigate GitHub sync inconsistencies and status updates
priority: medium
status: closed
issue_type: other
milestone: v.0.3.0
labels:
- priority:high
- status:todo
remote_ids:
  github: 7
created: '2026-01-02T19:20:53.336462+00:00'
updated: '2026-01-06T16:18:44.024407+00:00'
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
github_issue: 7
---

# Investigate GitHub sync inconsistencies and status updates

## Description

While the GitHub sync authentication has been fixed, there are inconsistencies between local roadmap issue status and GitHub issue status. Local issues show as "done" but some GitHub issues remain open, indicating that status updates may not be syncing properly in the bidirectional sync process.

## Issues Observed

### Local vs GitHub Status Mismatch

- **c0850c90** (Fix broken sync): Local = `done`, GitHub = needs verification
- **ac64f265** (Add project template): Local = `done`, GitHub = needs verification
- **88d2e91d** (Test issue): Local = `done`, GitHub = needs verification

### Sync Authentication Working

- ✅ Connection established successfully
- ✅ Bidirectional sync runs without errors
- ✅ New issues sync properly
- ❌ Status updates not propagating correctly

## Root Cause Investigation Needed

1. **Status Mapping**: Verify how local status (`done`) maps to GitHub issue state (`closed`)
2. **API Permissions**: Ensure token has permissions to update issue status
3. **Sync Logic**: Check if status updates are included in bidirectional sync
4. **Error Handling**: Review logs for any silent failures during status updates

## Acceptance Criteria

- [ ] Investigate why local `done` status doesn't close GitHub issues
- [ ] Verify GitHub API permissions for issue state changes
- [ ] Review sync logic for status update handling
- [ ] Test status changes sync in both directions (local→GitHub, GitHub→local)
- [ ] Document proper status mapping between roadmap and GitHub
- [ ] Ensure completed issues automatically close on GitHub
- [ ] Create test cases for status sync verification
- [ ] Update documentation with status sync behavior

## Technical Tasks

### Phase 1: Investigation

- [ ] Check GitHub API token permissions (needs `repo` scope for state changes?)
- [ ] Review sync code for status update logic
- [ ] Test manual status sync with verbose logging
- [ ] Verify GitHub issue state API endpoints

### Phase 2: Implementation

- [ ] Fix status mapping logic if broken
- [ ] Implement proper error handling for status updates
- [ ] Add status sync verification
- [ ] Test bidirectional status changes

### Phase 3: Validation

- [ ] Close the three identified issues manually on GitHub as test
- [ ] Verify new issues sync status changes properly
- [ ] Document expected sync behavior
- [ ] Add automated tests for status sync

## Priority Justification

**High Priority** because:
- Core functionality expectation: completed work should close GitHub issues
- User experience: manual GitHub issue management defeats automation purpose
- Data integrity: inconsistent status creates confusion about actual work state
- Trust: users need reliable sync to depend on the tool

## Related Issues

- c0850c90: Fix broken sync between GitHub issues and roadmap folder (completed locally)
- ac64f265: Add project level template (completed locally)
- 88d2e91d: test issue to validate sync (completed locally)

## Next Steps for Tomorrow

1. Start with `roadmap sync test-connection --verbose` to check current state
2. Review GitHub issues #3, #4, #5 to confirm they're still open
3. Investigate sync logs for status update attempts
4. Test manual status sync commands if available

---
*Created by roadmap CLI*
Assignee: @shanewilkins
