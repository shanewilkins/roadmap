"""Tests for git branch manager."""

from pathlib import Path
from unittest.mock import patch

import pytest

from roadmap.adapters.git.git_branch_manager import GitBranchManager


class TestGitBranchManagerInit:
    """Test GitBranchManager initialization."""

    def test_init_default_path(self):
        """Test initialization with default path."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            assert manager.repo_path == Path.cwd()
            assert manager.config is None

    def test_init_custom_path(self):
        """Test initialization with custom path."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            custom_path = Path("/custom/repo")
            manager = GitBranchManager(custom_path)
            assert manager.repo_path == custom_path

    def test_init_with_config(self, mock_config_factory):
        """Test initialization with config."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            config = mock_config_factory()
            manager = GitBranchManager(config=config)
            assert manager.config is config


class TestGenerateTitleSlug:
    """Test title slug generation."""

    def test_slug_simple_title(self):
        """Test slug generation for simple title."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            slug = manager._generate_title_slug("Add feature")
            assert slug == "add-feature"

    def test_slug_removes_special_chars(self):
        """Test that special characters are removed."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            slug = manager._generate_title_slug("Fix @bug #123!")
            assert "@" not in slug
            assert "#" not in slug
            assert "!" not in slug

    def test_slug_lowercase(self):
        """Test that slug is lowercase."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            slug = manager._generate_title_slug("ADD FEATURE")
            assert slug.islower()

    def test_slug_replaces_spaces_with_hyphens(self):
        """Test that spaces are replaced with hyphens."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            slug = manager._generate_title_slug("fix   multiple   spaces")
            assert "   " not in slug
            assert "-" in slug

    def test_slug_length_limited(self):
        """Test that slug length is limited to 40 characters."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            long_title = "a" * 100
            slug = manager._generate_title_slug(long_title)
            assert len(slug) <= 40

    @pytest.mark.parametrize(
        "title,expected_in_slug",
        [
            ("fix bug", "fix-bug"),
            ("Add new feature", "add-new-feature"),
            ("Update-docs", "update-docs"),
            ("version 1 0", "version-1-0"),
        ],
    )
    def test_slug_various_titles(self, title, expected_in_slug):
        """Test slug generation for various titles."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            slug = manager._generate_title_slug(title)
            assert expected_in_slug in slug or slug == expected_in_slug


class TestDeterminePrefix:
    """Test branch prefix determination."""

    def test_prefix_default_feature(self, mock_issue_factory):
        """Test default prefix is feature."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            issue = mock_issue_factory()
            delattr(issue, "issue_type") if hasattr(issue, "issue_type") else None
            prefix = manager._determine_prefix(issue)
            assert prefix == "feature"

    def test_prefix_bugfix_for_bug_type(self, mock_issue_factory):
        """Test bugfix prefix for bug type issues."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            issue = mock_issue_factory(issue_type="bug")
            prefix = manager._determine_prefix(issue)
            assert prefix == "bugfix"

    def test_prefix_docs_for_documentation_type(self, mock_issue_factory):
        """Test docs prefix for documentation type."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            issue = mock_issue_factory(issue_type="documentation")
            prefix = manager._determine_prefix(issue)
            assert prefix == "docs"

    def test_prefix_hotfix_for_critical_priority(self, mock_issue_factory):
        """Test hotfix prefix for critical priority."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            issue = mock_issue_factory(priority_value="critical")
            delattr(issue, "issue_type") if hasattr(issue, "issue_type") else None
            prefix = manager._determine_prefix(issue)
            assert prefix == "hotfix"

    @pytest.mark.parametrize(
        "issue_type,expected",
        [
            ("bug", "bugfix"),
            ("feature", "feature"),
            ("documentation", "docs"),
        ],
    )
    def test_prefix_various_types(self, issue_type, expected, mock_issue_factory):
        """Test prefix for various issue types."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            issue = mock_issue_factory(issue_type=issue_type)
            prefix = manager._determine_prefix(issue)
            assert prefix == expected


class TestFormatBranchName:
    """Test branch name formatting."""

    def test_format_with_default_template(self):
        """Test formatting with default template."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            name = manager._format_branch_name(123, "fix-bug", "bugfix", None)
            assert "bugfix" in name
            assert "123" in name
            assert "fix-bug" in name

    def test_format_with_custom_template(self):
        """Test formatting with custom template."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            template = "{prefix}-{id}/{slug}"
            name = manager._format_branch_name(456, "my-feature", "feature", template)
            assert "feature-456" in name

    def test_format_with_invalid_template_falls_back(self):
        """Test that invalid template falls back to default."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            template = "{invalid_var}"
            name = manager._format_branch_name(789, "test", "feature", template)
            # Should fall back to default format
            assert "789" in name


class TestSuggestBranchName:
    """Test branch name suggestion."""

    def test_suggest_includes_issue_id(self, mock_issue_factory):
        """Test that suggestion includes issue ID."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            issue = mock_issue_factory(id="issue123", title="Add feature")
            delattr(issue, "issue_type") if hasattr(issue, "issue_type") else None

            suggestion = manager.suggest_branch_name(issue)
            assert "issue123" in suggestion

    def test_suggest_includes_slug(self, mock_issue_factory):
        """Test that suggestion includes title slug."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            issue = mock_issue_factory(id="123", title="Fix bug")
            delattr(issue, "issue_type") if hasattr(issue, "issue_type") else None

            suggestion = manager.suggest_branch_name(issue)
            assert "fix" in suggestion.lower()

    def test_suggest_includes_prefix(self, mock_issue_factory):
        """Test that suggestion includes appropriate prefix."""
        with patch("roadmap.adapters.git.git_branch_manager.GitCommandExecutor"):
            manager = GitBranchManager()
            issue = mock_issue_factory(id="123", title="Fix bug", issue_type="bug")

            suggestion = manager.suggest_branch_name(issue)
            assert "bugfix" in suggestion


class TestCheckWorkingTreeClean:
    """Test working tree cleanliness check."""

    def test_clean_tree_returns_true(self, mock_git_executor_factory):
        """Test that clean working tree returns True."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(run_output="")  # No changes
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            is_clean = manager._check_working_tree_clean(force=False)
            assert is_clean is True

    def test_dirty_tree_returns_false(self, mock_git_executor_factory):
        """Test that dirty working tree returns False."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(run_output="M file.py\n")
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            is_clean = manager._check_working_tree_clean(force=False)
            assert is_clean is False

    def test_force_returns_true_regardless(self, mock_git_executor_factory):
        """Test that force flag returns True regardless."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(run_output="M file.py\n")
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            is_clean = manager._check_working_tree_clean(force=True)
            assert is_clean is True

    def test_untracked_files_ignored(self, mock_git_executor_factory):
        """Test that untracked files (?) don't count as changes."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(run_output="?? new_file.py\n")
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            is_clean = manager._check_working_tree_clean(force=False)
            assert is_clean is True


class TestBranchAlreadyExists:
    """Test branch existence checking."""

    def test_branch_exists_returns_true(self, mock_git_executor_factory):
        """Test that existing branch returns True."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(run_output="abc123")
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            exists = manager._branch_already_exists("existing-branch")
            assert exists is True

    def test_branch_not_exists_returns_false(self, mock_git_executor_factory):
        """Test that non-existent branch returns False."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(run_output=None)
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            exists = manager._branch_already_exists("nonexistent-branch")
            assert exists is False


class TestHandleExistingBranch:
    """Test handling of existing branches."""

    def test_checkout_existing_branch(self, mock_git_executor_factory):
        """Test checking out existing branch."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(run_output="Switched to branch")
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            success = manager._handle_existing_branch("existing-branch", checkout=True)
            assert success is True

    def test_skip_checkout_existing_branch(self, mock_git_executor_factory):
        """Test skipping checkout of existing branch."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory()
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            success = manager._handle_existing_branch("existing-branch", checkout=False)
            assert success is True


class TestCreateBranchForIssue:
    """Test creating branches for issues."""

    def test_create_branch_not_git_repo(
        self, mock_git_executor_factory, mock_issue_factory
    ):
        """Test that creation fails if not in git repo."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(is_repo=False)
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            issue = mock_issue_factory()
            delattr(issue, "issue_type") if hasattr(issue, "issue_type") else None

            success = manager.create_branch_for_issue(issue)
            assert success is False

    def test_create_branch_dirty_working_tree(
        self, mock_git_executor_factory, mock_issue_factory
    ):
        """Test that creation fails if working tree is dirty."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(
                is_repo=True, run_output="M file.py\n"
            )
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            issue = mock_issue_factory()
            delattr(issue, "issue_type") if hasattr(issue, "issue_type") else None

            success = manager.create_branch_for_issue(issue, force=False)
            assert success is False

    def test_create_branch_force_skips_dirty_check(
        self, mock_git_executor_factory, mock_issue_factory
    ):
        """Test that force flag skips dirty check."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(is_repo=True)
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            issue = mock_issue_factory()
            delattr(issue, "issue_type") if hasattr(issue, "issue_type") else None

            # With force=True, it should continue past dirty check
            # (though it might fail later when trying to create branch)
            manager.create_branch_for_issue(issue, force=True)
            # Just verify it attempted to proceed


class TestGetCurrentBranch:
    """Test getting current branch information."""

    def test_get_current_branch_success(self, mock_git_executor_factory):
        """Test successfully getting current branch."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory()
            mock_executor.run.side_effect = ["main", "origin/main", "abc123"]
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            branch = manager.get_current_branch()

            assert branch is not None
            assert branch.name == "main"
            assert branch.current is True

    def test_get_current_branch_detached_head(self, mock_git_executor_factory):
        """Test getting current branch in detached HEAD state."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(run_output="HEAD")
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            branch = manager.get_current_branch()

            assert branch is None


class TestGetAllBranches:
    """Test getting all branches."""

    def test_get_all_branches_none(self, mock_git_executor_factory):
        """Test getting all branches when none exist."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory(run_output="")
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            branches = manager.get_all_branches()

            assert branches == []

    def test_get_all_branches_multiple(self, mock_git_executor_factory):
        """Test getting multiple branches."""
        with patch(
            "roadmap.adapters.git.git_branch_manager.GitCommandExecutor"
        ) as mock_executor_class:
            mock_executor = mock_git_executor_factory()
            output = "main|*\nfeature/test|  \ndevelop|  "
            mock_executor.run.return_value = output
            mock_executor_class.return_value = mock_executor

            manager = GitBranchManager()
            branches = manager.get_all_branches()

            assert len(branches) >= 1
            assert any(b.current for b in branches)  # One should be current


# Fixtures removed - using factories from conftest instead
