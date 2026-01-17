"""Tests for entity health scanner service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.constants import Status
from roadmap.core.domain.comment import Comment
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone
from roadmap.core.domain.project import Project
from roadmap.core.services.health.entity_health_scanner import (
    EntityHealthScanner,
    EntityType,
    HealthSeverity,
)
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestEntityHealthScanner:
    """Test EntityHealthScanner class."""

    @pytest.fixture
    def scanner(self):
        """Create a scanner instance."""
        return EntityHealthScanner()

    @pytest.fixture
    def mock_issue(self):
        """Create a mock issue for testing."""
        issue = MagicMock(spec=Issue)
        issue.id = "issue-1"
        issue.title = "Test Issue"
        issue.status = Status.TODO
        issue.content = "Test content"
        issue.comments = []
        issue.estimated_hours = None
        issue.actual_start_date = None
        issue.actual_end_date = None
        issue.due_date = None
        issue.previous_assignee = None
        issue.handoff_date = None
        issue.progress_percentage = None
        return issue

    @pytest.fixture
    def mock_milestone(self):
        """Create a mock milestone for testing."""
        milestone = MagicMock(spec=Milestone)
        milestone.name = "v1.0.0"
        milestone.content = "Test milestone"
        milestone.status = Status.TODO
        milestone.created = datetime.now(UTC)
        milestone.due_date = datetime.now(UTC) + timedelta(days=30)
        milestone.calculated_progress = 0
        return milestone

    @pytest.fixture
    def mock_project(self):
        """Create a mock project for testing."""
        project = MagicMock(spec=Project)
        project.id = "project-1"
        project.name = "Test Project"
        project.status = Status.TODO
        project.content = "Test project description"
        project.owner = "test-owner"
        return project

    def test_scanner_init_without_core(self, scanner):
        """Test scanner initialization without core."""
        assert scanner.core is None
        assert scanner._entity_cache == {}

    def test_scanner_init_with_core(self):
        """Test scanner initialization with core."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        scanner = EntityHealthScanner(core=mock_core)
        assert scanner.core == mock_core

    def test_scan_issue_healthy(self, scanner, mock_issue):
        """Test scanning a healthy issue."""
        mock_issue.status = Status.CLOSED
        mock_issue.progress_percentage = 100
        mock_issue.actual_end_date = datetime.now(UTC)

        report = scanner.scan_issue(mock_issue)

        assert report.entity_id == "issue-1"
        assert report.entity_type == EntityType.ISSUE
        assert report.entity_title == "Test Issue"
        assert report.is_healthy

    @pytest.mark.parametrize(
        "field_to_set,field_value,issue_code,expected_severity",
        [
            ("content", "", "missing_description", HealthSeverity.INFO),
            (
                "progress_percentage",
                150,
                "invalid_progress_percentage",
                HealthSeverity.ERROR,
            ),
            ("estimated_hours", -5, "invalid_estimate", HealthSeverity.WARNING),
            (
                "previous_assignee",
                "old-owner",
                "missing_handoff_date",
                HealthSeverity.WARNING,
            ),
            (
                "status",
                Status.CLOSED,
                "missing_completion_date",
                HealthSeverity.WARNING,
            ),
        ],
    )
    def test_scan_issue_with_problems(
        self,
        scanner,
        mock_issue,
        field_to_set,
        field_value,
        issue_code,
        expected_severity,
    ):
        """Test scanning issue with various problems."""
        # Reset mock for clean state
        if field_to_set == "content":
            mock_issue.content = field_value
        elif field_to_set == "status":
            mock_issue.status = field_value
            if field_value == Status.IN_PROGRESS:
                mock_issue.estimated_hours = None
            elif field_value == Status.CLOSED:
                mock_issue.actual_end_date = None
                if issue_code == "inconsistent_completion":
                    mock_issue.progress_percentage = 75
        elif field_to_set == "progress_percentage":
            mock_issue.progress_percentage = field_value
        elif field_to_set == "estimated_hours":
            mock_issue.status = Status.IN_PROGRESS
            mock_issue.estimated_hours = field_value
        elif field_to_set == "previous_assignee":
            mock_issue.previous_assignee = field_value
            mock_issue.handoff_date = None

        report = scanner.scan_issue(mock_issue)
        found_issue = next((i for i in report.issues if i.code == issue_code), None)
        assert found_issue is not None
        assert found_issue.severity == expected_severity

    def test_scan_issue_missing_estimate(self, scanner, mock_issue):
        """Test scanning issue with missing time estimate."""
        mock_issue.status = Status.IN_PROGRESS
        report = scanner.scan_issue(mock_issue)
        found_issue = next(
            (i for i in report.issues if i.code == "missing_estimate"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.INFO

    def test_scan_issue_invalid_estimate_in_progress(self, scanner, mock_issue):
        """Test scanning issue with invalid estimate when in progress."""
        mock_issue.status = Status.IN_PROGRESS
        mock_issue.estimated_hours = -5
        report = scanner.scan_issue(mock_issue)
        found_issue = next(
            (i for i in report.issues if i.code == "invalid_estimate"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.WARNING

    def test_scan_issue_inconsistent_completion(self, scanner, mock_issue):
        """Test scanning issue marked done but incomplete."""
        mock_issue.status = Status.CLOSED
        mock_issue.progress_percentage = 75
        report = scanner.scan_issue(mock_issue)
        found_issue = next(
            (i for i in report.issues if i.code == "inconsistent_completion"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.WARNING

    def test_scan_issue_inconsistent_status(self, scanner, mock_issue):
        """Test scanning issue with start date but TODO status."""
        mock_issue.status = Status.TODO
        mock_issue.actual_start_date = datetime.now(UTC)
        report = scanner.scan_issue(mock_issue)
        found_issue = next(
            (i for i in report.issues if i.code == "inconsistent_status"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.WARNING

    def test_scan_issue_invalid_date_range(self, scanner, mock_issue):
        """Test scanning issue with invalid date range."""
        mock_issue.actual_start_date = datetime(2024, 12, 25)
        mock_issue.actual_end_date = datetime(2024, 12, 20)

        report = scanner.scan_issue(mock_issue)

        assert not report.is_healthy
        found_issue = next(
            (i for i in report.issues if i.code == "invalid_date_range"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.ERROR

    def test_scan_issue_missed_due_date(self, scanner, mock_issue):
        """Test scanning issue completed after due date."""
        mock_issue.due_date = datetime(2024, 12, 20)
        mock_issue.actual_end_date = datetime(2024, 12, 25)

        report = scanner.scan_issue(mock_issue)

        found_issue = next(
            (i for i in report.issues if i.code == "missed_due_date"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.INFO

    def test_scan_milestone_healthy(self, scanner, mock_milestone):
        """Test scanning a healthy milestone."""
        report = scanner.scan_milestone(mock_milestone)

        assert report.entity_id == "v1.0.0"
        assert report.entity_type == EntityType.MILESTONE
        assert report.is_healthy

    @pytest.mark.parametrize(
        "field_to_set,field_value,issue_code,expected_severity",
        [
            ("description", "", "missing_content", HealthSeverity.WARNING),
            (
                "status",
                Status.CLOSED,
                "inconsistent_completion",
                HealthSeverity.WARNING,
            ),
        ],
    )
    def test_scan_milestone_with_problems(
        self,
        scanner,
        mock_milestone,
        field_to_set,
        field_value,
        issue_code,
        expected_severity,
    ):
        """Test scanning milestone with various problems."""
        if field_to_set == "description":
            mock_milestone.content = field_value
        elif field_to_set == "status":
            mock_milestone.status = field_value
            mock_milestone.calculated_progress = 80

        report = scanner.scan_milestone(mock_milestone)

        found_issue = next((i for i in report.issues if i.code == issue_code), None)
        assert found_issue is not None
        assert found_issue.severity == expected_severity

    def test_scan_milestone_invalid_date_range(self, scanner, mock_milestone):
        """Test scanning milestone with invalid date range."""
        mock_milestone.created = datetime(2024, 12, 25)
        mock_milestone.due_date = datetime(2024, 12, 20)

        report = scanner.scan_milestone(mock_milestone)

        found_issue = next(
            (i for i in report.issues if i.code == "invalid_date_range"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.ERROR

    def test_scan_project_healthy(self, scanner, mock_project):
        """Test scanning a healthy project."""
        mock_project.status = Status.TODO  # Use a valid status

        report = scanner.scan_project(mock_project)

        assert report.entity_id == "project-1"
        assert report.entity_type == EntityType.PROJECT
        assert report.is_healthy

    @pytest.mark.parametrize(
        "field_to_set,field_value,issue_code",
        [
            ("description", "", "missing_content"),
            ("owner", "", "missing_owner"),
        ],
    )
    def test_scan_project_with_problems(
        self, scanner, mock_project, field_to_set, field_value, issue_code
    ):
        """Test scanning project with missing fields."""
        mock_project.status = Status.TODO
        if field_to_set == "description":
            mock_project.content = field_value
        elif field_to_set == "owner":
            mock_project.owner = field_value

        report = scanner.scan_project(mock_project)

        found_issue = next((i for i in report.issues if i.code == issue_code), None)
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.WARNING

    def test_scan_all_without_core(self, scanner):
        """Test scan_all raises error without core."""
        with pytest.raises(RuntimeError, match="Core must be initialized"):
            scanner.scan_all()

    @patch("roadmap.core.services.health.entity_health_scanner.logger")
    def test_scan_all_with_core(self, mock_logger, scanner):
        """Test scan_all with initialized core."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issue_repository.list.return_value = []
        mock_core.milestone_repository.list.return_value = []
        mock_core.project_repository.list.return_value = []

        scanner.core = mock_core
        reports = scanner.scan_all()

        assert reports == []
        mock_core.issue_repository.list.assert_called_once()

    @patch("roadmap.core.services.health.entity_health_scanner.logger")
    def test_scan_all_with_multiple_entities(
        self, mock_logger, scanner, mock_issue, mock_milestone, mock_project
    ):
        """Test scan_all with multiple entities."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issue_repository.list.return_value = [mock_issue]
        mock_core.milestone_repository.list.return_value = [mock_milestone]
        mock_core.project_repository.list.return_value = [mock_project]

        scanner.core = mock_core
        reports = scanner.scan_all()

        assert len(reports) == 3
        assert any(r.entity_type == EntityType.ISSUE for r in reports)
        assert any(r.entity_type == EntityType.MILESTONE for r in reports)
        assert any(r.entity_type == EntityType.PROJECT for r in reports)

    @pytest.mark.parametrize(
        "comment_list,should_have_error,error_pattern",
        [
            ([], False, None),
            (
                [
                    MagicMock(
                        spec=Comment,
                        id="comment-1",
                        body="Test",
                        author="user",
                        created_at=datetime.now(UTC),
                        in_reply_to=None,
                    )
                ],
                False,
                None,
            ),
            (
                [
                    MagicMock(
                        spec=Comment,
                        id="comment-1",
                        body="",
                        author="user",
                        created_at=datetime.now(UTC),
                        in_reply_to=None,
                    )
                ],
                True,
                "Empty",
            ),
            (
                [
                    MagicMock(
                        spec=Comment,
                        id="comment-1",
                        body="Test",
                        author="",
                        created_at=datetime.now(UTC),
                        in_reply_to=None,
                    )
                ],
                True,
                "author",
            ),
        ],
    )
    def test_validate_comment_thread(
        self, scanner, comment_list, should_have_error, error_pattern
    ):
        """Test comment thread validation with various scenarios."""
        errors = EntityHealthScanner._validate_comment_thread(comment_list)
        if should_have_error:
            assert any(error_pattern in error for error in errors)
        else:
            assert errors == []

    def test_validate_comment_thread_duplicate_ids(self, scanner):
        """Test comment thread validation with duplicate IDs."""
        comment1 = MagicMock(spec=Comment)
        comment1.id = "comment-1"
        comment1.body = "Test"
        comment1.author = "user"
        comment1.created_at = datetime.now(UTC)
        comment1.in_reply_to = None

        comment2 = MagicMock(spec=Comment)
        comment2.id = "comment-1"  # Duplicate ID
        comment2.body = "Test"
        comment2.author = "user"
        comment2.created_at = datetime.now(UTC)
        comment2.in_reply_to = None

        errors = EntityHealthScanner._validate_comment_thread([comment1, comment2])
        assert any("Duplicate" in error for error in errors)

    def test_validate_comment_thread_circular_reference(self, scanner):
        """Test comment thread validation with circular reference."""
        comment1 = MagicMock(spec=Comment)
        comment1.id = "comment-1"
        comment1.body = "Test 1"
        comment1.author = "user"
        comment1.created_at = datetime.now(UTC)
        comment1.in_reply_to = "comment-2"

        comment2 = MagicMock(spec=Comment)
        comment2.id = "comment-2"
        comment2.body = "Test 2"
        comment2.author = "user"
        comment2.created_at = datetime.now(UTC)
        comment2.in_reply_to = "comment-1"

        errors = EntityHealthScanner._validate_comment_thread([comment1, comment2])
        assert any("Circular" in error for error in errors)

    def test_scan_issue_with_invalid_comments(self, scanner, mock_issue):
        """Test scanning issue with invalid comment thread."""
        comment = MagicMock(spec=Comment)
        comment.id = "comment-1"
        comment.body = ""
        comment.author = "user"
        comment.created_at = datetime.now(UTC)
        comment.in_reply_to = None

        mock_issue.comments = [comment]

        report = scanner.scan_issue(mock_issue)

        # Should have at least one comment-related issue
        comment_issues = [i for i in report.issues if i.category == "content"]
        assert len(comment_issues) > 0
