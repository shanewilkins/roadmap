"""Tests for comment functionality."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from roadmap.github_client import GitHubAPIError, GitHubClient
from roadmap.models import Comment


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    with patch("roadmap.github_client.GitHubClient._check_repository"):
        client = GitHubClient(token="fake-token", owner="test-owner", repo="test-repo")
        return client


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


class TestGitHubClientComments:
    """Test GitHub client comment methods."""

    @patch("roadmap.github_client.GitHubClient._make_request")
    def test_get_issue_comments(self, mock_request, mock_github_client):
        """Test getting comments for an issue."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": 123456,
                "body": "This is the first comment",
                "user": {"login": "user1"},
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z",
                "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123456",
            },
            {
                "id": 123457,
                "body": "This is the second comment",
                "user": {"login": "user2"},
                "created_at": "2023-01-01T13:00:00Z",
                "updated_at": "2023-01-01T13:30:00Z",
                "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123457",
            },
        ]
        mock_request.return_value = mock_response

        # Test the method
        comments = mock_github_client.get_issue_comments(1)

        assert len(comments) == 2
        assert comments[0].id == 123456
        assert comments[0].author == "user1"
        assert comments[0].body == "This is the first comment"
        assert comments[1].id == 123457
        assert comments[1].author == "user2"
        assert comments[1].body == "This is the second comment"

        # Verify the API call
        mock_request.assert_called_once_with(
            "GET", "/repos/test-owner/test-repo/issues/1/comments"
        )

    @patch("roadmap.github_client.GitHubClient._make_request")
    def test_create_issue_comment(self, mock_request, mock_github_client):
        """Test creating a comment on an issue."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 123456,
            "body": "This is a new comment",
            "user": {"login": "testuser"},
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123456",
        }
        mock_request.return_value = mock_response

        # Test the method
        comment = mock_github_client.create_issue_comment(1, "This is a new comment")

        assert comment.id == 123456
        assert comment.author == "testuser"
        assert comment.body == "This is a new comment"
        assert comment.issue_id == "1"

        # Verify the API call
        mock_request.assert_called_once_with(
            "POST",
            "/repos/test-owner/test-repo/issues/1/comments",
            json={"body": "This is a new comment"},
        )

    @patch("roadmap.github_client.GitHubClient._make_request")
    def test_update_issue_comment(self, mock_request, mock_github_client):
        """Test updating an existing comment."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 123456,
            "body": "This is an updated comment",
            "user": {"login": "testuser"},
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T13:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/issues/1#issuecomment-123456",
        }
        mock_request.return_value = mock_response

        # Test the method
        comment = mock_github_client.update_issue_comment(
            123456, "This is an updated comment"
        )

        assert comment.id == 123456
        assert comment.author == "testuser"
        assert comment.body == "This is an updated comment"

        # Verify the API call
        mock_request.assert_called_once_with(
            "PATCH",
            "/repos/test-owner/test-repo/issues/comments/123456",
            json={"body": "This is an updated comment"},
        )

    @patch("roadmap.github_client.GitHubClient._make_request")
    def test_delete_issue_comment(self, mock_request, mock_github_client):
        """Test deleting a comment."""
        # Test the method
        mock_github_client.delete_issue_comment(123456)

        # Verify the API call
        mock_request.assert_called_once_with(
            "DELETE", "/repos/test-owner/test-repo/issues/comments/123456"
        )

    @patch("roadmap.github_client.GitHubClient._make_request")
    def test_get_issue_comments_empty(self, mock_request, mock_github_client):
        """Test getting comments when there are none."""
        # Mock empty API response
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        # Test the method
        comments = mock_github_client.get_issue_comments(1)

        assert len(comments) == 0
        assert comments == []


class TestCommentCLI:
    """Test comment CLI commands."""

    def test_comment_help_available(self):
        """Test that comment commands are available in CLI."""
        # This is a basic test to ensure the commands are properly registered
        from roadmap.cli import main

        # The main function should have a comment group
        comment_group = None
        for command in main.commands.values():
            if hasattr(command, "name") and command.name == "comment":
                comment_group = command
                break

        assert comment_group is not None
        assert "list" in comment_group.commands
        assert "create" in comment_group.commands
        assert "edit" in comment_group.commands
        assert "delete" in comment_group.commands


class TestBlockedStatus:
    """Test blocked status functionality."""

    def test_blocked_status_enum(self):
        """Test that blocked status is properly defined."""
        from roadmap.models import Status

        assert Status.BLOCKED == "blocked"
        assert Status.BLOCKED in Status

        # Test all statuses in order
        statuses = list(Status)
        assert Status.TODO in statuses
        assert Status.IN_PROGRESS in statuses
        assert Status.BLOCKED in statuses
        assert Status.REVIEW in statuses
        assert Status.DONE in statuses

    def test_github_client_blocked_status_mapping(self):
        """Test that GitHub client handles blocked status."""
        from unittest.mock import patch

        from roadmap.github_client import GitHubClient
        from roadmap.models import Status

        with patch("roadmap.github_client.GitHubClient._check_repository"):
            client = GitHubClient(token="fake-token", owner="test", repo="test")

            # Test status to labels
            labels = client.status_to_labels(Status.BLOCKED)
            assert labels == ["status:blocked"]

            # Test labels to status
            status = client.labels_to_status(["status:blocked"])
            assert status == Status.BLOCKED

    def test_blocked_status_label_setup(self):
        """Test that blocked status label is included in default setup."""
        from unittest.mock import Mock, patch

        from roadmap.github_client import GitHubClient

        with patch("roadmap.github_client.GitHubClient._check_repository"):
            with patch(
                "roadmap.github_client.GitHubClient._make_request"
            ) as mock_request:
                # Mock get_labels response
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
                assert blocked_label_call[1]["json"]["color"] == "d93f0b"
                assert (
                    "blocked waiting for dependencies"
                    in blocked_label_call[1]["json"]["description"]
                )
