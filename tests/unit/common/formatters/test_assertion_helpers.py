"""Test helpers for refactored testing pattern.

This module provides utilities to refactor tests away from parsing Rich console
output (which is incompatible with xdist) toward database-driven assertions.

Pattern:
- Instead of: assert "Created issue" in result.output
- Use: assert_issue_created(core, "Issue Title")

This approach:
1. Tests the actual business logic (database state)
2. Eliminates fragile output parsing
3. Works with xdist parallelization
4. Is more maintainable and faster
"""

from typing import Any

from roadmap.core.domain import Issue, Milestone
from roadmap.infrastructure.coordination.core import RoadmapCore


def assert_command_success(result: Any, message: str = "") -> None:
    """Assert a Click command succeeded.

    Args:
        result: Click CliRunner result
        message: Optional message if assertion fails
    """
    assert result.exit_code == 0, (
        f"Command failed with exit code {result.exit_code}. {message}"
    )


def assert_command_failed(result: Any, message: str = "") -> None:
    """Assert a Click command failed.

    Args:
        result: Click CliRunner result
        message: Optional message if assertion fails
    """
    assert result.exit_code != 0, f"Command should have failed. {message}"


def assert_issue_created(
    core: RoadmapCore,
    title: str,
    expected_count: int = 1,
    message: str = "",
) -> Issue:
    """Assert an issue was created and return it.

    Args:
        core: RoadmapCore instance
        title: Issue title to search for
        expected_count: Expected number of matching issues (default 1)
        message: Optional message if assertion fails

    Returns:
        The created issue
    """
    issues = [issue for issue in core.issues.list() if issue.title == title]
    assert len(issues) >= expected_count, (
        f"Expected {expected_count} issue(s) titled '{title}', "
        f"found {len(issues)}. {message}"
    )
    return issues[0]


def assert_issue_not_created(
    core: RoadmapCore,
    title: str,
    message: str = "",
) -> None:
    """Assert an issue was not created.

    Args:
        core: RoadmapCore instance
        title: Issue title that should not exist
        message: Optional message if assertion fails
    """
    issues = [issue for issue in core.issues.list() if issue.title == title]
    assert len(issues) == 0, (
        f"Issue titled '{title}' should not exist, but found {len(issues)}. {message}"
    )


def assert_milestone_created(
    core: RoadmapCore,
    name: str,
    message: str = "",
) -> Milestone:
    """Assert a milestone was created and return it.

    Args:
        core: RoadmapCore instance
        name: Milestone name to search for
        message: Optional message if assertion fails

    Returns:
        The created milestone
    """
    milestones = [m for m in core.milestones.list() if m.name == name]
    assert len(milestones) >= 1, (
        f"Expected milestone '{name}' to be created, "
        f"found {len(milestones)} milestones. {message}"
    )
    return milestones[0]


def assert_milestone_not_created(
    core: RoadmapCore,
    name: str,
    message: str = "",
) -> None:
    """Assert a milestone was not created.

    Args:
        core: RoadmapCore instance
        name: Milestone name that should not exist
        message: Optional message if assertion fails
    """
    milestones = [m for m in core.milestones.list() if m.name == name]
    assert len(milestones) == 0, (
        f"Milestone '{name}' should not exist, but found {len(milestones)}. {message}"
    )


def assert_issue_assigned_to_milestone(
    core: RoadmapCore,
    issue: Issue,
    milestone_name: str,
    message: str = "",
) -> None:
    """Assert an issue is assigned to a milestone.

    Args:
        core: RoadmapCore instance
        issue: The issue to check
        milestone_name: The expected milestone name
        message: Optional message if assertion fails
    """
    assert issue.milestone == milestone_name, (
        f"Issue '{issue.title}' should be assigned to '{milestone_name}', "
        f"but is assigned to '{issue.milestone}'. {message}"
    )


def assert_issue_status(
    core: RoadmapCore,
    issue: Issue,
    expected_status: str,
    message: str = "",
) -> None:
    """Assert an issue has the expected status.

    Args:
        core: RoadmapCore instance
        issue: The issue to check
        expected_status: The expected status value
        message: Optional message if assertion fails
    """
    # Refresh the issue from the database
    fresh_issue = core.issues.get(issue.id)
    assert fresh_issue is not None, f"Issue '{issue.title}' not found in database"
    assert str(fresh_issue.status.value) == expected_status, (
        f"Issue '{issue.title}' status should be '{expected_status}', "
        f"but is '{fresh_issue.status.value}'. {message}"
    )


def assert_issue_count(
    core: RoadmapCore,
    expected_count: int,
    message: str = "",
) -> None:
    """Assert the total number of issues.

    Args:
        core: RoadmapCore instance
        expected_count: Expected number of issues
        message: Optional message if assertion fails
    """
    issues = core.issues.list()
    assert len(issues) == expected_count, (
        f"Expected {expected_count} issues, found {len(issues)}. {message}"
    )


def assert_milestone_count(
    core: RoadmapCore,
    expected_count: int,
    message: str = "",
) -> None:
    """Assert the total number of milestones.

    Args:
        core: RoadmapCore instance
        expected_count: Expected number of milestones
        message: Optional message if assertion fails
    """
    milestones = core.milestones.list()
    assert len(milestones) == expected_count, (
        f"Expected {expected_count} milestones, found {len(milestones)}. {message}"
    )


def get_latest_issue(core: RoadmapCore) -> Issue | None:
    """Get the most recently created issue.

    Args:
        core: RoadmapCore instance

    Returns:
        The latest issue or None
    """
    issues = core.issues.list()
    if not issues:
        return None
    return sorted(issues, key=lambda i: i.created or "")[-1]


def get_latest_milestone(core: RoadmapCore) -> Milestone | None:
    """Get the most recently created milestone.

    Args:
        core: RoadmapCore instance

    Returns:
        The latest milestone or None
    """
    milestones = core.milestones.list()
    if not milestones:
        return None
    return sorted(milestones, key=lambda m: m.created or "")[-1]


# ============================================================================
# Mock Factory Functions (Phase 1C - Mock Improvement)
# ============================================================================
# These factories create realistic mocks for domain objects, reducing DRY
# violations and improving test clarity.


def create_mock_issue(**kwargs) -> Any:
    """Create a realistic mock Issue object.

    Args:
        **kwargs: Overrides for default mock attributes

    Returns:
        MagicMock configured as an Issue
    """
    from unittest.mock import MagicMock

    defaults = {
        "id": "issue-123",
        "title": "Test Issue",
        "description": "Test description",
        "status": "todo",
        "priority": "medium",
        "assignee": None,
        "milestone": None,
        "github_issue": None,
        "estimated_hours": None,
        "created": "2023-01-01T00:00:00Z",
        "updated": "2023-01-01T00:00:00Z",
    }
    defaults.update(kwargs)

    mock_issue = MagicMock()
    for key, value in defaults.items():
        setattr(mock_issue, key, value)
    return mock_issue


def create_mock_milestone(**kwargs) -> Any:
    """Create a realistic mock Milestone object.

    Args:
        **kwargs: Overrides for default mock attributes

    Returns:
        MagicMock configured as a Milestone
    """
    from unittest.mock import MagicMock

    defaults = {
        "name": "v1-0",
        "description": "Version 1.0 release",
        "status": "open",
        "target_date": None,
        "github_milestone": None,
        "created": "2023-01-01T00:00:00Z",
        "updated": "2023-01-01T00:00:00Z",
    }
    defaults.update(kwargs)

    mock_milestone = MagicMock()
    for key, value in defaults.items():
        setattr(mock_milestone, key, value)
    return mock_milestone


def create_mock_comment(**kwargs) -> Any:
    """Create a realistic mock Comment object.

    Args:
        **kwargs: Overrides for default mock attributes

    Returns:
        MagicMock configured as a Comment
    """
    from unittest.mock import MagicMock

    defaults = {
        "id": 123456,
        "issue_id": "issue-123",
        "author": "testuser",
        "body": "This is a test comment",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "github_url": None,
    }
    defaults.update(kwargs)

    mock_comment = MagicMock()
    for key, value in defaults.items():
        setattr(mock_comment, key, value)
    return mock_comment


def create_mock_github_response(**kwargs) -> Any:
    """Create a realistic mock GitHub API response.

    Args:
        **kwargs: Overrides for default response data

    Returns:
        MagicMock configured as a GitHub response
    """
    from unittest.mock import MagicMock

    defaults = {
        "id": 1,
        "number": 1,
        "title": "GitHub Issue",
        "body": "Issue description",
        "state": "open",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
        "user": {"login": "testuser"},
        "labels": [],
        "assignees": [],
        "html_url": "https://github.com/test/repo/issues/1",
    }
    defaults.update(kwargs)

    mock_response = MagicMock()
    for key, value in defaults.items():
        setattr(mock_response, key, value)

    # Add json() method
    mock_response.json.return_value = defaults
    return mock_response
