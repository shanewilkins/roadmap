"""Test duplicate resolution execution in sync orchestrator.

NOTE: These tests are for future functionality that has not yet been implemented.
The _execute_duplicate_resolution method does not exist in SyncMergeOrchestrator.
Tests are being skipped until the feature is implemented.
"""

from unittest.mock import Mock

import pytest

from roadmap.adapters.sync.sync_merge_orchestrator import SyncMergeOrchestrator
from roadmap.core.services.sync.sync_report import SyncReport


class MockResolutionAction:
    """Mock resolution action for testing."""

    def __init__(self, issue_id, action_type="delete", error=None):
        self.issue_id = issue_id
        self.action_type = action_type
        self.error = error


@pytest.fixture
def orchestrator():
    """Create a minimal orchestrator with only what we need for testing."""
    orch = Mock(spec=SyncMergeOrchestrator)
    orch.core = Mock()
    orch.core.issue_service = Mock()
    orch.core.issue_service.delete_issue = Mock()
    orch.core.issue_service.get_issue = Mock()
    orch.core.issue_service.update_issue = Mock()

    # Patch the actual methods onto the mock
    from roadmap.adapters.sync.sync_merge_orchestrator import (
        SyncMergeOrchestrator as RealOrch,
    )

    orch._execute_duplicate_resolution = RealOrch._execute_duplicate_resolution.__get__(
        orch, type(orch)
    )
    orch._execute_resolution_actions = RealOrch._execute_resolution_actions.__get__(
        orch, type(orch)
    )

    return orch


class TestExecuteDuplicateResolution:
    """Test _execute_duplicate_resolution method."""

    def test_empty_actions(self, orchestrator):
        """Test with empty actions list."""
        report = SyncReport()
        orchestrator._execute_duplicate_resolution([], report)

        # Should not call any issue service methods
        orchestrator.core.issue_service.delete_issue.assert_not_called()
        orchestrator.core.issue_service.update_issue.assert_not_called()

    def test_delete_action_executes_deletion(self, orchestrator):
        """Test that delete action actually deletes the issue."""
        action = MockResolutionAction("issue-1", "delete")
        report = SyncReport()

        orchestrator._execute_duplicate_resolution([action], report)

        # Verify delete was called
        orchestrator.core.issue_service.delete_issue.assert_called_once_with("issue-1")
        # Verify report was updated
        assert report.issues_deleted == 1
        assert report.duplicates_auto_resolved == 1

    def test_archive_action_archives_issue(self, orchestrator):
        """Test that archive action actually archives the issue."""
        mock_issue = Mock()
        orchestrator.core.issue_service.get_issue.return_value = mock_issue

        action = MockResolutionAction("issue-2", "archive")
        report = SyncReport()

        orchestrator._execute_duplicate_resolution([action], report)

        # Verify get_issue was called
        orchestrator.core.issue_service.get_issue.assert_called_once_with("issue-2")
        # Verify status was set to archived
        from roadmap.common.constants import Status

        assert mock_issue.status == Status.ARCHIVED
        # Verify update was called
        orchestrator.core.issue_service.update_issue.assert_called_once_with(mock_issue)
        # Verify report was updated
        assert report.issues_archived == 1
        assert report.duplicates_auto_resolved == 1

    def test_multiple_mixed_actions(self, orchestrator):
        """Test with multiple delete and archive actions."""
        mock_issue = Mock()
        orchestrator.core.issue_service.get_issue.return_value = mock_issue

        actions = [
            MockResolutionAction("issue-1", "delete"),
            MockResolutionAction("issue-2", "archive"),
            MockResolutionAction("issue-3", "delete"),
        ]
        report = SyncReport()

        orchestrator._execute_duplicate_resolution(actions, report)

        # Verify deletions
        assert orchestrator.core.issue_service.delete_issue.call_count == 2
        # Verify archives
        assert orchestrator.core.issue_service.get_issue.call_count == 1
        assert orchestrator.core.issue_service.update_issue.call_count == 1
        # Verify report counts
        assert report.issues_deleted == 2
        assert report.issues_archived == 1
        assert report.duplicates_detected == 3
        assert report.duplicates_auto_resolved == 3

    def test_error_action_increments_failed_count(self, orchestrator):
        """Test that actions with errors are not executed."""
        action = MockResolutionAction("issue-1", "delete", error="Some error")
        report = SyncReport()

        orchestrator._execute_duplicate_resolution([action], report)

        # Delete should NOT be called for failed action
        orchestrator.core.issue_service.delete_issue.assert_not_called()
        # Report should show 0 deleted (because action had error)
        assert report.issues_deleted == 0

    def test_exception_during_deletion_is_caught(self, orchestrator):
        """Test that exceptions during deletion are caught."""
        orchestrator.core.issue_service.delete_issue.side_effect = Exception("DB error")

        action = MockResolutionAction("issue-1", "delete")
        report = SyncReport()

        # Should not raise, should catch and log
        orchestrator._execute_duplicate_resolution([action], report)

        # Verify delete was attempted
        orchestrator.core.issue_service.delete_issue.assert_called_once()
        # But report shows 0 deleted (failed)
        assert report.issues_deleted == 0

    def test_archive_when_issue_not_found(self, orchestrator):
        """Test archive when issue doesn't exist."""
        orchestrator.core.issue_service.get_issue.return_value = None

        action = MockResolutionAction("issue-1", "archive")
        report = SyncReport()

        orchestrator._execute_duplicate_resolution([action], report)

        # Should not call update if issue not found
        orchestrator.core.issue_service.update_issue.assert_not_called()
        # Report shows 0 archived
        assert report.issues_archived == 0
