"""Tests for Git integration functionality."""

import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.adapters.git.git import GitBranch, GitCommit, GitIntegration
from roadmap.core.domain import IssueType, Priority
from roadmap.infrastructure.core import RoadmapCore


class TestGitCommit:
    """Test GitCommit functionality."""

    def test_commit_creation(self):
        """Test creating a GitCommit."""
        commit = GitCommit(
            hash="abc123def456789",
            author="Test Author",
            date=datetime.now(),
            message="feat: implement user auth [roadmap:abc12345] [progress:50%]",
            files_changed=["src/auth.py", "tests/test_auth.py"],
        )

        assert commit.short_hash == "abc123de"
        assert "abc12345" in commit.extract_roadmap_references()
        assert commit.extract_progress_info() == 50.0

    def test_extract_roadmap_references(self):
        """Test extracting roadmap references from commit messages."""
        test_cases = [
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
        ]

        for message, expected in test_cases:
            commit = GitCommit("hash", "author", datetime.now(), message, [])
            assert set(commit.extract_roadmap_references()) == set(expected)

    def test_extract_progress_info(self):
        """Test extracting progress information from commit messages."""
        test_cases = [
            ("feat: add feature [progress:25%]", 25.0),
            ("fix: bug [progress:100]", 100.0),
            ("docs: progress:75%", 75.0),
            ("normal commit", None),
        ]

        for message, expected in test_cases:
            commit = GitCommit("hash", "author", datetime.now(), message, [])
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

    def test_extract_issue_id_patterns(self):
        """Test various branch name patterns for issue ID extraction."""
        test_cases = [
            ("feature/abc12345-description", "abc12345"),
            ("bugfix/def67890-fix-login", "def67890"),
            ("hotfix/abc13579-urgent-patch", "abc13579"),
            ("abc12345-simple-format", "abc12345"),
            ("feature/issue-def67890-with-prefix", "def67890"),
            ("main", None),
            ("develop", None),
        ]

        for branch_name, expected in test_cases:
            branch = GitBranch(branch_name)
            assert branch.extract_issue_id() == expected

    def test_suggest_issue_type(self):
        """Test issue type suggestions based on branch names."""
        test_cases = [
            ("feature/abc12345-new-feature", "feature"),
            ("feat/abc12345-new-feature", "feature"),
            ("bugfix/abc12345-fix-bug", "bug"),
            ("bug/abc12345-fix-bug", "bug"),
            ("fix/abc12345-fix-bug", "bug"),
            ("hotfix/abc12345-urgent", "hotfix"),
            ("docs/abc12345-documentation", "documentation"),
            ("test/abc12345-add-tests", "testing"),
            ("main", None),
        ]

        for branch_name, expected in test_cases:
            branch = GitBranch(branch_name)
            assert branch.suggests_issue_type() == expected


class TestGitIntegration:
    """Test GitIntegration functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir)

        # Initialize a git repository
        subprocess.run(
            ["git", "init"], cwd=self.temp_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=self.temp_dir, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.temp_dir,
            check=True,
        )

        # Create initial commit
        test_file = self.repo_path / "README.md"
        test_file.write_text("# Test Repository")
        subprocess.run(["git", "add", "README.md"], cwd=self.temp_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"], cwd=self.temp_dir, check=True
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_git_repository_detection(self):
        """Test Git repository detection."""
        self.setUp()
        try:
            git = GitIntegration(self.repo_path)
            assert git.is_git_repository()

            # Test non-git directory
            non_git_dir = Path(tempfile.mkdtemp())
            git_non = GitIntegration(non_git_dir)
            assert not git_non.is_git_repository()
        finally:
            self.tearDown()

    def test_get_current_user(self):
        """Test getting current Git user."""
        self.setUp()
        try:
            git = GitIntegration(self.repo_path)
            user = git.get_current_user()
            assert user == "Test User"
        finally:
            self.tearDown()

    def test_get_current_branch(self):
        """Test getting current branch information."""
        self.setUp()
        try:
            git = GitIntegration(self.repo_path)
            branch = git.get_current_branch()
            assert branch is not None
            assert branch.name in ["main", "master"]  # Default branch name varies
            assert branch.current is True
        finally:
            self.tearDown()

    @patch("roadmap.adapters.git.git.GitIntegration._run_git_command")
    def test_get_recent_commits(self, mock_git_cmd):
        """Test getting recent commits."""
        # Mock git log output
        mock_git_cmd.return_value = "abc123|Test Author|2024-01-01 12:00:00 +0000|feat: add feature [roadmap:abc12345]"

        git = GitIntegration()
        commits = git.get_recent_commits(count=1)

        assert len(commits) == 1
        assert commits[0].hash == "abc123"
        assert commits[0].author == "Test Author"
        assert "abc12345" in commits[0].extract_roadmap_references()


class TestGitIntegrationCLI:
    """Test Git integration CLI commands."""

    def setUp(self):
        """Set up test environment with roadmap and git."""
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)

        # Initialize roadmap
        self.core = RoadmapCore()
        self.core.initialize()

        # Initialize git
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create initial commit
        test_file = Path("README.md")
        test_file.write_text("# Test Repository")
        subprocess.run(["git", "add", "README.md"], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir("/")
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_git_status_command(self):
        """Test git status command."""
        self.setUp()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["git", "status"])

            assert result.exit_code == 0
            assert "Git Repository Status" in result.output
            assert "Current branch:" in result.output
        finally:
            self.tearDown()

    def test_git_branch_command(self):
        """Test git branch command."""
        self.setUp()
        try:
            runner = CliRunner()

            # First create an issue
            result = runner.invoke(
                main, ["issue", "create", "Test Issue", "--type", "feature"]
            )
            assert result.exit_code == 0

            # Extract issue ID from output
            issue_id = result.output.split("ID:")[1].strip().split()[0]

            # Create a branch for the issue
            result = runner.invoke(main, ["git", "branch", issue_id])
            assert result.exit_code == 0
            assert "Created branch:" in result.output
            assert "Linked to issue:" in result.output
        finally:
            self.tearDown()

    def test_git_link_command(self):
        """Test git link command."""
        self.setUp()
        try:
            runner = CliRunner()

            # Create an issue
            result = runner.invoke(main, ["issue", "create", "Test Issue"])
            assert result.exit_code == 0
            issue_id = result.output.split("ID:")[1].strip().split()[0]

            # Create a new branch
            subprocess.run(["git", "checkout", "-b", "test-branch"], check=True)

            # Link issue to current branch
            result = runner.invoke(main, ["git", "link", issue_id])
            assert result.exit_code == 0
            assert "Linked issue to branch:" in result.output
        finally:
            self.tearDown()

    def test_issue_create_with_git_branch(self):
        """Test creating issue with automatic Git branch creation."""
        self.setUp()
        try:
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
        finally:
            self.tearDown()

    def test_issue_create_auto_assignee(self):
        """Test auto-detecting assignee from Git config."""
        self.setUp()
        try:
            runner = CliRunner()

            result = runner.invoke(main, ["issue", "create", "Test Issue"])

            assert result.exit_code == 0
            assert "Auto-detected assignee from Git: Test User" in result.output
            assert "Assignee: Test User" in result.output
        finally:
            self.tearDown()


class TestGitIntegrationCore:
    """Test Git integration in core functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)

        self.core = RoadmapCore()
        self.core.initialize()

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
        from roadmap.infrastructure.git_coordinator import GitCoordinator
        from roadmap.infrastructure.git_integration_ops import GitIntegrationOps

        git_integration = GitIntegration(self.core.root_path)
        git_ops = GitIntegrationOps(git_integration, self.core)
        self.core.git = GitCoordinator(git_ops)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir("/")
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_get_git_context(self):
        """Test getting Git context information."""
        self.setUp()
        try:
            context = self.core.git.get_context()

            assert context["is_git_repo"] is True
            assert "current_branch" in context
        finally:
            self.tearDown()

    def test_get_current_user_from_git(self):
        """Test getting current user from Git."""
        self.setUp()
        try:
            user = self.core.git.get_current_user()
            assert user == "Test User"
        finally:
            self.tearDown()

    def test_suggest_branch_name_for_issue(self):
        """Test suggesting branch names for issues."""
        self.setUp()
        try:
            # Create an issue
            issue = self.core.issues.create(
                title="Implement User Authentication",
                priority=Priority.HIGH,
                issue_type=IssueType.FEATURE,
            )

            branch_name = self.core.git.suggest_branch_name(issue.id)

            assert branch_name is not None
            assert issue.id in branch_name
            assert "feature/" in branch_name
            assert "implement-user-authentication" in branch_name
        finally:
            self.tearDown()

    @patch("roadmap.adapters.git.git.GitIntegration.get_commits_for_issue")
    def test_update_issue_from_git_activity(self, mock_get_commits):
        """Test updating issue from Git commit activity."""
        self.setUp()
        try:
            # Create an issue
            issue = self.core.issues.create(
                title="Test Issue", priority=Priority.MEDIUM
            )

            # Mock commit with progress info
            mock_commit = GitCommit(
                hash="abc123",
                author="Test User",
                date=datetime.now(),
                message=f"feat: implement feature [roadmap:{issue.id}] [progress:75%]",
                files_changed=["test.py"],
            )
            mock_get_commits.return_value = [mock_commit]

            # Update issue from Git activity
            success = self.core.git.update_issue_from_activity(issue.id)

            assert success is True

            # Check that issue was updated
            updated_issue = self.core.issues.get(issue.id)
            assert updated_issue.progress_percentage == 75.0
        finally:
            self.tearDown()


class TestGitIntegrationErrorHandling:
    """Test error handling in Git integration."""

    def test_non_git_repository(self):
        """Test behavior in non-Git repositories."""
        with tempfile.TemporaryDirectory() as temp_dir:
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

            assert git._run_git_command(["invalid-command"]) is None

    def test_malformed_commit_data(self):
        """Test handling of malformed commit data."""
        git = GitIntegration()

        with patch.object(git, "_run_git_command") as mock_cmd:
            # Return malformed commit data
            mock_cmd.return_value = "incomplete|data"

            commits = git.get_recent_commits()
            assert commits == []
