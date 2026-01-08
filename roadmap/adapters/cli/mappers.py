"""Mappers for converting between domain models and CLI DTOs.

Mappers handle the conversion logic between domain models (internal representation)
and DTOs (CLI presentation representation). They ensure DTOs don't leak domain
implementation details.
"""

from roadmap.adapters.cli.dtos import CommentDTO, IssueDTO, MilestoneDTO, ProjectDTO
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone
from roadmap.core.domain.project import Project


class IssueMapper:
    """Maps between Issue domain model and IssueDTO."""

    @staticmethod
    def domain_to_dto(issue: Issue) -> IssueDTO:
        """Convert domain Issue to CLI DTO.

        Converts enums to strings and selects only CLI-relevant fields.

        Args:
            issue: Domain model Issue instance

        Returns:
            IssueDTO instance ready for CLI display
        """
        # Convert comments to DTOs
        comments = []
        if hasattr(issue, "comments") and issue.comments:
            comments = [
                CommentDTO(
                    id=comment.id,
                    author=comment.author,
                    body=comment.body,
                    created_at=comment.created_at,
                    updated_at=comment.updated_at,
                    in_reply_to=comment.in_reply_to,
                )
                for comment in issue.comments
            ]

        return IssueDTO(
            id=issue.id,
            title=issue.title,
            headline=issue.headline or "",
            priority=issue.priority.value,  # Convert enum to string
            status=issue.status.value,  # Convert enum to string
            issue_type=issue.issue_type.value,  # Convert enum to string
            assignee=issue.assignee,
            milestone=issue.milestone,
            due_date=issue.due_date,
            estimated_hours=issue.estimated_hours,
            actual_end_date=issue.actual_end_date,
            progress_percentage=issue.progress_percentage,
            created=issue.created,
            updated=issue.updated,
            content=issue.content,
            labels=issue.labels.copy() if issue.labels else [],
            github_issue=str(issue.github_issue) if issue.github_issue else None,
            comments=comments,
        )

    @staticmethod
    def dto_to_domain(dto: IssueDTO) -> Issue:
        """Convert CLI DTO to domain Issue.

        Converts string fields back to appropriate enums.

        Args:
            dto: IssueDTO instance from CLI

        Returns:
            Domain model Issue instance
        """
        from roadmap.common.constants import IssueType, Priority, Status

        return Issue(
            id=dto.id,
            title=dto.title,
            headline=dto.headline or "",
            priority=Priority(dto.priority),
            status=Status(dto.status),
            issue_type=IssueType(dto.issue_type),
            assignee=dto.assignee,
            milestone=dto.milestone,
            due_date=dto.due_date,
            estimated_hours=dto.estimated_hours,
            actual_end_date=dto.actual_end_date,
            progress_percentage=dto.progress_percentage,
            content=dto.content or "",
            labels=dto.labels.copy() if dto.labels else [],
            remote_ids=(
                {"github": int(dto.github_issue)}
                if dto.github_issue and dto.github_issue.isdigit()
                else {}
            ),
        )


class MilestoneMapper:
    """Maps between Milestone domain model and MilestoneDTO."""

    @staticmethod
    def domain_to_dto(milestone: Milestone) -> MilestoneDTO:
        """Convert domain Milestone to CLI DTO.

        Args:
            milestone: Domain model Milestone instance

        Returns:
            MilestoneDTO instance ready for CLI display
        """
        return MilestoneDTO(
            id=milestone.name,  # Use name as ID
            name=milestone.name,
            status=milestone.status.value,  # Convert enum to string
            headline=milestone.headline or "",
            due_date=milestone.due_date,
            progress_percentage=milestone.calculated_progress,
            created=milestone.created,
            updated=milestone.updated,
        )

    @staticmethod
    def dto_to_domain(dto: MilestoneDTO) -> Milestone:
        """Convert CLI DTO to domain Milestone.

        Args:
            dto: MilestoneDTO instance from CLI

        Returns:
            Domain model Milestone instance
        """
        from roadmap.common.constants import MilestoneStatus

        return Milestone(
            name=dto.name,
            headline=dto.headline or "",
            status=MilestoneStatus(dto.status),
            due_date=dto.due_date,
            content="",
        )


class ProjectMapper:
    """Maps between Project domain model and ProjectDTO."""

    @staticmethod
    def domain_to_dto(project: Project) -> ProjectDTO:
        """Convert domain Project to CLI DTO.

        Args:
            project: Domain model Project instance

        Returns:
            ProjectDTO instance ready for CLI display
        """
        return ProjectDTO(
            id=project.id,
            name=project.name,
            status=project.status.value,  # Convert enum to string
            headline=project.headline or "",
            owner=project.owner,
            target_end_date=project.target_end_date,
            actual_end_date=project.actual_end_date,
            created=project.created,
            updated=project.updated,
        )

    @staticmethod
    def dto_to_domain(dto: ProjectDTO) -> Project:
        """Convert CLI DTO to domain Project.

        Args:
            dto: ProjectDTO instance from CLI

        Returns:
            Domain model Project instance
        """
        from roadmap.common.constants import ProjectStatus

        return Project(
            id=dto.id,
            name=dto.name,
            headline=dto.headline or "",
            status=ProjectStatus(dto.status),
            content="",
            owner=dto.owner,
            target_end_date=dto.target_end_date,
            actual_end_date=dto.actual_end_date,
        )


__all__ = [
    "IssueMapper",
    "MilestoneMapper",
    "ProjectMapper",
]
