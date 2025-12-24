"""Tests for comment functionality."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests

from roadmap.adapters.github.handlers.comments import CommentsHandler
from roadmap.core.domain import Comment
from tests.unit.shared.test_helpers import create_mock_comment


# Local fixture for real CommentsHandler with mocked session
@pytest.fixture
def comments_handler_with_session():
    """Create a real CommentsHandler with mocked session.

    Note: This is different from mock_comments_handler (which is a pure mock).
    This fixture creates a real CommentsHandler instance that can be patched.
    """
    mock_session = Mock(spec=requests.Session)
    handler = CommentsHandler(
        session=mock_session, owner="test-owner", repo="test-repo"
    )
    return handler


class TestComment:
    """Test Comment model."""

    def test_comment_creation(self):
        """Test creating a Comment object."""
        comment = Comment(
            id=123456,
            issue_id="test-issue-1",
            author="testuser",
            body="This is a test comment",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 1, 1, 12, 0, 0),
            github_url="https://github.com/owner/repo/issues/1#issuecomment-123456",
        )

        assert comment.id == 123456
        assert comment.issue_id == "test-issue-1"
        assert comment.author == "testuser"
        assert comment.body == "This is a test comment"
        assert str(comment) == "Comment by testuser on 2023-01-01 12:00"

    def test_comment_without_github_url(self):
        """Test creating a Comment without GitHub URL."""
        comment = Comment(
            id=123456,
            issue_id="test-issue-1",
            author="testuser",
            body="This is a test comment",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 1, 1, 12, 0, 0),
        )

        assert comment.github_url is None


class TestCommentsHandler:
    """Test CommentsHandler methods."""

    def test_get_issue_comments(self, comments_handler_with_session):
        """Test getting comments for an issue returns correct count."""
        # Create mock comments using factory
        comment1 = create_mock_comment(
            id=123456,
            author="user1",
            body="This is the first comment",
        )
        comment2 = create_mock_comment(
            id=123457,
            author="user2",
            body="This is the second comment",
        )

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": comment1.id,
                "body": comment1.body,
                "user": {"login": comment1.author},
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z",
                "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123456",
            },
            {
                "id": comment2.id,
                "body": comment2.body,
                "user": {"login": comment2.author},
                "created_at": "2023-01-01T13:00:00Z",
                "updated_at": "2023-01-01T13:30:00Z",
                "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123457",
            },
        ]

        # Mock the _make_request method
        with patch.object(
            comments_handler_with_session, "_make_request", return_value=mock_response
        ):
            # Test the method
            comments = comments_handler_with_session.get_issue_comments(1)

            assert len(comments) == 2

    def test_get_issue_comments_first_comment_data(self, comments_handler_with_session):
        """Test that first comment data is correctly populated."""
        # Create mock comments using factory
        comment1 = create_mock_comment(
            id=123456,
            author="user1",
            body="This is the first comment",
        )
        comment2 = create_mock_comment(
            id=123457,
            author="user2",
            body="This is the second comment",
        )

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": comment1.id,
                "body": comment1.body,
                "user": {"login": comment1.author},
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z",
                "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123456",
            },
            {
                "id": comment2.id,
                "body": comment2.body,
                "user": {"login": comment2.author},
                "created_at": "2023-01-01T13:00:00Z",
                "updated_at": "2023-01-01T13:30:00Z",
                "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123457",
            },
        ]

        # Mock the _make_request method
        with patch.object(
            comments_handler_with_session, "_make_request", return_value=mock_response
        ):
            comments = comments_handler_with_session.get_issue_comments(1)

            assert comments[0].id == comment1.id
            assert comments[0].author == comment1.author
            assert comments[0].body == comment1.body

    def test_get_issue_comments_second_comment_data(self, comments_handler_with_session):
        """Test that second comment data is correctly populated."""
        # Create mock comments using factory
        comment1 = create_mock_comment(
            id=123456,
            author="user1",
            body="This is the first comment",
        )
        comment2 = create_mock_comment(
            id=123457,
            author="user2",
            body="This is the second comment",
        )

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": comment1.id,
                "body": comment1.body,
                "user": {"login": comment1.author},
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z",
                "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123456",
            },
            {
                "id": comment2.id,
                "body": comment2.body,
                "user": {"login": comment2.author},
                "created_at": "2023-01-01T13:00:00Z",
                "updated_at": "2023-01-01T13:30:00Z",
                "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123457",
            },
        ]

        # Mock the _make_request method
        with patch.object(
            comments_handler_with_session, "_make_request", return_value=mock_response
        ):
            comments = comments_handler_with_session.get_issue_comments(1)

            assert comments[1].id == comment2.id
            assert comments[1].author == comment2.author
            assert comments[1].body == comment2.body

    def test_get_issue_comments_makes_correct_api_call(self, comments_handler_with_session):
        """Test that get_issue_comments makes the correct API call."""
        # Create mock comments using factory
        comment1 = create_mock_comment(
            id=123456,
            author="user1",
            body="This is the first comment",
        )
        comment2 = create_mock_comment(
            id=123457,
            author="user2",
            body="This is the second comment",
        )

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": comment1.id,
                "body": comment1.body,
                "user": {"login": comment1.author},
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z",
                "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123456",
            },
            {
                "id": comment2.id,
                "body": comment2.body,
                "user": {"login": comment2.author},
                "created_at": "2023-01-01T13:00:00Z",
                "updated_at": "2023-01-01T13:30:00Z",
                "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123457",
            },
        ]

        # Mock the _make_request method
        with patch.object(
            comments_handler_with_session, "_make_request", return_value=mock_response
        ):
            # Test the method
            comments_handler_with_session.get_issue_comments(1)

            # Verify the API call
            comments_handler_with_session._make_request.assert_called_once_with(
                "GET", "/repos/test-owner/test-repo/issues/1/comments"
            )

    def test_create_issue_comment(self, comments_handler_with_session):
        """Test creating a comment on an issue.

        Phase 1C refactoring:
        - Use create_mock_comment() for realistic mock data
        """
        # Create mock comment using factory
        new_comment = create_mock_comment(
            id=123456,
            author="testuser",
            body="This is a new comment",
        )

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": new_comment.id,
            "body": new_comment.body,
            "user": {"login": new_comment.author},
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123456",
        }

        # Mock the _make_request method
        with patch.object(
            comments_handler_with_session, "_make_request", return_value=mock_response
        ):
            # Test the method
            comment = comments_handler_with_session.create_issue_comment(1, new_comment.body)

            assert comment.id == new_comment.id
            assert comment.author == new_comment.author
            assert comment.body == new_comment.body

            # Verify the API call
            comments_handler_with_session._make_request.assert_called_once_with(
                "POST",
                "/repos/test-owner/test-repo/issues/1/comments",
                json={"body": new_comment.body},
            )

    def test_update_issue_comment(self, comments_handler_with_session):
        """Test updating an existing comment.

        Phase 1C refactoring:
        - Use create_mock_comment() for realistic mock data
        """
        # Create mock comment using factory
        updated_comment = create_mock_comment(
            id=123456,
            author="testuser",
            body="This is an updated comment",
        )

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": updated_comment.id,
            "body": updated_comment.body,
            "user": {"login": updated_comment.author},
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T13:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123456",
        }

        # Mock the _make_request method
        with patch.object(
            comments_handler_with_session, "_make_request", return_value=mock_response
        ):
            # Test the method
            comment = comments_handler_with_session.update_issue_comment(
                updated_comment.id, updated_comment.body
            )

            assert comment.id == updated_comment.id
            assert comment.author == updated_comment.author
            assert comment.body == updated_comment.body

            # Verify the API call
            comments_handler_with_session._make_request.assert_called_once_with(
                "PATCH",
                "/repos/test-owner/test-repo/issues/comments/123456",
                json={"body": updated_comment.body},
            )

    def test_delete_issue_comment(self, comments_handler_with_session):
        """Test deleting a comment."""
        # Mock the _make_request method
        with patch.object(comments_handler_with_session, "_make_request"):
            # Test the method
            comments_handler_with_session.delete_issue_comment(123456)

            # Verify the API call
            comments_handler_with_session._make_request.assert_called_once_with(
                "DELETE", "/repos/test-owner/test-repo/issues/comments/123456"
            )

    def test_get_issue_comments_empty(self, comments_handler_with_session):
        """Test getting comments when there are none."""
        # Mock empty API response
        mock_response = Mock()
        mock_response.json.return_value = []

        # Mock the _make_request method
        with patch.object(
            comments_handler_with_session, "_make_request", return_value=mock_response
        ):
            # Test the method
            comments = comments_handler_with_session.get_issue_comments(1)

            assert len(comments) == 0
            assert comments == []


class TestCommentCLI:
    """Test comment CLI commands."""

    def test_comment_help_available(self):
        """Test that comment commands are available in CLI."""
        # This is a basic test to ensure the commands are properly registered
        from roadmap.adapters.cli import main

        # The main function should have a comment group
        comment_group = None
        for command in main.commands.values():
            if hasattr(command, "name") and command.name == "comment":
                comment_group = command
                break

        assert comment_group is not None
        assert "list" in comment_group.commands  # type: ignore[attr-defined]
        assert "create" in comment_group.commands  # type: ignore[attr-defined]
        assert "edit" in comment_group.commands  # type: ignore[attr-defined]
        assert "delete" in comment_group.commands  # type: ignore[attr-defined]


class TestBlockedStatus:
    """Test blocked status functionality."""

    def test_blocked_status_enum_value(self):
        """Test that blocked status has correct value."""
        from roadmap.core.domain import Status

        assert Status.BLOCKED == "blocked"

    def test_blocked_status_enum_membership(self):
        """Test that blocked status is in Status enum."""
        from roadmap.core.domain import Status

        assert Status.BLOCKED in Status

    def test_all_statuses_exist(self):
        """Test that all expected statuses exist."""
        from roadmap.core.domain import Status

        # Test all statuses in order
        statuses = list(Status)
        assert Status.TODO in statuses
        assert Status.IN_PROGRESS in statuses
        assert Status.BLOCKED in statuses
        assert Status.REVIEW in statuses
        assert Status.CLOSED in statuses

    def test_github_client_blocked_status_to_labels(self):
        """Test that GitHub client converts blocked status to labels."""
        from unittest.mock import patch

        from roadmap.adapters.github.github import GitHubClient
        from roadmap.core.domain import Status

        with patch("roadmap.adapters.github.github.GitHubClient._check_repository"):
            client = GitHubClient(token="fake-token", owner="test", repo="test")

            # Test status to labels
            labels = client.status_to_labels(Status.BLOCKED)
            assert labels == ["status:blocked"]

    def test_github_client_blocked_labels_to_status(self):
        """Test that GitHub client converts blocked labels to status."""
        from unittest.mock import patch

        from roadmap.adapters.github.github import GitHubClient
        from roadmap.core.domain import Status

        with patch("roadmap.adapters.github.github.GitHubClient._check_repository"):
            client = GitHubClient(token="fake-token", owner="test", repo="test")

            # Test labels to status
            status = client.labels_to_status(["status:blocked"])
            assert status == Status.BLOCKED

    def test_blocked_status_label_setup(self):
        """Test that blocked status label is included in default setup."""
        from unittest.mock import Mock, patch

        from roadmap.adapters.github.github import GitHubClient

        with patch(
            "roadmap.adapters.github.handlers.base.BaseGitHubHandler._make_request"
        ) as mock_request:
            # Mock get_labels response (empty list so all labels get created)
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_request.return_value = mock_response

            client = GitHubClient(token="fake-token", owner="test", repo="test")

            # This should call create_label for each default label
            client.setup_default_labels()

            # Verify that status:blocked label was created
            calls = mock_request.call_args_list
            blocked_label_call = None

            for call in calls:
                if call[1].get("json", {}).get("name") == "status:blocked":
                    blocked_label_call = call
                    break

            assert blocked_label_call is not None
            assert blocked_label_call[1]["json"]["color"].lower() == "d73a49"
            assert "Blocked" in blocked_label_call[1]["json"]["description"]
