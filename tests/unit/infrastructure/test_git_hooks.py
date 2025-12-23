"""Unit tests for Git hooks management and workflow automation."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from roadmap.adapters.git.git import GitCommit
from roadmap.adapters.git.git_hooks import GitHookManager, WorkflowAutomation
from roadmap.core.domain import Issue, Status


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
        "roadmap.adapters.git.git_hooks.GitIntegration",
        return_value=mock_git_integration,
    ):
        manager = GitHookManager(mock_core)
        manager.hooks_dir = Path("/fake/.git/hooks")
        return manager


@pytest.fixture
def workflow_automation(mock_core, mock_git_integration):
    """Create a WorkflowAutomation instance with mocked dependencies."""
    with patch(
        "roadmap.adapters.git.git_hooks.GitIntegration",
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

    @pytest.mark.parametrize("is_git_repo,expected_hooks_dir", [
        (True, Path(".git/hooks")),
        (False, None),
    ])
    def test_init_variants(self, mock_core, is_git_repo, expected_hooks_dir):
        """Test initialization with different Git repository states."""
        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration"
        ) as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repository.return_value = is_git_repo
            mock_git_class.return_value = mock_git

            manager = GitHookManager(mock_core)

            assert manager.core == mock_core
            assert manager.hooks_dir == expected_hooks_dir


class TestGitHookManagerInstall:
    """Test Git hook installation."""

    @pytest.mark.parametrize("hooks_dir,dir_exists,hook_count,expected_result,scenario", [
        (Path("/fake/.git/hooks"), True, 4, True, "all_hooks"),
        (Path("/fake/.git/hooks"), True, 2, True, "specific_hooks"),
        (None, True, 0, False, "no_hooks_dir"),
        (Path("/fake/.git/hooks"), False, 0, False, "dir_not_exists"),
    ])
    def test_install_hooks_variants(self, hook_manager, hooks_dir, dir_exists, hook_count, expected_result, scenario):
        """Test installation with different states and configurations."""
        hook_manager.hooks_dir = hooks_dir
        
        with (
            patch("pathlib.Path.exists", return_value=dir_exists),
            patch("pathlib.Path.write_text") as mock_write,
            patch("pathlib.Path.chmod") as mock_chmod,
        ):
            if scenario == "specific_hooks":
                result = hook_manager.install_hooks(hooks=["post-commit", "pre-push"])
            else:
                result = hook_manager.install_hooks()

            assert result is expected_result
            if expected_result:
                assert mock_write.call_count == hook_count
                assert mock_chmod.call_count == hook_count
                for call_args in mock_chmod.call_args_list:
                    assert call_args[0][0] == 0o755

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

    def test_get_hooks_status_no_hooks_dir(self, hook_manager):
        """Test getting status when hooks_dir is None."""
        hook_manager.hooks_dir = None

        status = hook_manager.get_hooks_status()

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

    @pytest.mark.parametrize("handler_name,git_output,config_exists,should_call_write", [
        ("post_commit", "abc123def\n", False, True),
        ("post_commit", "", False, False),
        ("post_checkout", "feature-branch\n", False, True),
        ("pre_push", "main\n", False, True),
    ])
    def test_handle_hook_variants(self, hook_manager, handler_name, git_output, config_exists, should_call_write):
        """Test hook handlers with different git outputs and states."""
        with (
            patch("subprocess.run") as mock_run,
            patch("builtins.open", mock_open()) as mock_file,
            patch("pathlib.Path.exists", return_value=config_exists),
        ):
            mock_run.return_value = Mock(stdout=git_output, returncode=0)
            
            handler_method = getattr(hook_manager, f"handle_{handler_name}")
            handler_method()
            
            if git_output:
                mock_run.assert_called_once()
            if should_call_write:
                mock_file.assert_called_once_with(Path(".git/roadmap-hooks.log"), "a")

    def test_handle_post_commit_exception(self, hook_manager):
        """Test post-commit handler fails gracefully."""
        with patch("subprocess.run", side_effect=Exception("Git error")):
            hook_manager.handle_post_commit()

    def test_handle_post_merge_calls_update(self, hook_manager):
        """Test post-merge handler calls milestone update."""
        with patch.object(hook_manager, "_update_milestone_progress") as mock_update:
            hook_manager.handle_post_merge()

            mock_update.assert_called_once()


class TestWorkflowAutomationSetup:
    """Test workflow automation setup."""

    @pytest.mark.parametrize("features_to_setup,expect_all,expect_status,expect_tracking", [
        (None, True, True, True),
        (["git-hooks"], False, False, False),
    ])
    def test_setup_automation_variants(self, workflow_automation, features_to_setup, expect_all, expect_status, expect_tracking):
        """Test setup of automation features with different configurations."""
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
            if features_to_setup:
                results = workflow_automation.setup_automation(features=features_to_setup)
            else:
                results = workflow_automation.setup_automation()

            assert results["git-hooks"] is True
            if expect_all:
                assert results["status-automation"] is True
                assert results["progress-tracking"] is True
                assert mock_status.called is expect_status
                assert mock_tracking.called is expect_tracking
            else:
                assert mock_status.call_count == (1 if expect_status else 0)
                assert mock_tracking.call_count == (1 if expect_tracking else 0)

    @pytest.mark.parametrize("file_type,write_error,expected_result", [
        ("status", None, True),
        ("progress", None, True),
        ("status", OSError("Write error"), False),
        ("progress", OSError("Write error"), False),
    ])
    def test_setup_automation_config_variants(self, workflow_automation, file_type, write_error, expected_result):
        """Test setup of automation config with different error states."""
        with patch("pathlib.Path.write_text", side_effect=write_error if write_error else None) as mock_write:
            if file_type == "status":
                result = workflow_automation._setup_status_automation()
                if expected_result:
                    config_arg = mock_write.call_args[0][0]
                    config = json.loads(config_arg)
                    assert "status_rules" in config
            else:
                result = workflow_automation._setup_progress_tracking()
                if expected_result:
                    state_arg = mock_write.call_args[0][0]
                    state = json.loads(state_arg)
                    assert state["enabled"] is True

            assert result is expected_result


class TestWorkflowAutomationDisable:
    """Test workflow automation disabling."""

    @pytest.mark.parametrize("uninstall_success,context_files_exist,unlink_count,expected_result", [
        (True, True, 3, True),
        (True, False, 0, True),
        (False, False, 0, False),
    ])
    def test_disable_automation_variants(self, workflow_automation, uninstall_success, context_files_exist, unlink_count, expected_result):
        """Test disabling automation with different states."""
        if not uninstall_success:
            with patch.object(
                workflow_automation.hook_manager,
                "uninstall_hooks",
                side_effect=Exception("Error"),
            ):
                result = workflow_automation.disable_automation()
                assert result is expected_result
        else:
            with (
                patch.object(
                    workflow_automation.hook_manager, 
                    "uninstall_hooks", 
                    return_value=True
                ),
                patch("pathlib.Path.exists", return_value=context_files_exist),
                patch("pathlib.Path.unlink") as mock_unlink,
            ):
                result = workflow_automation.disable_automation()
                assert result is expected_result
                assert mock_unlink.call_count == unlink_count


class TestWorkflowAutomationSync:
    """Test workflow automation syncing."""

    @pytest.mark.parametrize("has_commits,commits_count,sync_success,scenario", [
        (True, 1, True, "with_commits"),
        (False, 0, False, "no_commits"),
        (True, 1, False, "with_errors"),
    ])
    def test_sync_all_issues_variants(self, workflow_automation, mock_core, sample_commit, has_commits, commits_count, sync_success, scenario):
        """Test syncing all issues with different commit and error states."""
        issue = Issue(
            id="TEST-001",
            title="Test Issue",
            status=Status.TODO,
        )
        mock_core.issues.list.return_value = [issue]

        if has_commits:
            workflow_automation.git_integration.get_recent_commits.return_value = [sample_commit] * commits_count
        else:
            workflow_automation.git_integration.get_recent_commits.return_value = []

        if scenario == "with_errors":
            with (
                patch.object(
                    workflow_automation,
                    "_sync_issue_with_commits",
                    side_effect=Exception("Sync error"),
                ),
                patch(
                    "roadmap.adapters.git.git_hooks.GitCommit.extract_roadmap_references",
                    return_value=["TEST-001"],
                ),
            ):
                results = workflow_automation.sync_all_issues_with_git()
                assert len(results.get("errors", [])) == 1
        else:
            with (
                patch.object(
                    workflow_automation,
                    "_sync_issue_with_commits",
                    return_value=sync_success,
                ),
                patch(
                    "roadmap.adapters.git.git_hooks.GitCommit.extract_roadmap_references",
                    return_value=["TEST-001"] if has_commits else [],
                ),
            ):
                results = workflow_automation.sync_all_issues_with_git()
                if has_commits:
                    assert results["synced_issues"] == (1 if sync_success else 0)
                else:
                    assert results["synced_issues"] == 0
                    assert len(results["updated_issues"]) == 0

    def test_sync_issue_with_commits_updates_status(self, workflow_automation, mock_core):
        """Test syncing issue updates its status from progress info."""
        issue = Issue(
            id="TEST-001",
            title="Test Issue",
            status=Status.TODO,
        )

        progress_commit = GitCommit(
            hash="def456",
            message="roadmap:TEST-001 - Work in progress",
            date=datetime(2025, 1, 15, 10, 30),
            author="Test Author",
            files_changed=["file1.py"],
        )
        progress_commit.extract_progress_info = Mock(return_value=50.0)

        with patch("roadmap.adapters.git.git_hooks.IssueParser.save_issue_file") as mock_save:
            result = workflow_automation._sync_issue_with_commits(
                issue, [progress_commit]
            )

            assert result is True
            assert issue.status == Status.IN_PROGRESS
            assert issue.progress_percentage == 50.0
            mock_save.assert_called_once()

    def test_sync_issue_with_commits_marks_completed(self, workflow_automation, mock_core, sample_commit):
        """Test syncing issue marks it as completed when no progress value."""
        issue = Issue(
            id="TEST-001",
            title="Test Issue",
            status=Status.IN_PROGRESS,
        )

        sample_commit.extract_progress_info = Mock(return_value=None)

        with patch("roadmap.adapters.git.git_hooks.IssueParser.save_issue_file") as mock_save:
            result = workflow_automation._sync_issue_with_commits(
                issue, [sample_commit]
            )

            assert result is True
            assert issue.status == Status.CLOSED
            assert issue.progress_percentage == 100.0
            mock_save.assert_called_once()

    def test_sync_issue_with_commits_no_changes(self, workflow_automation, mock_core, sample_commit):
        """Test syncing issue with no new commits."""
        issue = Issue(
            id="TEST-001",
            title="Test Issue",
            status=Status.TODO,
        )
        issue.git_commits = [{"hash": "abc123", "message": "Already tracked"}]

        sample_commit.extract_progress_info = Mock(return_value=None)

        with patch("roadmap.adapters.git.git_hooks.IssueParser.save_issue_file"):
            result = workflow_automation._sync_issue_with_commits(
                issue, [sample_commit]
            )

            assert result is False
