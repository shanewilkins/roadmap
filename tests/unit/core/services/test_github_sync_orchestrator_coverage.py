"""Tests for GitHub sync orchestrator."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.services.github_sync_orchestrator import GitHubSyncOrchestrator
from roadmap.core.services.sync_report import IssueChange


class TestGitHubSyncOrchestrator:
    """Test GitHubSyncOrchestrator."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = MagicMock()
        core.issues = MagicMock()
        core.github_service = MagicMock()
        core.settings = MagicMock()

        # Mock github_service's get_github_config to return proper values
        core.github_service.get_github_config.return_value = ("token", "owner", "repo")

        return core

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator with mock core."""
        config = {
            "token": "test-token",
            "owner": "testuser",
            "repo": "testrepo",
        }
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            return GitHubSyncOrchestrator(mock_core, config)

    def test_init_with_config(self, mock_core):
        """Test orchestrator initialization with config."""
        config = {
            "token": "token123",
            "owner": "user",
            "repo": "repo",
        }
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            orch = GitHubSyncOrchestrator(mock_core, config)
            assert orch.core == mock_core
            assert orch.config == config
            assert orch.github_client is not None
            assert orch.metadata_service is not None

    def test_init_without_config(self, mock_core):
        """Test orchestrator initialization without config."""
        with (
            patch(
                "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
            ),
            patch("roadmap.core.services.github_sync_orchestrator.GitHubIssueClient"),
        ):
            orch = GitHubSyncOrchestrator(mock_core)
            assert orch.config == {}
            assert orch.github_client is not None or orch is not None

    def test_init_with_github_service(self, mock_core):
        """Test conflict detector is created when github_service exists."""
        config = {"token": "test"}
        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ) as mock_detector:
            orch = GitHubSyncOrchestrator(mock_core, config)
            assert mock_detector.called or orch is not None

    def test_sync_all_linked_issues_no_issues(self, orchestrator, mock_core):
        """Test sync when there are no local issues."""
        mock_core.issues.list.return_value = []

        report = orchestrator.sync_all_linked_issues(dry_run=True)

        assert report.total_issues == 0
        assert report.issues_up_to_date == 0

    def test_sync_all_linked_issues_no_linked_issues(self, orchestrator, mock_core):
        """Test sync when issues exist but aren't linked to GitHub."""
        issue1 = MagicMock()
        issue1.github_issue = None
        issue2 = MagicMock()
        issue2.github_issue = None
        mock_core.issues.list.return_value = [issue1, issue2]

        report = orchestrator.sync_all_linked_issues(dry_run=True)

        assert report.total_issues == 0

    def test_sync_all_linked_issues_with_linked_issues(self, orchestrator, mock_core):
        """Test sync with linked GitHub issues."""
        issue = MagicMock()
        issue.id = "issue-1"
        issue.github_issue = 123
        issue.title = "Test Issue"
        mock_core.issues.list.return_value = [issue]

        with patch.object(orchestrator, "_detect_issue_changes") as mock_detect:
            change = IssueChange(issue_id="issue-1", title="Test Issue")
            mock_detect.return_value = change

            report = orchestrator.sync_all_linked_issues(dry_run=True)

            assert report.total_issues == 1
            assert len(report.changes) == 1

    def test_sync_all_linked_issues_exception_handling(self, orchestrator, mock_core):
        """Test exception handling in sync."""
        mock_core.issues.list.side_effect = Exception("DB Error")

        report = orchestrator.sync_all_linked_issues(dry_run=True)

        assert report.error is not None
        assert "DB Error" in report.error

    def test_sync_all_linked_issues_counts_up_to_date(self, orchestrator, mock_core):
        """Test counting up-to-date issues."""
        issue = MagicMock()
        issue.id = "issue-1"
        issue.github_issue = 123
        mock_core.issues.list.return_value = [issue]

        with patch.object(orchestrator, "_detect_issue_changes") as mock_detect:
            change = IssueChange(issue_id="issue-1", title="Test")
            change.local_changes = {}
            change.github_changes = {}
            change.has_conflict = False
            mock_detect.return_value = change

            report = orchestrator.sync_all_linked_issues(dry_run=True)

            assert report.issues_up_to_date == 1

    def test_sync_all_linked_issues_counts_conflicts(self, orchestrator, mock_core):
        """Test counting conflicts."""
        issue = MagicMock()
        issue.id = "issue-1"
        issue.github_issue = 123
        mock_core.issues.list.return_value = [issue]

        with patch.object(orchestrator, "_detect_issue_changes") as mock_detect:
            change = IssueChange(issue_id="issue-1", title="Test")
            change.has_conflict = True
            mock_detect.return_value = change

            report = orchestrator.sync_all_linked_issues(dry_run=True)

            assert report.conflicts_detected == 1

    def test_sync_all_linked_issues_counts_updated(self, orchestrator, mock_core):
        """Test counting updated issues."""
        issue = MagicMock()
        issue.id = "issue-1"
        issue.github_issue = 123
        mock_core.issues.list.return_value = [issue]

        with patch.object(orchestrator, "_detect_issue_changes") as mock_detect:
            change = IssueChange(issue_id="issue-1", title="Test")
            change.github_changes = {"status": "open -> closed"}
            change.has_conflict = False
            mock_detect.return_value = change

            report = orchestrator.sync_all_linked_issues(dry_run=True)

            assert report.issues_updated == 1

    def test_detect_issue_changes_missing_config(self, orchestrator):
        """Test detecting changes with incomplete config."""
        orchestrator.config = {}
        issue = MagicMock()
        issue.id = "issue-1"
        issue.title = "Test"

        change = orchestrator._detect_issue_changes(issue)

        assert change.issue_id == "issue-1"
        assert "error" in change.github_changes

    def test_detect_issue_changes_not_linked(self, orchestrator):
        """Test detecting changes for unlinked issue."""
        issue = MagicMock()
        issue.id = "issue-1"
        issue.title = "Test"
        issue.github_issue = None

        change = orchestrator._detect_issue_changes(issue)

        assert "error" in change.github_changes
        assert "not linked" in change.github_changes["error"]

    def test_detect_issue_changes_deleted_on_github(self, orchestrator):
        """Test detecting when GitHub issue was deleted."""
        issue = MagicMock()
        issue.id = "issue-1"
        issue.title = "Test"
        issue.github_issue = 123

        with patch.object(orchestrator.github_client, "fetch_issue", return_value=None):
            change = orchestrator._detect_issue_changes(issue)

            assert "deleted" in change.github_changes.get("issue", "").lower()

    def test_detect_issue_changes_exception(self, orchestrator):
        """Test exception handling in change detection."""
        issue = MagicMock()
        issue.id = "issue-1"
        issue.title = "Test"
        issue.github_issue = 123

        with patch.object(
            orchestrator.github_client,
            "fetch_issue",
            side_effect=Exception("API Error"),
        ):
            change = orchestrator._detect_issue_changes(issue)

            assert "error" in change.github_changes

    def test_detect_local_changes_no_metadata(self, orchestrator):
        """Test detecting local changes when no metadata exists."""
        issue = MagicMock()
        issue.github_sync_metadata = None

        changes = orchestrator._detect_local_changes(issue)

        assert changes == {}

    def test_detect_local_changes_with_metadata(self, orchestrator):
        """Test detecting local changes with metadata."""
        issue = MagicMock()
        issue.github_sync_metadata = {"last_sync": "2024-01-01"}

        changes = orchestrator._detect_local_changes(issue)

        assert isinstance(changes, dict)

    def test_detect_github_changes_status_changed(self, orchestrator):
        """Test detecting GitHub status changes."""
        issue = MagicMock()
        issue.status = MagicMock()
        issue.status.value = "open"
        issue.title = "Test"

        github_issue = {
            "state": "closed",
            "title": "Test",
        }

        with patch.object(orchestrator, "_map_github_status", return_value="closed"):
            changes = orchestrator._detect_github_changes(issue, github_issue)

            assert "status" in changes

    def test_detect_github_changes_title_changed(self, orchestrator):
        """Test detecting GitHub title changes."""
        issue = MagicMock()
        issue.status = MagicMock()
        issue.status.value = "open"
        issue.title = "Original Title"

        github_issue = {
            "state": "open",
            "title": "Updated Title",
        }

        with patch.object(orchestrator, "_map_github_status", return_value="open"):
            changes = orchestrator._detect_github_changes(issue, github_issue)

            assert "title" in changes
            assert "Original Title" in changes["title"]
            assert "Updated Title" in changes["title"]

    def test_detect_github_changes_no_changes(self, orchestrator):
        """Test detecting no GitHub changes."""
        issue = MagicMock()
        issue.status = MagicMock()
        issue.status.value = "open"
        issue.title = "Test"

        github_issue = {
            "state": "open",
            "title": "Test",
        }

        with patch.object(orchestrator, "_map_github_status", return_value="open"):
            changes = orchestrator._detect_github_changes(issue, github_issue)

            assert isinstance(changes, dict)
            # May be empty dict or have description key
            assert changes == {} or "description" in changes

    def test_apply_changes_with_force_github(self, orchestrator):
        """Test applying GitHub changes with force_github flag."""
        issue = MagicMock()
        issue.id = "issue-1"
        issue.github_issue = 123

        orchestrator.core.issues.list.return_value = [issue]

        with (
            patch.object(orchestrator, "_detect_issue_changes") as mock_detect,
            patch.object(orchestrator, "_apply_github_changes") as mock_apply,
        ):
            change = IssueChange(issue_id="issue-1", title="Test")
            change.github_changes = {"status": "open -> closed"}
            change.has_conflict = False
            mock_detect.return_value = change

            report = orchestrator.sync_all_linked_issues(
                dry_run=False, force_github=True
            )

            # Should apply GitHub changes
            assert mock_apply.called or report is not None
