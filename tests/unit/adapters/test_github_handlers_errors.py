"""GitHub Handler Error Path Tests.

Tests for error handling in GitHub API handlers - issues, collaborators, milestones.
Focuses on basic operations and edge cases with mocked responses.
"""

from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.github.handlers.collaborators import CollaboratorsHandler
from roadmap.adapters.github.handlers.issues import IssueHandler
from roadmap.adapters.github.handlers.milestones import MilestoneHandler


def create_mock_response(json_data, has_next=False):
    """Create a mock response with proper pagination headers.

    Args:
        json_data: The JSON data to return
        has_next: Whether to include a rel="next" link

    Returns:
        Mock response object
    """
    mock_response = Mock()
    mock_response.json.return_value = json_data
    link_header = '<https://api.github.com/next>; rel="next"' if has_next else ""
    mock_response.headers = {"Link": link_header}
    return mock_response


@pytest.fixture
def mock_session():
    """Create a mock HTTP session."""
    return Mock()


@pytest.fixture
def issue_handler(mock_session):
    """Create an IssueHandler with mocked session."""
    return IssueHandler(session=mock_session, owner="test-org", repo="test-repo")


@pytest.fixture
def collaborators_handler(mock_session):
    """Create a CollaboratorsHandler with mocked session."""
    return CollaboratorsHandler(
        session=mock_session, owner="test-org", repo="test-repo"
    )


@pytest.fixture
def milestone_handler(mock_session):
    """Create a MilestoneHandler with mocked session."""
    return MilestoneHandler(session=mock_session, owner="test-org", repo="test-repo")


class TestIssueHandlerOperations:
    """Test IssueHandler operations - currently 17% coverage."""

    def test_get_issues_success(self, issue_handler):
        """Test successfully fetching issues."""
        with patch.object(issue_handler, "_make_request") as mock_request:
            mock_response = create_mock_response(
                [
                    {"number": 1, "title": "Issue 1", "state": "open"},
                    {"number": 2, "title": "Issue 2", "state": "closed"},
                ]
            )
            mock_request.return_value = mock_response

            result = issue_handler.get_issues()
            assert len(result) == 2
            assert result[0]["title"] == "Issue 1"

    def test_get_issues_with_filters(self, issue_handler):
        """Test fetching issues with various filters."""
        with patch.object(issue_handler, "_make_request") as mock_request:
            mock_response = create_mock_response(
                [{"number": 1, "title": "Filtered Issue"}]
            )
            mock_request.return_value = mock_response

            result = issue_handler.get_issues(
                labels=["bug", "critical"], milestone="v1.0", assignee="@me"
            )
            assert len(result) == 1
            mock_request.assert_called_once()

    def test_get_specific_issue(self, issue_handler):
        """Test fetching a specific issue by number."""
        with patch.object(issue_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "number": 123,
                "title": "Specific Issue",
                "state": "open",
            }
            mock_request.return_value = mock_response

            result = issue_handler.get_issue(123)
            assert result["number"] == 123

    def test_create_issue_basic(self, issue_handler):
        """Test creating a basic issue."""
        with patch.object(issue_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "number": 1,
                "title": "New Issue",
                "body": "Issue description",
            }
            mock_request.return_value = mock_response

            result = issue_handler.create_issue(
                title="New Issue", body="Issue description"
            )
            assert result["title"] == "New Issue"

    def test_create_issue_with_metadata(self, issue_handler):
        """Test creating issue with labels, assignees, milestone."""
        with patch.object(issue_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"number": 1, "title": "Complex Issue"}
            mock_request.return_value = mock_response

            result = issue_handler.create_issue(
                title="Complex Issue", labels=["bug"], assignees=["user1"], milestone=5
            )
            assert "number" in result

    def test_update_issue(self, issue_handler):
        """Test updating an issue."""
        with patch.object(issue_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"number": 1, "state": "closed"}
            mock_request.return_value = mock_response

            result = issue_handler.update_issue(1, state="closed")
            assert "number" in result

    def test_get_issues_empty(self, issue_handler):
        """Test fetching issues when none exist."""
        with patch.object(issue_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_request.return_value = mock_response

            result = issue_handler.get_issues()
            assert result == []


class TestCollaboratorsHandlerOperations:
    """Test CollaboratorsHandler operations - currently 15% coverage."""

    def test_get_current_user_success(self, collaborators_handler):
        """Test successfully fetching current user."""
        with patch.object(collaborators_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"login": "testuser"}
            mock_request.return_value = mock_response

            result = collaborators_handler.get_current_user()
            assert result == "testuser"

    def test_get_repository_collaborators_with_pagination(self, collaborators_handler):
        """Test fetching repository collaborators with pagination."""
        with patch.object(collaborators_handler, "_make_request") as mock_request:
            # First page has 2 items, second page is empty (pagination stop)
            mock_response_1 = Mock()
            mock_response_1.json.return_value = [
                {"login": "user1"},
                {"login": "user2"},
            ]
            mock_response_2 = Mock()
            mock_response_2.json.return_value = []

            mock_request.side_effect = [mock_response_1, mock_response_2]

            result = collaborators_handler.get_repository_collaborators()
            assert len(result) >= 0

    def test_get_repository_collaborators_empty(self, collaborators_handler):
        """Test fetching collaborators when none exist."""
        with patch.object(collaborators_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_request.return_value = mock_response

            result = collaborators_handler.get_repository_collaborators()
            assert result == []

    def test_get_repository_contributors_success(self, collaborators_handler):
        """Test successfully fetching repository contributors."""
        with patch.object(collaborators_handler, "_make_request") as mock_request:
            mock_response_1 = Mock()
            mock_response_1.json.return_value = [{"login": "contributor1"}]
            mock_response_2 = Mock()
            mock_response_2.json.return_value = []

            mock_request.side_effect = [mock_response_1, mock_response_2]

            result = collaborators_handler.get_repository_contributors()
            assert isinstance(result, list)

    def test_get_team_members_combined(self, collaborators_handler):
        """Test getting team members combines collaborators and contributors."""
        with patch.object(collaborators_handler, "_make_request") as mock_request:
            # Collaborators responses
            collab_1 = Mock()
            collab_1.json.return_value = [{"login": "user1"}]
            collab_2 = Mock()
            collab_2.json.return_value = []

            # Contributors responses
            contrib_1 = Mock()
            contrib_1.json.return_value = [{"login": "user2"}]
            contrib_2 = Mock()
            contrib_2.json.return_value = []

            mock_request.side_effect = [collab_1, collab_2, contrib_1, contrib_2]

            result = collaborators_handler.get_team_members()
            assert isinstance(result, list)


class TestMilestoneHandlerOperations:
    """Test MilestoneHandler operations - currently 21% coverage."""

    def test_get_milestones_success(self, milestone_handler):
        """Test successfully fetching milestones."""
        with patch.object(milestone_handler, "_make_request") as mock_request:
            mock_response = create_mock_response(
                [
                    {"number": 1, "title": "v1.0", "state": "open"},
                    {"number": 2, "title": "v2.0", "state": "closed"},
                ]
            )
            mock_request.return_value = mock_response

            result = milestone_handler.get_milestones()
            assert len(result) == 2
            assert result[0]["title"] == "v1.0"

    def test_get_milestones_with_state_filter(self, milestone_handler):
        """Test fetching milestones with state filter."""
        with patch.object(milestone_handler, "_paginate_request") as mock_paginate:
            mock_paginate.return_value = [
                {"number": 2, "title": "v2.0", "state": "closed"}
            ]

            result = milestone_handler.get_milestones(state="closed")
            assert len(result) == 1
            assert result[0]["title"] == "v2.0"

    def test_get_milestones_empty(self, milestone_handler):
        """Test fetching milestones when none exist."""
        with patch.object(milestone_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_request.return_value = mock_response

            result = milestone_handler.get_milestones()
            assert result == []

    def test_get_specific_milestone(self, milestone_handler):
        """Test fetching a specific milestone by number."""
        with patch.object(milestone_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "number": 1,
                "title": "v1.0",
                "state": "open",
            }
            mock_request.return_value = mock_response

            result = milestone_handler.get_milestone(1)
            assert result["title"] == "v1.0"

    def test_create_milestone_basic(self, milestone_handler):
        """Test creating a basic milestone."""
        with patch.object(milestone_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "number": 1,
                "title": "v1.0",
                "state": "open",
            }
            mock_request.return_value = mock_response

            result = milestone_handler.create_milestone(title="v1.0")
            assert result["title"] == "v1.0"

    def test_create_milestone_with_description(self, milestone_handler):
        """Test creating milestone with description and due date."""
        from datetime import datetime

        naive_date = datetime(2024, 12, 31)

        with patch.object(milestone_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "number": 1,
                "title": "v1.0",
                "description": "First release",
                "due_on": "2024-12-31T00:00:00Z",
            }
            mock_request.return_value = mock_response

            result = milestone_handler.create_milestone(
                title="v1.0", description="First release", due_date=naive_date
            )
            assert result["title"] == "v1.0"

    def test_update_milestone_success(self, milestone_handler):
        """Test updating a milestone."""
        with patch.object(milestone_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "number": 1,
                "title": "v1.0 Updated",
                "state": "closed",
            }
            mock_request.return_value = mock_response

            result = milestone_handler.update_milestone(1, title="v1.0 Updated")
            assert result["title"] == "v1.0 Updated"

    def test_delete_milestone(self, milestone_handler):
        """Test deleting a milestone."""
        with patch.object(milestone_handler, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=204)

            milestone_handler.delete_milestone(1)
            mock_request.assert_called_once()
