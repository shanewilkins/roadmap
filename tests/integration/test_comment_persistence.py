"""Integration tests for comment persistence.

These tests verify that comments are properly saved to and loaded from
the database, including complex scenarios like threading and metadata.
"""

import pytest

from roadmap.common.constants import Priority
from roadmap.core.services.comment_service import CommentService
from roadmap.infrastructure.core import RoadmapCore


class TestCommentPersistence:
    """Test comment persistence to database."""

    @pytest.fixture
    def core_and_issue(self, temp_dir):
        """Create initialized roadmap with an issue."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        issue = core.issues.create("Test Issue for Comments", priority=Priority.HIGH)
        yield core, issue

    def test_add_comment_persists_to_database(self, core_and_issue):
        """Verify adding comment to issue persists data."""
        core, issue = core_and_issue

        # Add comment
        comment = CommentService.create_comment("alice", "First comment", issue.id)
        issue.comments.append(comment)

        # Update issue with comment using kwargs
        core.issues.update(issue.id, comments=issue.comments)

        # Reload and verify
        reloaded = core.issues.get(issue.id)
        assert len(reloaded.comments) == 1
        assert reloaded.comments[0].author == "alice"
        assert reloaded.comments[0].body == "First comment"

    def test_multiple_comments_persist(self, core_and_issue):
        """Verify multiple comments persist correctly."""
        core, issue = core_and_issue

        # Add multiple comments
        comment1 = CommentService.create_comment("alice", "Comment 1", issue.id)
        comment2 = CommentService.create_comment("bob", "Comment 2", issue.id)
        issue.comments.extend([comment1, comment2])

        # Update issue
        core.issues.update(issue.id, comments=issue.comments)

        # Reload and verify
        reloaded = core.issues.get(issue.id)
        assert len(reloaded.comments) == 2
        assert reloaded.comments[0].author == "alice"
        assert reloaded.comments[1].author == "bob"

    def test_comment_thread_persistence(self, core_and_issue):
        """Verify comment threading (in_reply_to) persists."""
        core, issue = core_and_issue

        # Create parent comment
        parent = CommentService.create_comment("alice", "Parent comment", issue.id)
        issue.comments.append(parent)
        core.issues.update(issue.id, comments=issue.comments)

        # Create reply
        reply = CommentService.create_comment(
            "bob", "Reply to parent", issue.id, in_reply_to=parent.id
        )
        issue.comments.append(reply)
        core.issues.update(issue.id, comments=issue.comments)

        # Reload and verify threading
        reloaded = core.issues.get(issue.id)
        assert len(reloaded.comments) == 2
        assert reloaded.comments[1].in_reply_to == parent.id

    def test_comment_metadata_persists(self, core_and_issue):
        """Verify comment metadata (timestamps, author) persists."""
        core, issue = core_and_issue

        # Create comment with metadata
        comment = CommentService.create_comment("charlie", "Test comment", issue.id)
        original_created = comment.created_at
        original_author = comment.author

        issue.comments.append(comment)
        core.issues.update(issue.id, comments=issue.comments)

        # Reload and verify metadata
        reloaded = core.issues.get(issue.id)
        assert reloaded.comments[0].created_at == original_created
        assert reloaded.comments[0].author == original_author
        assert reloaded.comments[0].body == "Test comment"

    def test_empty_comments_list_persists(self, core_and_issue):
        """Verify empty comments list persists correctly."""
        core, issue = core_and_issue

        # Ensure comments list is empty
        assert len(issue.comments) == 0

        # Update with empty list
        core.issues.update(issue.id, comments=[])

        # Reload and verify still empty
        reloaded = core.issues.get(issue.id)
        assert len(reloaded.comments) == 0

    def test_comment_persists_across_other_issue_updates(self, core_and_issue):
        """Verify comments persist when other issue fields are updated."""
        core, issue = core_and_issue

        # Add comment
        comment = CommentService.create_comment("diana", "Important note", issue.id)
        issue.comments.append(comment)
        core.issues.update(issue.id, comments=issue.comments)

        # Update other fields
        core.issues.update(issue.id, title="Updated Title", headline="New description")

        # Reload and verify comment still exists
        reloaded = core.issues.get(issue.id)
        assert len(reloaded.comments) == 1
        assert reloaded.comments[0].author == "diana"
        assert reloaded.comments[0].body == "Important note"

    def test_comment_count_in_list_view(self, core_and_issue):
        """Verify comment count is accessible in list view."""
        core, issue = core_and_issue

        # Add comments
        comment1 = CommentService.create_comment("eve", "Comment 1", issue.id)
        comment2 = CommentService.create_comment("frank", "Comment 2", issue.id)
        issue.comments.extend([comment1, comment2])
        core.issues.update(issue.id, comments=issue.comments)

        # Get all issues
        all_issues = core.issues.list()

        # Find our issue in the list
        found = False
        for i in all_issues:
            if i.id == issue.id:
                assert len(i.comments) == 2
                found = True
                break

        assert found, "Issue not found in list"

    def test_issue_deletion_with_comments(self, core_and_issue):
        """Verify issue with comments can be deleted cleanly."""
        core, issue = core_and_issue

        # Add comments
        comment = CommentService.create_comment("grace", "Comment to delete", issue.id)
        issue.comments.append(comment)
        core.issues.update(issue.id, comments=issue.comments)

        # Delete issue
        core.issues.delete(issue.id)

        # Verify deletion - get returns None
        assert core.issues.get(issue.id) is None

    def test_comment_id_uniqueness(self, core_and_issue):
        """Verify each comment has a unique ID."""
        core, issue = core_and_issue

        # Create multiple comments
        comment1 = CommentService.create_comment("user1", "Comment 1", issue.id)
        comment2 = CommentService.create_comment("user2", "Comment 2", issue.id)
        comment3 = CommentService.create_comment("user3", "Comment 3", issue.id)

        issue.comments.extend([comment1, comment2, comment3])
        core.issues.update(issue.id, comments=issue.comments)

        # Reload and verify IDs are unique
        reloaded = core.issues.get(issue.id)
        ids = [c.id for c in reloaded.comments]
        assert len(ids) == len(set(ids)), "Comment IDs must be unique"

    def test_comments_persist_after_multiple_updates(self, core_and_issue):
        """Verify comments persist through multiple issue updates."""
        core, issue = core_and_issue

        # First update with comment
        comment1 = CommentService.create_comment("user1", "First", issue.id)
        issue.comments.append(comment1)
        core.issues.update(issue.id, comments=issue.comments)

        # Second update with another comment
        reloaded = core.issues.get(issue.id)
        comment2 = CommentService.create_comment("user2", "Second", issue.id)
        reloaded.comments.append(comment2)
        core.issues.update(reloaded.id, comments=reloaded.comments)

        # Verify both comments persist
        final = core.issues.get(issue.id)
        assert len(final.comments) == 2
        assert final.comments[0].body == "First"
        assert final.comments[1].body == "Second"
