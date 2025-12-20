"""Unit tests for the sync-github command."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.issues import issue


@pytest.fixture
def cli_runner():
    """Provide a Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_core():
    """Provide a mock core object."""
    core = Mock()
    core.issues = Mock()
    core.root_path = "/test/roadmap"
    return core


def test_sync_github_issue_success(cli_runner, mock_core):
    """Test successful sync of issue from GitHub."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "test-123"
    mock_issue.github_issue = 456
    mock_issue.title = "Old Title"
    mock_issue.content = "Old content"
    mock_issue.model_dump.return_value = {
        "title": "Old Title",
        "content": "Old content",
    }

    mock_core.issues.get_by_id.return_value = mock_issue

    github_data = {
        "number": 456,
        "title": "New Title",
        "body": "New content",
        "state": "open",
        "assignees": [{"login": "jane"}],
        "labels": [{"name": "bug"}],
    }

    # Mock GitHubIntegrationService and GitHubIssueClient
    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIssueClient"
        ) as mock_gh_client_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = (
            "token",
            "owner",
            "repo",
        )
        mock_gh_service_cls.return_value = mock_gh_service

        mock_gh_client = Mock()
        mock_gh_client.fetch_issue.return_value = github_data
        mock_gh_client.get_issue_diff.return_value = {
            "title": ("Old Title", "New Title")
        }
        mock_gh_client_cls.return_value = mock_gh_client

        # Execute - with input for confirmation
        result = cli_runner.invoke(
            issue,
            ["sync-github", "test-123"],
            obj={"core": mock_core},
            input="y\n",  # Confirm sync
        )

        # Verify
        assert result.exit_code == 0
        assert "synced" in result.output


def test_sync_github_issue_not_found(cli_runner, mock_core):
    """Test sync when internal issue doesn't exist."""
    # Setup
    mock_core.issues.get_by_id.return_value = None

    # Execute
    result = cli_runner.invoke(
        issue,
        ["sync-github", "nonexistent"],
        obj={"core": mock_core},
    )

    # Verify
    assert result.exit_code == 1


def test_sync_github_issue_not_linked(cli_runner, mock_core):
    """Test sync when issue is not linked to GitHub."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "test-123"
    mock_issue.github_issue = None  # Not linked

    mock_core.issues.get_by_id.return_value = mock_issue

    # Execute
    result = cli_runner.invoke(
        issue,
        ["sync-github", "test-123"],
        obj={"core": mock_core},
    )

    # Verify
    assert result.exit_code == 1


def test_sync_github_issue_no_changes(cli_runner, mock_core):
    """Test sync when there are no changes."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "test-123"
    mock_issue.github_issue = 456
    mock_issue.title = "Title"
    mock_issue.content = "Content"
    mock_issue.model_dump.return_value = {
        "title": "Title",
        "content": "Content",
    }

    mock_core.issues.get_by_id.return_value = mock_issue

    github_data = {
        "number": 456,
        "title": "Title",
        "body": "Content",
        "state": "open",
    }

    # Mock services
    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIssueClient"
        ) as mock_gh_client_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = (
            "token",
            "owner",
            "repo",
        )
        mock_gh_service_cls.return_value = mock_gh_service

        mock_gh_client = Mock()
        mock_gh_client.fetch_issue.return_value = github_data
        mock_gh_client.get_issue_diff.return_value = {}  # No changes
        mock_gh_client_cls.return_value = mock_gh_client

        # Execute
        result = cli_runner.invoke(
            issue,
            ["sync-github", "test-123"],
            obj={"core": mock_core},
        )

        # Verify
        assert result.exit_code == 0
        assert "already in sync" in result.output


def test_sync_github_issue_with_config_options(cli_runner, mock_core):
    """Test sync with explicit owner and repo options."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "test-123"
    mock_issue.github_issue = 456
    mock_issue.model_dump.return_value = {}

    mock_core.issues.get_by_id.return_value = mock_issue

    github_data = {"number": 456, "title": "Title"}

    # Mock services
    with patch(
        "roadmap.adapters.cli.issues.sync.GitHubIssueClient"
    ) as mock_gh_client_cls:
        mock_gh_client = Mock()
        mock_gh_client.fetch_issue.return_value = github_data
        mock_gh_client.get_issue_diff.return_value = {}
        mock_gh_client_cls.return_value = mock_gh_client

        # Execute - with explicit owner/repo
        cli_runner.invoke(
            issue,
            ["sync-github", "test-123", "--owner", "myowner", "--repo", "myrepo"],
            obj={"core": mock_core},
        )

        # Verify that fetch_issue was called with the right params
        mock_gh_client.fetch_issue.assert_called_with("myowner", "myrepo", 456)


def test_sync_github_issue_auto_confirm(cli_runner, mock_core):
    """Test sync with auto-confirm flag skips prompt."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "test-123"
    mock_issue.github_issue = 456
    mock_issue.title = "Old"
    mock_issue.content = "Old"
    mock_issue.model_dump.return_value = {}

    mock_core.issues.get_by_id.return_value = mock_issue

    github_data = {
        "number": 456,
        "title": "New",
        "state": "open",
    }

    # Mock services
    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIssueClient"
        ) as mock_gh_client_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = (
            "token",
            "owner",
            "repo",
        )
        mock_gh_service_cls.return_value = mock_gh_service

        mock_gh_client = Mock()
        mock_gh_client.fetch_issue.return_value = github_data
        mock_gh_client.get_issue_diff.return_value = {"title": ("Old", "New")}
        mock_gh_client_cls.return_value = mock_gh_client

        # Execute - with auto-confirm
        result = cli_runner.invoke(
            issue,
            ["sync-github", "test-123", "--auto-confirm"],
            obj={"core": mock_core},
        )

        # Verify
        assert result.exit_code == 0


def test_sync_github_issue_github_not_found(cli_runner, mock_core):
    """Test sync when GitHub issue is not found."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "test-123"
    mock_issue.github_issue = 999

    mock_core.issues.get_by_id.return_value = mock_issue

    # Mock services
    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIssueClient"
        ) as mock_gh_client_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = (
            "token",
            "owner",
            "repo",
        )
        mock_gh_service_cls.return_value = mock_gh_service

        mock_gh_client = Mock()
        mock_gh_client.fetch_issue.return_value = None  # Not found
        mock_gh_client_cls.return_value = mock_gh_client

        # Execute
        result = cli_runner.invoke(
            issue,
            ["sync-github", "test-123"],
            obj={"core": mock_core},
        )

        # Verify
        assert result.exit_code == 1


def test_sync_github_issue_cancel_confirmation(cli_runner, mock_core):
    """Test canceling sync via confirmation prompt."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "test-123"
    mock_issue.github_issue = 456
    mock_issue.model_dump.return_value = {}

    mock_core.issues.get_by_id.return_value = mock_issue

    github_data = {"number": 456, "title": "New Title"}

    # Mock services
    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIssueClient"
        ) as mock_gh_client_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = (
            "token",
            "owner",
            "repo",
        )
        mock_gh_service_cls.return_value = mock_gh_service

        mock_gh_client = Mock()
        mock_gh_client.fetch_issue.return_value = github_data
        mock_gh_client.get_issue_diff.return_value = {"title": ("Old", "New")}
        mock_gh_client_cls.return_value = mock_gh_client

        # Execute - with input to cancel
        result = cli_runner.invoke(
            issue,
            ["sync-github", "test-123"],
            obj={"core": mock_core},
            input="n\n",  # Decline sync
        )

        # Verify
        assert result.exit_code == 0
        assert "Sync cancelled" in result.output


def test_sync_github_issue_fetch_error(cli_runner, mock_core):
    """Test sync handles GitHub API errors gracefully."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "test-123"
    mock_issue.github_issue = 456

    mock_core.issues.get_by_id.return_value = mock_issue

    # Mock services
    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIssueClient"
        ) as mock_gh_client_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = (
            "token",
            "owner",
            "repo",
        )
        mock_gh_service_cls.return_value = mock_gh_service

        mock_gh_client = Mock()
        mock_gh_client.fetch_issue.side_effect = RuntimeError("API Error")
        mock_gh_client_cls.return_value = mock_gh_client

        # Execute
        result = cli_runner.invoke(
            issue,
            ["sync-github", "test-123"],
            obj={"core": mock_core},
        )

        # Verify
        assert result.exit_code == 1


def test_sync_github_issue_with_closed_state(cli_runner, mock_core):
    """Test sync handles closed GitHub issues correctly."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "test-123"
    mock_issue.github_issue = 456
    mock_issue.title = "Issue"
    mock_issue.content = "Content"
    mock_issue.model_dump.return_value = {"title": "Issue", "content": "Content"}

    mock_core.issues.get_by_id.return_value = mock_issue

    github_data = {
        "number": 456,
        "title": "Issue",
        "state": "closed",  # Closed on GitHub
    }

    # Mock services
    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIssueClient"
        ) as mock_gh_client_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = (
            "token",
            "owner",
            "repo",
        )
        mock_gh_service_cls.return_value = mock_gh_service

        mock_gh_client = Mock()
        mock_gh_client.fetch_issue.return_value = github_data
        # Show there's a diff (state changed)
        mock_gh_client.get_issue_diff.return_value = {"state": ("open", "closed")}
        mock_gh_client_cls.return_value = mock_gh_client

        # Execute - with auto-confirm
        result = cli_runner.invoke(
            issue,
            ["sync-github", "test-123", "--auto-confirm"],
            obj={"core": mock_core},
        )

        # Verify
        assert result.exit_code == 0
        # Verify update was called with status=done
        mock_core.issues.update.assert_called_once()
        call_args = mock_core.issues.update.call_args
        assert "status" in call_args[0][1]
        assert call_args[0][1]["status"] == "done"
