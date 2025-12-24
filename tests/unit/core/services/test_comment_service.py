"""Comprehensive test suite for comment service."""

from datetime import datetime
from typing import cast

import pytest

from roadmap.common.errors.exceptions import ValidationError
from roadmap.core.domain import Comment
from roadmap.core.services.comment_service import CommentService


class TestCommentService:
    """Test CommentService static methods."""

    def test_generate_comment_id_returns_integer(self):
        """Test that comment ID generation returns an integer."""
        comment_id = CommentService.generate_comment_id()
        assert isinstance(comment_id, int)
        assert comment_id > 0

    def test_generate_comment_id_uniqueness(self):
        """Test that generated comment IDs are unique."""
        ids = [CommentService.generate_comment_id() for _ in range(10)]
        assert len(set(ids)) == len(ids), "Generated IDs should be unique"

    def test_create_comment_valid(self):
        """Test creating a comment with valid inputs."""
        comment = CommentService.create_comment(
            author="john_doe",
            body="This is a test comment",
            entity_id="issue-123",
        )

        assert comment.author == "john_doe"
        assert comment.body == "This is a test comment"
        assert comment.issue_id == "issue-123"
        assert comment.in_reply_to is None
        assert isinstance(comment.created_at, datetime)
        assert isinstance(comment.updated_at, datetime)

    def test_create_comment_with_reply_to(self):
        """Test creating a comment that replies to another comment."""
        parent_id = CommentService.generate_comment_id()
        comment = CommentService.create_comment(
            author="jane_doe",
            body="Reply comment",
            entity_id="issue-456",
            in_reply_to=parent_id,
        )

        assert comment.in_reply_to == parent_id
        assert comment.body == "Reply comment"

    def test_create_comment_strips_whitespace(self):
        """Test that comment creation strips leading/trailing whitespace."""
        comment = CommentService.create_comment(
            author="  author_name  ",
            body="  comment body  ",
        )

        assert comment.author == "author_name"
        assert comment.body == "comment body"

    def test_create_comment_empty_author_raises_error(self):
        """Test that empty author raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CommentService.create_comment(
                author="",
                body="Valid body",
            )

        assert "author cannot be empty" in str(exc_info.value).lower()

    def test_create_comment_whitespace_only_author_raises_error(self):
        """Test that whitespace-only author raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CommentService.create_comment(
                author="   ",
                body="Valid body",
            )

        assert "author cannot be empty" in str(exc_info.value).lower()

    def test_create_comment_empty_body_raises_error(self):
        """Test that empty body raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CommentService.create_comment(
                author="author",
                body="",
            )

        assert "body cannot be empty" in str(exc_info.value).lower()

    def test_create_comment_whitespace_only_body_raises_error(self):
        """Test that whitespace-only body raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CommentService.create_comment(
                author="author",
                body="   ",
            )

        assert "body cannot be empty" in str(exc_info.value).lower()

    def test_create_comment_none_author_raises_error(self):
        """Test that None author raises ValidationError."""
        with pytest.raises(ValidationError):
            CommentService.create_comment(
                author=cast(str, None),
                body="Valid body",
            )

    def test_create_comment_none_body_raises_error(self):
        """Test that None body raises ValidationError."""
        with pytest.raises(ValidationError):
            CommentService.create_comment(
                author="author",
                body=cast(str, None),
            )

    def test_validate_comment_thread_empty_list(self):
        """Test validation on empty comment list."""
        errors = CommentService.validate_comment_thread([])
        assert errors == []

    def test_validate_comment_thread_single_valid(self):
        """Test validation on single valid comment."""
        comment = CommentService.create_comment(
            author="author",
            body="Valid comment",
        )
        errors = CommentService.validate_comment_thread([comment])
        assert errors == []

    def test_validate_comment_thread_duplicate_ids(self):
        """Test validation catches duplicate comment IDs."""
        comment1 = CommentService.create_comment(
            author="author1",
            body="Comment 1",
        )
        # Create second comment with same ID
        comment2 = Comment(
            id=comment1.id,
            issue_id="issue-1",
            author="author2",
            body="Comment 2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        errors = CommentService.validate_comment_thread([comment1, comment2])
        assert any("Duplicate" in error for error in errors)

    def test_validate_comment_thread_invalid_created_at(self):
        """Test validation catches invalid created_at."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="author",
            body="Body",
            created_at=cast(datetime, "not-a-datetime"),
            updated_at=datetime.now(),
        )

        errors = CommentService.validate_comment_thread([comment])
        assert any("created_at" in error for error in errors)

    def test_validate_comment_thread_invalid_updated_at(self):
        """Test validation catches invalid updated_at."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="author",
            body="Body",
            created_at=datetime.now(),
            updated_at=cast(datetime, "not-a-datetime"),
        )

        errors = CommentService.validate_comment_thread([comment])
        assert any("updated_at" in error for error in errors)

    def test_validate_comment_thread_empty_author(self):
        """Test validation catches empty author."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="",
            body="Body",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        errors = CommentService.validate_comment_thread([comment])
        assert any("author cannot be empty" in error for error in errors)

    def test_validate_comment_thread_empty_body(self):
        """Test validation catches empty body."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="author",
            body="",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        errors = CommentService.validate_comment_thread([comment])
        assert any("body cannot be empty" in error for error in errors)

    def test_validate_comment_thread_invalid_reply_reference(self):
        """Test validation catches invalid in_reply_to references."""
        comment1 = CommentService.create_comment(
            author="author1",
            body="Comment 1",
        )
        # Create comment with invalid reply-to reference
        comment2 = Comment(
            id=CommentService.generate_comment_id(),
            issue_id="issue-1",
            author="author2",
            body="Comment 2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            in_reply_to=9999,  # Non-existent ID
        )

        errors = CommentService.validate_comment_thread([comment1, comment2])
        assert any("in_reply_to" in error for error in errors)

    def test_validate_comment_thread_multiple_errors(self):
        """Test validation catches multiple errors in thread."""
        comment1 = Comment(
            id=1,
            issue_id="issue-1",
            author="",  # Error 1: empty author
            body="",  # Error 2: empty body
            created_at=cast(datetime, "invalid"),
            updated_at=datetime.now(),
        )

        errors = CommentService.validate_comment_thread([comment1])
        assert len(errors) >= 3

    def test_validate_comment_thread_circular_reference(self):
        """Test validation catches circular references in reply chains."""
        # Create a circular reference: comment1 -> comment2 -> comment1
        comment1 = Comment(
            id=1,
            issue_id="issue-1",
            author="author1",
            body="Comment 1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            in_reply_to=2,  # Points to comment2
        )
        comment2 = Comment(
            id=2,
            issue_id="issue-1",
            author="author2",
            body="Comment 2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            in_reply_to=1,  # Points back to comment1 - circular!
        )

        errors = CommentService.validate_comment_thread([comment1, comment2])
        # Should detect circular reference or invalid reply references
        assert len(errors) > 0

    def test_build_comment_threads_empty_list(self):
        """Test building threads from empty list."""
        threads = CommentService.build_comment_threads([])
        assert threads == {}

    def test_build_comment_threads_single_comment(self):
        """Test building threads from single root comment."""
        comment = CommentService.create_comment(
            author="author",
            body="Root comment",
        )

        threads = CommentService.build_comment_threads([comment])

        assert None in threads
        assert len(threads[None]) == 1
        assert threads[None][0].author == "author"

    def test_build_comment_threads_with_replies(self):
        """Test building threads with replies."""
        root = CommentService.create_comment(
            author="author1",
            body="Root comment",
        )
        reply1 = CommentService.create_comment(
            author="author2",
            body="First reply",
            in_reply_to=root.id,
        )
        reply2 = CommentService.create_comment(
            author="author3",
            body="Second reply",
            in_reply_to=root.id,
        )

        threads = CommentService.build_comment_threads([root, reply1, reply2])

        assert None in threads
        assert root.id in threads
        assert len(threads[None]) == 1
        assert len(threads[root.id]) == 2

    def test_build_comment_threads_sorted_by_timestamp(self):
        """Test that comments in threads are sorted by created_at."""
        now = datetime.now()
        comment1 = Comment(
            id=1,
            issue_id="issue-1",
            author="author1",
            body="First",
            created_at=now,
            updated_at=now,
        )
        comment2 = Comment(
            id=2,
            issue_id="issue-1",
            author="author2",
            body="Third",
            created_at=datetime(2025, 1, 20),  # Latest
            updated_at=datetime(2025, 1, 20),
            in_reply_to=1,
        )
        comment3 = Comment(
            id=3,
            issue_id="issue-1",
            author="author3",
            body="Second",
            created_at=datetime(2025, 1, 10),
            updated_at=datetime(2025, 1, 10),
            in_reply_to=1,
        )

        threads = CommentService.build_comment_threads([comment1, comment2, comment3])

        # Check thread for comment1 is sorted
        thread = threads[1]
        assert thread[0].created_at <= thread[1].created_at

    def test_format_comment_for_display_no_indent(self):
        """Test formatting comment with no indentation."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="john_doe",
            body="Test comment body",
            created_at=datetime(2025, 1, 15, 14, 30),
            updated_at=datetime(2025, 1, 15, 14, 30),
        )

        formatted = CommentService.format_comment_for_display(comment, indent=0)

        assert "john_doe" in formatted
        assert "Test comment body" in formatted
        assert "2025-01-15 14:30" in formatted
        assert "💬" in formatted

    def test_format_comment_for_display_with_indent(self):
        """Test formatting comment with indentation."""
        comment = CommentService.create_comment(
            author="author",
            body="Indented reply",
        )

        formatted = CommentService.format_comment_for_display(comment, indent=2)

        # Should have 2 levels of indentation (2 * 2 spaces = 4 spaces)
        lines = formatted.split("\n")
        assert lines[0].startswith("    ")  # 4 spaces

    def test_format_comment_for_display_multiline_body(self):
        """Test formatting comment with multiline body."""
        comment = CommentService.create_comment(
            author="author",
            body="Line 1\nLine 2\nLine 3",
        )

        formatted = CommentService.format_comment_for_display(comment)

        assert "Line 1" in formatted
        assert "Line 2" in formatted
        assert "Line 3" in formatted

    def test_format_comment_for_display_special_characters(self):
        """Test formatting comment with special characters."""
        comment = CommentService.create_comment(
            author="author@example.com",
            body="Comment with @mentions and #tags",
        )

        formatted = CommentService.format_comment_for_display(comment)

        assert "author@example.com" in formatted
        assert "@mentions" in formatted
        assert "#tags" in formatted


class TestCommentServiceIntegration:
    """Integration tests for comment service workflows."""

    def test_create_comment_thread(self):
        """Test creating a thread of comments."""
        root = CommentService.create_comment(
            author="alice",
            body="Root comment",
        )
        reply = CommentService.create_comment(
            author="bob",
            body="Reply to root",
            in_reply_to=root.id,
        )

        assert root.author == "alice"
        assert reply.author == "bob"
        assert reply.in_reply_to == root.id

    def test_validate_created_comment_thread(self):
        """Test validating a created comment thread."""
        root = CommentService.create_comment(
            author="alice",
            body="Root comment",
        )
        reply = CommentService.create_comment(
            author="bob",
            body="Reply to root",
            in_reply_to=root.id,
        )

        thread = [root, reply]
        errors = CommentService.validate_comment_thread(thread)

        assert errors == []

    def test_build_comment_tree(self):
        """Test building comment tree structure."""
        root = CommentService.create_comment(
            author="alice",
            body="Root comment",
        )
        reply1 = CommentService.create_comment(
            author="bob",
            body="First reply",
            in_reply_to=root.id,
        )
        reply2 = CommentService.create_comment(
            author="charlie",
            body="Second reply",
            in_reply_to=root.id,
        )

        threads = CommentService.build_comment_threads([root, reply1, reply2])

        assert root.id in threads
        assert len(threads[root.id]) == 2

    def test_format_comment_tree_for_display(self):
        """Test formatting comment tree for display."""
        root = CommentService.create_comment(
            author="alice",
            body="Root comment",
        )
        reply1 = CommentService.create_comment(
            author="bob",
            body="First reply",
            in_reply_to=root.id,
        )
        reply2 = CommentService.create_comment(
            author="charlie",
            body="Second reply",
            in_reply_to=root.id,
        )

        threads = CommentService.build_comment_threads([root, reply1, reply2])

        # Format root
        root_formatted = CommentService.format_comment_for_display(root)
        assert "alice" in root_formatted

        # Format replies
        for reply in threads[root.id]:
            reply_formatted = CommentService.format_comment_for_display(reply, indent=1)
            assert reply.author in reply_formatted

    def test_comment_id_generation_consistency(self):
        """Test that comment IDs remain unique and consistent."""
        comments = []
        for i in range(5):
            comment = CommentService.create_comment(
                author=f"author{i}",
                body=f"Comment {i}",
            )
            comments.append(comment)

        # Validate all comments
        errors = CommentService.validate_comment_thread(comments)
        assert errors == []

        # Verify unique IDs
        ids = [c.id for c in comments]
        assert len(set(ids)) == len(ids)
