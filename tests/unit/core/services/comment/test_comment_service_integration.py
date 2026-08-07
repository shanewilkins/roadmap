"""Comprehensive test suite for comment service."""

from roadmap.core.services.comment.comment_service import CommentService


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
