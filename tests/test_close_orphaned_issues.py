"""Unit tests for closing remote orphaned GitHub issues."""

from unittest.mock import Mock, patch

import pytest

from roadmap.models import RoadmapConfig
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
