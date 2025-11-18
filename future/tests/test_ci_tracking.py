"""
Tests for CI/CD integration and automatic issue tracking functionality.
"""

import subprocess
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from roadmap.ci_tracking import (
    CIAutomation,
    CITracker,
    CITrackingConfig,
    GitBranch,
    GitCommit,
)
from roadmap.core import RoadmapCore
from roadmap.models import Issue, IssueType, Priority, Status


class TestCITracker:
    """Test CI/CD tracking functionality."""

    @pytest.fixture
    def mock_core(self):
        """Create a mock RoadmapCore for testing."""
        from pathlib import Path

        core = Mock(spec=RoadmapCore)

        # Add the issues_dir attribute that CI tracking expects
        core.issues_dir = Path("/tmp/test_issues")

        # Create sample issues
        issue1 = Issue(
            id="ea4606b6",
            title="Test Issue 1",
            priority=Priority.HIGH,
            status=Status.TODO,
            issue_type=IssueType.FEATURE,
            git_branches=[],
            git_commits=[],
        )

        issue2 = Issue(
            id="515a927c",
            title="Test Issue 2",
            priority=Priority.MEDIUM,
            status=Status.IN_PROGRESS,
            issue_type=IssueType.BUG,
            git_branches=["existing-branch"],
            git_commits=[
                {
                    "sha": "abc123",
                    "message": "test commit",
                    "date": "2025-11-15T12:00:00",
                }
            ],
        )

        # Mock core methods
        def get_issue_side_effect(issue_id):
            if issue_id == "ea4606b6":
                return issue1
            elif issue_id == "515a927c":
                return issue2
            return None

        core.get_issue.side_effect = get_issue_side_effect
        core.save_issue = Mock()

        return core, issue1, issue2

    @pytest.fixture
    def tracker(self, mock_core):
        """Create a CI tracker with mocked dependencies."""
        core, _, _ = mock_core
        config = CITrackingConfig()
        return CITracker(core, config)

    def test_extract_issue_ids_from_branch(self, tracker):
        """Test extraction of issue IDs from branch names."""
        test_cases = [
            ("feature/ea4606b6-ci-integration", ["ea4606b6"]),
            ("bugfix/515a927c-fix-bug", ["515a927c"]),
            ("hotfix/EA4606B6-urgent", ["ea4606b6"]),  # Case insensitive
            ("ea4606b6-simple", ["ea4606b6"]),
            ("complex/ea4606b6/feature-branch", ["ea4606b6"]),
            ("multi-515a927c-ea4606b6-branch", ["515a927c", "ea4606b6"]),
            ("no-issue-id-branch", []),
            ("short-abc123-branch", []),  # Too short
            ("", []),  # Empty
        ]

        for branch_name, expected in test_cases:
            result = tracker.extract_issue_ids_from_branch(branch_name)
            assert (
                result == expected
            ), f"Branch '{branch_name}' should extract {expected}, got {result}"

    def test_extract_issue_ids_from_commit(self, tracker):
        """Test extraction of issue IDs from commit messages."""
        test_cases = [
            ("fixes ea4606b6", ["ea4606b6"]),
            ("closes #515a927c", ["515a927c"]),
            ("resolves EA4606B6", ["ea4606b6"]),  # Case insensitive
            ("ea4606b6: implement feature", ["ea4606b6"]),
            ("related to 515a927c", ["515a927c"]),
            ("refs ea4606b6", ["ea4606b6"]),
            ("Multiple fixes ea4606b6 and 515a927c", ["ea4606b6", "515a927c"]),
            ("feat: add CI integration (fixes #ea4606b6)", ["ea4606b6"]),
            ("closes ea4606b6: complete implementation", ["ea4606b6"]),
            ("no issue reference here", []),
            ("", []),  # Empty
        ]

        for commit_message, expected in test_cases:
            result = tracker.extract_issue_ids_from_commit(commit_message)
            assert (
                result == expected
            ), f"Commit '{commit_message}' should extract {expected}, got {result}"

    @patch("roadmap.ci_tracking.IssueParser")
    def test_add_branch_to_issue(self, mock_issue_parser, mock_core, tracker):
        """Test adding branch association to issue."""
        core, issue1, issue2 = mock_core

        # Mock the IssueParser.save_issue_file method
        mock_issue_parser.save_issue_file = Mock()

        # Test successful addition
        result = tracker.add_branch_to_issue("ea4606b6", "feature/ea4606b6-test")
        assert result is True
        assert "feature/ea4606b6-test" in issue1.git_branches
        mock_issue_parser.save_issue_file.assert_called()

        # Test duplicate addition (should still return True)
        issue1.git_branches = ["feature/ea4606b6-test"]  # Simulate existing branch
        result = tracker.add_branch_to_issue("ea4606b6", "feature/ea4606b6-test")
        assert result is True

        # Test non-existent issue
        result = tracker.add_branch_to_issue("nonexistent", "test-branch")
        assert result is False

    @patch("roadmap.ci_tracking.IssueParser")
    def test_add_commit_to_issue(self, mock_issue_parser, mock_core, tracker):
        """Test adding commit association to issue."""
        core, issue1, issue2 = mock_core

        # Mock the IssueParser.save_issue_file method
        mock_issue_parser.save_issue_file = Mock()

        # Test successful addition
        result = tracker.add_commit_to_issue("ea4606b6", "abc12345")
        assert result is True
        # Check that a commit dictionary was added
        assert any(
            commit.get("sha") == "abc12345"
            if isinstance(commit, dict)
            else commit == "abc12345"
            for commit in issue1.git_commits
        )
        mock_issue_parser.save_issue_file.assert_called()

        # Test duplicate addition
        issue1.git_commits = [
            {"sha": "abc12345", "message": "test", "date": "2025-11-15T12:00:00"}
        ]
        result = tracker.add_commit_to_issue("ea4606b6", "abc12345")
        assert result is True

        # Test non-existent issue
        result = tracker.add_commit_to_issue("nonexistent", "def67890")
        assert result is False

    @patch("roadmap.ci_tracking.IssueParser")
    def test_remove_branch_from_issue(self, mock_issue_parser, mock_core, tracker):
        """Test removing branch association from issue."""
        core, issue1, issue2 = mock_core

        # Mock the IssueParser.save_issue_file method
        mock_issue_parser.save_issue_file = Mock()

        # Setup issue with existing branch
        issue1.git_branches = ["feature/ea4606b6-test", "another-branch"]

        # Test successful removal
        result = tracker.remove_branch_from_issue("ea4606b6", "feature/ea4606b6-test")
        assert result is True
        assert "feature/ea4606b6-test" not in issue1.git_branches
        assert (
            "another-branch" in issue1.git_branches
        )  # Should not affect other branches
        mock_issue_parser.save_issue_file.assert_called()

        # Test removing non-existent branch
        result = tracker.remove_branch_from_issue("ea4606b6", "non-existent-branch")
        assert result is True  # Should succeed even if not present

    @patch("subprocess.run")
    def test_get_current_branch(self, mock_run, tracker):
        """Test getting current git branch."""
        # Test successful branch retrieval
        mock_run.return_value.stdout = "feature/ea4606b6-test\n"
        mock_run.return_value.returncode = 0

        result = tracker.get_current_branch()
        assert result == "feature/ea4606b6-test"

        # Test git command failure
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        result = tracker.get_current_branch()
        assert result is None

    @patch("roadmap.ci_tracking.IssueParser")
    def test_track_branch(self, mock_issue_parser, mock_core, tracker):
        """Test comprehensive branch tracking."""
        core, issue1, issue2 = mock_core

        # Mock the IssueParser.save_issue_file method
        mock_issue_parser.save_issue_file = Mock()

        # Test tracking branch with issue ID
        results = tracker.track_branch("feature/ea4606b6-ci-integration")

        assert "ea4606b6" in results
        actions = results["ea4606b6"]
        assert "Added branch association" in actions
        assert "Auto-started issue" in actions  # Should auto-start TODO issue

        # Verify issue was updated
        assert issue1.status == Status.IN_PROGRESS
        assert issue1.actual_start_date is not None

        # Test tracking branch with no issue IDs
        results = tracker.track_branch("random-branch-name")
        assert results == {}

    @patch("roadmap.ci_tracking.IssueParser")
    @patch("subprocess.run")
    def test_track_commit(self, mock_run, mock_issue_parser, mock_core, tracker):
        """Test commit tracking functionality."""
        core, issue1, issue2 = mock_core

        # Mock the IssueParser.save_issue_file method
        mock_issue_parser.save_issue_file = Mock()

        # Mock git log command for commit message
        mock_run.return_value.stdout = "fixes ea4606b6: implement CI tracking"
        mock_run.return_value.returncode = 0

        # Test tracking commit
        results = tracker.track_commit("abc12345")

        assert "ea4606b6" in results
        actions = results["ea4606b6"]
        assert "Added commit association" in actions

        # Verify git log was called
        mock_run.assert_called_with(
            ["git", "log", "-1", "--format=%s", "abc12345"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("roadmap.ci_tracking.IssueParser")
    @patch("subprocess.run")
    def test_scan_branches(self, mock_run, mock_issue_parser, mock_core, tracker):
        """Test scanning all branches for associations."""
        core, issue1, issue2 = mock_core

        # Mock the IssueParser.save_issue_file method
        mock_issue_parser.save_issue_file = Mock()

        # Mock git branch command
        mock_run.return_value.stdout = """feature/ea4606b6-test
bugfix/515a927c-fix
main
develop"""
        mock_run.return_value.returncode = 0

        # Mock git log for last commit (called for each branch)
        def git_side_effect(*args, **kwargs):
            if args[0][1] == "log":
                result = Mock()
                result.stdout = "abc123"
                result.returncode = 0
                return result
            else:  # branch command
                result = Mock()
                result.stdout = """feature/ea4606b6-test
bugfix/515a927c-fix
main
develop"""
                result.returncode = 0
                return result

        mock_run.side_effect = git_side_effect

        results = tracker.scan_branches()

        # Should find associations for both issues
        assert "ea4606b6" in results
        assert "515a927c" in results
        assert results["ea4606b6"] == 1  # One branch association
        assert results["515a927c"] == 1  # One branch association


class TestCIAutomation:
    """Test CI automation functionality."""

    @pytest.fixture
    def mock_setup(self):
        """Create mocks for CI automation testing."""
        from pathlib import Path

        core = Mock(spec=RoadmapCore)

        # Add the issues_dir attribute that CI automation expects
        core.issues_dir = Path("/tmp/test_issues")

        config = CITrackingConfig()
        tracker = Mock(spec=CITracker)
        tracker.config = config

        # Create sample issue
        issue = Issue(
            id="ea4606b6",
            title="Test Issue",
            priority=Priority.HIGH,
            status=Status.TODO,
            issue_type=IssueType.FEATURE,
            git_branches=[],
            git_commits=[],
        )

        core.get_issue.return_value = issue
        tracker.extract_issue_ids_from_branch.return_value = ["ea4606b6"]

        automation = CIAutomation(core, tracker)
        return automation, core, tracker, issue

    def test_on_branch_created(self, mock_setup):
        """Test handling of branch creation event."""
        automation, core, tracker, issue = mock_setup

        # Mock tracker.track_branch to return successful results
        tracker.track_branch.return_value = {
            "ea4606b6": ["Added branch association", "Auto-started issue"]
        }

        results = automation.on_branch_created("feature/ea4606b6-test")

        assert results["branch_name"] == "feature/ea4606b6-test"
        assert "ea4606b6" in results["issue_associations"]

        # Verify tracker was called
        tracker.track_branch.assert_called_with("feature/ea4606b6-test")

    @patch("roadmap.ci_tracking.IssueParser")
    def test_on_pull_request_opened(self, mock_issue_parser, mock_setup):
        """Test handling of PR opened event."""
        automation, core, tracker, issue = mock_setup

        # Mock the IssueParser.save_issue_file method
        mock_issue_parser.save_issue_file = Mock()

        pr_info = {"number": 123, "head_branch": "feature/ea4606b6-test"}

        results = automation.on_pull_request_opened(pr_info)

        assert results["pr_number"] == 123
        assert results["branch"] == "feature/ea4606b6-test"

        # Should auto-start the issue
        assert issue.status == Status.IN_PROGRESS
        assert issue.actual_start_date is not None
        assert "Auto-started issue ea4606b6" in results["actions"]

    @patch("roadmap.ci_tracking.IssueParser")
    def test_on_pull_request_merged(self, mock_issue_parser, mock_setup):
        """Test handling of PR merged event."""
        automation, core, tracker, issue = mock_setup

        # Mock the IssueParser.save_issue_file method
        mock_issue_parser.save_issue_file = Mock()

        # Set issue to in-progress
        issue.status = Status.IN_PROGRESS

        pr_info = {
            "number": 123,
            "head_branch": "feature/ea4606b6-test",
            "base_branch": "main",  # Merging to main branch
        }

        results = automation.on_pull_request_merged(pr_info)

        assert results["pr_number"] == 123
        assert results["base_branch"] == "main"

        # Should auto-complete the issue
        assert issue.status == Status.DONE
        assert issue.actual_end_date is not None
        assert issue.completed_date is not None
        assert "Auto-completed issue ea4606b6" in results["actions"]

    @patch("roadmap.ci_tracking.IssueParser")
    def test_on_pull_request_merged_non_main_branch(
        self, mock_issue_parser, mock_setup
    ):
        """Test PR merged to non-main branch doesn't auto-close."""
        automation, core, tracker, issue = mock_setup

        # Reset issue status to TODO for this test (previous test may have modified it)
        issue.status = Status.TODO

        # Mock the IssueParser.save_issue_file method
        mock_issue_parser.save_issue_file = Mock()

        pr_info = {
            "number": 123,
            "head_branch": "feature/ea4606b6-test",
            "base_branch": "staging",  # Not a main branch (develop is in main_branches by default)
        }

        results = automation.on_pull_request_merged(pr_info)

        # Should not auto-complete the issue
        assert issue.status == Status.TODO  # Unchanged
        assert not results["actions"]  # No actions taken


class TestCITrackingConfig:
    """Test CI tracking configuration."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = CITrackingConfig()

        # Check default patterns
        assert len(config.branch_patterns) > 0
        assert len(config.commit_patterns) > 0

        # Check default behavior
        assert config.auto_start_on_branch is True
        assert config.auto_close_on_merge is True
        assert config.auto_progress_on_pr is True

        # Check main branches
        assert "main" in config.main_branches
        assert "master" in config.main_branches
        assert "develop" in config.main_branches

    def test_custom_configuration(self):
        """Test custom configuration creation."""
        config = CITrackingConfig(
            branch_patterns=["custom-({issue_id})-.*"],
            auto_start_on_branch=False,
            main_branches=["production"],
        )

        assert config.branch_patterns == ["custom-({issue_id})-.*"]
        assert config.auto_start_on_branch is False
        assert config.main_branches == ["production"]


class TestGitCommitAndBranch:
    """Test Git data structure classes."""

    def test_git_commit_creation(self):
        """Test GitCommit dataclass."""
        commit = GitCommit(
            sha="abc12345",
            message="Test commit",
            author="Test User",
            date=datetime.now(),
        )

        assert commit.sha == "abc12345"
        assert commit.message == "Test commit"
        assert commit.author == "Test User"
        assert commit.branch is None  # Default value

    def test_git_branch_creation(self):
        """Test GitBranch dataclass."""
        branch = GitBranch(name="feature/test", last_commit_sha="abc12345")

        assert branch.name == "feature/test"
        assert branch.last_commit_sha == "abc12345"
        assert branch.is_active is True  # Default value
        assert branch.created_date is None  # Default value


if __name__ == "__main__":
    pytest.main([__file__])
