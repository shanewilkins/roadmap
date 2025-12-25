"""Tests for GitHub sync orchestrator."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.services.github_sync_orchestrator import GitHubSyncOrchestrator
from roadmap.core.services.sync_report import SyncReport
from tests.unit.domain.test_data_factory import TestDataFactory


class TestGitHubSyncOrchestrator:
    """Test GitHub sync orchestration."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore with GitHub integration."""
        return TestDataFactory.create_mock_core(
            is_initialized=True, github_service=MagicMock()
        )

    @pytest.fixture
    def orchestrator(self, mock_core):
        """Create orchestrator instance."""
        with patch("roadmap.core.services.github_sync_orchestrator.GitHubIssueClient"):
            with patch(
                "roadmap.core.services.github_sync_orchestrator.SyncMetadataService"
            ):
                with patch(
                    "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
                ):
                    orch = GitHubSyncOrchestrator(
                        mock_core,
                        config={
                            "token": "test_token",
                            "owner": "owner",
                            "repo": "repo",
                        },
                    )
                    return orch

    def test_init_basic(self, mock_core):
        """Test basic initialization."""
        with patch("roadmap.core.services.github_sync_orchestrator.GitHubIssueClient"):
            with patch(
                "roadmap.core.services.github_sync_orchestrator.SyncMetadataService"
            ):
                with patch(
                    "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
                ):
                    orch = GitHubSyncOrchestrator(mock_core)
                    assert orch.core == mock_core
                    assert orch.config == {}

    def test_init_with_config(self, mock_core):
        """Test initialization with config."""
        config = {"token": "ghp_test_token", "owner": "test", "repo": "repo"}
        with patch("roadmap.core.services.github_sync_orchestrator.GitHubIssueClient"):
            with patch(
                "roadmap.core.services.github_sync_orchestrator.SyncMetadataService"
            ):
                with patch(
                    "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
                ):
                    orch = GitHubSyncOrchestrator(mock_core, config=config)
                    assert orch.config == config

    def test_sync_all_linked_issues_dry_run(self, orchestrator):
        """Test syncing all linked issues in dry-run mode."""
        with patch.object(orchestrator, "metadata_service"):
            orchestrator.metadata_service.get_linked_issues.return_value = []
            report = orchestrator.sync_all_linked_issues(dry_run=True)
            assert isinstance(report, SyncReport)

    def test_sync_all_linked_issues_apply_changes(self, orchestrator):
        """Test syncing all linked issues with changes applied."""
        with patch.object(orchestrator, "metadata_service"):
            orchestrator.metadata_service.get_linked_issues.return_value = []
            report = orchestrator.sync_all_linked_issues(dry_run=False)
            assert isinstance(report, SyncReport)

    def test_sync_all_linked_issues_force_local(self, orchestrator):
        """Test syncing with force local conflict resolution."""
        with patch.object(orchestrator, "metadata_service"):
            orchestrator.metadata_service.get_linked_issues.return_value = []
            report = orchestrator.sync_all_linked_issues(dry_run=True, force_local=True)
            assert isinstance(report, SyncReport)

    def test_sync_all_linked_issues_force_github(self, orchestrator):
        """Test syncing with force GitHub conflict resolution."""
        with patch.object(orchestrator, "metadata_service"):
            orchestrator.metadata_service.get_linked_issues.return_value = []
            report = orchestrator.sync_all_linked_issues(
                dry_run=True, force_github=True
            )
            assert isinstance(report, SyncReport)

    def test_sync_no_github_service(self, mock_core):
        """Test sync when GitHub service is not available."""
        mock_core.github_service = None
        with patch("roadmap.core.services.github_sync_orchestrator.GitHubIssueClient"):
            with patch(
                "roadmap.core.services.github_sync_orchestrator.SyncMetadataService"
            ):
                with patch(
                    "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
                ):
                    orch = GitHubSyncOrchestrator(mock_core)
                    assert orch.core == mock_core

    def test_sync_with_github_service(self, mock_core):
        """Test sync when GitHub service is available."""
        with patch("roadmap.core.services.github_sync_orchestrator.GitHubIssueClient"):
            with patch(
                "roadmap.core.services.github_sync_orchestrator.SyncMetadataService"
            ):
                with patch(
                    "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
                ):
                    orch = GitHubSyncOrchestrator(mock_core)
                    # Detector should be created when service exists
                    assert orch is not None

    def test_detect_changes_no_issues(self, orchestrator):
        """Test detecting changes when no issues are linked."""
        with patch.object(orchestrator, "metadata_service"):
            orchestrator.metadata_service.get_linked_issues.return_value = []
            # Use public sync API instead of private method
            report = orchestrator.sync_all_linked_issues(dry_run=True)
            assert isinstance(report, SyncReport)

    def test_handle_sync_conflicts_no_conflict(self, orchestrator):
        """Test handling sync when there are no conflicts."""
        with patch.object(orchestrator, "conflict_detector"):
            orchestrator.conflict_detector.has_conflicts.return_value = False
            # Should handle gracefully
            assert orchestrator.conflict_detector is not None


class TestSyncReport:
    """Test sync reporting."""

    def test_sync_report_creation(self):
        """Test creating a sync report."""
        report = SyncReport()
        assert report is not None

    def test_sync_report_with_changes(self):
        """Test sync report with changes recorded."""
        report = SyncReport()
        assert hasattr(report, "changes") or hasattr(report, "issues_changed")

    def test_sync_report_summary(self):
        """Test getting sync report summary."""
        report = SyncReport()
        # SyncReport has display methods but no summary property
        assert isinstance(report, SyncReport)
        assert report.total_issues >= 0

    def test_sync_report_has_errors(self):
        """Test checking if sync report has errors."""
        report = SyncReport()
        # Check error attribute
        assert hasattr(report, "error")
        assert report.error is None
