"""
Tests for issue update helpers.
"""

from unittest.mock import Mock

import pytest

from roadmap.common.errors.exceptions import ValidationError
from roadmap.core.domain import Priority
from roadmap.core.services import IssueUpdateService


class TestIssueUpdateBuilder:
    """Test issue update builder."""

    def test_build_updates_empty_params(self):
        """build_updates should return empty dict when no params provided."""
        mock_core = Mock()
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        result = service.build_update_dict(
            title=None,
            priority=None,
            status=None,
            assignee=None,
            milestone=None,
            description=None,
            estimate=None,
        )

        assert result == {}

    def test_build_updates_with_title(self):
        """build_updates should include title when provided."""
        mock_core = Mock()
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        result = service.build_update_dict(
            title="New Title",
            priority=None,
            status=None,
            assignee=None,
            milestone=None,
            description=None,
            estimate=None,
        )

        assert result == {"title": "New Title"}

    def test_build_updates_with_priority(self):
        """build_updates should convert priority string to Priority enum."""
        mock_core = Mock()
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        result = service.build_update_dict(
            title=None,
            priority="high",
            status=None,
            assignee=None,
            milestone=None,
            description=None,
            estimate=None,
        )

        assert result == {"priority": Priority.HIGH}

    def test_build_updates_with_status(self):
        """build_updates should include status when provided."""
        mock_core = Mock()
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        result = service.build_update_dict(
            title=None,
            priority=None,
            status="in-progress",
            assignee=None,
            milestone=None,
            description=None,
            estimate=None,
        )

        assert result == {"status": "in-progress"}

    def test_build_updates_with_valid_assignee(self):
        """build_updates should include validated assignee."""
        mock_core = Mock()
        mock_core.validate_assignee.return_value = (True, None)
        mock_core.team.get_canonical_assignee.return_value = "testuser"
        service = IssueUpdateService(mock_core)

        result = service.build_update_dict(
            title=None,
            priority=None,
            status=None,
            assignee="testuser",
            milestone=None,
            description=None,
            estimate=None,
        )

        assert result == {"assignee": "testuser"}
        mock_core.validate_assignee.assert_called_once_with("testuser")

    def test_build_updates_with_empty_assignee_for_unassignment(self):
        """build_updates should convert empty string assignee to None."""
        mock_core = Mock()
        service = IssueUpdateService(mock_core)

        result = service.build_update_dict(
            title=None,
            priority=None,
            status=None,
            assignee="",
            milestone=None,
            description=None,
            estimate=None,
        )

        assert result == {"assignee": None}

    def test_build_updates_with_invalid_assignee(self):
        """build_updates should raise ValidationError when assignee validation fails."""
        mock_core = Mock()
        mock_core.validate_assignee.return_value = (False, "User not found")
        service = IssueUpdateService(mock_core)

        with pytest.raises(ValidationError, match="Invalid assignee"):
            service.build_update_dict(
                title=None,
                priority=None,
                status=None,
                assignee="invaliduser",
                milestone=None,
                description=None,
                estimate=None,
            )

        mock_core.validate_assignee.assert_called_once_with("invaliduser")

    def test_build_updates_with_milestone(self):
        """build_updates should include milestone when provided."""
        mock_core = Mock()
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        result = service.build_update_dict(
            title=None,
            priority=None,
            status=None,
            assignee=None,
            milestone="v1.0",
            description=None,
            estimate=None,
        )

        assert result == {"milestone": "v1.0"}

    def test_build_updates_with_description(self):
        """build_updates should include description when provided."""
        mock_core = Mock()
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        result = service.build_update_dict(
            title=None,
            priority=None,
            status=None,
            assignee=None,
            milestone=None,
            description="New description",
            estimate=None,
        )

        assert result == {"description": "New description"}

    def test_build_updates_with_estimate(self):
        """build_updates should include estimated_hours when estimate provided."""
        mock_core = Mock()
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        result = service.build_update_dict(
            title=None,
            priority=None,
            status=None,
            assignee=None,
            milestone=None,
            description=None,
            estimate=8.0,
        )

        assert result == {"estimated_hours": 8.0}

    def test_build_updates_with_zero_estimate(self):
        """build_updates should include zero estimate (not None)."""
        mock_core = Mock()
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        result = service.build_update_dict(
            title=None,
            priority=None,
            status=None,
            assignee=None,
            milestone=None,
            description=None,
            estimate=0.0,
        )

        assert result == {"estimated_hours": 0.0}

    def test_build_updates_with_multiple_fields(self):
        """build_updates should handle multiple update fields."""
        mock_core = Mock()
        mock_core.validate_assignee.return_value = (True, None)
        mock_core.team.get_canonical_assignee.return_value = "testuser"
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console

        result = service.build_update_dict(
            title="Updated Title",
            priority="critical",
            status="closed",
            assignee="testuser",
            milestone="v2.0",
            description="Updated description",
            estimate=16.0,
        )

        assert len(result) == 7
        assert result["title"] == "Updated Title"
        assert result["priority"] == Priority.CRITICAL
        assert result["status"] == "closed"
        assert result["assignee"] == "testuser"
        assert result["milestone"] == "v2.0"
        assert result["description"] == "Updated description"
        assert result["estimated_hours"] == 16.0

    def test_resolve_assignee_empty_string(self):
        """_resolve_assignee should return None for empty string."""
        mock_core = Mock()
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console

        result = service.resolve_assignee_for_update("")

        assert result is None

    def test_resolve_assignee_valid(self):
        """_resolve_assignee should return canonical assignee for valid user."""
        mock_core = Mock()
        mock_core.validate_assignee.return_value = (True, None)
        mock_core.team.get_canonical_assignee.return_value = "canonicaluser"
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console

        result = service.resolve_assignee_for_update("testuser")

        assert result == "canonicaluser"
        mock_core.validate_assignee.assert_called_once_with("testuser")
        mock_core.team.get_canonical_assignee.assert_called_once_with("testuser")

    def test_resolve_assignee_invalid(self):
        """_resolve_assignee should raise ValidationError for invalid user."""
        mock_core = Mock()
        mock_core.validate_assignee.return_value = (False, "User not found")
        service = IssueUpdateService(mock_core)

        with pytest.raises(ValidationError, match="Invalid assignee"):
            service.resolve_assignee_for_update("baduser")

    def test_resolve_assignee_with_warning(self):
        """_resolve_assignee should display warning but accept assignee."""
        mock_core = Mock()
        mock_core.validate_assignee.return_value = (True, "Warning: User not in team")
        mock_core.team.get_canonical_assignee.return_value = "testuser"
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console

        result = service.resolve_assignee_for_update("testuser")

        assert result == "testuser"
        mock_console.print.assert_called_once()
        assert "Warning:" in mock_console.print.call_args[0][0]

    def test_resolve_assignee_shows_resolution(self):
        """_resolve_assignee should show when name is resolved to canonical form."""
        mock_core = Mock()
        mock_core.validate_assignee.return_value = (True, None)
        mock_core.team.get_canonical_assignee.return_value = "john.doe"
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console

        result = service.resolve_assignee_for_update("johndoe")

        assert result == "john.doe"
        mock_console.print.assert_called_once()
        assert "Resolved 'johndoe' to 'john.doe'" in mock_console.print.call_args[0][0]

    def test_resolve_assignee_no_resolution_message_when_same(self):
        """_resolve_assignee should not show resolution message when name unchanged."""
        mock_core = Mock()
        mock_core.validate_assignee.return_value = (True, None)
        mock_core.team.get_canonical_assignee.return_value = "testuser"
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console

        result = service.resolve_assignee_for_update("testuser")

        assert result == "testuser"
        mock_console.print.assert_not_called()


class TestIssueUpdateDisplay:
    """Test issue update display."""

    def test_show_update_result_basic(self):
        """show_update_result should display updated issue info."""
        mock_core = Mock()
        mock_issue = Mock()
        mock_issue.id = "ISS-123"
        mock_issue.title = "Test Issue"
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        updates = {"title": "New Title"}

        service.display_update_result(mock_issue, updates, None)

        assert mock_console.print.call_count >= 2
        calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("Updated issue: Test Issue" in c for c in calls)
        assert any("ISS-123" in c for c in calls)

    def test_show_update_result_with_title(self):
        """show_update_result should display title update."""
        mock_core = Mock()
        mock_issue = Mock()
        mock_issue.id = "ISS-123"
        mock_issue.title = "New Title"
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        updates = {"title": "New Title"}

        service.display_update_result(mock_issue, updates, None)

        calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("title: New Title" in c for c in calls)

    def test_show_update_result_with_estimate(self):
        """show_update_result should display estimate using estimated_time_display."""
        mock_core = Mock()
        mock_issue = Mock()
        mock_issue.id = "ISS-123"
        mock_issue.title = "Test Issue"
        mock_issue.estimated_time_display = "1d"
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        updates = {"estimated_hours": 8.0}

        service.display_update_result(mock_issue, updates, None)

        calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("estimate: 1d" in c for c in calls)

    def test_show_update_result_with_multiple_fields(self):
        """show_update_result should display multiple update fields."""
        mock_core = Mock()
        mock_issue = Mock()
        mock_issue.id = "ISS-123"
        mock_issue.title = "Test Issue"
        mock_issue.estimated_time_display = "2d"
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        updates = {
            "title": "Updated Title",
            "priority": "high",
            "status": "in-progress",
            "assignee": "testuser",
            "milestone": "v1.0",
            "estimated_hours": 16.0,
        }

        service.display_update_result(mock_issue, updates, None)

        calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("title: Updated Title" in c for c in calls)
        assert any("priority: high" in c for c in calls)
        assert any("status: in-progress" in c for c in calls)
        assert any("assignee: testuser" in c for c in calls)
        assert any("milestone: v1.0" in c for c in calls)
        assert any("estimate: 2d" in c for c in calls)

    def test_show_update_result_with_reason(self):
        """show_update_result should display reason when provided."""
        mock_core = Mock()
        mock_issue = Mock()
        mock_issue.id = "ISS-123"
        mock_issue.title = "Test Issue"
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        updates = {"status": "closed"}
        reason = "Completed implementation"

        service.display_update_result(mock_issue, updates, reason)

        calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("reason: Completed implementation" in c for c in calls)

    def test_show_update_result_without_reason(self):
        """show_update_result should not display reason when None."""
        mock_core = Mock()
        mock_issue = Mock()
        mock_issue.id = "ISS-123"
        mock_issue.title = "Test Issue"
        mock_console = Mock()
        service = IssueUpdateService(mock_core)
        service._console = mock_console
        service._console = mock_console

        updates = {"status": "closed"}

        service.display_update_result(mock_issue, updates, None)

        calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert not any("reason:" in c for c in calls)
