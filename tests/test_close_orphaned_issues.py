"""Unit tests for closing remote orphaned GitHub issues."""

from unittest.mock import Mock

import pytest

from roadmap.sync import SyncManager


@pytest.mark.unit
def test_close_orphaned_closes_missing_local_issue(mock_core, mock_config):
    """If a GitHub issue has the CLI footer and no matching local issue, it should be closed."""
    # Arrange
    sync_manager = SyncManager(mock_core, mock_config)
    # Ensure we have a github client mock
    sync_manager.github_client = Mock()

    # Remote issue created by CLI and not present locally
    gh_issue = {
        "number": 101,
        "title": "Stale Issue",
        "body": "Some content\n\n---\n*Created by roadmap CLI*",
        "labels": [],
        "assignee": None,
    }

    sync_manager.github_client.get_issues.return_value = [gh_issue]
    # Local core returns no issues (so the remote issue is orphaned)
    mock_core.list_issues.return_value = []

    # Act
    closed, errors, msgs = sync_manager._close_remote_orphaned_issues()

    # Assert
    assert closed == 1
    assert errors == 0
    sync_manager.github_client.update_issue.assert_called_once()


@pytest.mark.unit
def test_close_orphaned_skips_if_local_exists(mock_core, mock_config):
    """If a local issue points to the GitHub number, the remote issue is not closed."""
    sync_manager = SyncManager(mock_core, mock_config)
    sync_manager.github_client = Mock()

    gh_issue = {
        "number": 202,
        "title": "Linked Issue",
        "body": "Body\n\n---\n*Created by roadmap CLI*",
        "labels": [],
        "assignee": None,
    }

    sync_manager.github_client.get_issues.return_value = [gh_issue]

    # Local issue that references the GitHub number
    local_issue = Mock()
    local_issue.github_issue = 202
    mock_core.list_issues.return_value = [local_issue]

    closed, errors, msgs = sync_manager._close_remote_orphaned_issues()

    assert closed == 0
    assert errors == 0
    sync_manager.github_client.update_issue.assert_not_called()


@pytest.mark.unit
def test_close_orphaned_handles_api_error(mock_core, mock_config):
    """If listing GitHub issues raises an API error, the error should be reported."""
    from roadmap.github_client import GitHubAPIError

    sync_manager = SyncManager(mock_core, mock_config)
    sync_manager.github_client = Mock()

    sync_manager.github_client.get_issues.side_effect = GitHubAPIError("boom")

    closed, errors, msgs = sync_manager._close_remote_orphaned_issues()

    assert closed == 0
    assert errors == 1
    assert any("Failed to list GitHub issues" in m for m in msgs)


@pytest.mark.unit
def test_close_orphaned_skips_issues_without_cli_marker(mock_core, mock_config):
    """Remote issues not created by the CLI (missing footer) should not be closed."""
    sync_manager = SyncManager(mock_core, mock_config)
    sync_manager.github_client = Mock()

    # Issue without the CLI footer marker
    gh_issue = {
        "number": 303,
        "title": "External Issue",
        "body": "Created manually on GitHub",
        "labels": [],
        "assignee": None,
    }

    sync_manager.github_client.get_issues.return_value = [gh_issue]
    mock_core.list_issues.return_value = []

    closed, errors, msgs = sync_manager._close_remote_orphaned_issues()

    # Should not close issues without CLI marker
    assert closed == 0
    assert errors == 0
    sync_manager.github_client.update_issue.assert_not_called()


@pytest.mark.unit
def test_close_orphaned_handles_individual_close_error(mock_core, mock_config):
    """If closing an individual issue fails, it should be reported but not stop other closures."""
    from roadmap.github_client import GitHubAPIError

    sync_manager = SyncManager(mock_core, mock_config)
    sync_manager.github_client = Mock()

    # Two orphaned issues created by CLI
    gh_issue1 = {
        "number": 401,
        "title": "Orphan 1",
        "body": "Content\n\n---\n*Created by roadmap CLI*",
        "labels": [],
        "assignee": None,
    }
    gh_issue2 = {
        "number": 402,
        "title": "Orphan 2",
        "body": "Content\n\n---\n*Created by roadmap CLI*",
        "labels": [],
        "assignee": None,
    }

    sync_manager.github_client.get_issues.return_value = [gh_issue1, gh_issue2]
    mock_core.list_issues.return_value = []

    # First close fails, second succeeds
    sync_manager.github_client.update_issue.side_effect = [
        GitHubAPIError("Failed to close #401"),
        {"number": 402, "state": "closed"},
    ]

    closed, errors, msgs = sync_manager._close_remote_orphaned_issues()

    # One successful close, one error
    assert closed == 1
    assert errors == 1
    assert any("Failed to close issue #401" in m for m in msgs)


@pytest.mark.unit
def test_close_orphaned_handles_multiple_orphaned_issues(mock_core, mock_config):
    """Multiple orphaned issues should all be closed."""
    sync_manager = SyncManager(mock_core, mock_config)
    sync_manager.github_client = Mock()

    # Three orphaned issues
    gh_issues = [
        {
            "number": i,
            "title": f"Orphan {i}",
            "body": f"Content {i}\n\n---\n*Created by roadmap CLI*",
            "labels": [],
            "assignee": None,
        }
        for i in [501, 502, 503]
    ]

    sync_manager.github_client.get_issues.return_value = gh_issues
    mock_core.list_issues.return_value = []

    closed, errors, msgs = sync_manager._close_remote_orphaned_issues()

    assert closed == 3
    assert errors == 0
    assert sync_manager.github_client.update_issue.call_count == 3


@pytest.mark.unit
def test_close_orphaned_with_no_github_client(mock_core, mock_config):
    """If GitHub client is not configured, should return error message."""
    sync_manager = SyncManager(mock_core, mock_config)
    sync_manager.github_client = None

    closed, errors, msgs = sync_manager._close_remote_orphaned_issues()

    assert closed == 0
    assert errors == 0
    assert msgs == ["GitHub client not configured."]


@pytest.mark.unit
def test_close_orphaned_mixed_scenario(mock_core, mock_config):
    """Test mixed scenario with orphaned, linked, and non-CLI issues."""
    sync_manager = SyncManager(mock_core, mock_config)
    sync_manager.github_client = Mock()

    gh_issues = [
        # Orphaned CLI issue - should be closed
        {
            "number": 601,
            "title": "Orphaned",
            "body": "Content\n\n---\n*Created by roadmap CLI*",
            "labels": [],
            "assignee": None,
        },
        # Linked CLI issue - should NOT be closed
        {
            "number": 602,
            "title": "Linked",
            "body": "Content\n\n---\n*Created by roadmap CLI*",
            "labels": [],
            "assignee": None,
        },
        # Non-CLI issue - should NOT be closed
        {
            "number": 603,
            "title": "External",
            "body": "Created manually",
            "labels": [],
            "assignee": None,
        },
    ]

    sync_manager.github_client.get_issues.return_value = gh_issues

    # Local issue that references #602
    local_issue = Mock()
    local_issue.github_issue = 602
    mock_core.list_issues.return_value = [local_issue]

    closed, errors, msgs = sync_manager._close_remote_orphaned_issues()

    # Only #601 should be closed
    assert closed == 1
    assert errors == 0
    sync_manager.github_client.update_issue.assert_called_once()
