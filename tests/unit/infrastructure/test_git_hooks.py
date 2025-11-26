"""Unit tests for Git hooks management and workflow automation."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from roadmap.domain import Issue, Status
from roadmap.infrastructure.git import GitCommit
from roadmap.infrastructure.git_hooks import GitHookManager, WorkflowAutomation


@pytest.fixture
def mock_core():
    """Create a mock RoadmapCore instance."""
    core = Mock()
    core.issues_dir = Path("/fake/issues")
    return core


@pytest.fixture
def mock_git_integration():
    """Create a mock GitIntegration instance."""
    git = Mock()
    git.is_git_repository.return_value = True
    git.get_recent_commits.return_value = []
    return git


@pytest.fixture
def hook_manager(mock_core, mock_git_integration):
    """Create a GitHookManager instance with mocked dependencies."""
    with patch(
        "roadmap.infrastructure.git_hooks.GitIntegration",
        return_value=mock_git_integration,
    ):
        manager = GitHookManager(mock_core)
        manager.hooks_dir = Path("/fake/.git/hooks")
        return manager


@pytest.fixture
def workflow_automation(mock_core, mock_git_integration):
    """Create a WorkflowAutomation instance with mocked dependencies."""
    with patch(
        "roadmap.infrastructure.git_hooks.GitIntegration",
        return_value=mock_git_integration,
    ):
        automation = WorkflowAutomation(mock_core)
        automation.git_integration = mock_git_integration
        return automation


@pytest.fixture
def sample_commit():
    """Create a sample GitCommit for testing."""
    return GitCommit(
        hash="abc123",
        message="closes roadmap:TEST-001 - Complete feature",
        date=datetime(2025, 1, 15, 10, 30),
        author="Test Author",
        files_changed=["file1.py", "file2.py"],
    )


class TestGitHookManagerInit:
    """Test GitHookManager initialization."""

    def test_init_with_git_repository(self, mock_core):
        """Test initialization in a Git repository."""
        with patch("roadmap.infrastructure.git_hooks.GitIntegration") as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repository.return_value = True
            mock_git_class.return_value = mock_git

            manager = GitHookManager(mock_core)

            assert manager.core == mock_core
            assert manager.hooks_dir == Path(".git/hooks")

    def test_init_without_git_repository(self, mock_core):
        """Test initialization outside a Git repository."""
        with patch("roadmap.infrastructure.git_hooks.GitIntegration") as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repository.return_value = False
            mock_git_class.return_value = mock_git

            manager = GitHookManager(mock_core)

            assert manager.core == mock_core
            assert manager.hooks_dir is None


class TestGitHookManagerInstall:
    """Test Git hook installation."""

    def test_install_all_hooks_success(self, hook_manager):
        """Test successful installation of all hooks."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.write_text") as mock_write,
            patch("pathlib.Path.chmod") as mock_chmod,
        ):
            result = hook_manager.install_hooks()

            assert result is True
            # Should install 4 hooks
            assert mock_write.call_count == 4
            assert mock_chmod.call_count == 4
            # Check chmod was called with executable permissions
            for call_args in mock_chmod.call_args_list:
                assert call_args[0][0] == 0o755

    def test_install_specific_hooks(self, hook_manager):
        """Test installation of specific hooks only."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.write_text") as mock_write,
            patch("pathlib.Path.chmod"),
        ):
            result = hook_manager.install_hooks(hooks=["post-commit", "pre-push"])

            assert result is True
            assert mock_write.call_count == 2

    def test_install_hooks_no_hooks_dir(self, hook_manager):
        """Test installation fails when hooks directory is None."""
        hook_manager.hooks_dir = None

        result = hook_manager.install_hooks()

        assert result is False

    def test_install_hooks_dir_not_exists(self, hook_manager):
        """Test installation fails when hooks directory doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            result = hook_manager.install_hooks()

            assert result is False

    def test_install_hooks_exception(self, hook_manager):
        """Test installation fails gracefully on exception."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.write_text", side_effect=PermissionError("No access")),
        ):
            result = hook_manager.install_hooks()

            assert result is False


class TestGitHookManagerUninstall:
    """Test Git hook uninstallation."""

    def test_uninstall_hooks_success(self, hook_manager):
        """Test successful uninstallation of roadmap hooks."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="#!/bin/bash\n# roadmap-hook"),
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            result = hook_manager.uninstall_hooks()

            assert result is True
            # Should unlink 4 hooks
            assert mock_unlink.call_count == 4

    def test_uninstall_hooks_no_hooks_dir(self, hook_manager):
        """Test uninstallation fails when hooks_dir is None."""
        hook_manager.hooks_dir = None

        result = hook_manager.uninstall_hooks()

        assert result is False

    def test_uninstall_hooks_non_roadmap_hook(self, hook_manager):
        """Test uninstallation skips non-roadmap hooks."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "pathlib.Path.read_text", return_value="#!/bin/bash\n# Some other hook"
            ),
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            result = hook_manager.uninstall_hooks()

            assert result is True
            # Should NOT unlink non-roadmap hooks
            mock_unlink.assert_not_called()

    def test_uninstall_hooks_exception(self, hook_manager):
        """Test uninstallation fails gracefully on exception."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", side_effect=OSError("Read error")),
        ):
            result = hook_manager.uninstall_hooks()

            assert result is False


class TestGitHookManagerStatus:
    """Test Git hook status checking."""

    def test_get_hooks_status_all_installed(self, hook_manager):
        """Test getting status when all hooks are installed."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="#!/bin/bash\n# roadmap-hook"),
            patch("pathlib.Path.stat") as mock_stat,
        ):
            # Mock file permissions (executable)
            mock_stat.return_value = Mock(st_mode=0o755)

            status = hook_manager.get_hooks_status()

            assert len(status) == 4
            for hook_name in ["post-commit", "pre-push", "post-merge", "post-checkout"]:
                assert hook_name in status
                assert status[hook_name]["installed"] is True
                assert status[hook_name]["is_roadmap_hook"] is True
                assert status[hook_name]["executable"] is True
                assert status[hook_name]["file_exists"] is True

    def test_get_hooks_status_none_installed(self, hook_manager):
        """Test getting status when no hooks are installed."""
        from unittest.mock import MagicMock

        # Create a mock hooks_dir that exists but has no hook files
        mock_hooks_dir = MagicMock()
        mock_hooks_dir.exists.return_value = True
        mock_hooks_dir.__truediv__ = lambda self, other: Path(
            f"/fake/.git/hooks/{other}"
        )
        hook_manager.hooks_dir = mock_hooks_dir

        with patch("pathlib.Path.exists", return_value=False):
            status = hook_manager.get_hooks_status()

            assert len(status) == 4
            for hook_name in ["post-commit", "pre-push", "post-merge", "post-checkout"]:
                assert status[hook_name]["installed"] is False
                assert status[hook_name]["file_exists"] is False

    def test_get_hooks_status_no_hooks_dir(self, hook_manager):
        """Test getting status when hooks_dir is None."""
        hook_manager.hooks_dir = None

        status = hook_manager.get_hooks_status()

        assert status == {}

    def test_get_hooks_status_hooks_dir_not_exists(self, hook_manager):
        """Test getting status when hooks directory doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            status = hook_manager.get_hooks_status()

            # Should return empty dict when dir doesn't exist
            assert status == {}


class TestGitHookManagerConfig:
    """Test hook configuration retrieval."""

    def test_get_hook_config_full(self, hook_manager):
        """Test getting full hook configuration."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="#!/bin/bash\n# roadmap-hook"),
            patch("pathlib.Path.stat", return_value=Mock(st_mode=0o755)),
            patch("pathlib.Path.cwd", return_value=Path("/fake/repo")),
        ):
            config = hook_manager.get_hook_config()

            assert config is not None
            assert config["hooks_directory"] == "/fake/.git/hooks"
            assert config["repository_root"] == "/fake/repo"
            assert config["git_repository"] is True
            assert len(config["available_hooks"]) == 4
            assert config["core_initialized"] is True
            assert "hooks_status" in config


class TestGitHookManagerHandlers:
    """Test Git hook event handlers."""

    def test_handle_post_commit_success(self, hook_manager):
        """Test post-commit handler logs commit."""
        with (
            patch("subprocess.run") as mock_run,
            patch("builtins.open", mock_open()) as mock_file,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_run.return_value = Mock(stdout="abc123def\n", returncode=0)

            hook_manager.handle_post_commit()

            # Should call git rev-parse HEAD
            mock_run.assert_called_once()
            # Should write to log file
            mock_file.assert_called_once_with(Path(".git/roadmap-hooks.log"), "a")

    def test_handle_post_commit_no_commit(self, hook_manager):
        """Test post-commit handler with no commit SHA."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=0)

            # Should not raise exception
            hook_manager.handle_post_commit()

    def test_handle_post_commit_exception(self, hook_manager):
        """Test post-commit handler fails gracefully."""
        with patch("subprocess.run", side_effect=Exception("Git error")):
            # Should not raise exception (silent fail)
            hook_manager.handle_post_commit()

    def test_handle_post_checkout_success(self, hook_manager):
        """Test post-checkout handler logs branch switch."""
        with (
            patch("subprocess.run") as mock_run,
            patch("builtins.open", mock_open()) as mock_file,
        ):
            mock_run.return_value = Mock(stdout="feature-branch\n", returncode=0)

            hook_manager.handle_post_checkout()

            mock_run.assert_called_once()
            mock_file.assert_called_once_with(Path(".git/roadmap-hooks.log"), "a")

    def test_handle_post_checkout_no_branch(self, hook_manager):
        """Test post-checkout handler with no branch name."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=0)

            # Should not raise exception
            hook_manager.handle_post_checkout()

    def test_handle_pre_push_success(self, hook_manager):
        """Test pre-push handler logs push."""
        with (
            patch("subprocess.run") as mock_run,
            patch("builtins.open", mock_open()) as mock_file,
        ):
            mock_run.return_value = Mock(stdout="main\n", returncode=0)

            hook_manager.handle_pre_push()

            mock_run.assert_called_once()
            mock_file.assert_called_once_with(Path(".git/roadmap-hooks.log"), "a")

    def test_handle_post_merge_calls_update(self, hook_manager):
        """Test post-merge handler calls milestone update."""
        with patch.object(hook_manager, "_update_milestone_progress") as mock_update:
            hook_manager.handle_post_merge()

            mock_update.assert_called_once()


class TestWorkflowAutomationSetup:
    """Test workflow automation setup."""

    def test_setup_all_features(self, workflow_automation):
        """Test setup of all automation features."""
        with (
            patch.object(
                workflow_automation.hook_manager, "install_hooks", return_value=True
            ),
            patch.object(
                workflow_automation,
                "_setup_status_automation",
                return_value=True,
            ),
            patch.object(
                workflow_automation,
                "_setup_progress_tracking",
                return_value=True,
            ),
        ):
            results = workflow_automation.setup_automation()

            assert results["git-hooks"] is True
            assert results["status-automation"] is True
            assert results["progress-tracking"] is True

    def test_setup_specific_features(self, workflow_automation):
        """Test setup of specific features only."""
        with (
            patch.object(
                workflow_automation.hook_manager, "install_hooks", return_value=True
            ),
            patch.object(
                workflow_automation,
                "_setup_status_automation",
                return_value=True,
            ) as mock_status,
            patch.object(
                workflow_automation,
                "_setup_progress_tracking",
                return_value=True,
            ) as mock_tracking,
        ):
            results = workflow_automation.setup_automation(features=["git-hooks"])

            assert results["git-hooks"] is True
            mock_status.assert_not_called()
            mock_tracking.assert_not_called()

    def test_setup_status_automation_creates_config(self, workflow_automation):
        """Test status automation creates config file."""
        with patch("pathlib.Path.write_text") as mock_write:
            result = workflow_automation._setup_status_automation()

            assert result is True
            mock_write.assert_called_once()
            # Verify config structure
            config_arg = mock_write.call_args[0][0]
            config = json.loads(config_arg)
            assert "status_rules" in config
            assert "progress_rules" in config

    def test_setup_progress_tracking_creates_state(self, workflow_automation):
        """Test progress tracking creates state file."""
        with patch("pathlib.Path.write_text") as mock_write:
            result = workflow_automation._setup_progress_tracking()

            assert result is True
            mock_write.assert_called_once()
            # Verify state structure
            state_arg = mock_write.call_args[0][0]
            state = json.loads(state_arg)
            assert state["enabled"] is True
            assert "tracked_metrics" in state

    def test_setup_status_automation_exception(self, workflow_automation):
        """Test status automation fails gracefully on exception."""
        with patch("pathlib.Path.write_text", side_effect=OSError("Write error")):
            result = workflow_automation._setup_status_automation()

            assert result is False

    def test_setup_progress_tracking_exception(self, workflow_automation):
        """Test progress tracking fails gracefully on exception."""
        with patch("pathlib.Path.write_text", side_effect=OSError("Write error")):
            result = workflow_automation._setup_progress_tracking()

            assert result is False


class TestWorkflowAutomationDisable:
    """Test workflow automation disabling."""

    def test_disable_automation_success(self, workflow_automation):
        """Test successful disabling of automation."""
        with (
            patch.object(
                workflow_automation.hook_manager, "uninstall_hooks", return_value=True
            ),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            result = workflow_automation.disable_automation()

            assert result is True
            # Should unlink 3 context files
            assert mock_unlink.call_count == 3

    def test_disable_automation_no_context_files(self, workflow_automation):
        """Test disabling when no context files exist."""
        with (
            patch.object(
                workflow_automation.hook_manager, "uninstall_hooks", return_value=True
            ),
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            result = workflow_automation.disable_automation()

            assert result is True
            # Should not unlink any files
            mock_unlink.assert_not_called()

    def test_disable_automation_exception(self, workflow_automation):
        """Test disabling fails gracefully on exception."""
        with patch.object(
            workflow_automation.hook_manager,
            "uninstall_hooks",
            side_effect=Exception("Error"),
        ):
            result = workflow_automation.disable_automation()

            assert result is False


class TestWorkflowAutomationSync:
    """Test workflow automation syncing."""

    def test_sync_all_issues_with_commits(
        self, workflow_automation, mock_core, sample_commit
    ):
        """Test syncing all issues with Git commits."""
        # Create sample issue
        issue = Issue(
            id="TEST-001",
            title="Test Issue",
            status=Status.TODO,
        )
        mock_core.list_issues.return_value = [issue]

        # Mock commit with issue reference
        workflow_automation.git_integration.get_recent_commits.return_value = [
            sample_commit
        ]

        with (
            patch.object(
                workflow_automation,
                "_sync_issue_with_commits",
                return_value=True,
            ) as mock_sync,
            patch(
                "roadmap.infrastructure.git_hooks.GitCommit.extract_roadmap_references",
                return_value=["TEST-001"],
            ),
        ):
            results = workflow_automation.sync_all_issues_with_git()

            assert results["synced_issues"] == 1
            assert len(results["updated_issues"]) == 1
            assert results["updated_issues"][0]["id"] == "TEST-001"
            mock_sync.assert_called_once()

    def test_sync_all_issues_no_commits(self, workflow_automation, mock_core):
        """Test syncing when no commits reference issues."""
        issue = Issue(
            id="TEST-001",
            title="Test Issue",
            status=Status.TODO,
        )
        mock_core.list_issues.return_value = [issue]

        # No commits
        workflow_automation.git_integration.get_recent_commits.return_value = []

        results = workflow_automation.sync_all_issues_with_git()

        assert results["synced_issues"] == 0
        assert len(results["updated_issues"]) == 0

    def test_sync_all_issues_with_errors(
        self, workflow_automation, mock_core, sample_commit
    ):
        """Test syncing handles errors gracefully."""
        issue = Issue(
            id="TEST-001",
            title="Test Issue",
            status=Status.TODO,
        )
        mock_core.list_issues.return_value = [issue]

        workflow_automation.git_integration.get_recent_commits.return_value = [
            sample_commit
        ]

        with (
            patch.object(
                workflow_automation,
                "_sync_issue_with_commits",
                side_effect=Exception("Sync error"),
            ),
            patch(
                "roadmap.infrastructure.git_hooks.GitCommit.extract_roadmap_references",
                return_value=["TEST-001"],
            ),
        ):
            results = workflow_automation.sync_all_issues_with_git()

            assert results["synced_issues"] == 0
            assert len(results["errors"]) == 1
            assert "TEST-001" in results["errors"][0]

    def test_sync_issue_with_commits_updates_status(
        self, workflow_automation, mock_core, sample_commit
    ):
        """Test syncing issue updates its status."""
        issue = Issue(
            id="TEST-001",
            title="Test Issue",
            status=Status.TODO,
        )

        # Create a commit without completion keywords
        progress_commit = GitCommit(
            hash="def456",
            message="roadmap:TEST-001 - Work in progress",
            date=datetime(2025, 1, 15, 10, 30),
            author="Test Author",
            files_changed=["file1.py"],
        )
        progress_commit.extract_progress_info = Mock(return_value=50.0)

        with patch(
            "roadmap.infrastructure.git_hooks.IssueParser.save_issue_file"
        ) as mock_save:
            result = workflow_automation._sync_issue_with_commits(
                issue, [progress_commit]
            )

            assert result is True
            assert issue.status == Status.IN_PROGRESS
            assert issue.progress_percentage == 50.0
            mock_save.assert_called_once()

    def test_sync_issue_with_commits_marks_completed(
        self, workflow_automation, mock_core, sample_commit
    ):
        """Test syncing issue marks it as completed."""
        issue = Issue(
            id="TEST-001",
            title="Test Issue",
            status=Status.IN_PROGRESS,
        )

        # Mock the methods on the commit instance
        sample_commit.extract_progress_info = Mock(return_value=None)

        with patch(
            "roadmap.infrastructure.git_hooks.IssueParser.save_issue_file"
        ) as mock_save:
            result = workflow_automation._sync_issue_with_commits(
                issue, [sample_commit]
            )

            assert result is True
            assert issue.status == Status.CLOSED
            assert issue.progress_percentage == 100.0
            mock_save.assert_called_once()

    def test_sync_issue_with_commits_no_changes(
        self, workflow_automation, mock_core, sample_commit
    ):
        """Test syncing issue with no new commits."""
        issue = Issue(
            id="TEST-001",
            title="Test Issue",
            status=Status.TODO,
        )
        # Issue already has this commit tracked
        issue.git_commits = [{"hash": "abc123", "message": "Already tracked"}]

        # Mock the methods on the commit instance
        sample_commit.extract_progress_info = Mock(return_value=None)

        with patch("roadmap.infrastructure.git_hooks.IssueParser.save_issue_file"):
            result = workflow_automation._sync_issue_with_commits(
                issue, [sample_commit]
            )

            # No updates because commit already tracked
            assert result is False
