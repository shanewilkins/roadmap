"""Tests for entity health scanner service."""

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
