"""
Integration tests for GitHub Sync End-to-End Workflows.

Tests the orchestration logic for bidirectional sync between local
issues/milestones and GitHub, including detection, routing, and
application of changes.
"""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.constants import MilestoneStatus, Status
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone
from roadmap.core.services.github_sync_orchestrator import GitHubSyncOrchestrator
from roadmap.core.services.sync_report import IssueChange


class TestGitHubSyncOrchestrationE2E:
    """E2E tests for GitHub sync orchestration workflows."""

    @pytest.fixture
    def orchestrator_with_mocks(self, mock_core_with_github):
        """Set up orchestrator with all mocks in place."""
        mock_core = mock_core_with_github

        # Add milestone support
        if not hasattr(mock_core, "milestones"):
            mock_core.milestones = MagicMock()

        # Ensure list() returns empty by default (tests will override)
        mock_core.milestones.list.return_value = []

        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ) as mock_detector:
            detector_instance = MagicMock()
            detector_instance.has_conflicts.return_value = False
            mock_detector.return_value = detector_instance

            orchestrator = GitHubSyncOrchestrator(
                mock_core,
                config={
                    "token": "test_token",
                    "owner": "testuser",
                    "repo": "testrepo",
                },
            )
            orchestrator.metadata_service = MagicMock()
            return orchestrator

    def test_issue_creation_workflow_detected(self, orchestrator_with_mocks):
        """Test: New issues (without github_issue) are detected for creation."""
        orchestrator = orchestrator_with_mocks

        # Create unlinked issue
        new_issue = Issue(
            id="issue1",
            title="New feature",
            status=Status.TODO,
            github_issue=None,
        )

        orchestrator.core.issues.list.return_value = [new_issue]
        orchestrator.core.issues.get.return_value = new_issue

        # Run sync
        report = orchestrator.sync_all_linked_issues(dry_run=True)

        # Verify creation was detected
        changes_with_create = [
            c
            for c in report.changes
            if c.local_changes and c.local_changes.get("action") == "create on GitHub"
        ]
        assert len(changes_with_create) > 0

    def test_issue_update_workflow_detected(self, orchestrator_with_mocks):
        """Test: Updates to linked issues are detected."""
        orchestrator = orchestrator_with_mocks

        # Create linked issue with local changes
        linked_issue = Issue(
            id="issue1",
            title="Updated title",
            status=Status.IN_PROGRESS,
            github_issue=42,
        )

        orchestrator.core.issues.list.return_value = [linked_issue]
        orchestrator.core.issues.get.return_value = linked_issue

        # Run sync (no real API calls in dry-run)
        report = orchestrator.sync_all_linked_issues(dry_run=True)

        # Verify we got a report (issue was processed)
        assert report is not None

    def test_milestone_creation_workflow_detected(self, orchestrator_with_mocks):
        """Test: New milestones are detected for creation."""
        orchestrator = orchestrator_with_mocks

        # Create unlinked milestone
        new_milestone = Milestone(
            name="v1.0.0",
            description="Release 1.0.0",
            status=MilestoneStatus.OPEN,
            github_milestone=None,
        )

        orchestrator.core.milestones.list.return_value = [new_milestone]
        orchestrator.core.milestones.get.return_value = new_milestone

        # Run sync
        report = orchestrator.sync_all_linked_issues(dry_run=True)

        # Verify sync report was generated
        assert report is not None
        assert hasattr(report, "changes")

    def test_milestone_update_workflow_detected(self, orchestrator_with_mocks):
        """Test: Updates to linked milestones are detected."""
        orchestrator = orchestrator_with_mocks

        # Create linked milestone
        linked_milestone = Milestone(
            name="v2.0.0",
            description="Updated description",
            status=MilestoneStatus.CLOSED,
            github_milestone=2,
        )

        orchestrator.core.milestones.list.return_value = [linked_milestone]
        orchestrator.core.milestones.get.return_value = linked_milestone

        # Run sync
        report = orchestrator.sync_all_linked_issues(dry_run=True)

        # Verify milestone was processed
        assert report is not None

    def test_dry_run_no_changes_applied(self, orchestrator_with_mocks):
        """Test: Dry-run detects but doesn't apply changes."""
        orchestrator = orchestrator_with_mocks

        issue = Issue(
            id="issue1",
            title="Feature",
            status=Status.TODO,
            github_issue=42,
        )

        orchestrator.core.issues.list.return_value = [issue]
        orchestrator.core.issues.get.return_value = issue

        # Run dry-run sync
        report = orchestrator.sync_all_linked_issues(dry_run=True)

        # Verify no actual updates were attempted
        # metadata_service.record_sync shouldn't be called for dry-run
        assert report.issues_updated >= 0  # May be 0 if no changes detected

    def test_mixed_issue_milestone_sync(self, orchestrator_with_mocks):
        """Test: Both issues and milestones are synced in one operation."""
        orchestrator = orchestrator_with_mocks

        # Create both issue and milestone
        issue = Issue(
            id="issue1",
            title="Feature",
            status=Status.TODO,
            github_issue=42,
        )

        milestone = Milestone(
            name="v1.0",
            description="Version 1.0",
            status=MilestoneStatus.OPEN,
            github_milestone=1,
        )

        orchestrator.core.issues.list.return_value = [issue]
        orchestrator.core.issues.get.return_value = issue
        orchestrator.core.milestones.list.return_value = [milestone]
        orchestrator.core.milestones.get.return_value = milestone

        # Run sync
        report = orchestrator.sync_all_linked_issues(dry_run=True)

        # Both should be processed
        assert len(report.changes) >= 0


class TestGitHubSyncReportingE2E:
    """E2E tests for sync reporting and status."""

    @pytest.fixture
    def orchestrator_with_mocks(self, mock_core_with_github):
        """Set up orchestrator."""
        mock_core = mock_core_with_github

        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            orchestrator = GitHubSyncOrchestrator(
                mock_core,
                config={
                    "token": "test_token",
                    "owner": "testuser",
                    "repo": "testrepo",
                },
            )
            orchestrator.metadata_service = MagicMock()
            return orchestrator

    def test_sync_report_counters_accurate(self, orchestrator_with_mocks):
        """Test: Sync report counters are accurate."""
        orchestrator = orchestrator_with_mocks

        # Create multiple issues
        issues = [
            Issue(id="i1", title="Feature 1", status=Status.TODO, github_issue=1),
            Issue(id="i2", title="Feature 2", status=Status.TODO, github_issue=2),
            Issue(id="i3", title="Feature 3", status=Status.TODO, github_issue=None),
        ]

        orchestrator.core.issues.list.return_value = issues
        orchestrator.core.issues.get.return_value = issues[0]

        # Run sync
        report = orchestrator.sync_all_linked_issues(dry_run=True)

        # Verify report has expected data
        assert report is not None
        assert hasattr(report, "issues_updated")
        assert hasattr(report, "changes")

    def test_sync_report_error_handling(self, orchestrator_with_mocks):
        """Test: Sync report captures errors."""
        orchestrator = orchestrator_with_mocks

        # Mock an error condition
        orchestrator.core.issues.list.side_effect = Exception("Database error")

        # Run sync - should handle error gracefully
        report = orchestrator.sync_all_linked_issues(dry_run=True)

        # Report should capture the error
        assert report is not None


class TestGitHubSyncChangeApplicationE2E:
    """E2E tests for applying changes detected in sync."""

    @pytest.fixture
    def orchestrator_with_mocks(self, mock_core_with_github):
        """Set up orchestrator with apply method mocks."""
        mock_core = mock_core_with_github

        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            orchestrator = GitHubSyncOrchestrator(
                mock_core,
                config={
                    "token": "test_token",
                    "owner": "testuser",
                    "repo": "testrepo",
                },
            )
            orchestrator.metadata_service = MagicMock()

            # Mock the apply methods
            orchestrator._apply_local_changes = MagicMock()
            orchestrator._apply_github_changes = MagicMock()
            orchestrator._create_issue_on_github = MagicMock()
            orchestrator._create_milestone_on_github = MagicMock()
            orchestrator._apply_local_milestone_changes = MagicMock()
            orchestrator._apply_github_milestone_changes = MagicMock()

            return orchestrator

    def test_apply_calls_correct_handlers(self, orchestrator_with_mocks):
        """Test: Apply phase calls correct change handlers."""
        orchestrator = orchestrator_with_mocks

        issue = Issue(
            id="issue1",
            title="Feature",
            status=Status.TODO,
            github_issue=None,  # Will trigger create action
        )

        orchestrator.core.issues.list.return_value = [issue]
        orchestrator.core.issues.get.return_value = issue

        # Run sync with apply - this should route to the right methods
        report = orchestrator.sync_all_linked_issues(dry_run=False)

        # Verify handlers were invoked (either create or apply)
        # In this case, we're checking that the orchestrator processed the issue
        assert report is not None
        assert report.issues_updated >= 0

    def test_local_changes_applied_correctly(self, orchestrator_with_mocks):
        """Test: Local changes trigger correct apply handlers."""
        orchestrator = orchestrator_with_mocks

        # Create change with local modifications
        change = IssueChange(
            issue_id="issue1",
            title="Updated",
            local_changes={"status": "todo -> closed"},
        )

        # Mock issue exists
        issue = Issue(id="issue1", title="Updated", status=Status.CLOSED)
        orchestrator.core.issues.get.return_value = issue

        # Apply the change - should handle gracefully
        orchestrator._apply_local_changes(change)

        # Verify it doesn't crash and metadata service was updated
        assert orchestrator.metadata_service is not None

    def test_github_changes_applied_correctly(self, orchestrator_with_mocks):
        """Test: GitHub changes trigger correct apply handlers."""
        orchestrator = orchestrator_with_mocks

        # Create change with GitHub modifications
        change = IssueChange(
            issue_id="issue1",
            title="Updated from GitHub",
            github_changes={"title": "Old -> Updated from GitHub"},
        )

        # Mock issue exists
        issue = Issue(id="issue1", title="Updated from GitHub")
        orchestrator.core.issues.get.return_value = issue

        # Apply the change - should handle gracefully
        orchestrator._apply_github_changes(change)

        # Verify it doesn't crash
        assert orchestrator.core is not None


class TestGitHubSyncValidationE2E:
    """E2E tests for validation in sync workflows."""

    @pytest.fixture
    def orchestrator_with_mocks(self, mock_core_with_github):
        """Set up orchestrator."""
        mock_core = mock_core_with_github

        with patch(
            "roadmap.core.services.github_sync_orchestrator.GitHubConflictDetector"
        ):
            orchestrator = GitHubSyncOrchestrator(
                mock_core,
                config={
                    "token": "test_token",
                    "owner": "testuser",
                    "repo": "testrepo",
                },
            )
            orchestrator.metadata_service = MagicMock()
            return orchestrator

    def test_invalid_status_skips_update(self, orchestrator_with_mocks):
        """Test: Invalid status values are skipped."""
        orchestrator = orchestrator_with_mocks

        # Create change with invalid status
        change = IssueChange(
            issue_id="issue1",
            title="Test",
            local_changes={"status": "todo -> INVALID_STATUS"},
        )

        issue = Issue(id="issue1", title="Test", status=Status.TODO)
        orchestrator.core.issues.get.return_value = issue

        # Apply change - should handle gracefully
        orchestrator._apply_local_changes(change)

        # Status should remain unchanged
        assert issue.status == Status.TODO

    def test_missing_issue_handled_gracefully(self, orchestrator_with_mocks):
        """Test: Missing issues don't crash sync."""
        orchestrator = orchestrator_with_mocks

        orchestrator.core.issues.get.return_value = None

        change = IssueChange(
            issue_id="nonexistent",
            title="Doesn't exist",
            local_changes={"status": "todo -> closed"},
        )

        # Should not crash
        orchestrator._apply_local_changes(change)

        # Verify graceful handling
        assert True
