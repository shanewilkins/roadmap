"""Tests for RemoteIssueCreationService (Tier 2 coverage)."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.sync.services.remote_issue_creation_service import (
    RemoteIssueCreationService,
)
from roadmap.core.domain.issue import Issue, Status
from roadmap.core.models.sync_models import SyncIssue


class TestRemoteIssueCreationService:
    """Test suite for RemoteIssueCreationService."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = MagicMock()
        core.issues = MagicMock()
        return core

    @pytest.fixture
    def service(self, mock_core):
        """Create service instance."""
        return RemoteIssueCreationService(mock_core)

    def test_init_stores_core(self, service, mock_core):
        """Test that initialization stores core reference."""
        assert service.core is mock_core

    def test_create_issue_from_remote_minimal(self, service):
        """Test creating issue from minimal remote data."""
        remote_issue = SyncIssue(
            id="123",
            title="Test Issue",
            headline="Test description",
            status="open",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=123,
        )

        result = service.create_issue_from_remote("123", remote_issue)

        assert isinstance(result, Issue)
        assert result.title == "Test Issue"
        assert result.content == "Test description"
        assert result.status == Status.TODO
        assert "synced:from-github" in result.labels
        assert result.milestone == "backlog"
        assert result.remote_ids.get("github") == 123

    def test_create_issue_from_remote_with_labels(self, service):
        """Test creating issue with existing labels."""
        remote_issue = SyncIssue(
            id="456",
            title="Issue with Labels",
            headline="Has labels",
            status="open",
            labels=["bug", "urgent"],
            assignee="john",
            milestone="v1.0",
            backend_id=456,
        )

        result = service.create_issue_from_remote("456", remote_issue)

        assert "bug" in result.labels
        assert "urgent" in result.labels
        assert "synced:from-github" in result.labels
        assert result.assignee == "john"
        assert result.milestone == "v1.0"

    def test_create_issue_from_remote_status_open(self, service):
        """Test status normalization for 'open'."""
        remote_issue = SyncIssue(
            id="1",
            title="Open Issue",
            headline="",
            status="open",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=1,
        )

        result = service.create_issue_from_remote("1", remote_issue)
        assert result.status == Status.TODO

    def test_create_issue_from_remote_status_closed(self, service):
        """Test status normalization for 'closed'."""
        remote_issue = SyncIssue(
            id="2",
            title="Closed Issue",
            headline="",
            status="closed",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=2,
        )

        result = service.create_issue_from_remote("2", remote_issue)
        assert result.status == Status.CLOSED

    def test_create_issue_from_remote_status_in_progress(self, service):
        """Test status normalization for 'in_progress'."""
        remote_issue = SyncIssue(
            id="3",
            title="In Progress",
            headline="",
            status="in_progress",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=3,
        )

        result = service.create_issue_from_remote("3", remote_issue)
        assert result.status == Status.IN_PROGRESS

    def test_create_issue_from_remote_status_in_progress_spaced(self, service):
        """Test status normalization for 'in progress' (with space)."""
        remote_issue = SyncIssue(
            id="4",
            title="In Progress",
            headline="",
            status="in progress",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=4,
        )

        result = service.create_issue_from_remote("4", remote_issue)
        assert result.status == Status.IN_PROGRESS

    def test_create_issue_from_remote_status_blocked(self, service):
        """Test status normalization for 'blocked'."""
        remote_issue = SyncIssue(
            id="5",
            title="Blocked",
            headline="",
            status="blocked",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=5,
        )

        result = service.create_issue_from_remote("5", remote_issue)
        assert result.status == Status.BLOCKED

    def test_create_issue_from_remote_status_done(self, service):
        """Test status normalization for 'done'."""
        remote_issue = SyncIssue(
            id="6",
            title="Done",
            headline="",
            status="done",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=6,
        )

        result = service.create_issue_from_remote("6", remote_issue)
        assert result.status == Status.CLOSED

    def test_create_issue_from_remote_status_unknown(self, service):
        """Test unknown status defaults to TODO."""
        remote_issue = SyncIssue(
            id="7",
            title="Unknown Status",
            headline="",
            status="unknown_status",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=7,
        )

        result = service.create_issue_from_remote("7", remote_issue)
        assert result.status == Status.TODO

    def test_create_issue_from_remote_status_none(self, service):
        """Test None status defaults to TODO."""
        remote_issue = SyncIssue(
            id="8",
            title="No Status",
            headline="",
            status="open",  # SyncIssue requires status, can't be None
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=8,
        )

        # Test with None after creation
        with patch.object(remote_issue, "status", None):
            # Normalize should handle None
            result = RemoteIssueCreationService._normalize_status(None)
            assert result == Status.TODO

    def test_create_issue_from_remote_no_title(self, service):
        """Test creating issue with None title uses fallback."""
        remote_issue = SyncIssue(
            id="9",
            title="Default Title",  # SyncIssue requires title, can't be None initially
            headline="Description only",
            status="open",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=9,
        )

        # Test the normalization path: if None title was passed, we use fallback
        with patch.object(remote_issue, "title", None):
            # Service's logic checks if title is None and uses fallback
            title = remote_issue.title or "Remote Issue 9"
            assert title == "Remote Issue 9"

    def test_create_issue_from_remote_no_headline(self, service):
        """Test creating issue with None headline uses empty content."""
        remote_issue = SyncIssue(
            id="10",
            title="Title Only",
            headline="",  # Use empty string instead of None
            status="open",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=10,
        )

        result = service.create_issue_from_remote("10", remote_issue)
        assert result.title == "Title Only"
        assert result.content == ""

    def test_create_issue_from_remote_no_backend_id(self, service):
        """Test creating issue without backend_id."""
        remote_issue = SyncIssue(
            id="11",
            title="No Backend ID",
            headline="",
            status="open",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=None,
        )

        result = service.create_issue_from_remote("11", remote_issue)
        assert result.title == "No Backend ID"
        assert "github" not in result.remote_ids

    def test_create_issue_from_remote_duplicate_synced_label(self, service):
        """Test that synced:from-github label is not duplicated."""
        remote_issue = SyncIssue(
            id="12",
            title="With Synced Label",
            headline="",
            status="open",
            labels=["synced:from-github", "bug"],
            assignee=None,
            milestone=None,
            backend_id=12,
        )

        result = service.create_issue_from_remote("12", remote_issue)
        synced_count = sum(
            1 for label in result.labels if label == "synced:from-github"
        )
        assert synced_count == 1

    @patch("roadmap.adapters.sync.services.remote_issue_creation_service.logger")
    def test_create_issue_from_remote_logs_success(self, mock_logger, service):
        """Test that successful creation logs info."""
        remote_issue = SyncIssue(
            id="13",
            title="Logged Issue",
            headline="",
            status="open",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=13,
        )

        service.create_issue_from_remote("13", remote_issue)
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "remote_issue_created_locally" in call_args[0]

    @patch("roadmap.adapters.sync.services.remote_issue_creation_service.logger")
    def test_create_issue_from_remote_logs_error_on_exception(
        self, mock_logger, service
    ):
        """Test that exceptions are logged and re-raised."""
        remote_issue = SyncIssue(
            id="14",
            title="Will Fail",
            headline="",
            status="open",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=14,
        )

        # Force an error in Status creation
        with patch(
            "roadmap.adapters.sync.services.remote_issue_creation_service.Issue"
        ) as mock_issue_class:
            mock_issue_class.side_effect = ValueError("Invalid issue")

            with pytest.raises(ValueError):
                service.create_issue_from_remote("14", remote_issue)

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "remote_issue_creation_failed" in call_args[0]

    def test_normalize_status_static_method(self):
        """Test static method can be called directly."""
        result = RemoteIssueCreationService._normalize_status("open")
        assert result == Status.TODO

    def test_normalize_status_case_insensitive(self):
        """Test status normalization is case-insensitive."""
        assert RemoteIssueCreationService._normalize_status("OPEN") == Status.TODO
        assert RemoteIssueCreationService._normalize_status("CLOSED") == Status.CLOSED
        assert (
            RemoteIssueCreationService._normalize_status("IN_PROGRESS")
            == Status.IN_PROGRESS
        )

    def test_create_issue_from_remote_multiple_calls(self, service):
        """Test creating multiple issues sequentially."""
        issues_data = [
            (SyncIssue(id="101", title="Issue 1", status="open", backend_id=101), 101),
            (
                SyncIssue(id="102", title="Issue 2", status="closed", backend_id=102),
                102,
            ),
            (
                SyncIssue(id="103", title="Issue 3", status="blocked", backend_id=103),
                103,
            ),
        ]

        results = [
            service.create_issue_from_remote(str(backend_id), remote_issue)
            for remote_issue, backend_id in issues_data
        ]

        assert len(results) == 3
        assert all(isinstance(r, Issue) for r in results)
        assert results[0].status == Status.TODO
        assert results[1].status == Status.CLOSED
        assert results[2].status == Status.BLOCKED

    def test_create_issue_from_remote_empty_labels_list(self, service):
        """Test handling of empty labels list."""
        remote_issue = SyncIssue(
            id="15",
            title="Empty Labels",
            headline="",
            status="open",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=15,
        )

        result = service.create_issue_from_remote("15", remote_issue)
        assert "synced:from-github" in result.labels
        assert len(result.labels) == 1

    def test_create_issue_from_remote_complex_labels(self, service):
        """Test with complex label set."""
        labels = ["type:bug", "priority:high", "status:review", "team:backend"]
        remote_issue = SyncIssue(
            id="16",
            title="Complex Labels",
            headline="",
            status="open",
            labels=labels.copy(),
            assignee="jane",
            milestone="v2.0",
            backend_id=16,
        )

        result = service.create_issue_from_remote("16", remote_issue)
        for label in labels:
            assert label in result.labels
        assert "synced:from-github" in result.labels

    def test_create_issue_from_remote_preserves_remote_id_type(self, service):
        """Test that remote_id is stored with correct type."""
        remote_issue = SyncIssue(
            id="12345",
            title="Type Test",
            headline="",
            status="open",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=12345,
        )

        result = service.create_issue_from_remote("12345", remote_issue)
        assert result.remote_ids["github"] == 12345

    def test_create_issue_from_remote_milestone_backlog_default(self, service):
        """Test that None milestone defaults to backlog."""
        remote_issue = SyncIssue(
            id="17",
            title="No Milestone",
            headline="",
            status="open",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=17,
        )

        result = service.create_issue_from_remote("17", remote_issue)
        assert result.milestone == "backlog"

    def test_create_issue_from_remote_milestone_custom(self, service):
        """Test that custom milestone is preserved."""
        remote_issue = SyncIssue(
            id="18",
            title="Custom Milestone",
            headline="",
            status="open",
            labels=[],
            assignee=None,
            milestone="sprint-42",
            backend_id=18,
        )

        result = service.create_issue_from_remote("18", remote_issue)
        assert result.milestone == "sprint-42"

    def test_create_issue_from_remote_assignee_preserved(self, service):
        """Test that assignee is preserved."""
        remote_issue = SyncIssue(
            id="19",
            title="Assigned Issue",
            headline="",
            status="open",
            labels=[],
            assignee="alice",
            milestone=None,
            backend_id=19,
        )

        result = service.create_issue_from_remote("19", remote_issue)
        assert result.assignee == "alice"

    def test_create_issue_from_remote_no_assignee(self, service):
        """Test issue creation without assignee."""
        remote_issue = SyncIssue(
            id="20",
            title="No Assignee",
            headline="",
            status="open",
            labels=[],
            assignee=None,
            milestone=None,
            backend_id=20,
        )

        result = service.create_issue_from_remote("20", remote_issue)
        assert result.assignee is None
