"""Tests for entity health scanner service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from roadmap.common.constants import Status
from roadmap.core.domain.project import Project
from roadmap.core.services.health.entity_health_scanner import (
    EntityHealthScanner,
)


class TestEntityHealthScannerIntegration:
    """Integration tests for entity health scanner."""

    def test_scan_multiple_issues_with_various_problems(self, mock_issue_factory):
        """Test scanning multiple issues with different problems."""
        scanner = EntityHealthScanner()

        issues = []
        for i in range(3):
            issue = mock_issue_factory(
                id=f"issue-{i}",
                title=f"Test Issue {i}",
                status=Status.TODO if i == 0 else Status.IN_PROGRESS,
            )
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
        assert reports[0].is_healthy
        # Second issue should have missing description
        assert any(i.code == "missing_description" for i in reports[1].issues)
        # Third issue should have missing estimate warning
        assert any(i.code == "missing_estimate" for i in reports[2].issues)

    def test_scan_diverse_entity_types(
        self, mock_issue_factory, mock_milestone_factory
    ):
        """Test scanning different entity types in sequence."""
        scanner = EntityHealthScanner()

        # Create diverse entities
        issue = mock_issue_factory(
            id="issue-1",
            title="Issue",
            status=Status.CLOSED,
        )
        issue.content = "Content"
        issue.comments = []
        issue.estimated_hours = 5
        issue.actual_start_date = datetime.now(UTC) - timedelta(days=5)
        issue.actual_end_date = datetime.now(UTC)
        issue.due_date = datetime.now(UTC) + timedelta(days=1)
        issue.previous_assignee = None
        issue.handoff_date = None
        issue.progress_percentage = 100

        milestone = mock_milestone_factory(
            name="v1.0",
            status=Status.CLOSED,
        )
        milestone.content = "Release 1.0"
        milestone.created = datetime.now(UTC) - timedelta(days=30)
        milestone.due_date = datetime.now(UTC)
        milestone.calculated_progress = 100

        project = MagicMock(spec=Project)
        project.id = "project-1"
        project.name = "Project"
        project.status = Status.TODO
        project.content = "Project description"
        project.owner = "owner"

        issue_report = scanner.scan_issue(issue)
        milestone_report = scanner.scan_milestone(milestone)
        project_report = scanner.scan_project(project)

        assert issue_report.is_healthy
        assert milestone_report.is_healthy
        assert project_report.is_healthy
