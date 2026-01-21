"""Tests for issue update helpers."""

from unittest.mock import Mock

from roadmap.core.services import IssueUpdateService
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestIssueUpdateDisplay:
    """Test issue update display."""

    def test_show_update_result_basic(self):
        """show_update_result should display updated issue info."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = TestDataFactory.create_mock_issue(status="open", priority="medium")
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
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = TestDataFactory.create_mock_issue(status="open", priority="medium")
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
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = TestDataFactory.create_mock_issue(status="open", priority="medium")
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
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = TestDataFactory.create_mock_issue(status="open", priority="medium")
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
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = TestDataFactory.create_mock_issue(status="open", priority="medium")
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
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = TestDataFactory.create_mock_issue(status="open", priority="medium")
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
