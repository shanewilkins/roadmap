"""Comprehensive tests for headline validation.

Tests cover:
- Missing headlines detection in issues, milestones, and projects
- Empty and whitespace-only headlines
- Entities with valid headlines
- Error handling and graceful degradation
- Health status reporting
"""

from unittest.mock import Mock

from roadmap.core.services.validator_base import HealthStatus
from roadmap.core.services.validators.missing_headlines_validator import (
    MissingHeadlinesValidator,
)


class TestHeadlineValidationCheckName:
    """Test headline validator identification."""

    def test_check_name_returns_missing_headlines(self):
        """Validator should identify itself as missing_headlines check."""
        assert MissingHeadlinesValidator.get_check_name() == "missing_headlines"

    def test_check_name_is_string(self):
        """Check name should be a string."""
        name = MissingHeadlinesValidator.get_check_name()
        assert isinstance(name, str)
        assert len(name) > 0


class TestHeadlineValidationHealthyState:
    """Test detection of healthy headline state."""

    def test_all_entities_with_headlines_returns_healthy(self):
        """Should return HEALTHY when all entities have headlines."""
        # Create mock core with services
        core = Mock()

        # Mock issues with headlines
        issue1 = Mock()
        issue1.headline = "Build feature"
        issue1.id = "issue-1"

        issue2 = Mock()
        issue2.headline = "Fix bug"
        issue2.id = "issue-2"

        # Mock milestones with headlines
        milestone1 = Mock()
        milestone1.headline = "v1.0 Release"
        milestone1.id = "v1-0"

        # Mock projects with headlines
        project1 = Mock()
        project1.headline = "Core Platform"
        project1.id = "core"

        # Set up services
        core.issue_service.list_issues.return_value = [issue1, issue2]
        core.milestone_service.list_milestones.return_value = [milestone1]
        core.project_service.list_projects.return_value = [project1]

        status, _ = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.HEALTHY

    def test_issue_with_empty_string_headline_detected(self):
        """Should detect issues with empty string headlines."""
        core = Mock()

        issue_empty = Mock()
        issue_empty.headline = ""
        issue_empty.id = "issue-2"

        core.issue_service.list_issues.return_value = [issue_empty]
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, _ = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.DEGRADED

    def test_issue_with_whitespace_only_headline_detected(self):
        """Should detect issues with whitespace-only headlines."""
        core = Mock()

        issue_whitespace = Mock()
        issue_whitespace.headline = "   \t\n  "
        issue_whitespace.id = "issue-3"

        core.issue_service.list_issues.return_value = [issue_whitespace]
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, _ = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.DEGRADED

    def test_milestone_without_headline_detected(self):
        """Should detect milestones with missing headlines."""
        core = Mock()

        milestone_no_headline = Mock()
        milestone_no_headline.headline = None
        milestone_no_headline.id = "v1-0"

        core.issue_service.list_issues.return_value = []
        core.milestone_service.list_milestones.return_value = [milestone_no_headline]
        core.project_service.list_projects.return_value = []

        status, message = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.DEGRADED
        assert "milestone" in message.lower()

    def test_project_without_headline_detected(self):
        """Should detect projects with missing headlines."""
        core = Mock()

        project_no_headline = Mock()
        project_no_headline.headline = None
        project_no_headline.id = "core"

        core.issue_service.list_issues.return_value = []
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = [project_no_headline]

        status, message = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.DEGRADED
        assert "project" in message.lower()


class TestHeadlineValidationMultipleMissing:
    """Test detection of multiple missing headlines."""

    def test_multiple_issues_missing_headlines(self):
        """Should detect and count multiple issues with missing headlines."""
        core = Mock()

        issues = [
            Mock(headline=None, id="issue-1"),
            Mock(headline="", id="issue-2"),
            Mock(headline="Valid", id="issue-3"),
        ]

        core.issue_service.list_issues.return_value = issues
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, message = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.DEGRADED
        assert "2 issue" in message

    def test_mixed_missing_headlines_across_entities(self):
        """Should detect missing headlines across different entity types."""
        core = Mock()

        core.issue_service.list_issues.return_value = [
            Mock(headline=None, id="issue-1"),
        ]
        core.milestone_service.list_milestones.return_value = [
            Mock(headline="", id="v1-0"),
        ]
        core.project_service.list_projects.return_value = [
            Mock(headline=None, id="core"),
        ]

        status, message = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.DEGRADED
        assert "issue" in message.lower()
        assert "milestone" in message.lower()
        assert "project" in message.lower()


class TestHeadlineValidationErrorHandling:
    """Test error handling and graceful degradation."""

    def test_issue_service_attribute_error_handled(self):
        """Should gracefully handle AttributeError from issue service."""
        core = Mock()
        core.issue_service.list_issues.side_effect = AttributeError("No service")
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, _ = MissingHeadlinesValidator.check_missing_headlines(core)

        # Should still return a status (not crash)
        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    def test_milestone_service_type_error_handled(self):
        """Should gracefully handle TypeError from milestone service."""
        core = Mock()
        core.issue_service.list_issues.return_value = []
        core.milestone_service.list_milestones.side_effect = TypeError("Wrong type")
        core.project_service.list_projects.return_value = []

        status, _ = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    def test_project_service_attribute_error_handled(self):
        """Should gracefully handle AttributeError from project service."""
        core = Mock()
        core.issue_service.list_issues.return_value = []
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.side_effect = AttributeError("Missing")

        status, _ = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    def test_unexpected_exception_returns_degraded(self):
        """Should return DEGRADED status on unexpected exception."""
        core = Mock()
        core.issue_service.list_issues.side_effect = RuntimeError("Unexpected error")

        status, message = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.DEGRADED
        assert "error" in message.lower()

    def test_core_none_handled_gracefully(self):
        """Should handle None core gracefully."""
        status, _ = MissingHeadlinesValidator.check_missing_headlines(None)

        # Should either return DEGRADED or handle it without crashing
        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]


class TestHeadlineValidationPerformCheck:
    """Test perform_check method."""

    def test_perform_check_without_core_returns_healthy(self):
        """perform_check without core should return HEALTHY status."""
        status, _ = MissingHeadlinesValidator.perform_check()

        assert status == HealthStatus.HEALTHY

    def test_perform_check_with_core_parameter(self):
        """perform_check should accept optional core parameter."""
        core = Mock()
        core.issue_service.list_issues.return_value = []
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, _ = MissingHeadlinesValidator.perform_check(core=core)

        # Should return a valid status
        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    def test_perform_check_returns_tuple(self):
        """perform_check should return tuple of (status, message)."""
        result = MissingHeadlinesValidator.perform_check()

        assert isinstance(result, tuple)
        assert len(result) == 2
        status, message = result
        assert isinstance(status, str)
        assert isinstance(message, str)


class TestHeadlineValidationMessageQuality:
    """Test quality of validation messages."""

    def test_degraded_message_includes_count(self):
        """DEGRADED message should include count of missing headlines."""
        core = Mock()

        core.issue_service.list_issues.return_value = [
            Mock(headline=None, id="issue-1"),
            Mock(headline="", id="issue-2"),
        ]
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, message = MissingHeadlinesValidator.check_missing_headlines(core)

        assert "2" in message
        assert "entity" in message.lower() or "issue" in message.lower()

    def test_healthy_message_is_positive(self):
        """HEALTHY message should be positive and reassuring."""
        core = Mock()
        core.issue_service.list_issues.return_value = []
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, message = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.HEALTHY
        assert "headline" in message.lower()

    def test_degraded_message_provides_fix_guidance(self):
        """DEGRADED message should suggest remediation."""
        core = Mock()

        core.issue_service.list_issues.return_value = [
            Mock(headline=None, id="issue-1")
        ]
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, message = MissingHeadlinesValidator.check_missing_headlines(core)

        assert "fix" in message.lower() or "missing-headline" in message.lower()


class TestHeadlineValidationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_headline_accepted(self):
        """Should accept very long valid headlines."""
        core = Mock()

        long_headline = "A" * 1000  # Very long headline
        issue = Mock()
        issue.headline = long_headline
        issue.id = "issue-1"

        core.issue_service.list_issues.return_value = [issue]
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, _ = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.HEALTHY

    def test_special_characters_in_headline_accepted(self):
        """Should accept headlines with special characters."""
        core = Mock()

        issue = Mock()
        issue.headline = "Feature: Build API v2.0 (urgent!) 🚀"
        issue.id = "issue-1"

        core.issue_service.list_issues.return_value = [issue]
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, _ = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.HEALTHY

    def test_unicode_headline_accepted(self):
        """Should accept Unicode in headlines."""
        core = Mock()

        issue = Mock()
        issue.headline = "构建功能 (Build Feature) 🎉"
        issue.id = "issue-1"

        core.issue_service.list_issues.return_value = [issue]
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, _ = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.HEALTHY

    def test_single_space_in_headline_is_empty(self):
        """Should treat single space as empty headline."""
        core = Mock()

        issue = Mock()
        issue.headline = " "
        issue.id = "issue-1"

        core.issue_service.list_issues.return_value = [issue]
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, _ = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.DEGRADED


class TestHeadlineValidationLargeDatasets:
    """Test performance with large datasets."""

    def test_many_entities_with_valid_headlines(self):
        """Should handle many entities with valid headlines."""
        core = Mock()

        # Create 100 issues with valid headlines
        issues = [Mock(headline=f"Issue {i}", id=f"issue-{i}") for i in range(100)]

        core.issue_service.list_issues.return_value = issues
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, _ = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.HEALTHY

    def test_many_entities_with_missing_headlines(self):
        """Should handle many entities with missing headlines."""
        core = Mock()

        # Create 50 issues without headlines
        issues = [Mock(headline=None, id=f"issue-{i}") for i in range(50)]

        core.issue_service.list_issues.return_value = issues
        core.milestone_service.list_milestones.return_value = []
        core.project_service.list_projects.return_value = []

        status, message = MissingHeadlinesValidator.check_missing_headlines(core)

        assert status == HealthStatus.DEGRADED
        assert "50" in message
