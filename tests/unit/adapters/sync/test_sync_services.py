"""Unit tests for sync service layer (IssueStateService, IssuePersistenceService, SyncLinkingService)."""

from datetime import UTC, datetime
from unittest.mock import Mock

from roadmap.adapters.sync.services import (
    IssuePersistenceService,
    IssueStateService,
    SyncLinkingService,
)
from roadmap.common.constants import Priority, Status
from roadmap.core.models.sync_models import SyncIssue
from tests.fixtures.issue_factory import IssueFactory


class TestIssueStateService:
    """Test suite for IssueStateService."""

    def test_sync_issue_to_issue_basic_conversion(self):
        """Test basic SyncIssue to Issue conversion."""
        sync_issue = SyncIssue(
            id="remote-42",
            title="Test Issue",
            headline="Short description",
            status="todo",
            backend_name="github",
            backend_id=42,
        )

        result = IssueStateService.sync_issue_to_issue("local-123", sync_issue)

        assert result.id == "local-123"
        assert result.title == "Test Issue"
        assert result.content == "Short description"
        assert result.status == Status.TODO
        assert result.priority == Priority.MEDIUM

    def test_sync_issue_to_issue_with_timestamps(self):
        """Test timestamp handling in conversion."""
        now = datetime.now(UTC)
        sync_issue = SyncIssue(
            id="remote-42",
            title="Test",
            status="open",
            created_at=now,
            updated_at=now,
            backend_name="github",
            backend_id=42,
        )

        result = IssueStateService.sync_issue_to_issue("local-123", sync_issue)

        assert result.created == now
        assert result.updated == now

    def test_sync_issue_to_issue_preserves_remote_ids(self):
        """Test that remote_ids are preserved from SyncIssue."""
        sync_issue = SyncIssue(
            id="remote-42",
            title="Test",
            status="open",
            remote_ids={"github": 42, "gitlab": 100},
            backend_name="github",
            backend_id=42,
        )

        result = IssueStateService.sync_issue_to_issue("local-123", sync_issue)

        assert result.remote_ids == {"github": 42, "gitlab": 100}

    def test_sync_issue_to_issue_status_normalization(self):
        """Test status normalization from various backend formats."""
        test_cases = [
            ("closed", Status.CLOSED),
            ("done", Status.CLOSED),
            ("completed", Status.CLOSED),
            ("in_progress", Status.IN_PROGRESS),
            ("in progress", Status.IN_PROGRESS),
            ("active", Status.IN_PROGRESS),
            ("blocked", Status.BLOCKED),
            ("on_hold", Status.BLOCKED),
            ("on hold", Status.BLOCKED),
            ("unknown", Status.TODO),
            ("", Status.TODO),
        ]

        for backend_status, expected_status in test_cases:
            sync_issue = SyncIssue(
                id="remote-42",
                title="Test",
                status=backend_status or "open",  # Ensure status is not empty
                backend_name="github",
                backend_id=42,
            )
            result = IssueStateService.sync_issue_to_issue("local-123", sync_issue)
            assert result.status == expected_status, (
                f"Failed for status: {backend_status}"
            )

    def test_sync_issue_to_issue_metadata_tracking(self):
        """Test that backend metadata is tracked."""
        sync_issue = SyncIssue(
            id="remote-42",
            title="Test",
            status="open",
            backend_name="github",
            backend_id=42,
            metadata={"custom_field": "value"},
        )

        result = IssueStateService.sync_issue_to_issue("local-123", sync_issue)

        assert result.github_sync_metadata is not None
        assert result.github_sync_metadata["backend_name"] == "github"
        assert result.github_sync_metadata["backend_id"] == 42
        assert result.github_sync_metadata["custom_field"] == "value"

    def test_sync_issue_to_issue_with_labels_and_assignee(self):
        """Test that labels and assignee are preserved."""
        sync_issue = SyncIssue(
            id="remote-42",
            title="Test",
            status="open",
            labels=["bug", "urgent"],
            assignee="alice@example.com",
            milestone="v1-0",
            backend_name="github",
            backend_id=42,
        )

        result = IssueStateService.sync_issue_to_issue("local-123", sync_issue)

        assert result.labels == ["bug", "urgent"]
        assert result.assignee == "alice@example.com"
        assert result.milestone == "v1-0"

    def test_issue_to_push_payload_basic(self):
        """Test converting Issue to push payload."""
        issue = IssueFactory.create(
            id="local-123",
            title="Test Issue",
            content="Issue description",
            status=Status.TODO,
        )

        payload = IssueStateService.issue_to_push_payload(issue)

        assert payload["title"] == "Test Issue"
        assert payload["body"] == "Issue description"
        assert payload["state"] == "open"

    def test_issue_to_push_payload_closed_state(self):
        """Test that CLOSED status converts to 'closed' state."""
        issue = IssueFactory.create(
            id="local-123",
            title="Test",
            status=Status.CLOSED,
        )

        payload = IssueStateService.issue_to_push_payload(issue)

        assert payload["state"] == "closed"

    def test_issue_to_push_payload_with_labels(self):
        """Test payload generation with labels."""
        issue = IssueFactory.create(
            id="local-123",
            title="Test",
            labels=["bug", "feature"],
        )

        payload = IssueStateService.issue_to_push_payload(issue)

        assert "labels" in payload
        assert sorted(payload["labels"]) == ["bug", "feature"]

    def test_issue_to_push_payload_with_comma_separated_labels(self):
        """Test payload generation with comma-separated labels."""
        issue = IssueFactory.create(
            id="local-123",
            title="Test",
            labels=["bug, feature, urgent"],
        )

        payload = IssueStateService.issue_to_push_payload(issue)

        assert sorted(payload["labels"]) == ["bug", "feature", "urgent"]

    def test_issue_to_push_payload_empty_labels(self):
        """Test that empty labels are not included in payload."""
        issue = IssueFactory.create(
            id="local-123",
            title="Test",
            labels=[],
        )

        payload = IssueStateService.issue_to_push_payload(issue)

        assert "labels" not in payload

    def test_normalize_status_all_cases(self):
        """Test status normalization method."""
        test_cases = [
            ("closed", Status.CLOSED),
            ("done", Status.CLOSED),
            ("completed", Status.CLOSED),
            ("resolved", Status.CLOSED),
            ("in_progress", Status.IN_PROGRESS),
            ("in progress", Status.IN_PROGRESS),
            ("active", Status.IN_PROGRESS),
            ("started", Status.IN_PROGRESS),
            ("blocked", Status.BLOCKED),
            ("on_hold", Status.BLOCKED),
            ("on hold", Status.BLOCKED),
            ("paused", Status.BLOCKED),
            ("todo", Status.TODO),
            (None, Status.TODO),
            ("", Status.TODO),
            ("unknown", Status.TODO),
        ]

        for input_status, expected in test_cases:
            result = IssueStateService.normalize_status(input_status)
            assert result == expected, f"Failed for: {input_status}"


class TestIssuePersistenceService:
    """Test suite for IssuePersistenceService."""

    def test_update_issue_with_remote_id(self):
        """Test updating issue with remote ID."""
        issue = IssueFactory.create(id="local-123", title="Test")
        issue.remote_ids = {}

        IssuePersistenceService.update_issue_with_remote_id(issue, "github", 42)

        assert issue.remote_ids["github"] == "42"

    def test_update_issue_with_remote_id_preserves_existing(self):
        """Test that existing remote IDs are preserved."""
        issue = IssueFactory.create(id="local-123", title="Test")
        issue.remote_ids = {"gitlab": "100"}

        IssuePersistenceService.update_issue_with_remote_id(issue, "github", 42)

        assert issue.remote_ids["gitlab"] == "100"
        assert issue.remote_ids["github"] == "42"

    def test_update_issue_with_remote_id_initializes_dict(self):
        """Test that remote_ids dict is initialized if empty."""
        issue = IssueFactory.create(id="local-123", title="Test")
        issue.remote_ids = {}

        IssuePersistenceService.update_issue_with_remote_id(issue, "github", 42)

        assert issue.remote_ids is not None
        assert issue.remote_ids["github"] == "42"

    def test_update_github_issue_number(self):
        """Test updating github_issue field."""
        issue = IssueFactory.create(id="local-123", title="Test")

        IssuePersistenceService.update_github_issue_number(issue, 42)

        assert issue.github_issue == 42

    def test_save_issue_success(self, mock_core_with_repo_factory):
        """Test successful issue save."""
        issue = IssueFactory.create(id="local-123", title="Test")
        mock_core = mock_core_with_repo_factory()
        mock_repo = mock_core.issue_service.repository

        result = IssuePersistenceService.save_issue(issue, mock_core)

        assert result is True
        mock_repo.save.assert_called_once_with(issue)

    def test_save_issue_failure(self, mock_core_with_repo_factory):
        """Test issue save failure handling."""
        issue = IssueFactory.create(id="local-123", title="Test")
        mock_core = mock_core_with_repo_factory(
            save_side_effect=Exception("Save failed")
        )

        result = IssuePersistenceService.save_issue(issue, mock_core)

        assert result is False

    def test_get_issue_from_repo_found(self, mock_core_with_repo_factory):
        """Test retrieving an existing issue from repo."""
        issue = IssueFactory.create(id="local-123", title="Test")
        mock_core = mock_core_with_repo_factory(get_return=issue)
        mock_repo = mock_core.issue_service.repository

        result = IssuePersistenceService.get_issue_from_repo("local-123", mock_core)

        assert result == issue
        mock_repo.get.assert_called_once_with("local-123")

    def test_get_issue_from_repo_not_found(self, mock_core_with_repo_factory):
        """Test retrieving a non-existent issue from repo."""
        mock_core = mock_core_with_repo_factory(get_return=None)

        result = IssuePersistenceService.get_issue_from_repo("nonexistent", mock_core)

        assert result is None

    def test_get_issue_from_repo_failure(self, mock_core_with_repo_factory):
        """Test issue retrieval failure handling."""
        mock_core = mock_core_with_repo_factory(get_return=None)
        mock_core.issue_service.repository.get = Mock(
            side_effect=Exception("Repo error")
        )

        result = IssuePersistenceService.get_issue_from_repo("local-123", mock_core)

        assert result is None

    def test_apply_sync_issue_to_local_updates_fields(self):
        """Test applying sync issue updates to local issue."""
        local_issue = IssueFactory.create(
            id="local-123",
            title="Old Title",
            content="Old content",
            assignee="old@example.com",
        )
        sync_issue = SyncIssue(
            id="remote-42",
            title="New Title",
            status="open",
            headline="New content",
            assignee="new@example.com",
            labels=["updated"],
            backend_name="github",
            backend_id=42,
        )

        IssuePersistenceService.apply_sync_issue_to_local(local_issue, sync_issue)

        assert local_issue.title == "New Title"
        assert local_issue.assignee == "new@example.com"
        assert local_issue.labels == ["updated"]
        # Note: content field is NOT updated from headline in apply_sync_issue_to_local

    def test_apply_sync_issue_to_local_preserves_local_id(self):
        """Test that local ID is preserved during update."""
        local_issue = IssueFactory.create(id="local-123", title="Test")
        sync_issue = SyncIssue(
            id="remote-42",
            title="Updated",
            status="open",
            backend_name="github",
            backend_id=42,
        )

        IssuePersistenceService.apply_sync_issue_to_local(local_issue, sync_issue)

        assert local_issue.id == "local-123"

    def test_is_github_linked_with_direct_field(self):
        """Test detecting GitHub link via direct field."""
        issue = IssueFactory.create(id="local-123", title="Test")
        issue.remote_ids = {"github": 42}

        result = IssuePersistenceService.is_github_linked(issue)

        assert result is True

    def test_is_github_linked_not_linked(self):
        """Test detecting unlinked issue."""
        issue = IssueFactory.create(id="local-123", title="Test")
        issue.remote_ids = {"gitlab": 100}

        result = IssuePersistenceService.is_github_linked(issue)

        assert result is False

    def test_get_github_issue_number_from_remote_ids(self):
        """Test extracting GitHub number from remote_ids."""
        issue = IssueFactory.create(id="local-123", title="Test")
        issue.remote_ids = {"github": "42"}

        result = IssuePersistenceService.get_github_issue_number(issue)

        assert result == "42"

    def test_get_github_issue_number_not_found(self):
        """Test when GitHub issue is not linked."""
        issue = IssueFactory.create(id="local-123", title="Test")
        issue.remote_ids = {}

        result = IssuePersistenceService.get_github_issue_number(issue)

        assert result is None


class TestSyncLinkingService:
    """Test suite for SyncLinkingService."""

    def test_link_issue_in_database_success(self, mock_repo_factory):
        """Test successful database linking."""
        mock_repo = mock_repo_factory(link_issue_return=None)

        result = SyncLinkingService.link_issue_in_database(
            mock_repo, "local-123", "github", 42
        )

        assert result is True
        mock_repo.link_issue.assert_called_once_with(
            issue_uuid="local-123",
            backend_name="github",
            remote_id="42",
        )

    def test_link_issue_in_database_with_none_repo(self):
        """Test linking when repo is None."""
        result = SyncLinkingService.link_issue_in_database(
            None, "local-123", "github", 42
        )

        assert result is True  # Not an error if repo is None

    def test_link_issue_in_database_failure(self, mock_repo_factory):
        """Test linking failure handling."""
        mock_repo = mock_repo_factory(link_issue_side_effect=Exception("Link failed"))

        result = SyncLinkingService.link_issue_in_database(
            mock_repo, "local-123", "github", 42
        )

        assert result is False

    def test_find_duplicate_by_title_found(self, mock_core_with_repo_factory):
        """Test finding a duplicate issue by title."""
        found_issue = IssueFactory.create(id="existing-123", title="Test Title")

        mock_core = mock_core_with_repo_factory(
            list_return=[
                IssueFactory.create(id="other-1", title="Other"),
                found_issue,
                IssueFactory.create(id="other-2", title="Another"),
            ]
        )

        result = SyncLinkingService.find_duplicate_by_title(
            "Test Title", "github", mock_core
        )

        assert result == found_issue

    def test_find_duplicate_by_title_case_insensitive(
        self, mock_core_with_repo_factory
    ):
        """Test that duplicate search is case-insensitive."""
        found_issue = IssueFactory.create(id="existing-123", title="Test Title")

        mock_core = mock_core_with_repo_factory(list_return=[found_issue])

        result = SyncLinkingService.find_duplicate_by_title(
            "test title", "github", mock_core
        )

        assert result == found_issue

    def test_find_duplicate_by_title_not_found(self, mock_core_with_repo_factory):
        """Test when no duplicate is found."""
        mock_core = mock_core_with_repo_factory(
            list_return=[
                IssueFactory.create(id="other-1", title="Other"),
                IssueFactory.create(id="other-2", title="Another"),
            ]
        )

        result = SyncLinkingService.find_duplicate_by_title(
            "Nonexistent", "github", mock_core
        )

        assert result is None

    def test_find_duplicate_by_title_failure(self, mock_core_with_repo_factory):
        """Test duplicate search failure handling."""
        mock_core = mock_core_with_repo_factory()
        mock_core.issue_service.repository.list = Mock(
            side_effect=Exception("List failed")
        )

        result = SyncLinkingService.find_duplicate_by_title("Test", "github", mock_core)

        assert result is None

    def test_get_local_id_from_remote_found(self, mock_repo_factory):
        """Test retrieving local ID from remote ID."""
        mock_repo = mock_repo_factory(get_issue_uuid_return="local-123")

        result = SyncLinkingService.get_local_id_from_remote("github", 42, mock_repo)

        assert result == "local-123"
        mock_repo.get_issue_uuid.assert_called_once_with(
            backend_name="github", remote_id="42"
        )

    def test_get_local_id_from_remote_not_found(self, mock_repo_factory):
        """Test when local ID is not found."""
        mock_repo = mock_repo_factory(get_issue_uuid_return=None)

        result = SyncLinkingService.get_local_id_from_remote("github", 42, mock_repo)

        assert result is None

    def test_get_local_id_from_remote_with_none_repo(self):
        """Test retrieval when repo is None."""
        result = SyncLinkingService.get_local_id_from_remote("github", 42, None)

        assert result is None

    def test_get_local_id_from_remote_failure(self, mock_repo_factory):
        """Test retrieval failure handling."""
        mock_repo = mock_repo_factory()
        mock_repo.get_issue_uuid = Mock(side_effect=Exception("Lookup failed"))

        result = SyncLinkingService.get_local_id_from_remote("github", 42, mock_repo)

        assert result is None

    def test_link_sync_issue_success(self, mock_repo_factory):
        """Test linking a SyncIssue to database."""
        sync_issue = SyncIssue(
            id="remote-42",
            title="Test",
            status="open",
            backend_name="github",
            backend_id=42,
        )
        mock_repo = mock_repo_factory(link_issue_return=None)

        result = SyncLinkingService.link_sync_issue(sync_issue, "local-123", mock_repo)

        assert result is True
        mock_repo.link_issue.assert_called_once()

    def test_link_sync_issue_with_none_backend_id(self):
        """Test linking SyncIssue with None backend_id."""
        sync_issue = SyncIssue(
            id="remote-42",
            title="Test",
            status="open",
            backend_name="github",
            backend_id=None,
        )
        mock_repo = Mock()

        result = SyncLinkingService.link_sync_issue(sync_issue, "local-123", mock_repo)

        assert result is False
        mock_repo.link_issue.assert_not_called()

    def test_is_linked_true(self, mock_repo_factory):
        """Test detecting a linked issue."""
        mock_repo = mock_repo_factory(get_remote_id_return="42")

        result = SyncLinkingService.is_linked("local-123", "github", mock_repo)

        assert result is True

    def test_is_linked_false(self, mock_repo_factory):
        """Test detecting an unlinked issue."""
        mock_repo = mock_repo_factory(get_remote_id_return=None)

        result = SyncLinkingService.is_linked("local-123", "github", mock_repo)

        assert result is False

    def test_is_linked_with_none_repo(self):
        """Test is_linked when repo is None."""
        result = SyncLinkingService.is_linked("local-123", "github", None)

        assert result is False

    def test_is_linked_failure(self, mock_repo_factory):
        """Test is_linked failure handling."""
        mock_repo = mock_repo_factory()
        mock_repo.get_remote_id = Mock(side_effect=Exception("Lookup failed"))

        result = SyncLinkingService.is_linked("local-123", "github", mock_repo)

        assert result is False
