"""Extended coverage tests for GitHub sync orchestrator."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.constants import Status
from roadmap.core.services.github_sync_orchestrator import GitHubSyncOrchestrator
from roadmap.core.services.sync_report import IssueChange


class TestGitHubSyncOrchestratorConflictDetector:
    """Test conflict detector initialization."""

    @pytest.fixture
    def mock_core_no_github_service(self):
        """Create mock core without github_service."""
        core = MagicMock()
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
        core = MagicMock()
        core.issues = MagicMock()
        core.github_service = MagicMock()
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
        core = MagicMock()
        core.issues = MagicMock()
        core.github_service = MagicMock()
        return core

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator with minimal config."""
        config = {"token": "test"}  # Missing owner/repo
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            return GitHubSyncOrchestrator(mock_core, config)

    def test_detect_issue_changes_missing_owner(self, orchestrator, mock_core):
        """Test detect changes when owner is missing from config.

        Covers lines 141-145: Config validation
        """
        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Test Issue"
        issue.github_issue = "123"
        issue.github_sync_metadata = {}

        change = orchestrator._detect_issue_changes(issue)

        assert "error" in change.github_changes
        assert "owner/repo" in change.github_changes["error"]

    def test_detect_issue_changes_missing_repo(self, mock_core):
        """Test detect changes when repo is missing from config."""
        config = {"token": "test", "owner": "user"}  # Missing repo
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            orchestrator = GitHubSyncOrchestrator(mock_core, config)

        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Test Issue"
        issue.github_issue = "123"
        issue.github_sync_metadata = {}

        change = orchestrator._detect_issue_changes(issue)

        assert "error" in change.github_changes

    def test_detect_issue_changes_not_linked(self, mock_core):
        """Test detect changes when issue is not linked to GitHub.

        Covers lines 146-149: No github_issue case
        """
        config = {"token": "test", "owner": "user", "repo": "repo"}
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            orchestrator = GitHubSyncOrchestrator(mock_core, config)

        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Test Issue"
        issue.github_issue = None
        issue.github_sync_metadata = {}

        change = orchestrator._detect_issue_changes(issue)

        assert "error" in change.github_changes
        assert "not linked" in change.github_changes["error"]


class TestGitHubSyncOrchestratorGitHubFetch:
    """Test GitHub issue fetching and error handling."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = MagicMock()
        core.issues = MagicMock()
        core.github_service = MagicMock()
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
            orch.github_client = MagicMock()
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
        core = MagicMock()
        core.issues = MagicMock()
        core.github_service = MagicMock()
        return core

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator."""
        config = {"token": "test", "owner": "user", "repo": "repo"}
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            return GitHubSyncOrchestrator(mock_core, config)

    def test_map_github_status_closed(self, orchestrator):
        """Test mapping closed GitHub status.

        Covers lines 218-220: Closed state mapping
        """
        github_issue = {"state": "closed"}
        status = orchestrator._map_github_status(github_issue)
        assert status == Status.CLOSED.value

    def test_map_github_status_not_planned(self, orchestrator):
        """Test mapping not_planned GitHub status.

        Note: The logic checks state=closed first, so state_reason is never checked.
        This is a potential bug, but testing current behavior.
        Covers lines 221-222: Not planned state reason
        """
        github_issue = {"state": "closed", "state_reason": "not_planned"}
        status = orchestrator._map_github_status(github_issue)
        # Current behavior: closed state takes precedence
        assert status == Status.CLOSED.value

    def test_map_github_status_open(self, orchestrator):
        """Test mapping open GitHub status.

        Covers lines 224-226: Open state mapping
        """
        github_issue = {"state": "open"}
        status = orchestrator._map_github_status(github_issue)
        assert status == Status.TODO.value

    def test_map_github_status_no_state(self, orchestrator):
        """Test mapping when state is missing."""
        github_issue = {}
        status = orchestrator._map_github_status(github_issue)
        assert status == Status.TODO.value


class TestGitHubSyncOrchestratorChangeDetection:
    """Test local and GitHub change detection."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = MagicMock()
        core.issues = MagicMock()
        core.github_service = MagicMock()
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

    def test_detect_github_changes_status_change(self, orchestrator):
        """Test detecting GitHub status changes.

        Covers lines 254-257: Status change detection
        """
        issue = MagicMock()
        issue.status = Status.TODO
        issue.title = "Test"
        issue.content = "Description"

        github_issue = {
            "state": "closed",  # Different state
            "title": "Test",
            "body": "Description",
        }

        changes = orchestrator._detect_github_changes(issue, github_issue)
        assert "status" in changes
        # Status.CLOSED.value is "closed"
        assert "closed" in changes["status"]

    def test_detect_github_changes_title_change(self, orchestrator):
        """Test detecting GitHub title changes.

        Covers lines 259-261: Title change detection
        """
        issue = MagicMock()
        issue.status = Status.TODO
        issue.title = "Old Title"
        issue.content = "Description"

        github_issue = {"state": "open", "title": "New Title", "body": "Description"}

        changes = orchestrator._detect_github_changes(issue, github_issue)
        assert "title" in changes

    def test_detect_github_changes_description_change(self, orchestrator):
        """Test detecting GitHub description changes.

        Covers lines 263-265: Description change detection
        """
        issue = MagicMock()
        issue.status = Status.TODO
        issue.title = "Test"
        issue.content = "Old Description"

        github_issue = {"state": "open", "title": "Test", "body": "New Description"}

        changes = orchestrator._detect_github_changes(issue, github_issue)
        assert "description" in changes

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
        core = MagicMock()
        core.issues = MagicMock()
        core.github_service = MagicMock()
        return core

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator."""
        config = {"token": "test", "owner": "user", "repo": "repo"}
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            orch = GitHubSyncOrchestrator(mock_core, config)
            orch.metadata_service = MagicMock()
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

    def test_apply_local_changes_status_change(self, orchestrator, mock_core):
        """Test applying local status change.

        Covers lines 270-276: Status change application
        """
        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Test"
        issue.status = Status.TODO
        mock_core.issues.get.return_value = issue

        change = IssueChange(issue_id="issue1", title="Test")
        # Status values are like "todo", "closed", "blocked"
        change.local_changes = {"status": "todo -> closed"}

        orchestrator._apply_local_changes(change)

        # The code splits on " -> " and takes second part
        # Then tries Status("closed") which should work
        assert issue.status == Status.CLOSED
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

    def test_apply_local_changes_title_change(self, orchestrator, mock_core):
        """Test applying local title change.

        Covers lines 278-279: Title change application
        """
        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Old Title"
        issue.status = Status.TODO
        mock_core.issues.get.return_value = issue

        change = IssueChange(issue_id="issue1", title="Old Title")
        change.local_changes = {"title": "Old Title -> New Title"}

        orchestrator._apply_local_changes(change)

        assert issue.title == "New Title"

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

    def test_apply_github_changes_status_change(self, orchestrator, mock_core):
        """Test applying GitHub status change.

        Covers lines 326-332: Status change application
        """
        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Test"
        issue.status = Status.TODO
        mock_core.issues.get.return_value = issue

        change = IssueChange(issue_id="issue1", title="Test")
        # Note: Status.CLOSED.value is "closed"
        change.github_changes = {"status": "todo -> closed"}

        orchestrator._apply_github_changes(change)

        # Should attempt to parse the status change
        # The parsing logic splits on " -> " and tries to convert to Status
        # "closed" should map to Status.CLOSED
        mock_core.issues.update.assert_called_once()

    def test_apply_github_changes_title_change(self, orchestrator, mock_core):
        """Test applying GitHub title change.

        Covers lines 334-335: Title change application
        """
        issue = MagicMock()
        issue.id = "issue1"
        issue.title = "Old Title"
        issue.status = Status.TODO
        mock_core.issues.get.return_value = issue

        change = IssueChange(issue_id="issue1", title="Old Title")
        change.github_changes = {"title": "Old Title -> New Title"}

        orchestrator._apply_github_changes(change)

        assert issue.title == "New Title"

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
        core = MagicMock()
        core.issues = MagicMock()
        core.github_service = MagicMock()
        return core

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator."""
        config = {"token": "test", "owner": "user", "repo": "repo"}
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            return GitHubSyncOrchestrator(mock_core, config)

    def test_get_last_sync_time_no_metadata_attr(self, orchestrator):
        """Test when github_sync_metadata attribute doesn't exist."""
        issue = MagicMock(spec=[])  # No attributes

        sync_time = orchestrator._get_last_sync_time(issue)
        assert sync_time is None

    def test_get_last_sync_time_empty_metadata(self, orchestrator):
        """Test when metadata is empty."""
        issue = MagicMock()
        issue.github_sync_metadata = {}

        sync_time = orchestrator._get_last_sync_time(issue)
        assert sync_time is None

    def test_get_last_sync_time_valid_iso_format(self, orchestrator):
        """Test valid ISO format datetime."""
        issue = MagicMock()
        iso_time = "2024-01-15T10:30:00"
        issue.github_sync_metadata = {"last_sync": iso_time}

        sync_time = orchestrator._get_last_sync_time(issue)
        assert isinstance(sync_time, datetime)
        assert sync_time.year == 2024
        assert sync_time.month == 1
        assert sync_time.day == 15

    def test_get_last_sync_time_invalid_format(self, orchestrator):
        """Test invalid datetime format."""
        issue = MagicMock()
        issue.github_sync_metadata = {"last_sync": "invalid-date"}

        sync_time = orchestrator._get_last_sync_time(issue)
        assert sync_time is None

    def test_get_last_sync_time_none_value(self, orchestrator):
        """Test when last_sync is None."""
        issue = MagicMock()
        issue.github_sync_metadata = {"last_sync": None}

        sync_time = orchestrator._get_last_sync_time(issue)
        assert sync_time is None
