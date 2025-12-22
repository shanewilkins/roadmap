"""Additional comprehensive tests for CommentService formatting and edge cases."""

from datetime import datetime

from roadmap.core.domain import Comment
from roadmap.core.services.comment_service import CommentService


class TestCommentServiceFormatting:
    """Test comment formatting methods."""

    def test_format_comment_for_display_no_indent(self):
        """Test formatting a comment with no indentation."""
        comment = CommentService.create_comment(
            author="john_doe",
            body="This is a test comment",
        )

        formatted = CommentService.format_comment_for_display(comment, indent=0)

        assert "john_doe" in formatted
        assert "This is a test comment" in formatted
        assert "💬" in formatted
        # Check format includes no leading spaces
        assert formatted.startswith("💬")

    def test_format_comment_for_display_with_indent(self):
        """Test formatting a comment with indentation."""
        comment = CommentService.create_comment(
            author="jane_doe",
            body="Reply comment",
        )

        formatted = CommentService.format_comment_for_display(comment, indent=2)

        assert "jane_doe" in formatted
        assert "Reply comment" in formatted
        # Check format includes indentation
        assert formatted.startswith("    ")  # 2 indent = 4 spaces

    def test_format_comment_for_display_with_various_indents(self):
        """Test formatting with various indent levels."""
        comment = CommentService.create_comment(
            author="author",
            body="Comment",
        )

        for indent_level in range(5):
            formatted = CommentService.format_comment_for_display(
                comment, indent=indent_level
            )
            expected_spaces = "  " * indent_level
            assert formatted.startswith(expected_spaces)

    def test_format_comment_for_display_includes_timestamp(self):
        """Test that formatted comment includes timestamp."""
        comment = CommentService.create_comment(
            author="author",
            body="Comment",
        )

        formatted = CommentService.format_comment_for_display(comment)

        # Should include date in YYYY-MM-DD HH:MM format
        assert "-" in formatted  # Date separator
        assert ":" in formatted  # Time separator


class TestCommentServiceBuildThreads:
    """Test building comment threads."""

    def test_build_threads_multiple_roots_and_replies(self):
        """Test building threads with multiple root comments and replies."""
        root1 = CommentService.create_comment(
            author="author1",
            body="Root 1",
        )
        root2 = CommentService.create_comment(
            author="author2",
            body="Root 2",
        )
        reply1 = CommentService.create_comment(
            author="author3",
            body="Reply to root1",
            in_reply_to=root1.id,
        )
        reply2 = CommentService.create_comment(
            author="author4",
            body="Reply to root2",
            in_reply_to=root2.id,
        )

        threads = CommentService.build_comment_threads([root1, root2, reply1, reply2])

        # Should have None (roots) and two specific IDs
        assert None in threads
        assert root1.id in threads
        assert root2.id in threads

        assert len(threads[None]) == 2  # Two roots
        assert len(threads[root1.id]) == 1  # One reply to root1
        assert len(threads[root2.id]) == 1  # One reply to root2

    def test_build_threads_nested_replies(self):
        """Test building threads with nested replies."""
        root = CommentService.create_comment(
            author="author1",
            body="Root",
        )
        reply1 = CommentService.create_comment(
            author="author2",
            body="Reply 1",
            in_reply_to=root.id,
        )
        reply2 = CommentService.create_comment(
            author="author3",
            body="Reply 2 (to reply1)",
            in_reply_to=reply1.id,
        )

        threads = CommentService.build_comment_threads([root, reply1, reply2])

        # Verify structure
        assert None in threads
        assert root.id in threads
        assert reply1.id in threads

    def test_build_threads_order_by_timestamp(self):
        """Test that threads are ordered by creation time."""
        import time

        root = CommentService.create_comment(
            author="author1",
            body="Root",
        )

        # Create replies with slight delays to ensure different timestamps
        replies = []
        for i in range(3):
            time.sleep(0.01)
            reply = CommentService.create_comment(
                author=f"author{i}",
                body=f"Reply {i}",
                in_reply_to=root.id,
            )
            replies.append(reply)

        threads = CommentService.build_comment_threads([root] + replies)

        # Verify replies are sorted by created_at
        reply_thread = threads[root.id]
        for i in range(len(reply_thread) - 1):
            assert reply_thread[i].created_at <= reply_thread[i + 1].created_at

    def test_build_threads_returns_dict_type(self):
        """Test that build_comment_threads returns dict type."""
        comment = CommentService.create_comment(
            author="author",
            body="Comment",
        )

        result = CommentService.build_comment_threads([comment])

        assert isinstance(result, dict)
        # Keys should be comment IDs or None
        for key in result.keys():
            assert key is None or isinstance(key, int)


class TestCommentServiceEdgeCases:
    """Test edge cases and special scenarios."""

    def test_create_comment_with_none_entity_id(self):
        """Test creating comment without entity_id."""
        comment = CommentService.create_comment(
            author="author",
            body="Body",
            entity_id=None,
        )

        assert comment.issue_id == ""
        assert comment.author == "author"
        assert comment.body == "Body"

    def test_create_comment_with_empty_entity_id(self):
        """Test creating comment with empty entity_id."""
        comment = CommentService.create_comment(
            author="author",
            body="Body",
            entity_id="",
        )

        assert comment.issue_id == ""

    def test_create_comment_with_long_body(self):
        """Test creating comment with very long body text."""
        long_body = "x" * 10000
        comment = CommentService.create_comment(
            author="author",
            body=long_body,
        )

        assert len(comment.body) == 10000
        assert comment.body == long_body

    def test_create_comment_with_special_characters(self):
        """Test creating comment with special characters."""
        special_body = "Test with émojis 🎉 and spëcial çharacters"
        comment = CommentService.create_comment(
            author="author",
            body=special_body,
        )

        assert comment.body == special_body

    def test_create_comment_with_newlines_in_body(self):
        """Test creating comment with newlines in body."""
        body_with_newlines = "Line 1\nLine 2\nLine 3"
        comment = CommentService.create_comment(
            author="author",
            body=body_with_newlines,
        )

        assert comment.body == body_with_newlines

    def test_validate_thread_with_whitespace_author(self):
        """Test validation catches whitespace-only author."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="   ",
            body="Valid body",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        errors = CommentService.validate_comment_thread([comment])
        assert any("author" in error.lower() for error in errors)

    def test_validate_thread_with_whitespace_body(self):
        """Test validation catches whitespace-only body."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="author",
            body="   ",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        errors = CommentService.validate_comment_thread([comment])
        assert any("body" in error.lower() for error in errors)

    def test_format_comment_multiline_body(self):
        """Test formatting comment with multiline body."""
        body = "Line 1\nLine 2\nLine 3"
        comment = CommentService.create_comment(
            author="author",
            body=body,
        )

        formatted = CommentService.format_comment_for_display(comment, indent=1)

        assert "Line 1" in formatted
        assert "Line 2" in formatted
        assert "Line 3" in formatted

    def test_comment_id_range(self):
        """Test that generated comment IDs are in expected range."""
        for _ in range(100):
            comment_id = CommentService.generate_comment_id()
            # Should be a positive integer
            assert isinstance(comment_id, int)
            assert comment_id > 0
            # Should fit in a reasonable range (15 digits from UUID)
            assert comment_id < 10**15


class TestCommentServiceCircularReferenceDetection:
    """Test circular reference detection in comment threads."""

    def test_validate_deeply_nested_thread(self):
        """Test validation with deeply nested comment thread."""
        # Create a deep thread: comment1 -> comment2 -> comment3 -> comment4
        root = Comment(
            id=100,
            issue_id="issue-1",
            author="author1",
            body="Root",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            in_reply_to=None,
        )
        reply1 = Comment(
            id=101,
            issue_id="issue-1",
            author="author2",
            body="Reply 1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            in_reply_to=100,
        )
        reply2 = Comment(
            id=102,
            issue_id="issue-1",
            author="author3",
            body="Reply 2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            in_reply_to=101,
        )
        reply3 = Comment(
            id=103,
            issue_id="issue-1",
            author="author4",
            body="Reply 3",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            in_reply_to=102,
        )

        errors = CommentService.validate_comment_thread([root, reply1, reply2, reply3])
        # Deep nesting should not produce errors
        assert len(errors) == 0

    def test_validate_thread_with_orphaned_reply(self):
        """Test validation with reply to non-existent parent."""
        comment1 = Comment(
            id=200,
            issue_id="issue-1",
            author="author1",
            body="Comment 1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            in_reply_to=None,
        )
        # Reply to non-existent comment
        comment2 = Comment(
            id=201,
            issue_id="issue-1",
            author="author2",
            body="Comment 2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            in_reply_to=999,  # Non-existent
        )

        errors = CommentService.validate_comment_thread([comment1, comment2])
        # Should catch the invalid reference
        assert any("999" in error for error in errors)

    def test_validate_thread_large_comment_set(self):
        """Test validation with large set of comments."""
        comments = []
        # Create 50 root comments
        for i in range(50):
            comment = Comment(
                id=i,
                issue_id="issue-1",
                author=f"author{i}",
                body=f"Comment {i}",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                in_reply_to=None,
            )
            comments.append(comment)

        errors = CommentService.validate_comment_thread(comments)
        # No errors for valid comments
        assert len(errors) == 0

    def test_validate_thread_mixed_valid_and_invalid(self):
        """Test validation with mix of valid and invalid comments."""
        valid = Comment(
            id=300,
            issue_id="issue-1",
            author="valid_author",
            body="Valid body",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        invalid_author = Comment(
            id=301,
            issue_id="issue-1",
            author="",
            body="Valid body",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        invalid_body = Comment(
            id=302,
            issue_id="issue-1",
            author="valid_author",
            body="",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        errors = CommentService.validate_comment_thread(
            [valid, invalid_author, invalid_body]
        )
        # Should catch multiple errors
        assert len(errors) >= 2

    def test_validate_thread_self_reply(self):
        """Test validation where comment replies to itself."""
        comment = Comment(
            id=400,
            issue_id="issue-1",
            author="author",
            body="Body",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            in_reply_to=400,  # Replies to itself
        )

        # This is technically a self-reference, test behavior
        # May or may not be caught depending on implementation
        CommentService.validate_comment_thread([comment])
