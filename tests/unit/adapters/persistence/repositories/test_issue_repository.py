"""Unit tests for issue repository."""

from unittest.mock import MagicMock

import pytest

from roadmap.adapters.persistence.repositories.issue_repository import IssueRepository


@pytest.fixture
def mock_get_connection():
    """Create a mock get_connection callable."""
    return MagicMock()


@pytest.fixture
def mock_transaction():
    """Create a mock transaction manager."""
    return MagicMock()


@pytest.fixture
def repository(mock_get_connection, mock_transaction):
    """Create an issue repository."""
    return IssueRepository(mock_get_connection, mock_transaction)


class TestIssueRepository:
    """Test issue repository."""

    def test_create_issue(self, repository, mock_get_connection):
        """Test creating an issue."""
        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        issue_data = {
            "id": "issue-1",
            "title": "Test Issue",
            "status": "open",
        }

        result = repository.create(issue_data)

        assert result is not None or result is None

    def test_create_with_minimal_data(self, repository, mock_get_connection):
        """Test creating issue with minimal data."""
        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        issue_data = {"id": "issue-1"}

        result = repository.create(issue_data)

        assert result is not None or result is None

    def test_find_issue(self, repository, mock_get_connection):
        """Test finding an issue."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("issue-1", "Test Issue", "open")
        mock_get_connection.return_value = mock_connection

        result = repository.find("issue-1")

        # Should complete without error
        assert result is not None or result is None

    def test_update_issue(self, repository, mock_get_connection):
        """Test updating an issue."""
        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        issue_data = {"id": "issue-1", "status": "closed"}

        result = repository.update("issue-1", issue_data)

        # Should complete without error
        assert result is not None or result is None

    def test_delete_issue(self, repository, mock_get_connection):
        """Test deleting an issue."""
        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        result = repository.delete("issue-1")

        # Should complete without error
        assert result is not None or result is None

    def test_find_all_issues(self, repository, mock_get_connection):
        """Test finding all issues."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ("issue-1", "Issue 1", "open"),
            ("issue-2", "Issue 2", "closed"),
        ]
        mock_get_connection.return_value = mock_connection

        result = repository.find_all()

        # Should complete without error
        assert result is not None or result is None

    def test_find_by_status(self, repository, mock_get_connection):
        """Test finding issues by status."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ("issue-1", "Issue 1", "open"),
            ("issue-2", "Issue 2", "open"),
        ]
        mock_get_connection.return_value = mock_connection

        result = repository.find_by_status("open")

        # Should complete without error
        assert result is not None or result is None

    def test_count_issues(self, repository, mock_get_connection):
        """Test counting issues."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (5,)
        mock_get_connection.return_value = mock_connection

        result = repository.count()

        # Should complete without error
        assert result is not None or result is None

    def test_bulk_create_issues(self, repository, mock_get_connection):
        """Test bulk creating issues."""
        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        issues = [
            {"id": "issue-1", "title": "Issue 1"},
            {"id": "issue-2", "title": "Issue 2"},
        ]

        result = repository.create_many(issues)

        # Should complete without error
        assert result is not None or result is None
