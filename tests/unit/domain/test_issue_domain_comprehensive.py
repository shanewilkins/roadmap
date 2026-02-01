"""Phase 8: Comprehensive tests for Issue domain model.

Tests focus on:
- Object creation and initialization
- Status transitions and validity
- Field validation and constraints
- Relationship handling (milestones, comments, dependencies)
- Backwards compatibility (legacy github_issue field)

Uses parameterization for status combinations and data variations.
Minimal mocking - testing real Pydantic validation.
"""

from datetime import UTC, datetime

import pytest

from roadmap.common.constants import IssueType, Priority, Status
from roadmap.core.domain.comment import Comment
from roadmap.core.domain.issue import Issue


class TestIssueCreation:
    """Test Issue object creation and initialization."""

    def test_create_with_minimal_required_fields(self, p8_minimal_issue_data):
        """Issue should be creatable with only title field."""
        issue = Issue(**p8_minimal_issue_data)

        assert issue.title == "Minimal Issue"
        assert issue.status == Status.TODO  # default
        assert issue.priority == Priority.MEDIUM  # default
        assert issue.id  # auto-generated
        assert isinstance(issue.id, str)

    def test_create_with_complete_data(self, p8_complete_issue_data):
        """Issue should accept all optional fields."""
        issue = Issue(**p8_complete_issue_data)

        assert issue.title == p8_complete_issue_data["title"]
        assert issue.headline == "Brief summary"
        assert issue.assignee == "user@example.com"
        assert issue.labels == ["bug", "urgent"]
        assert issue.milestone == "v1.0"
        assert issue.estimated_hours == 8.0
        assert issue.progress_percentage == 50.0

    def test_create_with_explicit_id(self):
        """Issue should accept explicit ID on creation."""
        issue = Issue(title="Test", id="custom-id-123")

        assert issue.id == "custom-id-123"

    def test_auto_generated_id_is_unique(self, p8_minimal_issue_data):
        """Multiple issues should have different auto-generated IDs."""
        issue1 = Issue(**p8_minimal_issue_data)
        issue2 = Issue(**p8_minimal_issue_data)

        assert issue1.id != issue2.id

    def test_create_with_timestamps(self):
        """Issue should track created and updated timestamps."""
        issue = Issue(title="Test")

        assert issue.created is not None
        assert issue.updated is not None
        assert isinstance(issue.created, datetime)
        assert isinstance(issue.updated, datetime)
        # Timestamps should be in UTC
        assert issue.created.tzinfo == UTC

    def test_create_with_dependencies(self):
        """Issue should track depends_on and blocks relationships."""
        issue = Issue(
            title="Feature A",
            depends_on=["issue-1", "issue-2"],
            blocks=["issue-3"],
        )

        assert issue.depends_on == ["issue-1", "issue-2"]
        assert issue.blocks == ["issue-3"]

    def test_create_with_comments(self, p8_comment):
        """Issue should accept comments list."""
        issue = Issue(title="Test", comments=[p8_comment])

        assert len(issue.comments) == 1
        assert issue.comments[0].author == "alice"

    def test_empty_optional_lists_default_correctly(self):
        """Optional list fields should default to empty lists."""
        issue = Issue(title="Test")

        assert issue.labels == []
        assert issue.depends_on == []
        assert issue.blocks == []
        assert issue.comments == []
        assert issue.git_branches == []
        assert issue.git_commits == []


class TestIssueStatusTransitions:
    """Test valid and invalid status transitions."""

    @pytest.mark.parametrize(
        "from_status,to_status,is_valid",
        [
            (Status.TODO, Status.IN_PROGRESS, True),
            (Status.IN_PROGRESS, Status.CLOSED, True),
            (Status.IN_PROGRESS, Status.TODO, True),  # Can regress
            (Status.TODO, Status.CLOSED, True),  # Can skip states
            (Status.CLOSED, Status.TODO, True),  # Can reopen
            (Status.BLOCKED, Status.TODO, True),  # Can unblock
        ],
    )
    def test_status_transitions(self, from_status, to_status, is_valid):
        """Test that status can be changed (all transitions are valid in domain)."""
        issue = Issue(title="Test", status=from_status)

        # Change status
        issue.status = to_status

        assert issue.status == to_status

    def test_status_value_is_preserved(self):
        """Changing status should preserve the Status enum value."""
        issue = Issue(title="Test", status=Status.TODO)

        issue.status = Status.IN_PROGRESS

        assert issue.status == Status.IN_PROGRESS
        assert isinstance(issue.status, Status)

    @pytest.mark.parametrize(
        "status", [Status.TODO, Status.IN_PROGRESS, Status.CLOSED, Status.BLOCKED]
    )
    def test_issue_with_each_status(self, status):
        """Issue should be creatable with any status."""
        issue = Issue(title="Test", status=status)

        assert issue.status == status


class TestIssuePriorities:
    """Test issue priority handling."""

    @pytest.mark.parametrize(
        "priority",
        [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL],
    )
    def test_issue_with_each_priority(self, priority):
        """Issue should accept any priority level."""
        issue = Issue(title="Test", priority=priority)

        assert issue.priority == priority

    def test_priority_defaults_to_medium(self):
        """Priority should default to MEDIUM."""
        issue = Issue(title="Test")

        assert issue.priority == Priority.MEDIUM


class TestIssueTypes:
    """Test issue type tracking."""

    @pytest.mark.parametrize(
        "issue_type",
        [IssueType.BUG, IssueType.FEATURE, IssueType.OTHER],
    )
    def test_issue_with_each_type(self, issue_type):
        """Issue should accept any issue type."""
        issue = Issue(title="Test", issue_type=issue_type)

        assert issue.issue_type == issue_type

    def test_type_defaults_to_other(self):
        """Issue type should default to OTHER."""
        issue = Issue(title="Test")

        assert issue.issue_type == IssueType.OTHER


class TestIssueMilestoneAssociation:
    """Test milestone relationships."""

    def test_issue_with_milestone(self):
        """Issue should track assigned milestone."""
        issue = Issue(title="Test", milestone="v1.0")

        assert issue.milestone == "v1.0"

    def test_issue_with_no_milestone(self):
        """Issue milestone should default to None."""
        issue = Issue(title="Test")

        assert issue.milestone is None

    def test_issue_milestone_can_be_changed(self):
        """Issue milestone should be mutable."""
        issue = Issue(title="Test", milestone="v1.0")

        issue.milestone = "v2.0"

        assert issue.milestone == "v2.0"

    def test_issue_milestone_can_be_cleared(self):
        """Issue milestone can be set to None."""
        issue = Issue(title="Test", milestone="v1.0")

        issue.milestone = None

        assert issue.milestone is None


class TestIssueAssignee:
    """Test assignee tracking."""

    def test_issue_with_assignee(self):
        """Issue should track assigned user."""
        issue = Issue(title="Test", assignee="alice@example.com")

        assert issue.assignee == "alice@example.com"

    def test_issue_with_no_assignee(self):
        """Assignee should default to None."""
        issue = Issue(title="Test")

        assert issue.assignee is None

    def test_issue_assignee_can_be_changed(self):
        """Issue assignee should be mutable."""
        issue = Issue(title="Test", assignee="alice@example.com")

        issue.assignee = "bob@example.com"

        assert issue.assignee == "bob@example.com"

    def test_track_previous_assignee_on_handoff(self):
        """Issue should track previous assignee for handoff notes."""
        issue = Issue(
            title="Test",
            assignee="alice@example.com",
            previous_assignee="bob@example.com",
            handoff_notes="Handing off to Alice",
            handoff_date=datetime(2024, 1, 15, tzinfo=UTC),
        )

        assert issue.previous_assignee == "bob@example.com"
        assert issue.handoff_notes == "Handing off to Alice"
        assert issue.handoff_date == datetime(2024, 1, 15, tzinfo=UTC)


class TestIssueLabels:
    """Test label tracking."""

    def test_issue_with_labels(self):
        """Issue should track labels."""
        issue = Issue(title="Test", labels=["bug", "urgent", "backend"])

        assert issue.labels == ["bug", "urgent", "backend"]

    def test_issue_with_no_labels(self):
        """Labels should default to empty list."""
        issue = Issue(title="Test")

        assert issue.labels == []

    def test_labels_can_be_modified(self):
        """Issue labels should be mutable."""
        issue = Issue(title="Test", labels=["bug"])

        issue.labels.append("urgent")

        assert "urgent" in issue.labels
        assert len(issue.labels) == 2


class TestIssueEstimates:
    """Test effort estimation."""

    def test_issue_with_estimated_hours(self):
        """Issue should track estimated effort."""
        issue = Issue(title="Test", estimated_hours=8.0)

        assert issue.estimated_hours == 8.0

    def test_issue_with_no_estimate(self):
        """Estimated hours should default to None."""
        issue = Issue(title="Test")

        assert issue.estimated_hours is None

    def test_progress_tracking(self):
        """Issue should track progress percentage."""
        issue = Issue(title="Test", progress_percentage=50.0)

        assert issue.progress_percentage == 50.0

    def test_progress_can_change(self):
        """Progress percentage should be mutable."""
        issue = Issue(title="Test", progress_percentage=25.0)

        issue.progress_percentage = 75.0

        assert issue.progress_percentage == 75.0


class TestIssueDates:
    """Test date field tracking."""

    def test_due_date(self):
        """Issue should track due date."""
        due = datetime(2024, 12, 31, tzinfo=UTC)
        issue = Issue(title="Test", due_date=due)

        assert issue.due_date == due

    def test_actual_start_date(self):
        """Issue should track actual start date."""
        start = datetime(2024, 1, 1, tzinfo=UTC)
        issue = Issue(title="Test", actual_start_date=start)

        assert issue.actual_start_date == start

    def test_actual_end_date(self):
        """Issue should track actual end date."""
        end = datetime(2024, 2, 1, tzinfo=UTC)
        issue = Issue(title="Test", actual_end_date=end)

        assert issue.actual_end_date == end

    def test_completed_date(self):
        """Issue should track completion date from Git."""
        issue = Issue(title="Test", completed_date="2024-02-01T12:00:00Z")

        assert issue.completed_date == "2024-02-01T12:00:00Z"


class TestIssueGitTracking:
    """Test Git integration fields."""

    def test_git_branches(self):
        """Issue should track associated Git branches."""
        issue = Issue(title="Test", git_branches=["feature/test-branch"])

        assert issue.git_branches == ["feature/test-branch"]

    def test_git_commits(self):
        """Issue should track associated Git commits."""
        commits = [{"hash": "abc123", "message": "Fix issue"}]
        issue = Issue(title="Test", git_commits=commits)

        assert issue.git_commits == commits

    def test_branches_empty_by_default(self):
        """Git branches should default to empty list."""
        issue = Issue(title="Test")

        assert issue.git_branches == []

    def test_commits_empty_by_default(self):
        """Git commits should default to empty list."""
        issue = Issue(title="Test")

        assert issue.git_commits == []


class TestIssueRemoteIds:
    """Test remote ID tracking for sync integration."""

    def test_github_issue_stored_in_remote_ids(self):
        """Issue should store GitHub issue ID in remote_ids dict."""
        issue = Issue(title="Test", remote_ids={"github": 42})

        assert issue.remote_ids["github"] == 42

    def test_multiple_remote_ids(self):
        """Issue should support multiple remote system IDs."""
        issue = Issue(title="Test", remote_ids={"github": 42, "gitlab": 123})

        assert issue.remote_ids["github"] == 42
        assert issue.remote_ids["gitlab"] == 123

    def test_github_issue_backwards_compatibility_property(self):
        """Issue should provide github_issue property for backwards compatibility."""
        issue = Issue(title="Test")
        issue.github_issue = 42

        assert issue.github_issue == 42
        assert issue.remote_ids["github"] == 42

    def test_github_issue_setter_validates_positive(self):
        """Setting github_issue should validate positive integer."""
        issue = Issue(title="Test")

        with pytest.raises(ValueError, match="must be a positive integer"):
            issue.github_issue = 0

    def test_github_issue_migration_from_legacy_field(self):
        """Issue should migrate legacy github_issue field to remote_ids."""
        # Note: github_issue is a property, not a constructor parameter
        # It's accessible via property setter/getter for backwards compatibility
        issue = Issue(title="Test")
        issue.github_issue = 42

        assert issue.remote_ids.get("github") == 42
        assert issue.github_issue == 42


class TestIssueComments:
    """Test comment associations."""

    def test_issue_with_comments(self, p8_comment):
        """Issue should accept comments list."""
        issue = Issue(title="Test", comments=[p8_comment])

        assert len(issue.comments) == 1
        assert issue.comments[0].author == "alice"

    def test_multiple_comments(self):
        """Issue should handle multiple comments."""
        comments = [
            Comment(
                id=1,
                issue_id="issue-1",
                author="alice",
                body="First comment",
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
                updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            Comment(
                id=2,
                issue_id="issue-1",
                author="bob",
                body="Reply",
                created_at=datetime(2024, 1, 2, tzinfo=UTC),
                updated_at=datetime(2024, 1, 2, tzinfo=UTC),
            ),
        ]
        issue = Issue(title="Test", comments=comments)

        assert len(issue.comments) == 2
        assert issue.comments[0].author == "alice"
        assert issue.comments[1].author == "bob"

    def test_comments_empty_by_default(self):
        """Comments should default to empty list."""
        issue = Issue(title="Test")

        assert issue.comments == []


class TestIssueDependencies:
    """Test dependency and blocking relationships."""

    def test_depends_on_multiple_issues(self):
        """Issue should track issues it depends on."""
        issue = Issue(title="Feature B", depends_on=["issue-1", "issue-2"])

        assert issue.depends_on == ["issue-1", "issue-2"]

    def test_blocks_multiple_issues(self):
        """Issue should track issues it blocks."""
        issue = Issue(title="Blocker", blocks=["issue-3", "issue-4"])

        assert issue.blocks == ["issue-3", "issue-4"]

    def test_both_depends_and_blocks(self):
        """Issue can both depend on and block other issues."""
        issue = Issue(
            title="Test",
            depends_on=["issue-1"],
            blocks=["issue-2"],
        )

        assert issue.depends_on == ["issue-1"]
        assert issue.blocks == ["issue-2"]

    def test_empty_dependencies_by_default(self):
        """Dependency fields should default to empty lists."""
        issue = Issue(title="Test")

        assert issue.depends_on == []
        assert issue.blocks == []


class TestIssueSerialization:
    """Test Issue serialization for persistence."""

    def test_issue_model_dump(self, p8_complete_issue_data):
        """Issue should serialize to dict."""
        issue = Issue(**p8_complete_issue_data)

        data = issue.model_dump()

        assert isinstance(data, dict)
        assert data["title"] == p8_complete_issue_data["title"]
        assert data["status"] == Status.TODO

    def test_issue_model_dump_by_alias(self, p8_complete_issue_data):
        """Issue should support serialization by_alias."""
        issue = Issue(**p8_complete_issue_data)

        data = issue.model_dump(by_alias=True)

        assert isinstance(data, dict)

    def test_issue_model_dump_exclude_internal_fields(self, p8_complete_issue_data):
        """Issue should exclude internal file_path and sync metadata."""
        issue = Issue(**p8_complete_issue_data)
        issue.file_path = "/some/path"
        issue.github_sync_metadata = {"synced": True}

        data = issue.model_dump()

        # file_path and github_sync_metadata are marked with exclude=True
        # so they shouldn't appear in the dump by default
        assert "file_path" not in data
        assert "github_sync_metadata" not in data
