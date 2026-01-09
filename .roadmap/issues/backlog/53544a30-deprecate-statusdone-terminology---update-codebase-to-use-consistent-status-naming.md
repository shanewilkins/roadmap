---
id: 53544a30
title: Deprecate Status.DONE terminology - update codebase to use consistent status
  naming
headline: '# Deprecate Status.DONE terminology - update codebase to use consistent
  status naming'
priority: medium
status: closed
issue_type: feature
milestone: null
labels: []
remote_ids:
  github: '281'
created: '2026-01-09T21:31:55.905916+00:00'
updated: '2026-01-09T22:52:06.155086+00:00'
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
github_issue: '281'
---

Deprecate Status.DONE terminology - update codebase to use consistent status naming

## Context
The Status enum currently has a constant named DONE with value 'closed'. To align with consistent terminology throughout the codebase (using 'closed' instead of 'done'), we need to:
1. Rename the Status.DONE constant to Status.CLOSED
2. Update all usages in tests, fixtures, demos, and documentation
3. Update test names that reference 'done' to use 'closed'
4. Update README and demo examples

## Success Criteria
- [ ] Rename Status.DONE to Status.CLOSED in constants.py
- [ ] Update all ~25 test files using Status.DONE to use Status.CLOSED
- [ ] Rename test methods containing 'done' to use 'closed' (e.g., test_archive_single_done_issue → test_archive_single_closed_issue)
- [ ] Update all demo scripts and baseline scripts to use Status.CLOSED
- [ ] Update README.md examples to show 'closed' instead of 'done' status
- [ ] Update demo documentation (e.g., blocked_status_demo.py references to 'done')
- [ ] All tests pass with consistent terminology
- [ ] No references to Status.DONE remain in codebase
