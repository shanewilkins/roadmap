"""Tests for corrupted comments fixer."""

from unittest.mock import MagicMock

import pytest

from roadmap.adapters.cli.health.fixer import FixSafety
from roadmap.adapters.cli.health.fixers.corrupted_comments_fixer import (
    CorruptedCommentsFixer,
)


class TestCorruptedCommentsFixer:
    """Test suite for CorruptedCommentsFixer."""

    @pytest.fixture
    def fixer(self, mock_core):
        """Create fixer instance with mock_core.

        Uses the mock_core fixture provided by the test so configuration
        in test methods affects the fixer's core instance.
        """
        return CorruptedCommentsFixer(mock_core)

    # ========== Property Tests ==========

    def test_fix_type(self, fixer):
        """Test fix_type property."""
        assert fixer.fix_type == "corrupted_comments"

    def test_safety_level(self, fixer):
        """Test safety_level is REVIEW."""
        assert fixer.safety_level == FixSafety.REVIEW

    def test_description(self, fixer):
        """Test description property."""
        assert "malformed JSON" in fixer.description

    # ========== Scan Tests ==========

    def test_scan_no_corrupted_comments(self, fixer, mock_core):
        """Test scan when no corrupted comments found."""
        # Setup clean issues
        issue = MagicMock()
        issue.id = "ISSUE-1"
        issue.comments = [
            {"author": "user1", "content": "Clean comment", "created_at": "2025-01-01"}
        ]

        mock_core.issues.list.return_value = [issue]
        mock_core.milestones.list.return_value = []
        mock_core.projects.list.return_value = []

        result = fixer.scan()

        assert result["found"] is False
        assert result["count"] == 0
        assert "Found 0 comment(s)" in result["message"]
        assert result["details"] == []

    def test_scan_finds_corrupted_json_content(self, fixer, mock_core):
        """Test scan finds comments with malformed JSON."""
        issue = MagicMock()
        issue.id = "ISSUE-1"
        issue.comments = [
            {
                "author": "user1",
                "content": '{"key": invalid}',  # Invalid JSON
                "created_at": "2025-01-01",
            }
        ]

        mock_core.issues.list.return_value = [issue]
        mock_core.milestones.list.return_value = []
        mock_core.projects.list.return_value = []

        result = fixer.scan()

        assert result["found"] is True
        assert result["count"] == 1
        assert len(result["details"]) == 1
        assert result["details"][0]["entity_type"] == "issue"
        assert result["details"][0]["entity_id"] == "ISSUE-1"

    def test_scan_finds_none_comment(self, fixer, mock_core):
        """Test scan finds None comments as corrupted."""
        issue = MagicMock()
        issue.id = "ISSUE-1"
        issue.comments = [None]

        mock_core.issues.list.return_value = [issue]
        mock_core.milestones.list.return_value = []
        mock_core.projects.list.return_value = []

        result = fixer.scan()

        assert result["found"] is True
        assert result["count"] == 1

    def test_scan_multiple_entities(self, fixer, mock_core):
        """Test scan across multiple entity types."""
        issue = MagicMock()
        issue.id = "ISSUE-1"
        issue.comments = [
            {"author": "user1", "content": '{"bad": }', "created_at": "2025-01-01"}
        ]

        milestone = MagicMock()
        milestone.id = "v1-0-0"
        milestone.comments = [
            {
                "author": "user2",
                "content": '{"wrong": json}',
                "created_at": "2025-01-01",
            }
        ]

        project = MagicMock()
        project.id = "project-1"
        project.comments = []

        mock_core.issues.list.return_value = [issue]
        mock_core.milestones.list.return_value = [milestone]
        mock_core.projects.list.return_value = [project]

        result = fixer.scan()

        assert result["count"] == 2
        assert len(result["details"]) == 2
        entity_types = {d["entity_type"] for d in result["details"]}
        assert "issue" in entity_types
        assert "milestone" in entity_types

    def test_scan_handles_exception(self, fixer, mock_core):
        """Test scan handles exceptions gracefully."""
        mock_core.issues.list.side_effect = Exception("Database error")
        mock_core.milestones.list.return_value = []
        mock_core.projects.list.return_value = []

        result = fixer.scan()

        assert result["found"] is False
        assert result["count"] == 0

    # ========== Dry Run Tests ==========

    def test_dry_run_no_issues(self, fixer, mock_core):
        """Test dry_run with no corrupted comments."""
        mock_core.issues.list.return_value = []
        mock_core.milestones.list.return_value = []
        mock_core.projects.list.return_value = []

        result = fixer.dry_run()

        assert result.success is True
        assert result.dry_run is True
        assert result.changes_made == 0
        assert result.items_count == 0
        assert "Would fix 0" in result.message

    def test_dry_run_with_corrupted_comments(self, fixer, mock_core):
        """Test dry_run with corrupted comments found."""
        issue = MagicMock()
        issue.id = "ISSUE-1"
        issue.comments = [
            {"author": "user1", "content": '{"bad": }', "created_at": "2025-01-01"}
        ]

        mock_core.issues.list.return_value = [issue]
        mock_core.milestones.list.return_value = []
        mock_core.projects.list.return_value = []

        result = fixer.dry_run()

        assert result.success is True
        assert result.dry_run is True
        assert result.items_count == 1
        assert "Would fix 1" in result.message
        assert "issue:ISSUE-1" in result.affected_items

    # ========== Apply Tests ==========

    def test_apply_no_corrupted_comments(self, fixer, mock_core):
        """Test apply with no corrupted comments."""
        mock_core.issues.list.return_value = []
        mock_core.milestones.list.return_value = []
        mock_core.projects.list.return_value = []

        result = fixer.apply()

        assert result.success is True
        assert result.dry_run is False
        assert result.changes_made == 0
        assert "Fixed 0/0" in result.message

    def test_apply_fixes_corrupted_issue_comments(self, fixer, mock_core):
        """Test apply fixes issue comments."""
        issue = MagicMock()
        issue.id = "ISSUE-1"
        issue.comments = [
            {"author": "user1", "content": '{"bad": }', "created_at": "2025-01-01"},
            {"author": "user2", "content": "Clean comment", "created_at": "2025-01-01"},
        ]

        mock_core.issues.list.return_value = [issue]
        mock_core.milestones.list.return_value = []
        mock_core.projects.list.return_value = []
        mock_core.issues.get.return_value = issue

        result = fixer.apply()

        assert result.success is True
        assert result.dry_run is False
        assert result.items_count == 1
        assert result.changes_made == 1
        assert "Fixed 1/1" in result.message

    def test_apply_sanitizes_corrupted_content(self, fixer, mock_core):
        """Test that apply sanitizes corrupted comment content."""
        issue = MagicMock()
        issue.id = "ISSUE-1"
        original_comments = [
            {"author": "user1", "content": '{"bad": }', "created_at": "2025-01-01"},
        ]
        issue.comments = original_comments.copy()

        mock_core.issues.list.return_value = [issue]
        mock_core.milestones.list.return_value = []
        mock_core.projects.list.return_value = []
        mock_core.issues.get.return_value = issue

        fixer.apply()

        # Verify update was called with sanitized comments
        mock_core.issues.update.assert_called_once()
        updated_issue = mock_core.issues.update.call_args[0][0]
        assert len(updated_issue.comments) == 1
        assert updated_issue.comments[0]["content"] == "[corrupted comment sanitized]"

    def test_apply_multiple_entities(self, fixer, mock_core):
        """Test apply across multiple entity types."""
        issue = MagicMock()
        issue.id = "ISSUE-1"
        issue.comments = [{"author": "user1", "content": '{"bad": }', "created_at": ""}]

        milestone = MagicMock()
        milestone.id = "v1-0-0"
        milestone.comments = [
            {"author": "user2", "content": '{"wrong": json}', "created_at": ""}
        ]

        mock_core.issues.list.return_value = [issue]
        mock_core.milestones.list.return_value = [milestone]
        mock_core.projects.list.return_value = []
        mock_core.issues.get.return_value = issue
        mock_core.milestones.get.return_value = milestone

        result = fixer.apply()

        assert result.items_count == 2
        # Only issues.update is called (milestones doesn't have update in code)
        assert mock_core.issues.update.called

    def test_apply_handles_entity_not_found(self, fixer, mock_core):
        """Test apply handles case where entity not found."""
        issue = MagicMock()
        issue.id = "ISSUE-1"
        issue.comments = [{"author": "user1", "content": '{"bad": }', "created_at": ""}]

        mock_core.issues.list.return_value = [issue]
        mock_core.milestones.list.return_value = []
        mock_core.projects.list.return_value = []
        mock_core.issues.get.return_value = None  # Not found

        result = fixer.apply()

        assert result.success is True
        assert result.items_count == 1
        assert result.changes_made == 0

    # ========== Helper Method Tests ==========

    def test_is_corrupted_json_with_valid_json(self, fixer):
        """Test _is_corrupted_json with valid JSON."""
        comment = {
            "author": "user1",
            "content": '{"key": "value"}',
            "created_at": "2025-01-01",
        }
        assert fixer._is_corrupted_json(comment) is False

    def test_is_corrupted_json_with_invalid_json(self, fixer):
        """Test _is_corrupted_json with invalid JSON."""
        comment = {"author": "user1", "content": '{"bad": }', "created_at": ""}
        assert fixer._is_corrupted_json(comment) is True

    def test_is_corrupted_json_with_none(self, fixer):
        """Test _is_corrupted_json with None comment."""
        assert fixer._is_corrupted_json(None) is True

    def test_is_corrupted_json_with_non_dict(self, fixer):
        """Test _is_corrupted_json with non-dict."""
        assert fixer._is_corrupted_json("string") is True
        assert fixer._is_corrupted_json(123) is True

    def test_is_corrupted_json_with_plain_text(self, fixer):
        """Test _is_corrupted_json with plain text content."""
        comment = {"author": "user1", "content": "Plain text comment", "created_at": ""}
        assert fixer._is_corrupted_json(comment) is False

    def test_sanitize_comments_valid(self, fixer):
        """Test _sanitize_comments with all valid comments."""
        comments = [
            {"author": "user1", "content": "Comment 1", "created_at": "2025-01-01"},
            {"author": "user2", "content": "Comment 2", "created_at": "2025-01-02"},
        ]

        result = fixer._sanitize_comments(comments)

        assert result is not None
        assert len(result) == 2
        assert result == comments

    def test_sanitize_comments_mixed(self, fixer):
        """Test _sanitize_comments with mixed valid and invalid."""
        comments = [
            {"author": "user1", "content": '{"bad": }', "created_at": "2025-01-01"},
            {"author": "user2", "content": "Clean", "created_at": "2025-01-02"},
        ]

        result = fixer._sanitize_comments(comments)

        assert result is not None
        assert len(result) == 2
        assert result[0]["content"] == "[corrupted comment sanitized]"
        assert result[1]["content"] == "Clean"

    def test_sanitize_comments_exception(self, fixer):
        """Test _sanitize_comments handles exceptions."""
        # Pass something that will cause an exception
        result = fixer._sanitize_comments(None)
        assert result is None
