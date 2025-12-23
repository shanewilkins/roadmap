"""Tests for entity health scanner service."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.constants import Status
from roadmap.core.domain.comment import Comment
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone
from roadmap.core.domain.project import Project
from roadmap.core.services.entity_health_scanner import (
    EntityHealthReport,
    EntityHealthScanner,
    EntityType,
    HealthIssue,
    HealthSeverity,
)


class TestHealthIssue:
    """Test HealthIssue dataclass."""

    def test_create_health_issue(self):
        """Test creating a health issue."""
        issue = HealthIssue(
            code="missing_description",
            message="Issue has no description",
            severity=HealthSeverity.WARNING,
            category="content",
        )
        assert issue.code == "missing_description"
        assert issue.message == "Issue has no description"
        assert issue.severity == HealthSeverity.WARNING
        assert issue.category == "content"
        assert issue.details == {}

    def test_create_health_issue_with_details(self):
        """Test creating health issue with additional details."""
        issue = HealthIssue(
            code="broken_dependency",
            message="Issue references non-existent issue",
            severity=HealthSeverity.ERROR,
            category="dependency",
            details={"referenced_issue": "issue-999", "status": "missing"},
        )
        assert issue.details["referenced_issue"] == "issue-999"
        assert issue.details["status"] == "missing"

    def test_health_severities(self):
        """Test all health severity levels."""
        severities = [
            HealthSeverity.INFO,
            HealthSeverity.WARNING,
            HealthSeverity.ERROR,
            HealthSeverity.CRITICAL,
        ]
        for severity in severities:
            assert severity.value in ["info", "warning", "error", "critical"]


class TestEntityHealthReport:
    """Test EntityHealthReport dataclass."""

    def test_create_empty_report(self):
        """Test creating an empty health report."""
        report = EntityHealthReport(
            entity_id="issue-1",
            entity_type=EntityType.ISSUE,
            entity_title="Test Issue",
            status="open",
        )
        assert report.entity_id == "issue-1"
        assert report.entity_type == EntityType.ISSUE
        assert report.entity_title == "Test Issue"
        assert report.status == "open"
        assert report.issues == []

    def test_create_report_with_issues(self):
        """Test creating a report with health issues."""
        issue1 = HealthIssue(
            code="missing_description",
            message="Missing description",
            severity=HealthSeverity.WARNING,
            category="content",
        )
        issue2 = HealthIssue(
            code="missing_priority",
            message="Missing priority",
            severity=HealthSeverity.INFO,
            category="content",
        )
        report = EntityHealthReport(
            entity_id="issue-1",
            entity_type=EntityType.ISSUE,
            entity_title="Test Issue",
            status="open",
            issues=[issue1, issue2],
        )
        assert len(report.issues) == 2
        assert report.issue_count == 2

    def test_issue_count(self):
        """Test issue count property."""
        issues = [
            HealthIssue(
                code=f"issue_{i}",
                message=f"Issue {i}",
                severity=HealthSeverity.INFO,
                category="test",
            )
            for i in range(5)
        ]
        report = EntityHealthReport(
            entity_id="entity-1",
            entity_type=EntityType.MILESTONE,
            entity_title="Test Milestone",
            status="planned",
            issues=issues,
        )
        assert report.issue_count == 5

    def test_error_count(self):
        """Test error count property."""
        issues = [
            HealthIssue(
                code="error1",
                message="Error 1",
                severity=HealthSeverity.ERROR,
                category="test",
            ),
            HealthIssue(
                code="error2",
                message="Error 2",
                severity=HealthSeverity.ERROR,
                category="test",
            ),
            HealthIssue(
                code="warning1",
                message="Warning 1",
                severity=HealthSeverity.WARNING,
                category="test",
            ),
        ]
        report = EntityHealthReport(
            entity_id="entity-1",
            entity_type=EntityType.PROJECT,
            entity_title="Test Project",
            status="active",
            issues=issues,
        )
        assert report.error_count == 2

    def test_warning_count(self):
        """Test warning count property."""
        issues = [
            HealthIssue(
                code="warning1",
                message="Warning 1",
                severity=HealthSeverity.WARNING,
                category="test",
            ),
            HealthIssue(
                code="warning2",
                message="Warning 2",
                severity=HealthSeverity.WARNING,
                category="test",
            ),
        ]
        report = EntityHealthReport(
            entity_id="entity-1",
            entity_type=EntityType.ISSUE,
            entity_title="Test",
            status="done",
            issues=issues,
        )
        assert report.warning_count == 2

    def test_info_count(self):
        """Test info count property."""
        issues = [
            HealthIssue(
                code="info1",
                message="Info 1",
                severity=HealthSeverity.INFO,
                category="test",
            ),
            HealthIssue(
                code="info2",
                message="Info 2",
                severity=HealthSeverity.INFO,
                category="test",
            ),
            HealthIssue(
                code="info3",
                message="Info 3",
                severity=HealthSeverity.INFO,
                category="test",
            ),
        ]
        report = EntityHealthReport(
            entity_id="entity-1",
            entity_type=EntityType.MILESTONE,
            entity_title="Test",
            status="completed",
            issues=issues,
        )
        assert report.info_count == 3

    def test_is_healthy_no_issues(self):
        """Test is_healthy when there are no issues."""
        report = EntityHealthReport(
            entity_id="entity-1",
            entity_type=EntityType.ISSUE,
            entity_title="Test",
            status="done",
        )
        assert report.is_healthy is True

    def test_is_healthy_with_info_only(self):
        """Test is_healthy with only info-level issues."""
        issues = [
            HealthIssue(
                code="info1",
                message="Info",
                severity=HealthSeverity.INFO,
                category="test",
            ),
        ]
        report = EntityHealthReport(
            entity_id="entity-1",
            entity_type=EntityType.ISSUE,
            entity_title="Test",
            status="done",
            issues=issues,
        )
        assert report.is_healthy is True

    def test_is_healthy_with_warning(self):
        """Test is_healthy with warning-level issues."""
        issues = [
            HealthIssue(
                code="warning1",
                message="Warning",
                severity=HealthSeverity.WARNING,
                category="test",
            ),
        ]
        report = EntityHealthReport(
            entity_id="entity-1",
            entity_type=EntityType.ISSUE,
            entity_title="Test",
            status="done",
            issues=issues,
        )
        # Warnings don't make it unhealthy - only errors/critical do
        assert report.is_healthy is True

    def test_is_healthy_with_error(self):
        """Test is_healthy with error-level issues."""
        issues = [
            HealthIssue(
                code="error1",
                message="Error",
                severity=HealthSeverity.ERROR,
                category="test",
            ),
        ]
        report = EntityHealthReport(
            entity_id="entity-1",
            entity_type=EntityType.ISSUE,
            entity_title="Test",
            status="done",
            issues=issues,
        )
        assert report.is_healthy is False

    def test_entity_types(self):
        """Test all entity types."""
        types = [EntityType.ISSUE, EntityType.MILESTONE, EntityType.PROJECT]
        for entity_type in types:
            report = EntityHealthReport(
                entity_id="entity-1",
                entity_type=entity_type,
                entity_title="Test",
                status="active",
            )
            assert report.entity_type == entity_type


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
        milestone.description = "Test milestone"
        milestone.status = Status.TODO
        milestone.created = datetime.now()
        milestone.due_date = datetime.now() + timedelta(days=30)
        milestone.calculated_progress = 0
        return milestone

    @pytest.fixture
    def mock_project(self):
        """Create a mock project for testing."""
        project = MagicMock(spec=Project)
        project.id = "project-1"
        project.name = "Test Project"
        project.status = Status.TODO
        project.description = "Test project description"
        project.owner = "test-owner"
        return project

    def test_scanner_init_without_core(self, scanner):
        """Test scanner initialization without core."""
        assert scanner.core is None
        assert scanner._entity_cache == {}

    def test_scanner_init_with_core(self):
        """Test scanner initialization with core."""
        mock_core = MagicMock()
        scanner = EntityHealthScanner(core=mock_core)
        assert scanner.core == mock_core

    def test_scan_issue_healthy(self, scanner, mock_issue):
        """Test scanning a healthy issue."""
        mock_issue.status = Status.CLOSED
        mock_issue.progress_percentage = 100
        mock_issue.actual_end_date = datetime.now()

        report = scanner.scan_issue(mock_issue)

        assert report.entity_id == "issue-1"
        assert report.entity_type == EntityType.ISSUE
        assert report.entity_title == "Test Issue"
        assert report.is_healthy is True

    def test_scan_issue_missing_description(self, scanner, mock_issue):
        """Test scanning issue with missing description."""
        mock_issue.content = ""

        report = scanner.scan_issue(mock_issue)

        found_issue = next(
            (i for i in report.issues if i.code == "missing_description"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.INFO
        # Info severity doesn't make it unhealthy
        assert report.is_healthy is True

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

    def test_scan_issue_missing_estimate(self, scanner, mock_issue):
        """Test scanning issue with missing time estimate."""
        mock_issue.status = Status.IN_PROGRESS

        report = scanner.scan_issue(mock_issue)

        found_issue = next(
            (i for i in report.issues if i.code == "missing_estimate"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.INFO

    def test_scan_issue_invalid_estimate(self, scanner, mock_issue):
        """Test scanning issue with invalid estimate."""
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

    def test_scan_issue_invalid_progress_percentage(self, scanner, mock_issue):
        """Test scanning issue with invalid progress percentage."""
        mock_issue.progress_percentage = 150

        report = scanner.scan_issue(mock_issue)

        found_issue = next(
            (i for i in report.issues if i.code == "invalid_progress_percentage"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.ERROR

    def test_scan_issue_missing_handoff_date(self, scanner, mock_issue):
        """Test scanning issue with previous assignee but no handoff date."""
        mock_issue.previous_assignee = "old-owner"
        mock_issue.handoff_date = None

        report = scanner.scan_issue(mock_issue)

        found_issue = next(
            (i for i in report.issues if i.code == "missing_handoff_date"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.WARNING

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

    def test_scan_issue_missing_completion_date(self, scanner, mock_issue):
        """Test scanning issue marked done but without completion date."""
        mock_issue.status = Status.CLOSED
        mock_issue.actual_end_date = None

        report = scanner.scan_issue(mock_issue)

        found_issue = next(
            (i for i in report.issues if i.code == "missing_completion_date"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.WARNING

    def test_scan_issue_inconsistent_status(self, scanner, mock_issue):
        """Test scanning issue with start date but TODO status."""
        mock_issue.status = Status.TODO
        mock_issue.actual_start_date = datetime.now()

        report = scanner.scan_issue(mock_issue)

        found_issue = next(
            (i for i in report.issues if i.code == "inconsistent_status"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.WARNING

    def test_scan_milestone_healthy(self, scanner, mock_milestone):
        """Test scanning a healthy milestone."""
        report = scanner.scan_milestone(mock_milestone)

        assert report.entity_id == "v1.0.0"
        assert report.entity_type == EntityType.MILESTONE
        assert report.is_healthy is True

    def test_scan_milestone_missing_description(self, scanner, mock_milestone):
        """Test scanning milestone with missing description."""
        mock_milestone.description = ""

        report = scanner.scan_milestone(mock_milestone)

        found_issue = next(
            (i for i in report.issues if i.code == "missing_description"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.WARNING

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

    def test_scan_milestone_inconsistent_completion(self, scanner, mock_milestone):
        """Test scanning milestone marked done but incomplete."""
        mock_milestone.status = Status.CLOSED
        mock_milestone.calculated_progress = 80

        report = scanner.scan_milestone(mock_milestone)

        found_issue = next(
            (i for i in report.issues if i.code == "inconsistent_completion"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.WARNING

    def test_scan_project_healthy(self, scanner, mock_project):
        """Test scanning a healthy project."""
        mock_project.status = Status.TODO  # Use a valid status

        report = scanner.scan_project(mock_project)

        assert report.entity_id == "project-1"
        assert report.entity_type == EntityType.PROJECT
        assert report.is_healthy is True

    def test_scan_project_missing_description(self, scanner, mock_project):
        """Test scanning project with missing description."""
        mock_project.status = Status.TODO
        mock_project.description = ""

        report = scanner.scan_project(mock_project)

        found_issue = next(
            (i for i in report.issues if i.code == "missing_description"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.WARNING

    def test_scan_project_missing_owner(self, scanner, mock_project):
        """Test scanning project with missing owner."""
        mock_project.status = Status.TODO
        mock_project.owner = ""

        report = scanner.scan_project(mock_project)

        found_issue = next(
            (i for i in report.issues if i.code == "missing_owner"), None
        )
        assert found_issue is not None
        assert found_issue.severity == HealthSeverity.WARNING

    def test_scan_all_without_core(self, scanner):
        """Test scan_all raises error without core."""
        with pytest.raises(RuntimeError, match="Core must be initialized"):
            scanner.scan_all()

    @patch("roadmap.core.services.entity_health_scanner.logger")
    def test_scan_all_with_core(self, mock_logger, scanner):
        """Test scan_all with initialized core."""
        mock_core = MagicMock()
        mock_core.issue_repository.list.return_value = []
        mock_core.milestone_repository.list.return_value = []
        mock_core.project_repository.list.return_value = []

        scanner.core = mock_core
        reports = scanner.scan_all()

        assert reports == []
        mock_core.issue_repository.list.assert_called_once()

    @patch("roadmap.core.services.entity_health_scanner.logger")
    def test_scan_all_with_multiple_entities(
        self, mock_logger, scanner, mock_issue, mock_milestone, mock_project
    ):
        """Test scan_all with multiple entities."""
        mock_core = MagicMock()
        mock_core.issue_repository.list.return_value = [mock_issue]
        mock_core.milestone_repository.list.return_value = [mock_milestone]
        mock_core.project_repository.list.return_value = [mock_project]

        scanner.core = mock_core
        reports = scanner.scan_all()

        assert len(reports) == 3
        assert any(r.entity_type == EntityType.ISSUE for r in reports)
        assert any(r.entity_type == EntityType.MILESTONE for r in reports)
        assert any(r.entity_type == EntityType.PROJECT for r in reports)

    def test_validate_comment_thread_empty(self, scanner):
        """Test comment thread validation with empty list."""
        errors = EntityHealthScanner._validate_comment_thread([])
        assert errors == []

    def test_validate_comment_thread_duplicate_ids(self, scanner):
        """Test comment thread validation with duplicate IDs."""
        comment1 = MagicMock(spec=Comment)
        comment1.id = "comment-1"
        comment1.body = "Test"
        comment1.author = "user"
        comment1.created_at = datetime.now()
        comment1.in_reply_to = None

        comment2 = MagicMock(spec=Comment)
        comment2.id = "comment-1"  # Duplicate ID
        comment2.body = "Test"
        comment2.author = "user"
        comment2.created_at = datetime.now()
        comment2.in_reply_to = None

        errors = EntityHealthScanner._validate_comment_thread([comment1, comment2])
        assert any("Duplicate" in error for error in errors)

    def test_validate_comment_thread_empty_body(self, scanner):
        """Test comment thread validation with empty body."""
        comment = MagicMock(spec=Comment)
        comment.id = "comment-1"
        comment.body = ""
        comment.author = "user"
        comment.created_at = datetime.now()
        comment.in_reply_to = None

        errors = EntityHealthScanner._validate_comment_thread([comment])
        assert any("Empty" in error for error in errors)

    def test_validate_comment_thread_missing_author(self, scanner):
        """Test comment thread validation with missing author."""
        comment = MagicMock(spec=Comment)
        comment.id = "comment-1"
        comment.body = "Test"
        comment.author = ""
        comment.created_at = datetime.now()
        comment.in_reply_to = None

        errors = EntityHealthScanner._validate_comment_thread([comment])
        assert any("author" in error.lower() for error in errors)

    def test_validate_comment_thread_circular_reference(self, scanner):
        """Test comment thread validation with circular reference."""
        comment1 = MagicMock(spec=Comment)
        comment1.id = "comment-1"
        comment1.body = "Test 1"
        comment1.author = "user"
        comment1.created_at = datetime.now()
        comment1.in_reply_to = "comment-2"

        comment2 = MagicMock(spec=Comment)
        comment2.id = "comment-2"
        comment2.body = "Test 2"
        comment2.author = "user"
        comment2.created_at = datetime.now()
        comment2.in_reply_to = "comment-1"

        errors = EntityHealthScanner._validate_comment_thread([comment1, comment2])
        assert any("Circular" in error for error in errors)

    def test_scan_issue_with_invalid_comments(self, scanner, mock_issue):
        """Test scanning issue with invalid comment thread."""
        comment = MagicMock(spec=Comment)
        comment.id = "comment-1"
        comment.body = ""
        comment.author = "user"
        comment.created_at = datetime.now()
        comment.in_reply_to = None

        mock_issue.comments = [comment]

        report = scanner.scan_issue(mock_issue)

        # Should have at least one comment-related issue
        comment_issues = [i for i in report.issues if i.category == "content"]
        assert len(comment_issues) > 0


class TestEntityHealthScannerIntegration:
    """Integration tests for entity health scanner."""

    def test_scan_multiple_issues_with_various_problems(self):
        """Test scanning multiple issues with different problems."""
        scanner = EntityHealthScanner()

        issues = []
        for i in range(3):
            issue = MagicMock(spec=Issue)
            issue.id = f"issue-{i}"
            issue.title = f"Test Issue {i}"
            issue.status = Status.TODO if i == 0 else Status.IN_PROGRESS
            issue.content = "" if i == 1 else "Content"
            issue.comments = []
            issue.estimated_hours = None
            issue.actual_start_date = None
            issue.actual_end_date = None
            issue.due_date = None
            issue.previous_assignee = None
            issue.handoff_date = None
            issue.progress_percentage = None
            issues.append(issue)

        reports = [scanner.scan_issue(issue) for issue in issues]

        assert len(reports) == 3
        # First issue should be clean
        assert reports[0].is_healthy is True
        # Second issue should have missing description
        assert any(i.code == "missing_description" for i in reports[1].issues)
        # Third issue should have missing estimate warning
        assert any(i.code == "missing_estimate" for i in reports[2].issues)

    def test_scan_diverse_entity_types(self):
        """Test scanning different entity types in sequence."""
        scanner = EntityHealthScanner()

        # Create diverse entities
        issue = MagicMock(spec=Issue)
        issue.id = "issue-1"
        issue.title = "Issue"
        issue.status = Status.CLOSED
        issue.content = "Content"
        issue.comments = []
        issue.estimated_hours = 5
        issue.actual_start_date = datetime.now() - timedelta(days=5)
        issue.actual_end_date = datetime.now()
        issue.due_date = datetime.now() + timedelta(days=1)
        issue.previous_assignee = None
        issue.handoff_date = None
        issue.progress_percentage = 100

        milestone = MagicMock(spec=Milestone)
        milestone.name = "v1.0"
        milestone.description = "Release 1.0"
        milestone.status = Status.CLOSED
        milestone.created = datetime.now() - timedelta(days=30)
        milestone.due_date = datetime.now()
        milestone.calculated_progress = 100

        project = MagicMock(spec=Project)
        project.id = "project-1"
        project.name = "Project"
        project.status = Status.TODO
        project.description = "Project description"
        project.owner = "owner"

        issue_report = scanner.scan_issue(issue)
        milestone_report = scanner.scan_milestone(milestone)
        project_report = scanner.scan_project(project)

        assert issue_report.is_healthy is True
        assert milestone_report.is_healthy is True
        assert project_report.is_healthy is True
