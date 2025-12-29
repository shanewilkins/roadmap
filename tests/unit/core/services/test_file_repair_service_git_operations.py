"""Comprehensive unit tests for file repair service.

Tests cover YAML parsing, git data normalization, and file repair operations.
"""

import pytest

from roadmap.core.services.file_repair_service import (
    FileRepairResult,
    FileRepairService,
)


class TestFileRepairResult:
    """Test FileRepairResult class."""

    def test_initialization(self):
        """Test result initialization."""
        result = FileRepairResult()
        assert result.fixed_files == []
        assert result.errors == []

    @pytest.mark.parametrize(
        "files_to_add,expected_count,expected_contains",
        [
            (["issues/issue-123.md"], 1, "issues/issue-123.md"),
            (
                ["issues/issue-123.md", "issues/issue-456.md", "issues/issue-789.md"],
                3,
                "issues/issue-456.md",
            ),
        ],
    )
    def test_add_fixed(self, files_to_add, expected_count, expected_contains):
        """Test recording fixed files."""
        result = FileRepairResult()
        for file in files_to_add:
            result.add_fixed(file)

        assert len(result.fixed_files) == expected_count
        assert expected_contains in result.fixed_files

    @pytest.mark.parametrize(
        "files_to_add,expected_count,expected_contains",
        [
            (["issues/issue-bad.md"], 1, "issues/issue-bad.md"),
            (
                ["issues/issue-bad1.md", "issues/issue-bad2.md"],
                2,
                "issues/issue-bad1.md",
            ),
        ],
    )
    def test_add_error(self, files_to_add, expected_count, expected_contains):
        """Test recording error files."""
        result = FileRepairResult()
        for file in files_to_add:
            result.add_error(file)

        assert len(result.errors) == expected_count
        assert expected_contains in result.errors

    def test_fixed_and_errors_separate(self):
        """Test that fixed and error lists are separate."""
        result = FileRepairResult()
        result.add_fixed("issues/ok.md")
        result.add_error("issues/bad.md")

        assert len(result.fixed_files) == 1
        assert len(result.errors) == 1


class TestFixGitCommits:
    """Test _fix_git_commits static method."""

    def test_fix_string_commits_to_dict(self):
        """Test converting string commits to dict format."""
        frontmatter = {
            "git_commits": ["abc123", "def456", "ghi789"],
            "other": "data",
        }

        FileRepairService._fix_git_commits(frontmatter)

        assert len(frontmatter["git_commits"]) == 3
        assert frontmatter["git_commits"][0] == {"hash": "abc123"}
        assert frontmatter["git_commits"][1] == {"hash": "def456"}
        assert frontmatter["git_commits"][2] == {"hash": "ghi789"}

    def test_preserve_dict_commits(self):
        """Test that dict-format commits are preserved."""
        frontmatter = {
            "git_commits": [
                {"hash": "abc123", "message": "fix bug"},
                {"hash": "def456"},
            ],
        }

        FileRepairService._fix_git_commits(frontmatter)

        assert frontmatter["git_commits"][0] == {"hash": "abc123", "message": "fix bug"}
        assert frontmatter["git_commits"][1] == {"hash": "def456"}

    def test_mixed_commit_formats(self):
        """Test handling mixed string and dict commits."""
        frontmatter = {
            "git_commits": ["abc123", {"hash": "def456"}, "ghi789"],
        }

        FileRepairService._fix_git_commits(frontmatter)

        assert len(frontmatter["git_commits"]) == 3
        assert frontmatter["git_commits"][0] == {"hash": "abc123"}
        assert frontmatter["git_commits"][1] == {"hash": "def456"}
        assert frontmatter["git_commits"][2] == {"hash": "ghi789"}

    def test_missing_git_commits(self):
        """Test when git_commits field is missing."""
        frontmatter = {"other": "data"}

        FileRepairService._fix_git_commits(frontmatter)

        assert "git_commits" not in frontmatter

    def test_empty_git_commits(self):
        """Test with empty git_commits list."""
        frontmatter = {"git_commits": []}

        FileRepairService._fix_git_commits(frontmatter)

        assert frontmatter["git_commits"] == []

    def test_non_list_git_commits(self):
        """Test when git_commits is not a list."""
        frontmatter = {"git_commits": "not a list"}

        FileRepairService._fix_git_commits(frontmatter)

        # Should not modify non-list values
        assert frontmatter["git_commits"] == "not a list"


class TestFixGitBranches:
    """Test _fix_git_branches static method."""

    def test_fix_dict_branches_to_strings(self):
        """Test converting dict branches to string format."""
        frontmatter = {
            "git_branches": [
                {"name": "main"},
                {"name": "develop"},
                {"name": "feature/test"},
            ],
        }

        FileRepairService._fix_git_branches(frontmatter)

        assert frontmatter["git_branches"] == ["main", "develop", "feature/test"]

    def test_preserve_string_branches(self):
        """Test that string-format branches are preserved."""
        frontmatter = {
            "git_branches": ["main", "develop", "feature/test"],
        }

        FileRepairService._fix_git_branches(frontmatter)

        assert frontmatter["git_branches"] == ["main", "develop", "feature/test"]

    def test_mixed_branch_formats(self):
        """Test handling mixed dict and string branches."""
        frontmatter = {
            "git_branches": [
                {"name": "main"},
                "develop",
                {"name": "feature/test"},
            ],
        }

        FileRepairService._fix_git_branches(frontmatter)

        assert frontmatter["git_branches"] == ["main", "develop", "feature/test"]

    def test_dict_without_name_field(self):
        """Test dict branch without 'name' field."""
        frontmatter = {
            "git_branches": [{"other_field": "value"}, "main"],
        }

        FileRepairService._fix_git_branches(frontmatter)

        # Should convert to string representation
        assert len(frontmatter["git_branches"]) == 2
        assert "main" in frontmatter["git_branches"]

    def test_missing_git_branches(self):
        """Test when git_branches field is missing."""
        frontmatter = {"other": "data"}

        FileRepairService._fix_git_branches(frontmatter)

        assert "git_branches" not in frontmatter

    def test_empty_git_branches(self):
        """Test with empty git_branches list."""
        frontmatter = {"git_branches": []}

        FileRepairService._fix_git_branches(frontmatter)

        assert frontmatter["git_branches"] == []

    def test_non_list_git_branches(self):
        """Test when git_branches is not a list."""
        frontmatter = {"git_branches": "not a list"}

        FileRepairService._fix_git_branches(frontmatter)

        # Should not modify non-list values
        assert frontmatter["git_branches"] == "not a list"


class TestNormalizeGitData:
    """Test _normalize_git_data static method."""

    def test_normalize_both_git_fields(self):
        """Test normalizing both git_commits and git_branches."""
        frontmatter = {
            "git_commits": ["abc123", "def456"],
            "git_branches": [{"name": "main"}, {"name": "develop"}],
            "other": "data",
        }

        FileRepairService._normalize_git_data(frontmatter)

        assert frontmatter["git_commits"][0] == {"hash": "abc123"}
        assert frontmatter["git_branches"][0] == "main"

    def test_normalize_only_commits(self):
        """Test normalizing only git_commits."""
        frontmatter = {
            "git_commits": ["abc123"],
            "other": "data",
        }

        FileRepairService._normalize_git_data(frontmatter)

        assert frontmatter["git_commits"][0] == {"hash": "abc123"}

    def test_normalize_only_branches(self):
        """Test normalizing only git_branches."""
        frontmatter = {
            "git_branches": [{"name": "main"}],
            "other": "data",
        }

        FileRepairService._normalize_git_data(frontmatter)

        assert frontmatter["git_branches"][0] == "main"

    def test_normalize_empty_frontmatter(self):
        """Test normalizing empty frontmatter."""
        frontmatter = {}

        FileRepairService._normalize_git_data(frontmatter)

        assert frontmatter == {}
