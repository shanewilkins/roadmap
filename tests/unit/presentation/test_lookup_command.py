"""Unit tests for the lookup-github command."""

from unittest.mock import Mock

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
    return core


def test_lookup_github_issue_success(cli_runner, mock_core):
    """Test successful lookup of issue by GitHub ID."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "test-issue-123"
    mock_issue.title = "Test Issue"
    mock_issue.status = Mock(value="todo")
    mock_issue.priority = Mock(value="high")
    mock_issue.assignee = "shane"
    mock_issue.milestone = "v0.8"
    mock_issue.labels = ["bug", "github"]
    mock_issue.estimated_hours = 5
    mock_issue.estimated_time_display = "5 hours"
    mock_issue.content = "Issue description"
    mock_issue.github_issue = 456

    mock_core.issues.get_all.return_value = [mock_issue]

    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "456"],
        obj={"core": mock_core},
    )

    # Verify
    assert result.exit_code == 0
    assert "GitHub issue #456" in result.output
    assert "test-issue-123" in result.output
    assert "Test Issue" in result.output
    assert "todo" in result.output
    assert "high" in result.output
    assert "shane" in result.output
    assert "v0.8" in result.output
    assert "bug" in result.output


def test_lookup_github_issue_not_found(cli_runner, mock_core):
    """Test lookup when GitHub ID is not found."""
    # Setup
    mock_core.issues.get_all.return_value = []

    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "999"],
        obj={"core": mock_core},
    )

    # Verify
    assert result.exit_code == 1


def test_lookup_github_issue_multiple_issues(cli_runner, mock_core):
    """Test lookup when multiple issues exist, finds the correct one."""
    # Setup
    mock_issue_1 = Mock()
    mock_issue_1.github_issue = 100

    mock_issue_2 = Mock()
    mock_issue_2.github_issue = 456
    mock_issue_2.id = "correct-issue"
    mock_issue_2.title = "Correct Issue"
    mock_issue_2.status = Mock(value="in_progress")
    mock_issue_2.priority = Mock(value="medium")
    mock_issue_2.assignee = None
    mock_issue_2.milestone = None
    mock_issue_2.labels = []
    mock_issue_2.estimated_hours = None
    mock_issue_2.content = None

    mock_issue_3 = Mock()
    mock_issue_3.github_issue = 789

    mock_core.issues.get_all.return_value = [mock_issue_1, mock_issue_2, mock_issue_3]

    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "456"],
        obj={"core": mock_core},
    )

    # Verify
    assert result.exit_code == 0
    assert "correct-issue" in result.output
    assert "Correct Issue" in result.output


def test_lookup_github_issue_invalid_id_zero(cli_runner, mock_core):
    """Test lookup with zero as GitHub ID (invalid)."""
    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "0"],
        obj={"core": mock_core},
    )

    # Verify
    assert result.exit_code == 1
    assert "Invalid" in result.output or "0" in result.output


def test_lookup_github_issue_invalid_id_negative(cli_runner, mock_core):
    """Test lookup with negative GitHub ID (invalid)."""
    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "-1"],
        obj={"core": mock_core},
    )

    # Verify
    assert result.exit_code != 0  # Exit code 2 for invalid argument parsing


def test_lookup_github_issue_not_string(cli_runner, mock_core):
    """Test that non-integer arguments are rejected by Click."""
    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "not-a-number"],
        obj={"core": mock_core},
    )

    # Verify - Click will fail to parse the argument
    assert result.exit_code != 0


def test_lookup_github_issue_minimal_fields(cli_runner, mock_core):
    """Test lookup with issue that has minimal fields set."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "minimal-issue"
    mock_issue.title = "Minimal Issue"
    mock_issue.status = Mock(value="todo")
    mock_issue.priority = Mock(value="low")
    mock_issue.assignee = None
    mock_issue.milestone = None
    mock_issue.labels = []
    mock_issue.estimated_hours = None
    mock_issue.content = None
    mock_issue.github_issue = 123

    mock_core.issues.get_all.return_value = [mock_issue]

    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "123"],
        obj={"core": mock_core},
    )

    # Verify
    assert result.exit_code == 0
    assert "GitHub issue #123" in result.output
    assert "minimal-issue" in result.output
    assert "Minimal Issue" in result.output


def test_lookup_github_issue_with_description(cli_runner, mock_core):
    """Test lookup displays description when available."""
    # Setup
    mock_issue = Mock()
    mock_issue.id = "desc-issue"
    mock_issue.title = "Issue with Description"
    mock_issue.status = Mock(value="todo")
    mock_issue.priority = Mock(value="high")
    mock_issue.assignee = None
    mock_issue.milestone = None
    mock_issue.labels = []
    mock_issue.estimated_hours = None
    mock_issue.content = "This is a detailed description"
    mock_issue.github_issue = 789

    mock_core.issues.get_all.return_value = [mock_issue]

    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "789"],
        obj={"core": mock_core},
    )

    # Verify
    assert result.exit_code == 0
    assert "detailed description" in result.output


def test_lookup_github_issue_none_github_issue(cli_runner, mock_core):
    """Test that issues with None github_issue don't match."""
    # Setup
    mock_issue = Mock()
    mock_issue.github_issue = None

    mock_core.issues.get_all.return_value = [mock_issue]

    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "456"],
        obj={"core": mock_core},
    )

    # Verify - should not find it
    assert result.exit_code == 1
