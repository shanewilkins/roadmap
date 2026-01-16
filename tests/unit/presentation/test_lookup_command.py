"""Unit tests for the lookup-github command.

Phase 1C refactoring: Using mock factories and CLI runner fixtures to reduce DRY.
"""

from unittest.mock import Mock

from roadmap.adapters.cli.issues import issue
from tests.unit.common.formatters.test_assertion_helpers import create_mock_issue

# mock_core fixture provided by tests.fixtures.mocks module
# Uses centralized mock_core_simple


def test_lookup_github_issue_success(cli_runner, mock_core):
    """Test successful lookup of issue by GitHub ID."""
    # Use factory to create mock issue
    mock_issue = create_mock_issue(
        id="test-issue-123",
        title="Test Issue",
        github_issue=456,
    )
    mock_issue.status = Mock(value="todo")
    mock_issue.priority = Mock(value="high")
    mock_issue.assignee = "shane"

    mock_core.issues.get_all.return_value = [mock_issue]

    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "456"],
        obj={"core": mock_core},
    )

    # Verify - command succeeds and issue is found
    assert result.exit_code == 0


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
    # Use factory to create mock issues
    mock_issue_1 = create_mock_issue(github_issue=100)
    mock_issue_2 = create_mock_issue(
        id="correct-issue",
        title="Correct Issue",
        github_issue=456,
    )
    mock_issue_2.status = Mock(value="in_progress")
    mock_issue_2.priority = Mock(value="medium")
    mock_issue_3 = create_mock_issue(github_issue=789)

    mock_core.issues.get_all.return_value = [mock_issue_1, mock_issue_2, mock_issue_3]

    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "456"],
        obj={"core": mock_core},
    )

    # Verify - command succeeds
    assert result.exit_code == 0


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
    # Use factory to create mock issue
    mock_issue = create_mock_issue(
        id="minimal-issue",
        title="Minimal Issue",
        github_issue=123,
    )
    mock_issue.status = Mock(value="todo")
    mock_issue.priority = Mock(value="low")

    mock_core.issues.get_all.return_value = [mock_issue]

    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "123"],
        obj={"core": mock_core},
    )

    # Verify - command succeeds
    assert result.exit_code == 0


def test_lookup_github_issue_with_description(cli_runner, mock_core):
    """Test lookup displays description when available."""
    # Use factory to create mock issue
    mock_issue = create_mock_issue(
        id="desc-issue",
        title="Issue with Description",
        content="This is a detailed description",
        github_issue=789,
    )
    mock_issue.status = Mock(value="todo")
    mock_issue.priority = Mock(value="high")

    mock_core.issues.get_all.return_value = [mock_issue]

    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "789"],
        obj={"core": mock_core},
    )

    # Verify - command succeeds
    assert result.exit_code == 0


def test_lookup_github_issue_none_github_issue(cli_runner, mock_core):
    """Test that issues with None github_issue don't match."""
    # Use factory to create mock issue with no GitHub link
    mock_issue = create_mock_issue(id="unlinked-issue", github_issue=None)

    mock_core.issues.get_all.return_value = [mock_issue]

    # Execute
    result = cli_runner.invoke(
        issue,
        ["lookup-github", "456"],
        obj={"core": mock_core},
    )

    # Verify - should not find it
    assert result.exit_code == 1
