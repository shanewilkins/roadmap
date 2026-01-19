"""Mock builders and factories for common test objects.

This module provides factory functions for creating commonly-used mock objects
in tests, reducing duplication of mock setup code across the test suite.

Usage:
    from tests.fixtures.mock_builders import build_mock_repo, build_mock_core

    # Create a mock repository
    mock_repo = build_mock_repo()

    # Create a mock core with custom attributes
    mock_core = build_mock_core(has_github=True)
"""

from typing import Any
from unittest.mock import Mock

# ============================================================================
# Repository Mocks
# ============================================================================


def build_mock_repo(
    list_return: Any = None,
    get_return: Any = None,
    save_side_effect: Any = None,
    link_issue_return: Any = None,
    link_issue_side_effect: Any = None,
    get_remote_id_return: Any = None,
    get_issue_uuid_return: Any = None,
) -> Mock:
    """Build a mock repository with common methods.

    Args:
        list_return: Value to return from repo.list() call
        get_return: Value to return from repo.get() call
        save_side_effect: Side effect for repo.save() call (exception or None)
        link_issue_return: Value to return from repo.link_issue() call
        link_issue_side_effect: Side effect for repo.link_issue() (e.g., exception)
        get_remote_id_return: Value to return from repo.get_remote_id() call
        get_issue_uuid_return: Value to return from repo.get_issue_uuid() call

    Returns:
        Configured Mock repository
    """
    mock_repo = Mock()

    if list_return is not None:
        mock_repo.list = Mock(return_value=list_return)
    else:
        mock_repo.list = Mock(return_value=[])

    if get_return is not None:
        mock_repo.get = Mock(return_value=get_return)
    else:
        mock_repo.get = Mock(return_value=None)

    if save_side_effect is not None:
        mock_repo.save = Mock(side_effect=save_side_effect)
    else:
        mock_repo.save = Mock(return_value=None)

    if link_issue_side_effect is not None:
        mock_repo.link_issue = Mock(side_effect=link_issue_side_effect)
    elif link_issue_return is not None:
        mock_repo.link_issue = Mock(return_value=link_issue_return)
    else:
        mock_repo.link_issue = Mock(return_value=None)

    if get_remote_id_return is not None:
        mock_repo.get_remote_id = Mock(return_value=get_remote_id_return)
    else:
        mock_repo.get_remote_id = Mock(return_value=None)

    if get_issue_uuid_return is not None:
        mock_repo.get_issue_uuid = Mock(return_value=get_issue_uuid_return)
    else:
        mock_repo.get_issue_uuid = Mock(return_value=None)

    return mock_repo


# ============================================================================
# Core Mocks
# ============================================================================


def build_mock_core(
    has_github: bool = False,
    has_repository: bool = True,
    **kwargs: Any,
) -> Mock:
    """Build a mock RoadmapCore instance.

    Args:
        has_github: If True, add github_service to mock
        has_repository: If True, add issue_service.repository to mock
        **kwargs: Additional attributes to set on the mock

    Returns:
        Configured Mock core instance
    """
    mock_core = Mock(**kwargs)

    if has_repository:
        mock_core.issue_service = Mock()
        mock_core.issue_service.repository = build_mock_repo()

    if has_github:
        mock_core.github_service = Mock()

    return mock_core


def build_mock_core_with_repo(
    list_return: Any = None,
    get_return: Any = None,
    save_side_effect: Any = None,
    link_issue_return: Any = None,
    link_issue_side_effect: Any = None,
    get_remote_id_return: Any = None,
    get_issue_uuid_return: Any = None,
) -> Mock:
    """Build a mock core with a pre-configured repository.

    Args:
        list_return: Value for repo.list() to return
        get_return: Value for repo.get() to return
        save_side_effect: Side effect for repo.save()
        link_issue_return: Value for repo.link_issue() to return
        link_issue_side_effect: Side effect for repo.link_issue()
        get_remote_id_return: Value for repo.get_remote_id() to return
        get_issue_uuid_return: Value for repo.get_issue_uuid() to return

    Returns:
        Mock core with configured repository
    """
    mock_core = Mock()
    mock_core.issue_service = Mock()
    mock_core.issue_service.repository = build_mock_repo(
        list_return=list_return,
        get_return=get_return,
        save_side_effect=save_side_effect,
        link_issue_return=link_issue_return,
        link_issue_side_effect=link_issue_side_effect,
        get_remote_id_return=get_remote_id_return,
        get_issue_uuid_return=get_issue_uuid_return,
    )
    return mock_core


# ============================================================================


def build_mock_git_service() -> Mock:
    """Build a mock Git service.

    Returns:
        Configured Mock Git service
    """
    mock_git = Mock()
    mock_git.get_current_branch = Mock(return_value="main")
    mock_git.get_status = Mock(return_value={"clean": True})
    return mock_git


def build_mock_github_service() -> Mock:
    """Build a mock GitHub service.

    Returns:
        Configured Mock GitHub service
    """
    mock_github = Mock()
    mock_github.get_issues = Mock(return_value=[])
    mock_github.create_issue = Mock(return_value={"id": "123"})
    return mock_github


def build_mock_sync_service() -> Mock:
    """Build a mock Sync service.

    Returns:
        Configured Mock Sync service
    """
    mock_sync = Mock()
    mock_sync.pull = Mock(return_value={"issues": [], "conflicts": []})
    mock_sync.push = Mock(return_value={"success": True})
    return mock_sync


# ============================================================================
# File/Filesystem Mocks
# ============================================================================


def build_mock_path(
    name: str = "test.txt",
    exists: bool = True,
    is_dir: bool = False,
    is_file: bool = True,
    content: str = "",
    glob_results: list[Any] | None = None,
) -> Mock:
    """Build a mock Path object with common filesystem operations.

    Args:
        name: Name/path of the file
        exists: Whether the path exists
        is_dir: Whether this is a directory
        is_file: Whether this is a file
        content: Content to return from read_text()
        glob_results: Results to return from glob() calls

    Returns:
        Configured Mock Path object
    """
    from pathlib import Path

    mock_path = Mock(spec=Path)
    mock_path.exists = Mock(return_value=exists)
    mock_path.is_dir = Mock(return_value=is_dir)
    mock_path.is_file = Mock(return_value=is_file)
    mock_path.name = name
    mock_path.read_text = Mock(return_value=content)
    mock_path.write_text = Mock(return_value=None)
    mock_path.relative_to = Mock(return_value=Path(name))

    if glob_results is None:
        glob_results = []
    mock_path.glob = Mock(return_value=glob_results)
    mock_path.iterdir = Mock(return_value=glob_results)

    return mock_path


def build_mock_file_handle(content: str = "") -> Mock:
    """Build a mock file handle for file operations.

    Args:
        content: Content to return when file is read

    Returns:
        Configured Mock file handle
    """
    mock_file = Mock()
    mock_file.read = Mock(return_value=content)
    mock_file.write = Mock(return_value=len(content))
    mock_file.__enter__ = Mock(return_value=mock_file)
    mock_file.__exit__ = Mock(return_value=None)
    return mock_file


def build_mock_directory(files: list[str] | None = None) -> Mock:
    """Build a mock directory/path object.

    Args:
        files: List of filenames that should appear in directory

    Returns:
        Configured Mock directory
    """
    mock_dir = Mock()
    mock_dir.exists = Mock(return_value=True)
    mock_dir.is_dir = Mock(return_value=True)

    if files is None:
        files = []

    mock_dir.iterdir = Mock(return_value=files)
    mock_dir.glob = Mock(return_value=files)

    return mock_dir


# ============================================================================
# Database Mocks
# ============================================================================


def build_mock_database_connection(
    fetch_result: Any = None,
    execute_side_effect: Any = None,
) -> tuple[Mock, Mock]:
    """Build a mock database connection with cursor.

    Args:
        fetch_result: Value for cursor.fetchone() to return
        execute_side_effect: Side effect for connection.execute()

    Returns:
        Tuple of (mock_get_connection function, mock_connection)
    """
    mock_cursor = Mock()
    if fetch_result is not None:
        mock_cursor.fetchone.return_value = fetch_result
        mock_cursor.fetchall.return_value = (
            [fetch_result] if not isinstance(fetch_result, list) else fetch_result
        )
    else:
        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []

    mock_cursor.execute = Mock(return_value=mock_cursor)

    mock_conn = Mock()
    if execute_side_effect is not None:
        mock_conn.execute = Mock(side_effect=execute_side_effect)
    else:
        mock_conn.execute = Mock(return_value=mock_cursor)
    mock_conn.cursor.return_value = mock_cursor

    mock_get_connection = Mock(return_value=mock_conn)

    return mock_get_connection, mock_conn


# ============================================================================
# Builder Pattern for Complex Mocks
# ============================================================================


class CoreMockBuilder:
    """Fluent builder for constructing complex mock cores.

    Useful for tests that need specific mock configurations.

    Example:
        mock_core = (CoreMockBuilder()
                     .with_github()
                     .with_repository(has_issues=True)
                     .build())
    """

    def __init__(self) -> None:
        """Initialize builder."""
        self._attrs: dict[str, Any] = {}
        self._has_github = False
        self._has_repository = False
        self._repo_config: dict[str, Any] = {}

    def with_github(self) -> "CoreMockBuilder":
        """Add GitHub service to mock."""
        self._has_github = True
        return self

    def with_repository(self, **kwargs: Any) -> "CoreMockBuilder":
        """Add repository to mock."""
        self._has_repository = True
        self._repo_config = kwargs
        return self

    def with_attribute(self, name: str, value: Any) -> "CoreMockBuilder":
        """Add custom attribute to mock."""
        self._attrs[name] = value
        return self

    def build(self) -> Mock:
        """Build and return the mock core."""
        mock_core = Mock(**self._attrs)

        if self._has_repository:
            mock_core.issue_service = Mock()
            mock_core.issue_service.repository = build_mock_repo(**self._repo_config)

        if self._has_github:
            mock_core.github_service = Mock()

        return mock_core


# ============================================================================
# Domain Entity Mocks
# ============================================================================


def build_mock_issue(
    id: str = "issue-1",
    title: str = "Test Issue",
    status: str = "TODO",
    priority: str = "MEDIUM",
    **kwargs: Any,
) -> Mock:
    """Build a mock Issue entity.

    Args:
        id: Issue ID
        title: Issue title
        status: Issue status (TODO, IN_PROGRESS, DONE, BLOCKED)
        priority: Issue priority (LOW, MEDIUM, HIGH)
        **kwargs: Additional attributes

    Returns:
        Configured Mock Issue
    """
    from roadmap.core.domain.issue import Issue

    mock_issue = Mock(spec=Issue)
    mock_issue.id = id
    mock_issue.title = title
    mock_issue.status = status
    mock_issue.priority = priority
    for key, value in kwargs.items():
        setattr(mock_issue, key, value)
    return mock_issue


def build_mock_milestone(
    id: str = "milestone-1",
    name: str = "v1.0",
    status: str = "IN_PROGRESS",
    **kwargs: Any,
) -> Mock:
    """Build a mock Milestone entity.

    Args:
        id: Milestone ID
        name: Milestone name
        status: Milestone status
        **kwargs: Additional attributes

    Returns:
        Configured Mock Milestone
    """
    from roadmap.core.domain.milestone import Milestone

    mock_milestone = Mock(spec=Milestone)
    mock_milestone.id = id
    mock_milestone.name = name
    mock_milestone.status = status
    for key, value in kwargs.items():
        setattr(mock_milestone, key, value)
    return mock_milestone


def build_mock_comment(
    id: str = "comment-1",
    author: str = "test_user",
    content: str = "Test comment",
    **kwargs: Any,
) -> Mock:
    """Build a mock Comment entity.

    Args:
        id: Comment ID
        author: Comment author
        content: Comment content
        **kwargs: Additional attributes

    Returns:
        Configured Mock Comment
    """
    from roadmap.core.domain.comment import Comment

    mock_comment = Mock(spec=Comment)
    mock_comment.id = id
    mock_comment.author = author
    mock_comment.content = content
    for key, value in kwargs.items():
        setattr(mock_comment, key, value)
    return mock_comment


def build_mock_roadmap_core(
    has_github: bool = False,
    has_repository: bool = True,
    **kwargs: Any,
) -> Mock:
    """Build a mock RoadmapCore instance with domain entities.

    Args:
        has_github: If True, add github_service
        has_repository: If True, add issue_service with repository
        **kwargs: Additional attributes

    Returns:
        Configured Mock RoadmapCore
    """
    from roadmap.infrastructure.coordination.core import RoadmapCore

    mock_core = Mock(spec=RoadmapCore)
    for key, value in kwargs.items():
        setattr(mock_core, key, value)

    if has_repository:
        mock_core.issue_service = Mock()
        mock_core.issue_service.repository = build_mock_repo()

    if has_github:
        mock_core.github_service = Mock()

    return mock_core
