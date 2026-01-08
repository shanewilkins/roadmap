"""Tests for coordinator parameters dataclasses."""

from datetime import datetime

import pytest

from roadmap.core.domain import IssueType, Priority
from roadmap.infrastructure.coordinator_params import (
    IssueCreateParams,
    IssueListParams,
    IssueUpdateParams,
    MilestoneCreateParams,
    MilestoneUpdateParams,
    ProjectCreateParams,
    ProjectUpdateParams,
)


class TestIssueCreateParams:
    """Test IssueCreateParams dataclass."""

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            # Default values
            (
                {"title": "Test Issue"},
                {
                    "title": "Test Issue",
                    "priority": Priority.MEDIUM,
                    "issue_type": IssueType.OTHER,
                    "milestone": None,
                    "labels": None,
                    "assignee": None,
                    "estimated_hours": None,
                    "depends_on": None,
                    "blocks": None,
                },
            ),
            # All fields specified
            (
                {
                    "title": "Test Issue",
                    "priority": Priority.HIGH,
                    "issue_type": IssueType.FEATURE,
                    "milestone": "v1.0",
                    "labels": ["bug", "urgent"],
                    "assignee": "john@example.com",
                    "estimated_hours": 5.5,
                    "depends_on": ["issue-1"],
                    "blocks": ["issue-2"],
                },
                {
                    "title": "Test Issue",
                    "priority": Priority.HIGH,
                    "issue_type": IssueType.FEATURE,
                    "milestone": "v1.0",
                    "labels": ["bug", "urgent"],
                    "assignee": "john@example.com",
                    "estimated_hours": 5.5,
                    "depends_on": ["issue-1"],
                    "blocks": ["issue-2"],
                },
            ),
            # Partial: milestone and labels
            (
                {
                    "title": "Test Issue",
                    "milestone": "v1.0",
                    "labels": ["bug", "urgent"],
                },
                {
                    "title": "Test Issue",
                    "milestone": "v1.0",
                    "labels": ["bug", "urgent"],
                    "priority": Priority.MEDIUM,
                    "issue_type": IssueType.OTHER,
                },
            ),
            # Partial: assignee and time
            (
                {
                    "title": "Test Issue",
                    "assignee": "john@example.com",
                    "estimated_hours": 5.5,
                },
                {
                    "title": "Test Issue",
                    "assignee": "john@example.com",
                    "estimated_hours": 5.5,
                    "priority": Priority.MEDIUM,
                    "issue_type": IssueType.OTHER,
                },
            ),
            # Partial: dependencies
            (
                {
                    "title": "Test Issue",
                    "depends_on": ["issue-1"],
                    "blocks": ["issue-2"],
                },
                {
                    "title": "Test Issue",
                    "depends_on": ["issue-1"],
                    "blocks": ["issue-2"],
                    "priority": Priority.MEDIUM,
                    "issue_type": IssueType.OTHER,
                },
            ),
            # Priority variations
            (
                {"title": "Test Issue", "priority": Priority.CRITICAL},
                {"title": "Test Issue", "priority": Priority.CRITICAL},
            ),
            # Issue type variations
            (
                {"title": "Test Issue", "issue_type": IssueType.BUG},
                {"title": "Test Issue", "issue_type": IssueType.BUG},
            ),
        ],
    )
    def test_create_issue_params(self, kwargs, expected):
        """Test IssueCreateParams with various field combinations (parameterized)."""
        params = IssueCreateParams(**kwargs)

        # Verify all expected attributes
        for attr, expected_value in expected.items():
            assert getattr(params, attr) == expected_value


class TestIssueListParams:
    """Test IssueListParams dataclass."""

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            # Defaults
            (
                {},
                {
                    "milestone": None,
                    "status": None,
                    "priority": None,
                    "issue_type": None,
                    "assignee": None,
                },
            ),
            # All filters
            (
                {
                    "milestone": "v1.0",
                    "status": "open",
                    "priority": Priority.HIGH,
                    "issue_type": IssueType.BUG,
                    "assignee": "john@example.com",
                },
                {
                    "milestone": "v1.0",
                    "status": "open",
                    "priority": Priority.HIGH,
                    "issue_type": IssueType.BUG,
                    "assignee": "john@example.com",
                },
            ),
        ],
    )
    def test_list_issue_params(self, kwargs, expected):
        """Test IssueListParams with various filter combinations."""
        params = IssueListParams(**kwargs)
        for attr, expected_value in expected.items():
            assert getattr(params, attr) == expected_value


class TestIssueUpdateParams:
    """Test IssueUpdateParams dataclass."""

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            # Defaults (only issue_id)
            (
                {"issue_id": "issue-1"},
                {"issue_id": "issue-1", "updates": {}},
            ),
            # With updates
            (
                {
                    "issue_id": "issue-1",
                    "updates": {"status": "done", "priority": Priority.LOW},
                },
                {
                    "issue_id": "issue-1",
                    "updates": {"status": "done", "priority": Priority.LOW},
                },
            ),
        ],
    )
    def test_update_issue_params(self, kwargs, expected):
        """Test IssueUpdateParams with various update combinations."""
        params = IssueUpdateParams(**kwargs)
        for attr, expected_value in expected.items():
            assert getattr(params, attr) == expected_value


class TestMilestoneCreateParams:
    """Test MilestoneCreateParams dataclass."""

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            # Defaults
            (
                {"name": "v1.0"},
                {"name": "v1.0", "content": "", "due_date": None},
            ),
            # All fields
            (
                {
                    "name": "v1.0",
                    "content": "Release version 1.0",
                    "due_date": datetime(2025, 12, 31),
                },
                {
                    "name": "v1.0",
                    "content": "Release version 1.0",
                    "due_date": datetime(2025, 12, 31),
                },
            ),
        ],
    )
    def test_create_milestone_params(self, kwargs, expected):
        """Test MilestoneCreateParams with various field combinations."""
        params = MilestoneCreateParams(**kwargs)
        for attr, expected_value in expected.items():
            assert getattr(params, attr) == expected_value


class TestMilestoneUpdateParams:
    """Test MilestoneUpdateParams dataclass."""

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            # Defaults
            (
                {"name": "v1.0"},
                {
                    "name": "v1.0",
                    "content": None,
                    "due_date": None,
                    "clear_due_date": False,
                    "status": None,
                },
            ),
            # All fields
            (
                {
                    "name": "v1.0",
                    "content": "Updated description",
                    "due_date": datetime(2025, 12, 31),
                    "clear_due_date": False,
                    "status": "completed",
                },
                {
                    "name": "v1.0",
                    "content": "Updated description",
                    "due_date": datetime(2025, 12, 31),
                    "clear_due_date": False,
                    "status": "completed",
                },
            ),
            # Clear due date
            (
                {
                    "name": "v1.0",
                    "clear_due_date": True,
                },
                {
                    "name": "v1.0",
                    "clear_due_date": True,
                    "due_date": None,
                    "content": None,
                    "status": None,
                },
            ),
        ],
    )
    def test_update_milestone_params(self, kwargs, expected):
        """Test MilestoneUpdateParams with various field combinations."""
        params = MilestoneUpdateParams(**kwargs)
        for attr, expected_value in expected.items():
            assert getattr(params, attr) == expected_value


class TestProjectCreateParams:
    """Test ProjectCreateParams dataclass."""

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            # Defaults
            (
                {"name": "My Project"},
                {"name": "My Project", "content": "", "milestones": None},
            ),
            # All fields
            (
                {
                    "name": "My Project",
                    "content": "Project description",
                    "milestones": ["v1.0", "v1.1"],
                },
                {
                    "name": "My Project",
                    "content": "Project description",
                    "milestones": ["v1.0", "v1.1"],
                },
            ),
        ],
    )
    def test_create_project_params(self, kwargs, expected):
        """Test ProjectCreateParams with various field combinations."""
        params = ProjectCreateParams(**kwargs)
        for attr, expected_value in expected.items():
            assert getattr(params, attr) == expected_value


class TestProjectUpdateParams:
    """Test ProjectUpdateParams dataclass."""

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            # Defaults
            (
                {"project_id": "proj-1"},
                {"project_id": "proj-1", "updates": {}},
            ),
            # With updates
            (
                {
                    "project_id": "proj-1",
                    "updates": {
                        "name": "Updated Project",
                        "description": "New description",
                    },
                },
                {
                    "project_id": "proj-1",
                    "updates": {
                        "name": "Updated Project",
                        "description": "New description",
                    },
                },
            ),
        ],
    )
    def test_update_project_params(self, kwargs, expected):
        """Test ProjectUpdateParams with various update combinations."""
        params = ProjectUpdateParams(**kwargs)
        for attr, expected_value in expected.items():
            assert getattr(params, attr) == expected_value
