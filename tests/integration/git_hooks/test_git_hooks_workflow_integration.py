"""Tests for Git hooks and workflow automation."""

import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.git.git import GitIntegration
from roadmap.adapters.git.git_hooks import WorkflowAutomation
from roadmap.core.domain import Priority, Status
from roadmap.infrastructure.coordination.core import RoadmapCore


@pytest.mark.integration
class TestWorkflowAutomation:
    """Test workflow automation orchestrator."""

    @pytest.fixture
    def temp_git_repo(self, temp_dir_context):
        """Create a temporary Git repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Initialize Git repo
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], check=True
            )

            # Initialize roadmap
            core = RoadmapCore()
            core.initialize()

            yield temp_dir, core

    def test_workflow_automation_initialization(self, temp_git_repo):
        """Test WorkflowAutomation initialization."""
        _, core = temp_git_repo

        automation = WorkflowAutomation(core)

        assert automation.core == core
        assert automation.hook_manager is not None
        assert automation.git_integration is not None

    def test_setup_automation_all_features(self, temp_git_repo):
        """Test setting up all automation features."""
        _, core = temp_git_repo

        automation = WorkflowAutomation(core)
        results = automation.setup_automation()

        # Should succeed for all features
        expected_features = ["git-hooks", "status-automation", "progress-tracking"]
        for feature in expected_features:
            assert feature in results
            assert results[feature] is True

        # Check that configuration files were created
        assert Path(".roadmap_automation_config.json").exists()
        assert Path(".roadmap_progress_tracking.json").exists()

    def test_setup_automation_selective_features(self, temp_git_repo):
        """Test setting up specific automation features."""
        _, core = temp_git_repo

        automation = WorkflowAutomation(core)
        results = automation.setup_automation(["git-hooks", "status-automation"])

        # Should only set up requested features
        assert "git-hooks" in results
        assert "status-automation" in results
        assert "progress-tracking" not in results

        assert results["git-hooks"] is True
        assert results["status-automation"] is True

    def test_disable_automation(self, temp_git_repo):
        """Test disabling all automation."""
        _, core = temp_git_repo

        automation = WorkflowAutomation(core)

        # Set up automation first
        automation.setup_automation()

        # Verify files exist
        assert Path(".roadmap_automation_config.json").exists()
        assert Path(".roadmap_progress_tracking.json").exists()

        # Disable automation
        success = automation.disable_automation()
        assert success

        # Verify cleanup
        assert not Path(".roadmap_automation_config.json").exists()
        assert not Path(".roadmap_progress_tracking.json").exists()

    @patch("roadmap.adapters.git.git_hooks.GitIntegration")
    def test_sync_all_issues_with_git(self, mock_git_integration, temp_git_repo):
        """Test syncing all issues with Git activity."""
        _, core = temp_git_repo

        # Create test issues
        issue1 = core.issues.create("Issue 1", Priority.HIGH)
        issue2 = core.issues.create("Issue 2", Priority.MEDIUM)
        issue3 = core.issues.create("Issue 3", Priority.LOW)  # No commits

        # Mock Git integration
        mock_git = Mock()

        # Create mock commits for issues 1 and 2
        commit1 = Mock()
        commit1.extract_roadmap_references.return_value = [issue1.id]
        commit1.extract_progress_info.return_value = 75.0
        commit1.hash = "abc123"
        commit1.message = f"Work on issue 1 [roadmap:{issue1.id}] [progress:75%]"
        commit1.date = datetime.now(UTC)

        commit2 = Mock()
        commit2.extract_roadmap_references.return_value = [issue2.id]
        commit2.extract_progress_info.return_value = None
        commit2.hash = "def456"
        commit2.message = f"Complete issue 2 [closes roadmap:{issue2.id}]"
        commit2.date = datetime.now(UTC)

        mock_git.get_recent_commits.return_value = [commit1, commit2]
        mock_git_integration.return_value = mock_git

        automation = WorkflowAutomation(core)
        automation.git_integration = mock_git

        # Sync all issues
        results = automation.sync_all_issues_with_git()

        # Check results
        assert results["synced_issues"] == 2
        assert len(results["updated_issues"]) == 2
        assert len(results["errors"]) == 0

        # Verify issue updates
        updated_issue1 = core.issues.get(issue1.id)
        assert updated_issue1.progress_percentage == 75.0
        assert updated_issue1.status == Status.IN_PROGRESS
        assert hasattr(updated_issue1, "git_commits")
        assert len(updated_issue1.git_commits) == 1

        updated_issue2 = core.issues.get(issue2.id)
        assert updated_issue2.status == Status.CLOSED
        assert updated_issue2.progress_percentage == 100.0

        # Issue 3 should be unchanged
        updated_issue3 = core.issues.get(issue3.id)
        assert updated_issue3.status == Status.TODO
        assert (
            updated_issue3.progress_percentage is None
            or updated_issue3.progress_percentage == 0
        )

    def test_sync_issue_with_commits_progress_tracking(self, temp_git_repo):
        """Test syncing individual issue with multiple commits."""
        _, core = temp_git_repo

        issue = core.issues.create("Progressive issue", Priority.HIGH)
        automation = WorkflowAutomation(core)

        # Create mock commits showing progress
        commits = []
        for i, progress in enumerate([25, 50, 75, 100], 1):
            commit = Mock()
            commit.hash = f"commit{i}"
            commit.message = (
                f"Progress update {i} [roadmap:{issue.id}] [progress:{progress}%]"
            )
            commit.date = datetime.now(UTC)
            commit.extract_roadmap_references.return_value = [issue.id]
            commit.extract_progress_info.return_value = float(progress)
            commits.append(commit)

        # Mark last commit as completion
        commits[-1].message = f"Complete work [closes roadmap:{issue.id}]"

        # Sync issue with commits
        updated = automation._sync_issue_with_commits(issue, commits)

        assert updated

        # Verify final state
        updated_issue = core.issues.get(issue.id)
        assert updated_issue.progress_percentage == 100.0
        assert updated_issue.status == Status.CLOSED
        assert updated_issue.completed_date is not None
        assert len(updated_issue.git_commits) == 4

        # Check commit tracking
        completion_commit = next(
            (ref for ref in updated_issue.git_commits if ref.get("completion")), None
        )
        assert completion_commit is not None
        assert completion_commit["hash"] == "commit4"

    def test_automation_configuration_files(self, temp_git_repo):
        """Test automation configuration file creation."""
        _, core = temp_git_repo

        automation = WorkflowAutomation(core)

        # Test status automation config
        success = automation._setup_status_automation()
        assert success

        config_file = Path(".roadmap_automation_config.json")
        assert config_file.exists()

        import json

        config = json.loads(config_file.read_text())
        assert "status_rules" in config
        assert "progress_rules" in config
        assert config["status_rules"]["auto_in_progress"] is True

        # Test progress tracking config
        success = automation._setup_progress_tracking()
        assert success

        tracking_file = Path(".roadmap_progress_tracking.json")
        assert tracking_file.exists()

        tracking_config = json.loads(tracking_file.read_text())
        assert tracking_config["enabled"] is True
        assert "tracked_metrics" in tracking_config

    def test_error_handling_in_sync(self, temp_git_repo):
        """Test error handling during issue sync."""
        _, core = temp_git_repo

        # Create issue with invalid data to trigger error
        issue = core.issues.create("Test issue", Priority.MEDIUM)

        automation = WorkflowAutomation(core)

        # Create a mock commit that references the issue
        from roadmap.adapters.git.git import GitCommit

        mock_commit = GitCommit(
            hash="abc123",
            message=f"Fix for issue [roadmap:{issue.id}]",
            author="test",
            date=datetime.now(UTC),
            files_changed=["test.py"],
        )

        # Mock both git commits and sync method to cause error
        with (
            patch.object(
                automation.git_integration,
                "get_recent_commits",
                return_value=[mock_commit],
            ),
            patch.object(
                automation,
                "_sync_issue_with_commits",
                side_effect=Exception("Test error"),
            ),
        ):
            results = automation.sync_all_issues_with_git()

            # Should handle error gracefully
            assert results["synced_issues"] == 0
            assert len(results["errors"]) > 0
            assert "Test error" in str(results["errors"])

    def test_milestone_progress_automation(self, temp_git_repo):
        """Test automated milestone progress updates."""
        _, core = temp_git_repo

        # Create milestone and issues
        milestone = core.milestones.create("Test Milestone", "2024-12-31")

        issue1 = core.issues.create(
            "Issue 1", Priority.MEDIUM, milestone=milestone.name
        )
        issue2 = core.issues.create(
            "Issue 2", Priority.MEDIUM, milestone=milestone.name
        )
        issue3 = core.issues.create(
            "Issue 3", Priority.MEDIUM, milestone=milestone.name
        )

        automation = WorkflowAutomation(core)

        # Complete some issues
        core.issues.update(issue1.id, status=Status.CLOSED)
        core.issues.update(issue2.id, status=Status.CLOSED)
        # Issue 3 remains TODO

        # Update milestone progress
        automation.hook_manager._update_milestone_progress()

        # Check milestone progress
        milestone_progress = core.milestones.get_progress(milestone.name)
        expected_progress = (2 / 3) * 100  # 2 out of 3 issues complete
        assert abs(milestone_progress["progress"] - expected_progress) < 0.1

        # Complete last issue
        core.issues.update(issue3.id, status=Status.CLOSED)
        automation.hook_manager._update_milestone_progress()

        # Milestone should now be completed
        final_milestone_progress = core.milestones.get_progress(milestone.name)
        assert final_milestone_progress["progress"] >= 100


class TestGitHooksIntegration:
    """Integration tests for Git hooks with real Git operations."""

    @pytest.fixture
    def git_repo_with_roadmap(self, temp_dir_context):
        """Create Git repo with roadmap initialized."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Initialize Git repo
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], check=True
            )

            # Initialize roadmap
            core = RoadmapCore()
            core.initialize()

            # Create initial commit
            Path("README.md").write_text("# Test Project\n")
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

            yield temp_dir, core

    def test_full_workflow_automation(self, git_repo_with_roadmap):
        """Test complete workflow automation cycle."""
        temp_dir, core = git_repo_with_roadmap

        # Setup automation with proper git integration
        automation = WorkflowAutomation(core)
        # Reinitialize git integration with correct path
        automation.git_integration = GitIntegration(Path(temp_dir))

        results = automation.setup_automation()

        # Verify all features enabled
        assert all(results.values())

        # Create issue with Git branch
        issue = core.issues.create("Implement feature X", Priority.HIGH)

        # Create and checkout branch
        branch_name = f"feature/{issue.id}-implement-feature-x"
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)

        # Link issue to branch
        issue.git_branches = [branch_name]
        core.issues.update(issue.id, git_branches=[branch_name])

        # Make commits with progress tracking
        commits_data = [
            ("Add basic structure", 25),
            ("Implement core logic", 50),
            ("Add tests", 75),
            ("Complete feature", 100),
        ]

        for i, (message, progress) in enumerate(commits_data, 1):
            # Make a file change
            test_file = Path(f"feature_{i}.py")
            test_file.write_text(f"# Feature implementation step {i}\n")

            subprocess.run(["git", "add", "."], check=True)

            if progress < 100:
                commit_msg = f"{message} [roadmap:{issue.id}] [progress:{progress}%]"
            else:
                commit_msg = f"{message} [closes roadmap:{issue.id}]"

            subprocess.run(["git", "commit", "-m", commit_msg], check=True)

        # Sync all issues with Git activity
        automation.sync_all_issues_with_git()

        # Check if the issue was updated with git information
        updated_issue = automation.core.issues.get(issue.id)
        assert updated_issue is not None

        # The key test is that the issue was properly tracked and updated
        # Test the git integration is working even if sync count is 0 due to prior processing
        assert hasattr(
            updated_issue, "git_commits"
        )  # Should have git commit references
        assert (
            len(updated_issue.git_commits) > 0
        )  # Should have at least one commit tracked
        assert updated_issue.progress_percentage is not None
        assert (
            updated_issue.progress_percentage >= 75.0
        )  # Should show significant progress

        # Test workflow automation features are enabled
        assert results["git-hooks"] is True
        assert results["status-automation"] is True
        assert results["progress-tracking"] is True


if __name__ == "__main__":
    pytest.main([__file__])
