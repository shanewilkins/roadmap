"""Integration tests for GitSyncMonitor with real git repository."""

import subprocess

import pytest

from roadmap.adapters.git.sync_monitor import GitSyncMonitor


class TestGitSyncMonitorIntegration:
    """Integration tests with real git operations."""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a real git repository for testing."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Configure git user (required for commits)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        return repo_path

    @pytest.fixture
    def monitor_with_repo(self, git_repo):
        """Create a GitSyncMonitor for the test repository."""
        from roadmap.adapters.persistence.storage.state_manager import StateManager

        # Create a state manager with database in the test repo
        db_path = git_repo / ".roadmap" / "state.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        state_manager = StateManager(db_path=db_path)

        return GitSyncMonitor(repo_path=git_repo, state_manager=state_manager)

    def test_detect_changes_with_real_git_repo(self, git_repo, monitor_with_repo):
        """Should detect changes in a real git repository."""
        # Create initial structure
        issues_dir = git_repo / ".roadmap" / "issues"
        issues_dir.mkdir(parents=True)

        # Create and commit an initial file
        issue_file = issues_dir / "issue-1.yaml"
        issue_file.write_text("id: issue-1\ntitle: Test\n")

        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Monitor should detect initial files
        monitor_with_repo.clear_cache()
        changes = monitor_with_repo.detect_changes()
        assert len(changes) > 0

        # Now save the sync state
        monitor_with_repo._save_last_synced_commit()

        # Modify the file and commit the change
        issue_file.write_text("id: issue-1\ntitle: Updated Test\n")

        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "commit", "-m", "Update issue"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Should detect the modification
        monitor_with_repo.clear_cache()
        changes = monitor_with_repo.detect_changes()

        assert len(changes) > 0
        assert any("issue-1.yaml" in path for path in changes.keys())

    def test_detect_first_sync_with_real_git(self, git_repo, monitor_with_repo):
        """Should get all files on first sync."""
        # Create initial files
        issues_dir = git_repo / ".roadmap" / "issues"
        issues_dir.mkdir(parents=True)

        issue_file1 = issues_dir / "issue-1.yaml"
        issue_file1.write_text("id: issue-1\n")

        issue_file2 = issues_dir / "issue-2.yaml"
        issue_file2.write_text("id: issue-2\n")

        # Commit them
        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "commit", "-m", "Add issues"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # First sync should find all files
        changes = monitor_with_repo.detect_changes()

        assert len(changes) == 2
        assert all(status == "added" for status in changes.values())

    def test_archive_detection_with_real_git(self, git_repo, monitor_with_repo):
        """Should detect changes in archive directory."""
        # Create issue and archive directories
        issues_dir = git_repo / ".roadmap" / "issues"
        archive_dir = git_repo / ".roadmap" / "archive" / "issues"
        archive_dir.mkdir(parents=True)

        # Create files
        (issues_dir).mkdir(parents=True)
        (issues_dir / "issue-1.yaml").write_text("id: issue-1\n")
        (archive_dir / "archived-1.yaml").write_text("id: archived-1\n")

        # Commit
        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "commit", "-m", "Add issues and archives"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Detect changes (first sync)
        changes = monitor_with_repo.detect_changes()

        # Should have both regular and archived files
        assert len(changes) == 2
        paths = set(changes.keys())
        assert any("issues/issue-1.yaml" in p for p in paths)
        assert any("archive/issues/archived-1.yaml" in p for p in paths)

    def test_ignores_non_issue_files_with_real_git(self, git_repo, monitor_with_repo):
        """Should ignore non-.roadmap/issues/ files."""
        # Create mixed file structure
        issues_dir = git_repo / ".roadmap" / "issues"
        issues_dir.mkdir(parents=True)

        (issues_dir / "issue-1.yaml").write_text("id: issue-1\n")
        (git_repo / "README.md").write_text("# Project\n")
        (git_repo / "pyproject.toml").write_text("[project]\n")

        # Commit
        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "commit", "-m", "Add mixed files"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Should only detect the issue file
        changes = monitor_with_repo.detect_changes()

        assert len(changes) == 1
        assert ".roadmap/issues/issue-1.yaml" in list(changes.keys())[0]

    def test_delete_detection_with_real_git(self, git_repo, monitor_with_repo):
        """Should detect deleted files."""
        # Create and commit a file
        issues_dir = git_repo / ".roadmap" / "issues"
        issues_dir.mkdir(parents=True)

        issue_file = issues_dir / "issue-1.yaml"
        issue_file.write_text("id: issue-1\n")

        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "commit", "-m", "Add issue"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Sync once
        monitor_with_repo._save_last_synced_commit()

        # Delete the file and commit
        issue_file.unlink()

        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "commit", "-m", "Delete issue"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Should detect the deletion
        monitor_with_repo.clear_cache()
        changes = monitor_with_repo.detect_changes()

        assert len(changes) > 0
        assert any("deleted" in status for status in changes.values())

    def test_sync_state_persistence_with_real_git(self, git_repo, monitor_with_repo):
        """Should persist and retrieve sync state correctly."""
        # Create and commit a file
        issues_dir = git_repo / ".roadmap" / "issues"
        issues_dir.mkdir(parents=True)

        (issues_dir / "issue-1.yaml").write_text("id: issue-1\n")

        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Get first commit
        first_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        # Save sync state
        monitor_with_repo._save_last_synced_commit()

        # Create a new monitor with the same state manager and verify it reads the saved state
        new_monitor = GitSyncMonitor(
            repo_path=git_repo, state_manager=monitor_with_repo.state_manager
        )
        retrieved_commit = new_monitor._get_last_synced_commit()

        assert retrieved_commit == first_commit

    def test_detached_head_handling(self, git_repo, monitor_with_repo):
        """Should handle detached HEAD state gracefully."""
        # Create and commit a file
        issues_dir = git_repo / ".roadmap" / "issues"
        issues_dir.mkdir(parents=True)

        (issues_dir / "issue-1.yaml").write_text("id: issue-1\n")

        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "commit", "-m", "Add issue"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Get commit hash
        commit_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        # Checkout to detached HEAD
        subprocess.run(
            ["git", "checkout", commit_hash],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Should still work in detached HEAD
        monitor_with_repo.clear_cache()
        current = monitor_with_repo._get_current_commit()

        assert current == commit_hash
