"""Tests for entity health scanner service."""

import pytest

from roadmap.core.services.entity_health_scanner import (
    EntityHealthReport,
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

    @pytest.mark.parametrize(
        "count_type,severity,expected_count",
        [
            ("issue_count", None, 5),
            ("error_count", HealthSeverity.ERROR, 2),
            ("warning_count", HealthSeverity.WARNING, 2),
            ("info_count", HealthSeverity.INFO, 3),
        ],
    )
    def test_count_properties(self, count_type, severity, expected_count):
        """Test count properties with various severity levels."""
        if count_type == "issue_count":
            issues = [
                HealthIssue(
                    code=f"issue_{i}",
                    message=f"Issue {i}",
                    severity=HealthSeverity.INFO,
                    category="test",
                )
                for i in range(5)
            ]
        elif count_type == "error_count":
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
        elif count_type == "warning_count":
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
        else:  # info_count
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
            status="active",
            issues=issues,
        )

        assert getattr(report, count_type) == expected_count

    @pytest.mark.parametrize(
        "issue_list,expect_healthy",
        [
            ([], True),
            ([HealthIssue("info1", "Info", HealthSeverity.INFO, "test")], True),
            (
                [HealthIssue("warning1", "Warning", HealthSeverity.WARNING, "test")],
                True,
            ),
            ([HealthIssue("error1", "Error", HealthSeverity.ERROR, "test")], False),
        ],
    )
    def test_is_healthy_with_various_severities(self, issue_list, expect_healthy):
        """Test is_healthy with different severity levels."""
        report = EntityHealthReport(
            entity_id="entity-1",
            entity_type=EntityType.ISSUE,
            entity_title="Test",
            status="done",
            issues=issue_list,
        )
        assert report.is_healthy is expect_healthy

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
