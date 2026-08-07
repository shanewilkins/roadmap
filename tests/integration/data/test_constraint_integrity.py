"""Integration tests for database constraint integrity.

These tests verify that foreign key constraints and data integrity
constraints work correctly, especially for complex operations.
"""

import pytest

from roadmap.common.constants import Priority, Status
from roadmap.core.services.comment.comment_service import CommentService
from roadmap.infrastructure.coordination.core import RoadmapCore


class TestForeignKeyConstraints:
    """Test foreign key constraint enforcement."""

    @pytest.fixture
    def core_with_data(self, temp_dir):
        """Create initialized roadmap with issues and comments."""
        core = RoadmapCore(temp_dir)
        core.initialize()

        # Create issues
        issue1 = core.issues.create("Issue 1", priority=Priority.HIGH)
        issue2 = core.issues.create("Issue 2")
        issue3 = core.issues.create("Issue 3")

        # Add comments to first issue
        comment1 = CommentService.create_comment(
            "alice", "Comment on issue 1", issue1.id
        )
        issue1.comments.append(comment1)
        core.issues.update(issue1.id, comments=issue1.comments)

        # Add comments to second issue
        comment2 = CommentService.create_comment("bob", "Comment on issue 2", issue2.id)
        issue2.comments.append(comment2)
        core.issues.update(issue2.id, comments=issue2.comments)

        yield core, {"issue1": issue1, "issue2": issue2, "issue3": issue3}

    def test_issue_with_comments_deletes_cleanly(self, core_with_data):
        """Verify deleting an issue with comments doesn't violate constraints."""
        core, data = core_with_data
        issue = data["issue1"]

        # Verify issue has comment
        reloaded = core.issues.get(issue.id)
        assert len(reloaded.comments) > 0

        # Delete should work (cascade or explicit cleanup)
        core.issues.delete(issue.id)

        # Verify deletion - get returns None
        assert core.issues.get(issue.id) is None

    def test_multiple_issues_with_comments_delete(self, core_with_data):
        """Verify deleting multiple issues with comments works."""
        core, data = core_with_data

        # Delete two issues with comments
        core.issues.delete(data["issue1"].id)
        core.issues.delete(data["issue2"].id)

        # Verify both deleted - get returns None
        assert core.issues.get(data["issue1"].id) is None
        assert core.issues.get(data["issue2"].id) is None

        # Verify issue without comments still exists
        remaining = core.issues.get(data["issue3"].id)
        assert remaining is not None

    def test_issue_reassignment_preserves_comments(self, core_with_data):
        """Verify reassigning issue preserves comments."""
        core, data = core_with_data
        issue = data["issue1"]

        # Add another comment
        comment = CommentService.create_comment("charlie", "Another comment", issue.id)
        issue.comments.append(comment)
        core.issues.update(issue.id, comments=issue.comments)

        comments_before = len(core.issues.get(issue.id).comments)

        # Update issue fields
        result = core.issues.update(
            issue.id, title="Updated Title", status=Status.IN_PROGRESS
        )
        assert result is not None  # Verify update succeeded

        # Verify comments preserved
        reloaded = core.issues.get(issue.id)
        assert reloaded is not None
        assert len(reloaded.comments) == comments_before

    def test_comment_id_uniqueness_across_issues(self, core_with_data):
        """Verify comment IDs are unique across all issues."""
        core, data = core_with_data

        all_comment_ids = []

        # Collect comment IDs from all issues
        for issue_data in data.values():
            reloaded = core.issues.get(issue_data.id)
            for comment in reloaded.comments:
                all_comment_ids.append(comment.id)

        # Verify all IDs are unique
        assert len(all_comment_ids) == len(set(all_comment_ids)), (
            "Comment IDs must be unique"
        )

    def test_issue_updates_maintain_comment_order(self, core_with_data):
        """Verify comment order is maintained after issue updates."""
        core, data = core_with_data
        issue = data["issue3"]

        # Add multiple comments in order
        comment1 = CommentService.create_comment("user1", "First", issue.id)
        comment2 = CommentService.create_comment("user2", "Second", issue.id)
        comment3 = CommentService.create_comment("user3", "Third", issue.id)

        issue.comments.extend([comment1, comment2, comment3])
        core.issues.update(issue.id, comments=issue.comments)

        # Update other field
        core.issues.update(issue.id, priority="high")

        # Verify comment order maintained
        reloaded = core.issues.get(issue.id)
        assert len(reloaded.comments) == 3
        assert reloaded.comments[0].body == "First"
        assert reloaded.comments[1].body == "Second"
        assert reloaded.comments[2].body == "Third"

    def test_comment_threading_persists_through_updates(self, core_with_data):
        """Verify comment threading relationships persist."""
        core, data = core_with_data
        issue = data["issue3"]

        # Create parent comment
        parent = CommentService.create_comment("alice", "Parent", issue.id)
        issue.comments.append(parent)
        core.issues.update(issue.id, comments=issue.comments)

        # Create reply
        reply = CommentService.create_comment(
            "bob", "Reply", issue.id, in_reply_to=parent.id
        )
        issue.comments.append(reply)
        core.issues.update(issue.id, comments=issue.comments)

        # Update other field
        core.issues.update(issue.id, status="closed")

        # Verify threading maintained
        reloaded = core.issues.get(issue.id)
        assert len(reloaded.comments) == 2
        assert reloaded.comments[1].in_reply_to == parent.id

    def test_empty_to_non_empty_comments(self, core_with_data):
        """Verify transitioning from empty to non-empty comments works."""
        core, data = core_with_data
        issue = data["issue3"]

        # Start empty
        assert len(issue.comments) == 0

        # Add first comment
        comment1 = CommentService.create_comment("user1", "First comment", issue.id)
        issue.comments.append(comment1)
        core.issues.update(issue.id, comments=issue.comments)

        # Add second comment
        reloaded = core.issues.get(issue.id)
        comment2 = CommentService.create_comment("user2", "Second comment", issue.id)
        reloaded.comments.append(comment2)
        core.issues.update(reloaded.id, comments=reloaded.comments)

        # Verify both present
        final = core.issues.get(issue.id)
        assert len(final.comments) == 2

    def test_non_empty_to_empty_comments(self, core_with_data):
        """Verify removing all comments works."""
        core, data = core_with_data
        issue = data["issue1"]

        # Verify has comments
        assert len(core.issues.get(issue.id).comments) > 0

        # Clear comments
        core.issues.update(issue.id, comments=[])

        # Verify empty
        reloaded = core.issues.get(issue.id)
        assert len(reloaded.comments) == 0

    def test_concurrent_comment_additions_to_different_issues(self, core_with_data):
        """Verify adding comments to different issues doesn't cause conflicts."""
        core, data = core_with_data

        # Add comment to issue 1
        comment1 = CommentService.create_comment(
            "user1", "Comment 1", data["issue1"].id
        )
        issue1 = core.issues.get(data["issue1"].id)
        issue1.comments.append(comment1)
        core.issues.update(issue1.id, comments=issue1.comments)

        # Add comment to issue 3
        comment3 = CommentService.create_comment(
            "user3", "Comment 3", data["issue3"].id
        )
        issue3 = core.issues.get(data["issue3"].id)
        issue3.comments.append(comment3)
        core.issues.update(issue3.id, comments=issue3.comments)

        # Verify both have their comments
        final1 = core.issues.get(data["issue1"].id)
        final3 = core.issues.get(data["issue3"].id)

        assert len(final1.comments) == 2  # Original + new
        assert len(final3.comments) == 1
