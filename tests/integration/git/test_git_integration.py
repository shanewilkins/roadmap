"""Tests for Git integration functionality."""

import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.adapters.git.git import GitBranch, GitCommit, GitIntegration
from roadmap.core.domain import IssueType, Priority
from roadmap.infrastructure.coordination.core import RoadmapCore
from tests.unit.common.formatters.test_assertion_helpers import assert_command_success


class TestGitCommit:
    """Test GitCommit functionality."""

    def test_commit_creation(self):
        """Test creating a GitCommit."""
        commit = GitCommit(
            hash="abc123def456789",
            author="Test Author",
            date=datetime.now(UTC),
            message="feat: implement user auth [roadmap:abc12345] [progress:50%]",
            files_changed=["src/auth.py", "tests/test_auth.py"],
        )

        assert commit.short_hash == "abc123de"
        assert "abc12345" in commit.extract_roadmap_references()
        assert commit.extract_progress_info() == 50.0

    @pytest.mark.parametrize(
        "message,expected",
        [
            ("feat: add login [roadmap:abc12345]", ["abc12345"]),
            ("fix: resolve bug [closes roadmap:def67890]", ["def67890"]),
            ("docs: update API [fixes roadmap:ghi13579]", ["ghi13579"]),
            ("refactor: clean code roadmap:jkl24680", ["jkl24680"]),
            (
                "feat: multiple refs [roadmap:abc12345] [roadmap:def67890]",
                ["abc12345", "def67890"],
            ),
            ("normal commit message", []),
            # New GitHub/GitLab style patterns
            ("fixes #abc12345", ["abc12345"]),
            ("closes #def67890", ["def67890"]),
            ("resolves #ghi13579", ["ghi13579"]),
            ("fix #jkl24680 and addresses #mno97531", ["jkl24680", "mno97531"]),
            ("refs #deadbeef", ["deadbeef"]),
            (
                "Mixed formats: fixes #abc12345 and [roadmap:def67890]",
                ["abc12345", "def67890"],
            ),
        ],
    )
    def test_extract_roadmap_references(self, message, expected):
        """Test extracting roadmap references from commit messages."""
        commit = GitCommit("hash", "author", datetime.now(UTC), message, [])
        assert set(commit.extract_roadmap_references()) == set(expected)

    @pytest.mark.parametrize(
        "message,expected",
        [
            ("feat: add feature [progress:25%]", 25.0),
            ("fix: bug [progress:100]", 100.0),
            ("docs: progress:75%", 75.0),
            ("normal commit", None),
        ],
    )
    def test_extract_progress_info(self, message, expected):
        """Test extracting progress information from commit messages."""
        commit = GitCommit("hash", "author", datetime.now(UTC), message, [])
        assert commit.extract_progress_info() == expected


class TestGitBranch:
    """Test GitBranch functionality."""

    def test_branch_creation(self):
        """Test creating a GitBranch."""
        branch = GitBranch(
            name="feature/abc12345-user-authentication",
            current=True,
            remote="origin/feature/abc12345-user-authentication",
        )

        assert branch.extract_issue_id() == "abc12345"
        assert branch.suggests_issue_type() == "feature"

    @pytest.mark.parametrize(
        "branch_name,expected",
        [
            ("feature/abc12345-description", "abc12345"),
            ("bugfix/def67890-fix-login", "def67890"),
            ("hotfix/abc13579-urgent-patch", "abc13579"),
            ("abc12345-simple-format", "abc12345"),
            ("feature/issue-def67890-with-prefix", "def67890"),
            ("main", None),
            ("develop", None),
        ],
    )
    def test_extract_issue_id_patterns(self, branch_name, expected):
        """Test various branch name patterns for issue ID extraction."""
        branch = GitBranch(branch_name)
        assert branch.extract_issue_id() == expected

    @pytest.mark.parametrize(
        "branch_name,expected",
        [
            ("feature/abc12345-new-feature", "feature"),
            ("feat/abc12345-new-feature", "feature"),
            ("bugfix/abc12345-fix-bug", "bug"),
            ("bug/abc12345-fix-bug", "bug"),
            ("fix/abc12345-fix-bug", "bug"),
            ("hotfix/abc12345-urgent", "hotfix"),
            ("docs/abc12345-documentation", "documentation"),
            ("test/abc12345-add-tests", "testing"),
            ("main", None),
        ],
    )
    def test_suggest_issue_type(self, branch_name, expected):
        """Test issue type suggestions based on branch names."""
        branch = GitBranch(branch_name)
        assert branch.suggests_issue_type() == expected


@pytest.fixture
def git_repo():
    """Set up test Git repository."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)

    # Initialize a git repository
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=temp_dir,
        check=True,
    )

    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository")
    subprocess.run(["git", "add", "README.md"], cwd=temp_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)

    yield repo_path

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)


class TestGitIntegration:
    """Test GitIntegration functionality."""

    def test_git_repository_detection(self, git_repo):
        """Test Git repository detection."""
        git = GitIntegration(git_repo)
        assert git.is_git_repository()

        # Test non-git directory
        non_git_dir = Path(tempfile.mkdtemp())
        git_non = GitIntegration(non_git_dir)
        assert not git_non.is_git_repository()

    def test_get_current_user(self, git_repo):
        """Test getting current Git user."""
        git = GitIntegration(git_repo)
        user = git.get_current_user()
        assert user == "Test User"

    def test_get_current_branch(self, git_repo):
        """Test getting current branch information."""
        git = GitIntegration(git_repo)
        branch = git.get_current_branch()
        assert branch is not None
        assert branch.name in ["main", "master"]  # Default branch name varies
        assert branch.current is True

    @patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor.run")
    def test_get_recent_commits(self, mock_git_cmd):
        """Test getting recent commits."""
        # Mock git log output
        mock_git_cmd.return_value = "abc123|Test Author|2024-01-01T12:00:00+0000|feat: add feature [roadmap:abc12345]"

        git = GitIntegration()
        commits = git.get_recent_commits(count=1)

        assert len(commits) == 1
        assert commits[0].hash == "abc123"
        assert commits[0].author == "Test Author"
        assert "abc12345" in commits[0].extract_roadmap_references()


@pytest.fixture
def roadmap_with_git():
    """Set up test environment with roadmap and git."""
    temp_dir = tempfile.mkdtemp()
    original_dir = os.getcwd()
    os.chdir(temp_dir)

    try:
        # Initialize roadmap
        core = RoadmapCore()
        core.initialize()

        # Initialize git
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create initial commit
        test_file = Path("README.md")
        test_file.write_text("# Test Repository")
        subprocess.run(["git", "add", "README.md"], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

        yield temp_dir, core

    finally:
        os.chdir(original_dir)
        import shutil

        shutil.rmtree(temp_dir)


class TestGitIntegrationCLI:
    """Test Git integration CLI commands."""

    def test_git_status_command(self, roadmap_with_git):
        """Test git status command."""
        _, _ = roadmap_with_git
        runner = CliRunner()
        result = runner.invoke(main, ["git", "status"])

        assert result.exit_code == 0
        assert "Git Repository Status" in result.output
        assert "Current branch:" in result.output

    def test_git_branch_command(self, roadmap_with_git):
        """Test git branch command."""
        _, core = roadmap_with_git
        runner = CliRunner()

        # First create an issue
        result = runner.invoke(
            main, ["issue", "create", "Test Issue", "--type", "feature"]
        )
        assert_command_success(result)

        # Get the created issue from database instead of parsing output
        issues = core.issues.list()
        assert len(issues) > 0, "No issues found after creation"
        issue = issues[0]
        issue_id = str(issue.id)

        # Create a branch for the issue
        result = runner.invoke(main, ["git", "branch", issue_id])
        assert result.exit_code == 0

    def test_git_link_command(self, roadmap_with_git):
        """Test git link command."""
        _, core = roadmap_with_git
        runner = CliRunner()

        # Create an issue
        result = runner.invoke(main, ["issue", "create", "Test Issue"])
        assert_command_success(result)

        # Get the created issue from database instead of parsing output
        issues = core.issues.list()
        assert len(issues) > 0, "No issues found after creation"
        issue = issues[0]
        issue_id = str(issue.id)

        # Create a new branch
        subprocess.run(["git", "checkout", "-b", "test-branch"], check=True)

        # Link issue to current branch
        result = runner.invoke(main, ["git", "link", issue_id])
        assert result.exit_code == 0

    def test_issue_create_with_git_branch(self, roadmap_with_git):
        """Test creating issue with automatic Git branch creation."""
        _, _ = roadmap_with_git
        runner = CliRunner()

        result = runner.invoke(
            main,
            [
                "issue",
                "create",
                "Test Feature",
                "--type",
                "feature",
                "--git-branch",
            ],
        )

        assert result.exit_code == 0
        assert "Created issue:" in result.output
        assert "Created Git branch:" in result.output
        assert "Checked out branch:" in result.output

    def test_issue_create_auto_assignee(self, roadmap_with_git):
        """Test auto-detecting assignee from Git config."""
        _, _ = roadmap_with_git
        runner = CliRunner()

        result = runner.invoke(main, ["issue", "create", "Test Issue"])

        assert result.exit_code == 0
        assert "Auto-detected assignee from Git: Test User" in result.output
        assert "Assignee: Test User" in result.output


@pytest.fixture
def roadmap_with_git_core():
    """Set up test environment with roadmap and Git repository."""
    temp_dir = tempfile.mkdtemp()
    original_dir = os.getcwd()
    os.chdir(temp_dir)

    try:
        core = RoadmapCore()
        core.initialize()

        # Mock git repository
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create initial commit so git has a HEAD
        Path("README.md").write_text("# Test Repository")
        subprocess.run(["git", "add", "README.md"], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

        # Refresh git integration after git repo is created
        from roadmap.adapters.git.git import GitIntegration
        from roadmap.infrastructure.coordination.git_coordinator import GitCoordinator
        from roadmap.infrastructure.git.git_integration_ops import GitIntegrationOps

        git_integration = GitIntegration(core.root_path)
        git_ops = GitIntegrationOps(git_integration, core)
        core.git = GitCoordinator(git_ops)

        yield core

    finally:
        os.chdir(original_dir)
        import shutil

        shutil.rmtree(temp_dir)


class TestGitIntegrationCore:
    """Test Git integration in core functionality."""

    def test_get_git_context(self, roadmap_with_git_core):
        """Test getting Git context information."""
        core = roadmap_with_git_core
        context = core.git.get_context()

        assert context["is_git_repo"] is True
        assert "current_branch" in context

    def test_get_current_user_from_git(self, roadmap_with_git_core):
        """Test getting current user from Git."""
        core = roadmap_with_git_core
        user = core.git.get_current_user()
        assert user == "Test User"

    def test_suggest_branch_name_for_issue(self, roadmap_with_git_core):
        """Test suggesting branch names for issues."""
        core = roadmap_with_git_core
        # Create an issue
        issue = core.issues.create(
            title="Implement User Authentication",
            priority=Priority.HIGH,
            issue_type=IssueType.FEATURE,
        )

        branch_name = core.git.suggest_branch_name(issue.id)

        assert branch_name is not None
        assert issue.id in branch_name
        assert "feature/" in branch_name
        assert "implement-user-authentication" in branch_name

    @patch("roadmap.adapters.git.git.GitIntegration.get_commits_for_issue")
    def test_update_issue_from_git_activity(
        self, mock_get_commits, roadmap_with_git_core
    ):
        """Test updating issue from Git commit activity."""
        core = roadmap_with_git_core
        # Create an issue
        issue = core.issues.create(title="Test Issue", priority=Priority.MEDIUM)

        # Mock commit with progress info
        mock_commit = GitCommit(
            hash="abc123",
            author="Test User",
            date=datetime.now(UTC),
            message=f"feat: implement feature [roadmap:{issue.id}] [progress:75%]",
            files_changed=["test.py"],
        )
        mock_get_commits.return_value = [mock_commit]

        # Update issue from Git activity
        success = core.git.update_issue_from_activity(issue.id)

        assert success is True

        # Check that issue was updated
        updated_issue = core.issues.get(issue.id)
        assert updated_issue.progress_percentage == 75.0


class TestGitIntegrationErrorHandling:
    """Test error handling in Git integration."""

    def test_non_git_repository(self, temp_dir_context):
        """Test behavior in non-Git repositories."""
        with temp_dir_context() as temp_dir:
            git = GitIntegration(Path(temp_dir))

            assert not git.is_git_repository()
            assert git.get_current_user() is None
            assert git.get_current_branch() is None
            assert git.get_recent_commits() == []

    def test_invalid_git_commands(self):
        """Test handling of invalid Git commands."""
        git = GitIntegration()

        # Mock a non-existent git command
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            assert git.executor.run(["invalid-command"]) is None

    def test_malformed_commit_data(self):
        """Test handling of malformed commit data."""
        # Test that malformed input data is handled gracefully
        commit = GitCommit(
            hash="",
            author="",
            date=datetime.now(UTC),
            message="",
            files_changed=[],
        )
        assert commit.hash == ""
        assert commit.message == ""
