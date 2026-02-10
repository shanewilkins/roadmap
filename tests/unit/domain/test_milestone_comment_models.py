"""Phase 8: Comprehensive tests for Milestone and Comment domain models.

Tests focus on:
- Milestone creation, status tracking, progress calculation
- Milestone relationships to issues and projects
- Comment creation, authoring, threading
- Serialization and deserialization

Minimal mocking - testing real Pydantic validation and behavior.
"""

from datetime import UTC, datetime

import pytest

from roadmap.common.constants import MilestoneStatus, RiskLevel
from roadmap.core.domain.comment import Comment
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone

# ============================================================================
# MILESTONE TESTS
# ============================================================================


class TestMilestoneCreation:
    """Test Milestone object creation and initialization."""

    def test_create_with_required_fields_only(self):
        """Milestone should be creatable with only name."""
        milestone = Milestone(name="v1-0")

        assert milestone.name == "v1-0"
        assert milestone.status == MilestoneStatus.OPEN  # default
        assert milestone.headline == ""
        assert milestone.content == ""

    def test_create_with_complete_data(self, p8_complete_milestone_data):
        """Milestone should accept all optional fields."""
        milestone = Milestone(**p8_complete_milestone_data)

        assert milestone.name == p8_complete_milestone_data["name"]
        assert milestone.headline == "First release"
        assert milestone.content == "Release notes"
        assert milestone.due_date == datetime(2024, 12, 31, tzinfo=UTC)

    def test_milestone_timestamps_created(self):
        """Milestone should track created and updated timestamps."""
        milestone = Milestone(name="v1-0")

        assert milestone.created is not None
        assert milestone.updated is not None
        assert isinstance(milestone.created, datetime)
        assert isinstance(milestone.updated, datetime)
        assert milestone.created.tzinfo == UTC

    def test_milestone_with_due_date(self):
        """Milestone should track due date."""
        due = datetime(2024, 12, 31, tzinfo=UTC)
        milestone = Milestone(name="v1-0", due_date=due)

        assert milestone.due_date == due

    def test_milestone_with_project_id(self):
        """Milestone should track associated project."""
        milestone = Milestone(name="v1-0", project_id="project-123")

        assert milestone.project_id == "project-123"

    def test_milestone_with_github_id(self):
        """Milestone should track GitHub milestone ID."""
        milestone = Milestone(name="v1-0", github_milestone=42)

        assert milestone.github_milestone == 42

    def test_milestone_with_comments(self):
        """Milestone should accept comments list."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="alice",
            body="Progress update",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        milestone = Milestone(name="v1-0", comments=[comment])

        assert len(milestone.comments) == 1
        assert milestone.comments[0].author == "alice"

    def test_milestone_comments_empty_by_default(self):
        """Comments should default to empty list."""
        milestone = Milestone(name="v1-0")

        assert milestone.comments == []


class TestMilestoneStatus:
    """Test milestone status tracking."""

    @pytest.mark.parametrize(
        "status",
        [MilestoneStatus.OPEN, MilestoneStatus.CLOSED],
    )
    def test_milestone_with_each_status(self, status):
        """Milestone should accept any status."""
        milestone = Milestone(name="v1-0", status=status)

        assert milestone.status == status

    def test_status_defaults_to_open(self):
        """Status should default to OPEN."""
        milestone = Milestone(name="v1-0")

        assert milestone.status == MilestoneStatus.OPEN

    def test_status_can_be_changed(self):
        """Milestone status should be mutable."""
        milestone = Milestone(name="v1-0", status=MilestoneStatus.OPEN)

        milestone.status = MilestoneStatus.CLOSED

        assert milestone.status == MilestoneStatus.CLOSED


class TestMilestoneRiskLevel:
    """Test risk level tracking."""

    @pytest.mark.parametrize(
        "risk",
        [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH],
    )
    def test_milestone_with_each_risk_level(self, risk):
        """Milestone should accept any risk level."""
        milestone = Milestone(name="v1-0", risk_level=risk)

        assert milestone.risk_level == risk

    def test_risk_defaults_to_low(self):
        """Risk level should default to LOW."""
        milestone = Milestone(name="v1-0")

        assert milestone.risk_level == RiskLevel.LOW

    def test_risk_can_be_changed(self):
        """Risk level should be mutable."""
        milestone = Milestone(name="v1-0", risk_level=RiskLevel.LOW)

        milestone.risk_level = RiskLevel.HIGH

        assert milestone.risk_level == RiskLevel.HIGH


class TestMilestoneProgressTracking:
    """Test automatic progress calculation."""

    def test_milestone_with_calculated_progress(self):
        """Milestone should track calculated progress."""
        milestone = Milestone(name="v1-0", calculated_progress=50.0)

        assert milestone.calculated_progress == 50.0

    def test_milestone_with_progress_update_timestamp(self):
        """Milestone should track when progress was last updated."""
        now = datetime.now(UTC)
        milestone = Milestone(name="v1-0", last_progress_update=now)

        assert milestone.last_progress_update == now

    def test_milestone_with_completion_velocity(self):
        """Milestone should track completion velocity (issues/week)."""
        milestone = Milestone(name="v1-0", completion_velocity=2.5)

        assert milestone.completion_velocity == 2.5

    def test_milestone_progress_defaults_to_none(self):
        """Progress fields should default to None."""
        milestone = Milestone(name="v1-0")

        assert milestone.calculated_progress is None
        assert milestone.last_progress_update is None
        assert milestone.completion_velocity is None


class TestMilestoneDates:
    """Test date tracking for milestone lifecycle."""

    def test_milestone_with_actual_start_date(self):
        """Milestone should track actual start date."""
        start = datetime(2024, 1, 1, tzinfo=UTC)
        milestone = Milestone(name="v1-0", actual_start_date=start)

        assert milestone.actual_start_date == start

    def test_milestone_with_actual_end_date(self):
        """Milestone should track actual end date."""
        end = datetime(2024, 2, 1, tzinfo=UTC)
        milestone = Milestone(name="v1-0", actual_end_date=end)

        assert milestone.actual_end_date == end

    def test_milestone_with_both_dates(self):
        """Milestone should track both start and end dates."""
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 2, 1, tzinfo=UTC)
        milestone = Milestone(name="v1-0", actual_start_date=start, actual_end_date=end)

        assert milestone.actual_start_date == start
        assert milestone.actual_end_date == end


class TestMilestoneContent:
    """Test content fields."""

    def test_milestone_with_headline(self):
        """Milestone should track headline for list views."""
        milestone = Milestone(name="v1-0", headline="Major release")

        assert milestone.headline == "Major release"

    def test_milestone_with_markdown_content(self):
        """Milestone should accept markdown content."""
        content = "# Release Notes\n\nFeatures included..."
        milestone = Milestone(name="v1-0", content=content)

        assert milestone.content == content

    def test_headline_empty_by_default(self):
        """Headline should default to empty string."""
        milestone = Milestone(name="v1-0")

        assert milestone.headline == ""

    def test_content_empty_by_default(self):
        """Content should default to empty string."""
        milestone = Milestone(name="v1-0")

        assert milestone.content == ""


class TestMilestoneSerialization:
    """Test Milestone serialization."""

    def test_milestone_model_dump(self, p8_complete_milestone_data):
        """Milestone should serialize to dict."""
        milestone = Milestone(**p8_complete_milestone_data)

        data = milestone.model_dump()

        assert isinstance(data, dict)
        assert data["name"] == p8_complete_milestone_data["name"]
        assert data["status"] == MilestoneStatus.OPEN

    def test_milestone_exclude_internal_fields(self, p8_complete_milestone_data):
        """Milestone should exclude internal file_path."""
        milestone = Milestone(**p8_complete_milestone_data)
        milestone.file_path = "/some/path"

        data = milestone.model_dump()

        # file_path is marked with exclude=True
        assert "file_path" not in data


# ============================================================================
# COMMENT TESTS
# ============================================================================


class TestCommentCreation:
    """Test Comment object creation."""

    def test_create_with_required_fields(self, p8_valid_comment_data):
        """Comment should be creatable with all required fields."""
        comment = Comment(**p8_valid_comment_data)

        assert comment.id == 1
        assert comment.issue_id == "issue-1"
        assert comment.author == "alice"
        assert comment.body == "This is a comment"
        assert comment.created_at == datetime(2024, 1, 1, tzinfo=UTC)
        assert comment.updated_at == datetime(2024, 1, 1, tzinfo=UTC)

    def test_comment_fields_are_accessible(self, p8_valid_comment_data):
        """All comment fields should be accessible."""
        comment = Comment(**p8_valid_comment_data)

        assert hasattr(comment, "id")
        assert hasattr(comment, "issue_id")
        assert hasattr(comment, "author")
        assert hasattr(comment, "body")
        assert hasattr(comment, "created_at")
        assert hasattr(comment, "updated_at")

    def test_comment_with_github_url(self):
        """Comment should track GitHub URL."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="alice",
            body="Test",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            github_url="https://github.com/repo/issues/1#issuecomment-123",
        )

        assert comment.github_url == "https://github.com/repo/issues/1#issuecomment-123"

    def test_comment_with_reply_threading(self):
        """Comment should track reply-to relationship."""
        comment = Comment(
            id=2,
            issue_id="issue-1",
            author="bob",
            body="Reply to alice",
            created_at=datetime(2024, 1, 2, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, tzinfo=UTC),
            in_reply_to=1,
        )

        assert comment.in_reply_to == 1


class TestCommentAttributes:
    """Test comment attribute tracking."""

    def test_comment_id_is_github_comment_id(self):
        """Comment ID should be the GitHub comment ID."""
        comment = Comment(
            id=12345,
            issue_id="issue-1",
            author="alice",
            body="Test",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        assert comment.id == 12345

    def test_comment_author_is_github_username(self):
        """Comment author should be GitHub username."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="alice-smith",
            body="Test",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        assert comment.author == "alice-smith"

    def test_comment_body_supports_markdown(self):
        """Comment body should support markdown."""
        markdown_body = """# Header

- Bullet point
- Another point

**Bold text** and *italic*"""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="alice",
            body=markdown_body,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        assert comment.body == markdown_body


class TestCommentTimestamps:
    """Test comment timestamp handling."""

    def test_comment_created_at_timestamp(self):
        """Comment should track creation time."""
        created = datetime(2024, 1, 1, 10, 30, 0, tzinfo=UTC)
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="alice",
            body="Test",
            created_at=created,
            updated_at=created,
        )

        assert comment.created_at == created

    def test_comment_updated_at_timestamp(self):
        """Comment should track last update time."""
        created = datetime(2024, 1, 1, 10, 30, 0, tzinfo=UTC)
        updated = datetime(2024, 1, 1, 11, 45, 0, tzinfo=UTC)
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="alice",
            body="Test",
            created_at=created,
            updated_at=updated,
        )

        assert comment.updated_at == updated
        assert comment.updated_at > comment.created_at

    def test_comment_timestamps_in_utc(self):
        """Comment timestamps should be in UTC."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="alice",
            body="Test",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        assert comment.created_at.tzinfo == UTC
        assert comment.updated_at.tzinfo == UTC


class TestCommentStringRepresentation:
    """Test comment string representation."""

    def test_comment_str_format(self):
        """Comment should have readable string representation."""
        comment = Comment(
            id=1,
            issue_id="issue-1",
            author="alice",
            body="Test comment",
            created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )

        str_repr = str(comment)

        assert "alice" in str_repr
        assert "2024-01-15" in str_repr


class TestCommentThreading:
    """Test comment reply threading."""

    def test_reply_comment_references_parent(self):
        """Reply comment should reference parent comment."""
        parent = Comment(
            id=1,
            issue_id="issue-1",
            author="alice",
            body="Original comment",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        reply = Comment(
            id=2,
            issue_id="issue-1",
            author="bob",
            body="Reply to alice",
            created_at=datetime(2024, 1, 2, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, tzinfo=UTC),
            in_reply_to=parent.id,
        )

        assert reply.in_reply_to == parent.id

    def test_multiple_replies_to_same_comment(self):
        """Multiple comments can reply to the same comment."""
        parent_id = 1

        reply1 = Comment(
            id=2,
            issue_id="issue-1",
            author="alice",
            body="First reply",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            in_reply_to=parent_id,
        )

        reply2 = Comment(
            id=3,
            issue_id="issue-1",
            author="bob",
            body="Second reply",
            created_at=datetime(2024, 1, 2, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, tzinfo=UTC),
            in_reply_to=parent_id,
        )

        assert reply1.in_reply_to == parent_id
        assert reply2.in_reply_to == parent_id
        assert reply1.id != reply2.id


class TestCommentIssueAssociation:
    """Test comment to issue relationship."""

    def test_comment_associated_with_issue(self):
        """Comment should track which issue it belongs to."""
        comment = Comment(
            id=1,
            issue_id="issue-123",
            author="alice",
            body="Test",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        assert comment.issue_id == "issue-123"

    def test_multiple_comments_for_same_issue(self):
        """Multiple comments can belong to the same issue."""
        issue_id = "issue-1"

        comment1 = Comment(
            id=1,
            issue_id=issue_id,
            author="alice",
            body="First comment",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        comment2 = Comment(
            id=2,
            issue_id=issue_id,
            author="bob",
            body="Second comment",
            created_at=datetime(2024, 1, 2, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        )

        assert comment1.issue_id == issue_id
        assert comment2.issue_id == issue_id
        assert comment1.id != comment2.id


class TestIssueWithCommentsIntegration:
    """Test Issue and Comment integration."""

    def test_issue_with_comment_thread(self):
        """Issue should hold a thread of comments."""
        comments = [
            Comment(
                id=1,
                issue_id="issue-1",
                author="alice",
                body="Original issue",
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
                updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            Comment(
                id=2,
                issue_id="issue-1",
                author="bob",
                body="I can help",
                created_at=datetime(2024, 1, 2, tzinfo=UTC),
                updated_at=datetime(2024, 1, 2, tzinfo=UTC),
                in_reply_to=1,
            ),
            Comment(
                id=3,
                issue_id="issue-1",
                author="alice",
                body="Thanks!",
                created_at=datetime(2024, 1, 3, tzinfo=UTC),
                updated_at=datetime(2024, 1, 3, tzinfo=UTC),
                in_reply_to=2,
            ),
        ]

        issue = Issue(title="Test Issue", comments=comments)

        assert len(issue.comments) == 3
        assert issue.comments[0].author == "alice"
        assert issue.comments[1].in_reply_to == 1
        assert issue.comments[2].in_reply_to == 2

    def test_issue_and_milestone_with_comments(self):
        """Both Issue and Milestone can have their own comment threads."""
        issue_comment = Comment(
            id=1,
            issue_id="issue-1",
            author="alice",
            body="Issue comment",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        milestone_comment = Comment(
            id=2,
            issue_id="milestone-1",  # Can reference milestone too
            author="bob",
            body="Milestone comment",
            created_at=datetime(2024, 1, 2, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        )

        issue = Issue(title="Test", comments=[issue_comment])
        milestone = Milestone(name="v1-0", comments=[milestone_comment])

        assert len(issue.comments) == 1
        assert len(milestone.comments) == 1
        assert issue.comments[0].body == "Issue comment"
        assert milestone.comments[0].body == "Milestone comment"
