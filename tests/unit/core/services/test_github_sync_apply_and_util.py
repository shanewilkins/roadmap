"""Extended coverage tests for GitHub sync orchestrator."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.constants import Status
from roadmap.core.services.github_sync_orchestrator import GitHubSyncOrchestrator
from roadmap.core.services.sync_report import IssueChange
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestGitHubSyncOrchestratorApplyChanges:
    """Test applying sync changes to issues."""

    @pytest.fixture
    def mock_core(self, mock_core_initialized):
        """Create mock RoadmapCore with issues service.





        Uses centralized mock_core_initialized and adds service.


        """

        mock_core_initialized.issues = TestDataFactory.create_mock_core(
            is_initialized=True
        )

        return mock_core_initialized

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator."""
        config = {"token": "test", "owner": "user", "repo": "repo"}
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            orch = GitHubSyncOrchestrator(mock_core, config)
            orch.metadata_service = TestDataFactory.create_mock_core(
                is_initialized=True
            )
            return orch

    def test_apply_local_changes_no_changes(self, orchestrator):
        """Test applying when there are no local changes.

        Covers lines 257-259: Early return for no changes
        """
        change = IssueChange(issue_id="issue1", title="Test")
        # local_changes defaults to empty dict, which is falsy in if check

        orchestrator._apply_local_changes(change)

        # metadata_service should not be called
        orchestrator.metadata_service.record_sync.assert_not_called()

    def test_apply_local_changes_issue_not_found(self, orchestrator, mock_core):
        """Test applying when issue is not found.

        Covers lines 265-268: Issue not found case
        """
        mock_core.issues.get.return_value = None

        change = IssueChange(issue_id="issue1", title="Test")
        change.local_changes = {"status": "TODO -> DONE"}

        orchestrator._apply_local_changes(change)

        mock_core.issues.get.assert_called_once_with("issue1")

    @pytest.mark.parametrize(
        "change_field,old_value,new_value",
        [
            ("status", "todo", "closed"),
            ("title", "Old Title", "New Title"),
        ],
    )
    def test_apply_local_changes_field_update(
        self, orchestrator, mock_core, change_field, old_value, new_value
    ):
        """Test applying local field changes (status/title).

        Covers lines 270-279: Field change application
        """
        issue = MagicMock()
        issue.id = "issue1"
        issue.github_issue = 123  # Set GitHub issue number
        issue.title = old_value if change_field == "title" else "Test"
        issue.status = Status.TODO if change_field != "status" else Status(old_value)
        mock_core.issues.get.return_value = issue

        change = IssueChange(issue_id="issue1", title="Test")
        change.local_changes = {change_field: f"{old_value} -> {new_value}"}

        with patch(
            "roadmap.adapters.github.handlers.issues.IssueHandler"
        ) as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler

            orchestrator._apply_local_changes(change)

            if change_field == "status":
                assert issue.status == Status.CLOSED
            else:
                assert issue.title == new_value
            # Verify that IssueHandler.update_issue was called
            mock_handler.update_issue.assert_called_once()

    def test_apply_local_changes_invalid_status(self, orchestrator, mock_core):
        """Test applying invalid status value."""
        issue = MagicMock()
        issue.id = "issue1"
        issue.github_issue = 123  # Set GitHub issue number
        issue.title = "Test"
        issue.status = Status.TODO
        mock_core.issues.get.return_value = issue

        change = IssueChange(issue_id="issue1", title="Test")
        change.local_changes = {"status": "TODO -> INVALID_STATUS"}

        with patch(
            "roadmap.adapters.github.handlers.issues.IssueHandler"
        ) as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler

            orchestrator._apply_local_changes(change)

            # Status should remain unchanged on invalid value, no handler call should happen
            # because the mapping fails and no update_data is sent
            mock_handler.update_issue.assert_not_called()

    def test_apply_local_changes_exception(self, orchestrator, mock_core):
        """Test exception handling in apply local changes.

        Covers lines 290-297: Exception handling
        """
        # First call raises, second call (in exception handler) returns None
        mock_core.issues.get.side_effect = [Exception("Database error"), None]

        change = IssueChange(issue_id="issue1", title="Test")
        change.local_changes = {"status": "todo -> closed"}

        # Should not raise, should catch exception and record failed sync
        with patch("builtins.print"):  # Suppress print output
            orchestrator._apply_local_changes(change)

        # Should have tried to get the issue twice (main and exception handler)
        assert mock_core.issues.get.call_count == 2

    def test_apply_github_changes_no_changes(self, orchestrator):
        """Test applying GitHub changes when there are none.

        Covers lines 313-315: Early return for no changes
        """
        change = IssueChange(issue_id="issue1", title="Test")
        # github_changes defaults to empty dict, which is falsy in if check

        orchestrator._apply_github_changes(change)

        orchestrator.metadata_service.record_sync.assert_not_called()

    def test_apply_github_changes_issue_not_found(self, orchestrator, mock_core):
        """Test applying when issue is not found.

        Covers lines 321-324: Issue not found case
        """
        mock_core.issues.get.return_value = None

        change = IssueChange(issue_id="issue1", title="Test")
        change.github_changes = {"status": "TODO -> DONE"}

        orchestrator._apply_github_changes(change)

        mock_core.issues.get.assert_called_once_with("issue1")

    @pytest.mark.parametrize(
        "change_field,old_value,new_value",
        [
            ("status", "todo", "closed"),
            ("title", "Old Title", "New Title"),
        ],
    )
    def test_apply_github_changes_field_update(
        self, orchestrator, mock_core, change_field, old_value, new_value
    ):
        """Test applying GitHub field changes (status/title).

        Covers lines 326-335: Field change application
        """
        issue = MagicMock()
        issue.id = "issue1"
        issue.title = old_value if change_field == "title" else "Test"
        issue.status = Status.TODO
        mock_core.issues.get.return_value = issue

        change = IssueChange(issue_id="issue1", title="Old Title")
        change.github_changes = {change_field: f"{old_value} -> {new_value}"}

        orchestrator._apply_github_changes(change)

        mock_core.issues.update.assert_called_once()

    def test_apply_github_changes_exception(self, orchestrator, mock_core):
        """Test exception handling in apply GitHub changes.

        Covers lines 346-353: Exception handling
        """
        # First call raises, second call (in exception handler) returns None
        mock_core.issues.get.side_effect = [Exception("Database error"), None]

        change = IssueChange(issue_id="issue1", title="Test")
        change.github_changes = {"status": "todo -> closed"}

        # Should not raise, should catch exception and record failed sync
        with patch("builtins.print"):  # Suppress print output
            orchestrator._apply_github_changes(change)

        # Should have tried to get the issue twice (main and exception handler)
        assert mock_core.issues.get.call_count == 2


class TestGetLastSyncTime:
    """Test last sync time retrieval."""

    @pytest.fixture
    def mock_core(self, mock_core_initialized):
        """Create mock RoadmapCore with issues service.





        Uses centralized mock_core_initialized and adds service.


        """

        mock_core_initialized.issues = TestDataFactory.create_mock_core(
            is_initialized=True
        )

        return mock_core_initialized

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator."""
        config = {"token": "test", "owner": "user", "repo": "repo"}
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            return GitHubSyncOrchestrator(mock_core, config)

    @pytest.mark.parametrize(
        "sync_metadata,expected_result",
        [
            ({}, None),
            ({"last_sync": None}, None),
            ({"last_sync": "invalid-date"}, None),
            (
                {"last_sync": "2024-01-15T10:30:00Z"},
                datetime(
                    2024, 1, 15, 10, 30, 0, tzinfo=__import__("datetime").timezone.utc
                ),
            ),
        ],
    )
    def test_get_last_sync_time(self, orchestrator, sync_metadata, expected_result):
        """Test last sync time retrieval for various metadata states.

        Covers lines 370-384: Metadata parsing and datetime conversion
        """
        issue = MagicMock()
        issue.github_sync_metadata = sync_metadata

        sync_time = orchestrator._get_last_sync_time(issue)

        if expected_result is None:
            assert sync_time is None
        else:
            assert isinstance(sync_time, datetime)
            assert sync_time.year == expected_result.year
            assert sync_time.month == expected_result.month
            assert sync_time.day == expected_result.day
            assert sync_time.hour == expected_result.hour
            assert sync_time.minute == expected_result.minute

    def test_get_last_sync_time_no_metadata_attr(self, orchestrator):
        """Test when github_sync_metadata attribute doesn't exist."""
        issue = MagicMock(spec=[])  # No attributes

        sync_time = orchestrator._get_last_sync_time(issue)
        assert sync_time is None
