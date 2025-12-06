"""
Tests for git status display helper.
"""

from unittest.mock import Mock

import pytest

from roadmap.adapters.cli.git.status_display import GitStatusDisplay


class TestGitStatusDisplay:
    """Test git status display formatting."""

    @pytest.fixture
    def console(self):
        """Create a mock console."""
        return Mock()

    @pytest.fixture
    def display(self, console):
        """Create a GitStatusDisplay instance."""
        return GitStatusDisplay(console)

    def test_init_stores_console(self, console):
        """__init__ should store the console instance."""
        display = GitStatusDisplay(console)
        assert display.console == console

    def test_show_not_git_repo(self, display, console):
        """show_not_git_repo should display warning message."""
        display.show_not_git_repo()

        console.print.assert_called_once()
        call_text = console.print.call_args[0][0]
        assert "Not in a Git repository" in call_text
        assert "📁" in call_text

    def test_show_header(self, display, console):
        """show_header should display status header."""
        display.show_header()

        assert console.print.call_count == 2  # Header + blank line
        header_text = console.print.call_args_list[0][0][0]
        assert "Git Repository Status" in header_text
        assert "🔍" in header_text

    def test_show_repository_info_with_origin(self, display, console):
        """show_repository_info should display origin URL."""
        git_context = {"origin_url": "https://github.com/user/repo.git"}

        display.show_repository_info(git_context)

        console.print.assert_called_once()
        call_text = console.print.call_args[0][0]
        assert "Origin:" in call_text
        assert "https://github.com/user/repo.git" in call_text

    def test_show_repository_info_with_github(self, display, console):
        """show_repository_info should display GitHub owner/repo."""
        git_context = {"github_owner": "testuser", "github_repo": "test-repo"}

        display.show_repository_info(git_context)

        console.print.assert_called_once()
        call_text = console.print.call_args[0][0]
        assert "GitHub:" in call_text
        assert "testuser/test-repo" in call_text

    def test_show_repository_info_with_both(self, display, console):
        """show_repository_info should display both origin and GitHub info."""
        git_context = {
            "origin_url": "https://github.com/user/repo.git",
            "github_owner": "testuser",
            "github_repo": "test-repo",
        }

        display.show_repository_info(git_context)

        assert console.print.call_count == 2
        calls = [call[0][0] for call in console.print.call_args_list]
        assert any("Origin:" in c for c in calls)
        assert any("GitHub:" in c for c in calls)

    def test_show_repository_info_empty_context(self, display, console):
        """show_repository_info should handle empty context gracefully."""
        display.show_repository_info({})

        console.print.assert_not_called()

    def test_show_current_branch_no_branch(self, display, console):
        """show_current_branch should return early if no branch."""
        display.show_current_branch({})

        console.print.assert_not_called()

    def test_show_current_branch_without_issue(self, display, console):
        """show_current_branch should show branch without linked issue."""
        git_context = {"current_branch": "main"}

        display.show_current_branch(git_context)

        assert console.print.call_count == 2
        calls = [call[0][0] for call in console.print.call_args_list]
        assert any("Current branch: main" in c for c in calls)
        assert any("No linked issue" in c for c in calls)

    def test_show_current_branch_with_linked_issue(self, display, console):
        """show_current_branch should show linked issue details."""
        git_context = {
            "current_branch": "feature/ISS-123",
            "linked_issue": {
                "id": "ISS-123",
                "title": "Test Issue",
                "status": "in-progress",
                "priority": "high",
            },
        }

        display.show_current_branch(git_context)

        assert console.print.call_count >= 5
        calls = [call[0][0] for call in console.print.call_args_list]

        # Check branch name
        assert any("feature/ISS-123" in c for c in calls)
        # Check linked issue details
        assert any("Linked issue:" in c for c in calls)
        assert any("Test Issue" in c for c in calls)
        assert any("ISS-123" in c for c in calls)
        assert any("Status: in-progress" in c for c in calls)
        assert any("Priority: high" in c for c in calls)

    def test_show_linked_issue_details_critical_priority(self, display, console):
        """_show_linked_issue_details should use red for critical priority."""
        linked_issue = {
            "id": "ISS-999",
            "title": "Critical Bug",
            "status": "blocked",
            "priority": "critical",
        }

        display._show_linked_issue_details(linked_issue)

        # Should call print multiple times for different fields
        assert console.print.call_count == 5
        calls = console.print.call_args_list

        # Check that critical priority call uses red style
        priority_call = next(c for c in calls if "Priority:" in c[0][0])
        assert priority_call[1].get("style") == "red"

    def test_show_linked_issue_details_non_critical_priority(self, display, console):
        """_show_linked_issue_details should use yellow for non-critical priority."""
        linked_issue = {
            "id": "ISS-100",
            "title": "Feature Request",
            "status": "todo",
            "priority": "medium",
        }

        display._show_linked_issue_details(linked_issue)

        calls = console.print.call_args_list
        priority_call = next(c for c in calls if "Priority:" in c[0][0])
        assert priority_call[1].get("style") == "yellow"

    def test_show_branch_issue_links_empty(self, display, console):
        """show_branch_issue_links should handle empty branch_issues."""
        mock_core = Mock()

        display.show_branch_issue_links({}, "main", mock_core)

        console.print.assert_not_called()

    def test_show_branch_issue_links_single(self, display, console):
        """show_branch_issue_links should display single branch-issue link."""
        mock_core = Mock()
        mock_issue = Mock()
        mock_issue.title = "Test Issue"
        mock_core.issues.get.return_value = mock_issue

        branch_issues = {"feature/test": ["ISS-123"]}

        display.show_branch_issue_links(branch_issues, "main", mock_core)

        # Should print header + branch link
        assert console.print.call_count >= 2
        calls = [call[0][0] for call in console.print.call_args_list]
        assert any("Branch-Issue Links:" in c for c in calls)
        assert any("feature/test" in c and "Test Issue" in c for c in calls)

    def test_show_branch_issue_links_multiple(self, display, console):
        """show_branch_issue_links should display multiple branch-issue links."""
        mock_core = Mock()
        mock_issue1 = Mock()
        mock_issue1.title = "First Issue"
        mock_issue2 = Mock()
        mock_issue2.title = "Second Issue"

        mock_core.issues.get.side_effect = [mock_issue1, mock_issue2]

        branch_issues = {
            "feature/first": ["ISS-1"],
            "feature/second": ["ISS-2"],
        }

        display.show_branch_issue_links(branch_issues, "main", mock_core)

        assert console.print.call_count >= 3  # Header + 2 links
        mock_core.issues.get.assert_any_call("ISS-1")
        mock_core.issues.get.assert_any_call("ISS-2")

    def test_show_branch_issue_links_skips_none_issues(self, display, console):
        """show_branch_issue_links should skip branches with None issues."""
        mock_core = Mock()
        mock_core.issues.get.return_value = None

        branch_issues = {"feature/test": ["ISS-MISSING"]}

        display.show_branch_issue_links(branch_issues, "main", mock_core)

        # Should only print header, no branch link
        assert console.print.call_count == 1
        call_text = console.print.call_args[0][0]
        assert "Branch-Issue Links:" in call_text

    def test_show_branch_issue_link_current_branch(self, display, console):
        """_show_branch_issue_link should mark current branch."""
        mock_issue = Mock()
        mock_issue.title = "Test Issue"

        display._show_branch_issue_link("feature/test", mock_issue, "feature/test")

        console.print.assert_called_once()
        call_text = console.print.call_args[0][0]
        assert "👉" in call_text
        assert "feature/test" in call_text

    def test_show_branch_issue_link_other_branch(self, display, console):
        """_show_branch_issue_link should not mark other branches."""
        mock_issue = Mock()
        mock_issue.title = "Test Issue"

        display._show_branch_issue_link("feature/other", mock_issue, "main")

        console.print.assert_called_once()
        call_text = console.print.call_args[0][0]
        assert "👉" not in call_text
        assert "feature/other" in call_text

    def test_show_branch_issue_link_truncates_long_title(self, display, console):
        """_show_branch_issue_link should truncate long titles."""
        mock_issue = Mock()
        mock_issue.title = "A" * 60  # 60 character title

        display._show_branch_issue_link("feature/test", mock_issue, "main")

        call_text = console.print.call_args[0][0]
        assert "..." in call_text
        assert len(mock_issue.title) > 50
        # Check that the displayed text is truncated
        assert call_text.count("A") <= 53  # 50 + "..."

    def test_show_recent_commits_not_git_repo(self, display, console):
        """show_recent_commits should return early if not git repo."""
        mock_core = Mock()
        mock_core.git.is_git_repository.return_value = False

        display.show_recent_commits(mock_core)

        console.print.assert_not_called()

    def test_show_recent_commits_no_roadmap_commits(self, display, console):
        """show_recent_commits should skip if no roadmap references."""
        mock_core = Mock()
        mock_core.git.is_git_repository.return_value = True

        mock_commit = Mock()
        mock_commit.extract_roadmap_references.return_value = []

        mock_core.git.get_recent_commits.return_value = [mock_commit]

        display.show_recent_commits(mock_core)

        console.print.assert_not_called()

    def test_show_recent_commits_with_roadmap_refs(self, display, console):
        """show_recent_commits should display commits with roadmap references."""
        mock_core = Mock()
        mock_core.git.is_git_repository.return_value = True

        mock_commit = Mock()
        mock_commit.message = "Fix bug in feature"
        mock_commit.short_hash = "abc1234"
        mock_commit.extract_roadmap_references.return_value = ["ISS-123"]

        mock_core.git.get_recent_commits.return_value = [mock_commit]

        display.show_recent_commits(mock_core)

        assert console.print.call_count >= 2  # Header + commit details
        calls = [call[0][0] for call in console.print.call_args_list]
        assert any("Recent Roadmap Commits:" in c for c in calls)
        assert any("abc1234" in c for c in calls)
        assert any("ISS-123" in c for c in calls)

    def test_show_recent_commits_limits_to_three(self, display, console):
        """show_recent_commits should limit display to 3 commits."""
        mock_core = Mock()
        mock_core.git.is_git_repository.return_value = True

        # Create 5 commits with roadmap references
        commits = []
        for i in range(5):
            mock_commit = Mock()
            mock_commit.message = f"Commit {i}"
            mock_commit.short_hash = f"abc{i}"
            mock_commit.extract_roadmap_references.return_value = [f"ISS-{i}"]
            commits.append(mock_commit)

        mock_core.git.get_recent_commits.return_value = commits

        display.show_recent_commits(mock_core)

        # Should show header + 3 commits (2 lines each: message + refs)
        # = 1 + (3 * 2) = 7 calls
        assert console.print.call_count == 7

    def test_show_commit_details_truncates_long_message(self, display, console):
        """_show_commit_details should truncate long commit messages."""
        mock_commit = Mock()
        mock_commit.message = "A" * 70  # 70 character message
        mock_commit.short_hash = "abc1234"
        mock_commit.extract_roadmap_references.return_value = []

        display._show_commit_details(mock_commit)

        call_text = console.print.call_args[0][0]
        assert "..." in call_text
        assert "abc1234" in call_text

    def test_show_commit_details_with_multiple_refs(self, display, console):
        """_show_commit_details should show multiple references."""
        mock_commit = Mock()
        mock_commit.message = "Update features"
        mock_commit.short_hash = "abc1234"
        mock_commit.extract_roadmap_references.return_value = [
            "ISS-1",
            "ISS-2",
            "ISS-3",
        ]

        display._show_commit_details(mock_commit)

        assert console.print.call_count == 2
        refs_call = console.print.call_args_list[1][0][0]
        assert "ISS-1" in refs_call
        assert "ISS-2" in refs_call
        assert "ISS-3" in refs_call

    def test_show_error(self, display, console):
        """show_error should display error message."""
        error = Exception("Test error message")

        display.show_error(error)

        console.print.assert_called_once()
        call_text = console.print.call_args[0][0]
        assert "Failed to get Git status" in call_text
        assert "Test error message" in call_text
        assert "❌" in call_text
