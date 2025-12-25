"""Extended coverage tests for GitHub sync orchestrator."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.constants import Status
from roadmap.core.services.github_sync_orchestrator import GitHubSyncOrchestrator
from roadmap.core.services.sync_report import IssueChange
from tests.unit.domain.test_data_factory import TestDataFactory


class TestGitHubSyncOrchestratorConflictDetector:
    """Test conflict detector initialization."""

    @pytest.fixture
    def mock_core_no_github_service(self):
        """Create mock core without github_service."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        # Explicitly remove github_service attribute
        if hasattr(core, "github_service"):
            delattr(core, "github_service")
        return core

    def test_init_without_github_service(self, mock_core_no_github_service):
        """Test orchestrator initialization when github_service is missing.

        This covers line 33: self.conflict_detector = None
        """
        with (
            patch("roadmap.core.services.github_sync_orchestrator.GitHubIssueClient"),
            patch("roadmap.core.services.github_sync_orchestrator.SyncMetadataService"),
        ):
            orch = GitHubSyncOrchestrator(mock_core_no_github_service)
            assert orch.conflict_detector is None


class TestGitHubSyncOrchestratorEmptyIssues:
    """Test sync with empty or no linked issues."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.issues = TestDataFactory.create_mock_core(is_initialized=True)
        return core

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator."""
        config = {"token": "test", "owner": "user", "repo": "repo"}
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            return GitHubSyncOrchestrator(mock_core, config)

    def test_sync_all_linked_issues_empty_list(self, orchestrator, mock_core):
        """Test sync when no issues exist at all.

        Covers lines 89-90: Empty linked_issues case
        """
        mock_core.issues.list.return_value = []

        report = orchestrator.sync_all_linked_issues(dry_run=True)

        assert report.total_issues == 0
        assert report.issues_up_to_date == 0
        assert len(report.changes) == 0


class TestGitHubSyncOrchestratorConfigValidation:
    """Test GitHub config validation and error handling."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.issues = TestDataFactory.create_mock_core(is_initialized=True)
        return core

    @pytest.mark.parametrize(
        "config,issue_github_id,error_key,error_substring",
        [
            ({"token": "test"}, "123", "error", "owner/repo"),
            ({"token": "test", "owner": "user"}, "123", "error", "owner/repo"),
            (
                {"token": "test", "owner": "user", "repo": "repo"},
                None,
                "error",
                "not linked",
            ),
        ],
    )
    def test_detect_issue_changes_config_missing_or_not_linked(
        self, mock_core, config, issue_github_id, error_key, error_substring
    ):
        """Test detect changes with missing config or unlinked issues.

        Covers lines 141-149: Config validation and unlinked issue cases
        """
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            orchestrator = GitHubSyncOrchestrator(mock_core, config)

        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Test Issue"
        issue.github_issue = issue_github_id
        issue.github_sync_metadata = {}

        change = orchestrator._detect_issue_changes(issue)

        assert error_key in change.github_changes
        assert error_substring in change.github_changes[error_key]


class TestGitHubSyncOrchestratorGitHubFetch:
    """Test GitHub issue fetching and error handling."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.issues = TestDataFactory.create_mock_core(is_initialized=True)
        return core

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator."""
        config = {"token": "test", "owner": "user", "repo": "repo"}
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            orch = GitHubSyncOrchestrator(mock_core, config)
            # Mock the github_client
            orch.github_client = TestDataFactory.create_mock_core(is_initialized=True)
            return orch

    def test_detect_issue_changes_github_issue_deleted(self, orchestrator):
        """Test when GitHub issue has been deleted.

        Covers lines 150-152: GitHub issue fetch returns None
        """
        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Test Issue"
        issue.github_issue = 123
        issue.github_sync_metadata = {}

        orchestrator.github_client.fetch_issue.return_value = None

        change = orchestrator._detect_issue_changes(issue)

        assert "issue" in change.github_changes
        assert "deleted" in change.github_changes["issue"]

    def test_detect_issue_changes_fetch_exception(self, orchestrator):
        """Test exception handling during GitHub fetch.

        Covers lines 164-165: Exception during fetch
        """
        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Test Issue"
        issue.github_issue = 123
        issue.github_sync_metadata = {}

        orchestrator.github_client.fetch_issue.side_effect = Exception("Network error")

        change = orchestrator._detect_issue_changes(issue)

        assert "error" in change.github_changes
        assert "Failed to fetch" in change.github_changes["error"]

    def test_detect_issue_changes_github_issue_string(self, orchestrator):
        """Test handling of github_issue as string."""
        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Test Issue"
        issue.github_issue = "456"  # String instead of int
        issue.github_sync_metadata = {}
        issue.status = Status.TODO
        issue.content = "Description"

        github_issue = {"state": "open", "title": "Test Issue", "body": "Description"}
        orchestrator.github_client.fetch_issue.return_value = github_issue

        orchestrator._detect_issue_changes(issue)

        # Should successfully parse string to int
        orchestrator.github_client.fetch_issue.assert_called_once()
        call_args = orchestrator.github_client.fetch_issue.call_args
        # Third argument should be 456 (as int)
        assert call_args[0][2] == 456


class TestGitHubStatusMapping:
    """Test GitHub status mapping to local status."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.issues = TestDataFactory.create_mock_core(is_initialized=True)
        return core

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator."""
        config = {"token": "test", "owner": "user", "repo": "repo"}
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            return GitHubSyncOrchestrator(mock_core, config)

    @pytest.mark.parametrize(
        "github_issue,expected_status",
        [
            ({"state": "closed"}, Status.CLOSED.value),
            ({"state": "closed", "state_reason": "not_planned"}, Status.CLOSED.value),
            ({"state": "open"}, Status.TODO.value),
            ({}, Status.TODO.value),
        ],
    )
    def test_map_github_status(self, orchestrator, github_issue, expected_status):
        """Test mapping GitHub status to local status.

        Covers lines 218-226: Status mapping logic
        """
        status = orchestrator._map_github_status(github_issue)
        assert status == expected_status


class TestGitHubSyncOrchestratorChangeDetection:
    """Test local and GitHub change detection."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.issues = TestDataFactory.create_mock_core(is_initialized=True)
        return core

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator."""
        config = {"token": "test", "owner": "user", "repo": "repo"}
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            return GitHubSyncOrchestrator(mock_core, config)

    def test_detect_local_changes_no_metadata(self, orchestrator):
        """Test detect local changes when no metadata exists.

        Covers lines 239-242: No metadata case
        """
        issue = MagicMock()
        issue.github_sync_metadata = None

        changes = orchestrator._detect_local_changes(issue)
        assert changes == {}

    def test_detect_local_changes_no_github_sync_metadata_attr(self, orchestrator):
        """Test detect local changes when attribute doesn't exist."""
        issue = MagicMock(spec=[])  # No attributes

        changes = orchestrator._detect_local_changes(issue)
        assert changes == {}

    @pytest.mark.parametrize(
        "change_field,old_value,new_value",
        [
            ("status", Status.TODO, Status.CLOSED),
            ("title", "Old Title", "New Title"),
            ("description", "Old Description", "New Description"),
        ],
    )
    def test_detect_github_changes(
        self, orchestrator, change_field, old_value, new_value
    ):
        """Test detecting various GitHub changes.

        Covers lines 254-265: Change detection for status, title, and description
        """
        issue = MagicMock()
        issue.status = old_value if change_field == "status" else Status.TODO
        issue.title = old_value if change_field == "title" else "Test"
        issue.content = old_value if change_field == "description" else "Description"

        github_issue = {
            "state": "closed" if new_value == Status.CLOSED else "open",
            "title": new_value if change_field == "title" else "Test",
            "body": new_value if change_field == "description" else "Description",
        }

        changes = orchestrator._detect_github_changes(issue, github_issue)
        assert change_field in changes

    def test_detect_github_changes_no_changes(self, orchestrator):
        """Test when there are no GitHub changes."""
        issue = MagicMock()
        issue.status = Status.TODO
        issue.title = "Test"
        issue.content = "Description"

        github_issue = {"state": "open", "title": "Test", "body": "Description"}

        changes = orchestrator._detect_github_changes(issue, github_issue)
        assert changes == {}


class TestGitHubSyncOrchestratorApplyChanges:
    """Test applying sync changes to issues."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.issues = TestDataFactory.create_mock_core(is_initialized=True)
        return core

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
        issue.title = old_value if change_field == "title" else "Test"
        issue.status = Status.TODO if change_field != "status" else Status(old_value)
        mock_core.issues.get.return_value = issue

        change = IssueChange(issue_id="issue1", title="Test")
        change.local_changes = {change_field: f"{old_value} -> {new_value}"}

        orchestrator._apply_local_changes(change)

        if change_field == "status":
            assert issue.status == Status.CLOSED
        else:
            assert issue.title == new_value
        mock_core.issues.update.assert_called_once()

    def test_apply_local_changes_invalid_status(self, orchestrator, mock_core):
        """Test applying invalid status value."""
        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Test"
        issue.status = Status.TODO
        mock_core.issues.get.return_value = issue

        change = IssueChange(issue_id="issue1", title="Test")
        change.local_changes = {"status": "TODO -> INVALID_STATUS"}

        orchestrator._apply_local_changes(change)

        # Status should remain unchanged on invalid value
        mock_core.issues.update.assert_called_once()

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
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.issues = TestDataFactory.create_mock_core(is_initialized=True)
        return core

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
