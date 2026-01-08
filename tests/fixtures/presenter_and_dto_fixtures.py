"""Reusable fixtures for presenter and DTO testing.

This module provides common fixtures used across multiple integration test files,
particularly for testing view presenters and CLI DTOs.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from roadmap.adapters.cli.dtos import MilestoneDTO, ProjectDTO

# ============================================================================
# MilestoneDTO Fixtures
# ============================================================================


@pytest.fixture
def milestone_dto():
    """Basic milestone DTO with standard fields."""
    return MilestoneDTO(
        id="m1",
        name="v1.0.0",
        status="open",
        headline="Release version 1.0",
        due_date=datetime.now() + timedelta(days=30),
        progress_percentage=75,
        issue_count=4,
        completed_count=3,
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def milestone_dto_minimal():
    """Minimal milestone DTO with only required fields."""
    return MilestoneDTO(
        id="m1",
        name="v1.0.0",
        status="closed",
        headline="",
        due_date=None,
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def milestone_dto_overdue():
    """Milestone DTO with overdue due date."""
    return MilestoneDTO(
        id="m1",
        name="v0.9.0",
        status="open",
        headline="Overdue milestone",
        due_date=datetime.now() - timedelta(days=5),
        created=datetime.now() - timedelta(days=30),
        updated=datetime.now(),
    )


# ============================================================================
# ProjectDTO Fixtures
# ============================================================================


@pytest.fixture
def project_dto():
    """Basic project DTO with standard fields."""
    return ProjectDTO(
        id="p1",
        name="Website Redesign",
        status="active",
        headline="Redesign the main website",
        owner="alice",
        target_end_date=datetime.now() + timedelta(days=60),
        actual_end_date=None,
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def project_dto_minimal():
    """Minimal project DTO with only required fields."""
    return ProjectDTO(
        id="p1",
        name="Small Task",
        status="planning",
        headline="",
        owner=None,
        target_end_date=None,
        actual_end_date=None,
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def project_dto_with_large_effort():
    """Project DTO with significant effort estimate (should display in days)."""
    return ProjectDTO(
        id="p1",
        name="Major Project",
        status="active",
        headline="Large undertaking",
        owner="bob",
        target_end_date=datetime.now() + timedelta(days=120),
        actual_end_date=None,
        milestone_count=5,
        issue_count=50,
        created=datetime.now(),
        updated=datetime.now(),
    )


# ============================================================================
# Mock Issue Fixtures
# ============================================================================


@pytest.fixture
def mock_closed_issue():
    """Mock issue that is closed/completed."""
    return MagicMock(
        id="i1",
        title="Feature A",
        status=MagicMock(value="closed"),
        priority=MagicMock(value="high"),
        assignee="alice",
        progress_display="100%",
        estimated_time_display="8h",
    )


@pytest.fixture
def mock_in_progress_issue():
    """Mock issue that is in progress."""
    return MagicMock(
        id="i2",
        title="Feature B with a longer title that should be truncated",
        status=MagicMock(value="in-progress"),
        priority=MagicMock(value="medium"),
        assignee="bob",
        progress_display="50%",
        estimated_time_display="16h",
    )


@pytest.fixture
def mock_issues(mock_closed_issue, mock_in_progress_issue):
    """Collection of mock issues with various states."""
    return [mock_closed_issue, mock_in_progress_issue]


@pytest.fixture
def mock_issues_with_third():
    """Collection of mock issues with three items."""
    return [
        MagicMock(
            id="i1",
            title="Feature A",
            status=MagicMock(value="closed"),
            priority=MagicMock(value="high"),
            assignee="alice",
            progress_display="100%",
            estimated_time_display="8h",
        ),
        MagicMock(
            id="i2",
            title="Feature B",
            status=MagicMock(value="in-progress"),
            priority=MagicMock(value="medium"),
            assignee="bob",
            progress_display="50%",
            estimated_time_display="16h",
        ),
        MagicMock(
            id="i3",
            title="Feature C",
            status=MagicMock(value="not-started"),
            priority=MagicMock(value="low"),
            assignee="charlie",
            progress_display="0%",
            estimated_time_display="12h",
        ),
    ]


# ============================================================================
# Data Fixtures
# ============================================================================


@pytest.fixture
def progress_data():
    """Standard progress tracking data."""
    return {"completed": 3, "total": 4}


@pytest.fixture
def effort_data():
    """Standard effort estimate data (in hours)."""
    return {"estimated": 320.0, "actual": 240.0}


@pytest.fixture
def large_effort_data():
    """Large effort data that should display in days."""
    return {"estimated": 800.0, "actual": 600.0}


@pytest.fixture
def milestone_description_content():
    """Standard milestone description content."""
    return (
        "This is the milestone description.\n"
        "\n"
        "## Goals\n"
        "- Complete feature A\n"
        "- Complete feature B"
    )


@pytest.fixture
def project_description_content():
    """Standard project description content."""
    return "Project to redesign the main website and improve UX."


# ============================================================================
# Presenter Helper Fixtures
# ============================================================================


@pytest.fixture
def milestone_with_all_components(
    milestone_dto, mock_issues, progress_data, milestone_description_content
):
    """Fixture providing a fully-populated milestone with all optional data."""
    return {
        "milestone_dto": milestone_dto,
        "issues": mock_issues,
        "progress_data": progress_data,
        "description_content": milestone_description_content,
        "comments_text": None,
    }


@pytest.fixture
def project_with_all_components(project_dto, effort_data, project_description_content):
    """Fixture providing a fully-populated project with all optional data."""
    return {
        "project_dto": project_dto,
        "milestones": None,  # Skip milestone rendering in tests
        "effort_data": effort_data,
        "description_content": project_description_content,
        "comments_text": None,
    }
