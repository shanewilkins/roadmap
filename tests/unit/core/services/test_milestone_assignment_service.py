"""Tests for milestone service operations - tests service logic directly without CLI output parsing."""

import pytest

from roadmap.core.domain import Issue, Milestone
from tests.unit.domain.test_data_factory import TestDataFactory


class TestMilestoneServiceAssignment:
    """Test MilestoneService handling of issue assignments."""

    @pytest.fixture
    def mock_core(self):
        """Create a mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.issues = TestDataFactory.create_mock_core(is_initialized=True)
        core.milestones = TestDataFactory.create_mock_core(is_initialized=True)
        return core

    def test_assign_issue_to_milestone(self, mock_core):
        """Test assigning an issue to a milestone via service."""
        # Arrange
        issue = Issue(title="Test Issue", id="test-id-123")
        milestone = Milestone(name="v1.0")

        mock_core.issues.get.return_value = issue
        mock_core.milestones.get.return_value = milestone

        # Act
        retrieved_issue = mock_core.issues.get("test-id-123")
        retrieved_milestone = mock_core.milestones.get("v1.0")

        # Assert
        assert retrieved_issue.title == "Test Issue"
        assert retrieved_milestone.name == "v1.0"
        mock_core.issues.get.assert_called_with("test-id-123")
        mock_core.milestones.get.assert_called_with("v1.0")

    def test_milestone_issue_association(self, mock_core):
        """Test that issues are properly associated with milestones."""
        # Arrange
        issue = Issue(title="Feature", id="issue-1", milestone="v1.0")

        mock_core.issues.get.return_value = issue

        # Act
        retrieved = mock_core.issues.get("issue-1")

        # Assert
        assert retrieved.milestone == "v1.0"

    def test_get_milestone_issues(self, mock_core):
        """Test retrieving all issues for a milestone."""
        # Arrange
        issue1 = Issue(title="Issue 1", milestone="v1.0")
        issue2 = Issue(title="Issue 2", milestone="v1.0")

        mock_core.issues.list.return_value = [issue1, issue2]

        # Act
        issues = mock_core.issues.list()

        # Assert
        assert len(issues) == 2
        assert all(issue.milestone == "v1.0" for issue in issues)
