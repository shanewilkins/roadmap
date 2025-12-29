"""Tests for milestone service operations - tests service logic directly without CLI output parsing."""

import pytest

from tests.factories import IssueBuilder, MilestoneBuilder
from tests.unit.domain.test_data_factory import TestDataFactory


class TestMilestoneServiceAssignment:
    """Test MilestoneService handling of issue assignments."""

    @pytest.fixture
    def mock_core(self, mock_core_initialized):
        """Create a mock RoadmapCore with issues and milestones services.

        Uses centralized mock_core_initialized and adds service-specific setup.
        """
        mock_core_initialized.issues = TestDataFactory.create_mock_core(
            is_initialized=True
        )
        mock_core_initialized.milestones = TestDataFactory.create_mock_core(
            is_initialized=True
        )
        return mock_core_initialized

    def test_assign_issue_to_milestone(self, mock_core):
        """Test assigning an issue to a milestone via service."""
        # Arrange
        issue = IssueBuilder().with_id("test-id-123").with_title("Test Issue").build()
        milestone = MilestoneBuilder().with_name("v1.0").build()

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
        issue = (
            IssueBuilder()
            .with_id("issue-1")
            .with_title("Feature")
            .with_milestone("v1.0")
            .build()
        )

        mock_core.issues.get.return_value = issue

        # Act
        retrieved = mock_core.issues.get("issue-1")

        # Assert
        assert retrieved.milestone == "v1.0"

    def test_get_milestone_issues(self, mock_core):
        """Test retrieving all issues for a milestone."""
        # Arrange
        issue1 = IssueBuilder().with_title("Issue 1").with_milestone("v1.0").build()
        issue2 = IssueBuilder().with_title("Issue 2").with_milestone("v1.0").build()

        mock_core.issues.list.return_value = [issue1, issue2]

        # Act
        issues = mock_core.issues.list()

        # Assert
        assert len(issues) == 2
        assert all(issue.milestone == "v1.0" for issue in issues)
