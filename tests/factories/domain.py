"""Domain object builders with fluent interfaces for test data creation.

Builders provide a clean, readable way to create domain objects for testing.
They support sensible defaults while allowing flexible customization.
"""

from datetime import datetime

from roadmap.common.constants import (
    IssueType,
    MilestoneStatus,
    Priority,
    ProjectStatus,
    RiskLevel,
    Status,
)
from roadmap.core.domain import Comment, Issue, Milestone, Project


class IssueBuilder:
    """Builder for creating Issue objects with fluent interface.

    Example:
        issue = (IssueBuilder()
            .with_title("Fix authentication bug")
            .with_priority(Priority.HIGH)
            .with_status(Status.IN_PROGRESS)
            .with_milestone("v1.0")
            .build())
    """

    def __init__(self):
        """Initialize builder with sensible defaults."""
        self._issue = Issue(
            title="Test Issue",
            priority=Priority.MEDIUM,
            status=Status.TODO,
            issue_type=IssueType.FEATURE,
        )

    def with_id(self, issue_id: str) -> "IssueBuilder":
        """Set the issue ID."""
        self._issue.id = issue_id
        return self

    def with_title(self, title: str) -> "IssueBuilder":
        """Set the issue title."""
        self._issue.title = title
        return self

    def with_headline(self, headline: str) -> "IssueBuilder":
        """Set the issue headline (short summary for list views)."""
        self._issue.headline = headline
        return self

    def with_priority(self, priority: Priority) -> "IssueBuilder":
        """Set the issue priority."""
        self._issue.priority = priority
        return self

    def with_status(self, status: Status) -> "IssueBuilder":
        """Set the issue status."""
        self._issue.status = status
        return self

    def with_type(self, issue_type: IssueType) -> "IssueBuilder":
        """Set the issue type."""
        self._issue.issue_type = issue_type
        return self

    def with_milestone(self, milestone: str | None) -> "IssueBuilder":
        """Set the associated milestone."""
        self._issue.milestone = milestone
        return self

    def with_assignee(self, assignee: str | None) -> "IssueBuilder":
        """Set the assignee."""
        self._issue.assignee = assignee
        return self

    def with_labels(self, labels: list[str]) -> "IssueBuilder":
        """Set the issue labels."""
        self._issue.labels = labels
        return self

    def with_label(self, label: str) -> "IssueBuilder":
        """Add a single label."""
        self._issue.labels.append(label)
        return self

    def with_content(self, content: str) -> "IssueBuilder":
        """Set the issue content (markdown)."""
        self._issue.content = content
        return self

    def with_estimated_hours(self, hours: float | None) -> "IssueBuilder":
        """Set estimated hours to complete."""
        self._issue.estimated_hours = hours
        return self

    def with_github_issue(self, github_issue: str | int | None) -> "IssueBuilder":
        """Link to a GitHub issue."""
        self._issue.github_issue = github_issue
        return self

    def with_remote_ids(self, remote_ids: dict[str, str | int]) -> "IssueBuilder":
        """Set remote IDs for multiple backends."""
        self._issue.remote_ids = remote_ids
        return self

    def with_due_date(self, due_date: datetime | None) -> "IssueBuilder":
        """Set the due date."""
        self._issue.due_date = due_date
        return self

    def with_created_date(self, created: datetime) -> "IssueBuilder":
        """Set the creation date."""
        self._issue.created = created
        return self

    def with_updated_date(self, updated: datetime) -> "IssueBuilder":
        """Set the last updated date."""
        self._issue.updated = updated
        return self

    def with_progress(self, percentage: float) -> "IssueBuilder":
        """Set progress percentage (0-100)."""
        self._issue.progress_percentage = percentage
        return self

    def with_dependencies(self, depends_on: list[str]) -> "IssueBuilder":
        """Set issue dependencies."""
        self._issue.depends_on = depends_on
        return self

    def with_blocked_issues(self, blocks: list[str]) -> "IssueBuilder":
        """Set issues this one blocks."""
        self._issue.blocks = blocks
        return self

    def with_git_branches(self, branches: list[str]) -> "IssueBuilder":
        """Set associated git branches."""
        self._issue.git_branches = branches
        return self

    def build(self) -> Issue:
        """Build and return the Issue object."""
        return self._issue

    def clone(self) -> "IssueBuilder":
        """Create a new builder with current state cloned."""
        new_builder = IssueBuilder()
        new_builder._issue = self._issue.model_copy(deep=True)
        return new_builder


class MilestoneBuilder:
    """Builder for creating Milestone objects with fluent interface.

    Example:
        milestone = (MilestoneBuilder()
            .with_name("v1.0")
            .with_status(MilestoneStatus.IN_PROGRESS)
            .with_due_date(date)
            .build())
    """

    def __init__(self):
        """Initialize builder with sensible defaults."""
        self._milestone = Milestone(
            name="Test Milestone",
            status=MilestoneStatus.OPEN,
        )

    def with_name(self, name: str) -> "MilestoneBuilder":
        """Set the milestone name."""
        self._milestone.name = name
        return self

    def with_headline(self, headline: str) -> "MilestoneBuilder":
        """Set the milestone headline (short summary for list views)."""
        self._milestone.headline = headline
        return self

    def with_description(self, content: str) -> "MilestoneBuilder":
        """Set the milestone description."""
        self._milestone.content = content
        return self

    def with_status(self, status: MilestoneStatus) -> "MilestoneBuilder":
        """Set the milestone status."""
        self._milestone.status = status
        return self

    def with_due_date(self, due_date: datetime | None) -> "MilestoneBuilder":
        """Set the due date."""
        self._milestone.due_date = due_date
        return self

    def with_content(self, content: str) -> "MilestoneBuilder":
        """Set the milestone content (markdown)."""
        self._milestone.content = content
        return self

    def with_github_milestone(self, github_id: int | None) -> "MilestoneBuilder":
        """Link to a GitHub milestone."""
        self._milestone.github_milestone = github_id
        return self

    def with_progress(self, progress: float) -> "MilestoneBuilder":
        """Set calculated progress percentage (0-100)."""
        self._milestone.calculated_progress = progress
        return self

    def with_risk_level(self, risk: RiskLevel) -> "MilestoneBuilder":
        """Set the risk level."""
        self._milestone.risk_level = risk
        return self

    def with_created_date(self, created: datetime) -> "MilestoneBuilder":
        """Set the creation date."""
        self._milestone.created = created
        return self

    def with_updated_date(self, updated: datetime) -> "MilestoneBuilder":
        """Set the last updated date."""
        self._milestone.updated = updated
        return self

    def with_start_date(self, start: datetime | None) -> "MilestoneBuilder":
        """Set the actual start date."""
        self._milestone.actual_start_date = start
        return self

    def with_end_date(self, end: datetime | None) -> "MilestoneBuilder":
        """Set the actual end date."""
        self._milestone.actual_end_date = end
        return self

    def build(self) -> Milestone:
        """Build and return the Milestone object."""
        return self._milestone

    def clone(self) -> "MilestoneBuilder":
        """Create a new builder with current state cloned."""
        new_builder = MilestoneBuilder()
        new_builder._milestone = self._milestone.model_copy(deep=True)
        return new_builder


class ProjectBuilder:
    """Builder for creating Project objects with fluent interface.

    Example:
        project = (ProjectBuilder()
            .with_name("roadmap")
            .with_description("Project management tool")
            .with_status(ProjectStatus.IN_PROGRESS)
            .build())
    """

    def __init__(self):
        """Initialize builder with sensible defaults."""
        self._project = Project(
            name="Test Project",
            content="",
            status=ProjectStatus.PLANNING,
        )

    def with_id(self, project_id: str) -> "ProjectBuilder":
        """Set the project ID."""
        self._project.id = project_id
        return self

    def with_name(self, name: str) -> "ProjectBuilder":
        """Set the project name."""
        self._project.name = name
        return self

    def with_headline(self, headline: str) -> "ProjectBuilder":
        """Set the project headline (short summary for list views)."""
        self._project.headline = headline
        return self

    def with_description(self, description: str) -> "ProjectBuilder":
        """Set the project description."""
        self._project.content = description
        return self

    def with_status(self, status: ProjectStatus) -> "ProjectBuilder":
        """Set the project status."""
        self._project.status = status
        return self

    def with_priority(self, priority: Priority) -> "ProjectBuilder":
        """Set the project priority."""
        self._project.priority = priority
        return self

    def with_owner(self, owner: str | None) -> "ProjectBuilder":
        """Set the project owner."""
        self._project.owner = owner
        return self

    def with_content(self, content: str) -> "ProjectBuilder":
        """Set the project content (markdown)."""
        self._project.content = content
        return self

    def with_milestones(self, milestones: list[str]) -> "ProjectBuilder":
        """Set associated milestone names."""
        self._project.milestones = milestones
        return self

    def with_milestone(self, milestone: str) -> "ProjectBuilder":
        """Add a single milestone."""
        self._project.milestones.append(milestone)
        return self

    def with_estimated_hours(self, hours: float | None) -> "ProjectBuilder":
        """Set estimated hours."""
        self._project.estimated_hours = hours
        return self

    def with_actual_hours(self, hours: float | None) -> "ProjectBuilder":
        """Set actual hours spent."""
        self._project.actual_hours = hours
        return self

    def with_start_date(self, start: datetime | None) -> "ProjectBuilder":
        """Set the start date."""
        self._project.start_date = start
        return self

    def with_target_end_date(self, end: datetime | None) -> "ProjectBuilder":
        """Set the target end date."""
        self._project.target_end_date = end
        return self

    def with_actual_end_date(self, end: datetime | None) -> "ProjectBuilder":
        """Set the actual end date."""
        self._project.actual_end_date = end
        return self

    def with_progress(self, progress: float) -> "ProjectBuilder":
        """Set calculated progress percentage (0-100)."""
        self._project.calculated_progress = progress
        return self

    def with_risk_level(self, risk: RiskLevel) -> "ProjectBuilder":
        """Set the risk level."""
        self._project.risk_level = risk
        return self

    def with_created_date(self, created: datetime) -> "ProjectBuilder":
        """Set the creation date."""
        self._project.created = created
        return self

    def with_updated_date(self, updated: datetime) -> "ProjectBuilder":
        """Set the last updated date."""
        self._project.updated = updated
        return self

    def build(self) -> Project:
        """Build and return the Project object."""
        return self._project

    def clone(self) -> "ProjectBuilder":
        """Create a new builder with current state cloned."""
        new_builder = ProjectBuilder()
        new_builder._project = self._project.model_copy(deep=True)
        return new_builder


class CommentBuilder:
    """Builder for creating Comment objects with fluent interface.

    Example:
        comment = (CommentBuilder()
            .with_issue_id("ISSUE-1")
            .with_author("jane.doe")
            .with_body("This needs more details")
            .build())
    """

    def __init__(self):
        """Initialize builder with sensible defaults."""
        now = datetime.now()
        self._comment = Comment(
            id=1,
            issue_id="TEST-1",
            author="test_user",
            body="Test comment",
            created_at=now,
            updated_at=now,
        )

    def with_id(self, comment_id: int) -> "CommentBuilder":
        """Set the comment ID."""
        self._comment.id = comment_id
        return self

    def with_issue_id(self, issue_id: str) -> "CommentBuilder":
        """Set the issue ID this comment belongs to."""
        self._comment.issue_id = issue_id
        return self

    def with_author(self, author: str) -> "CommentBuilder":
        """Set the comment author."""
        self._comment.author = author
        return self

    def with_body(self, body: str) -> "CommentBuilder":
        """Set the comment body (markdown)."""
        self._comment.body = body
        return self

    def with_created_at(self, created_at: datetime) -> "CommentBuilder":
        """Set the creation timestamp."""
        self._comment.created_at = created_at
        return self

    def with_updated_at(self, updated_at: datetime) -> "CommentBuilder":
        """Set the last update timestamp."""
        self._comment.updated_at = updated_at
        return self

    def with_github_url(self, url: str | None) -> "CommentBuilder":
        """Set the GitHub comment URL."""
        self._comment.github_url = url
        return self

    def with_reply_to(self, comment_id: int | None) -> "CommentBuilder":
        """Set the comment this is replying to (for threading)."""
        self._comment.in_reply_to = comment_id
        return self

    def build(self) -> Comment:
        """Build and return the Comment object."""
        return self._comment

    def clone(self) -> "CommentBuilder":
        """Create a new builder with current state cloned."""
        new_builder = CommentBuilder()
        # Comments are dataclasses, so we can just create a new instance with same values
        new_builder._comment = Comment(
            id=self._comment.id,
            issue_id=self._comment.issue_id,
            author=self._comment.author,
            body=self._comment.body,
            created_at=self._comment.created_at,
            updated_at=self._comment.updated_at,
            github_url=self._comment.github_url,
            in_reply_to=self._comment.in_reply_to,
        )
        return new_builder
