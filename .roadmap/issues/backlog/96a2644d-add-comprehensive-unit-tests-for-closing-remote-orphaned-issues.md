---
id: 96a2644d
title: Add comprehensive unit tests for closing remote orphaned issues
priority: medium
status: closed
issue_type: other
milestone: null
labels: []
remote_ids:
  github: 47
created: '2026-01-02T19:20:54.126964+00:00'
updated: '2026-01-06T02:12:07.824768+00:00'
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
github_issue: 47
---

This PR adds comprehensive unit tests for the `SyncManager._close_remote_orphaned_issues()` method, which implements the opt-in orphan closure logic for remote GitHub issues that were created by the CLI but no longer have local counterparts.

## Changes

### Enhanced Test Coverage (`tests/test_close_orphaned_issues.py`)

The test file now includes **8 unit tests** (up from 3) that verify all aspects of the orphan closure behavior:

**Original Tests:**
- Remote issues created by CLI are closed when local counterparts are missing
- Linked remote issues are not closed when local counterparts exist
- API errors when listing issues are properly reported

**New Tests Added:**
1. **`test_close_orphaned_skips_issues_without_cli_marker`** - Ensures safety by verifying that issues not created by the CLI (those missing the `*Created by roadmap CLI*` footer marker) are never closed, even if no local issue exists. This prevents accidentally closing manually-created GitHub issues.

2. **`test_close_orphaned_handles_individual_close_error`** - Tests resilience when closing individual issues fails. Verifies that an error closing one issue doesn't prevent other orphaned issues from being closed, and that the error is properly reported.

3. **`test_close_orphaned_handles_multiple_orphaned_issues`** - Validates bulk closure functionality by testing that multiple orphaned issues can all be successfully closed in a single operation.

4. **`test_close_orphaned_with_no_github_client`** - Tests graceful handling when the GitHub client is not configured, ensuring appropriate error messages are returned.

5. **`test_close_orphaned_mixed_scenario`** - Comprehensive integration test that validates behavior with a realistic mix of:
   - Orphaned CLI-created issues (should be closed)
   - Linked CLI-created issues (should NOT be closed)
   - Non-CLI issues (should NOT be closed)

### Configuration Improvements

- Fixed `pytest.ini` marker format from `[tool:pytest]` to `[pytest]` to properly register custom markers
- Added marker definitions to `pyproject.toml` for better IDE support and test organization
- Eliminated all pytest marker warnings during test execution

## Testing

All tests pass successfully:
```
8 passed in 0.09s
```

The tests use `@pytest.mark.unit` for fast execution without filesystem operations and leverage existing fixtures (`mock_core`, `mock_config`) for consistency with the rest of the test suite.

## Notes

These tests exercise the opt-in orphan closure logic that helps prevent orphaned remote issues when local issues are deleted. The feature is controlled by the `config.sync.close_orphaned` configuration option to avoid surprising behavior during default syncs.

<!-- START COPILOT CODING AGENT SUFFIX -->



<details>

<summary>Original prompt</summary>

> tests: add unit tests for closing remote orphaned issues
>
> This PR adds unit tests for the new SyncManager._close_remote_orphaned_issues() behavior.
>
> Changes:
> - tests/test_close_orphaned_issues.py: new tests that verify:
>   - remote issues created by the CLI are closed when local counterparts are missing
>   - linked remote issues are not closed
>   - API errors when listing issues are reported
>
> These tests exercise the opt-in orphan closure logic and help prevent regressions.
>
> Please review and let me know if you want additional CLI/integration tests or a dry-run mode for closure.


</details>

Created from VS Code via the [GitHub Pull Request](https://marketplace.visualstudio.com/items?itemName=GitHub.vscode-pull-request-github) extension.

<!-- START COPILOT CODING AGENT TIPS -->
---

💡 You can make Copilot smarter by setting up custom instructions, customizing its development environment and configuring Model Context Protocol (MCP) servers. Learn more [Copilot coding agent tips](https://gh.io/copilot-coding-agent-tips) in the docs.
