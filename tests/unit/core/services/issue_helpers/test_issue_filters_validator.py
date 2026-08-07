"""Tests for issue filters module."""

from roadmap.core.services.issue_helpers.issue_filters import (
    IssueFilterValidator,
)


class TestIssueFilterValidator:
    """Tests for IssueFilterValidator."""

    def test_validate_filters_no_conflicts(self):
        """Test valid filter combinations."""
        is_valid, error = IssueFilterValidator.validate_filters(
            assignee=None,
            my_issues=False,
            backlog=False,
            unassigned=False,
            next_milestone=False,
            milestone=None,
        )

        assert is_valid is True
        assert error is None

    def test_validate_filters_assignee_only(self):
        """Test valid assignee-only filter."""
        is_valid, error = IssueFilterValidator.validate_filters(
            assignee="user1",
            my_issues=False,
            backlog=False,
            unassigned=False,
            next_milestone=False,
            milestone=None,
        )

        assert is_valid is True
        assert error is None

    def test_validate_filters_my_issues_only(self):
        """Test valid my_issues filter."""
        is_valid, error = IssueFilterValidator.validate_filters(
            assignee=None,
            my_issues=True,
            backlog=False,
            unassigned=False,
            next_milestone=False,
            milestone=None,
        )

        assert is_valid is True
        assert error is None

    def test_validate_filters_backlog_only(self):
        """Test valid backlog filter."""
        is_valid, error = IssueFilterValidator.validate_filters(
            assignee=None,
            my_issues=False,
            backlog=True,
            unassigned=False,
            next_milestone=False,
            milestone=None,
        )

        assert is_valid is True
        assert error is None

    def test_validate_filters_milestone_only(self):
        """Test valid milestone filter."""
        is_valid, error = IssueFilterValidator.validate_filters(
            assignee=None,
            my_issues=False,
            backlog=False,
            unassigned=False,
            next_milestone=False,
            milestone="v1-0",
        )

        assert is_valid is True
        assert error is None

    def test_validate_filters_assignee_and_my_issues_conflict(self):
        """Test conflicting assignee filters."""
        is_valid, error = IssueFilterValidator.validate_filters(
            assignee="user1",
            my_issues=True,
            backlog=False,
            unassigned=False,
            next_milestone=False,
            milestone=None,
        )

        assert is_valid is False
        assert error is not None
        assert "assignee" in error.lower() and "my-issues" in error.lower()

    def test_validate_filters_backlog_and_unassigned_conflict(self):
        """Test conflicting collection filters."""
        is_valid, error = IssueFilterValidator.validate_filters(
            assignee=None,
            my_issues=False,
            backlog=True,
            unassigned=True,
            next_milestone=False,
            milestone=None,
        )

        assert is_valid is False

    def test_validate_filters_backlog_and_next_milestone_conflict(self):
        """Test conflicting collection filters."""
        is_valid, error = IssueFilterValidator.validate_filters(
            assignee=None,
            my_issues=False,
            backlog=True,
            unassigned=False,
            next_milestone=True,
            milestone=None,
        )

        assert is_valid is False

    def test_validate_filters_milestone_and_next_milestone_conflict(self):
        """Test conflicting collection filters."""
        is_valid, error = IssueFilterValidator.validate_filters(
            assignee=None,
            my_issues=False,
            backlog=False,
            unassigned=False,
            next_milestone=True,
            milestone="v1-0",
        )

        assert is_valid is False
