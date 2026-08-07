"""Service for issue update operations.

Consolidates business logic for updating issues, including building update
dictionaries from CLI parameters, resolving assignees, and displaying results.
"""

from roadmap.common.console import get_console
from roadmap.common.errors.exceptions import ValidationError
from roadmap.common.update_constants import DISPLAYABLE_UPDATE_FIELDS
from roadmap.core.domain import Priority, Status


class IssueUpdateService:
    """Service for updating issues with all supporting operations."""

    def __init__(self, core):
        """Initialize service with core instance.

        Args:
            core: RoadmapCore instance
        """
        self.core = core
        self._console = get_console()

    # ─────────────────────────────────────────────────────────────────────────
    # Update Dictionary Building
    # ─────────────────────────────────────────────────────────────────────────

    def build_update_dict(
        self,
        title: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        assignee: str | None = None,
        milestone: str | None = None,
        description: str | None = None,
        estimate: float | None = None,
    ) -> dict:
        """Build update dictionary from provided parameters.

        Validates and normalizes all update fields, resolving assignees and
        converting enum strings to proper types.

        Args:
            title: New title (optional)
            priority: New priority as string (optional)
            status: New status as string (optional)
            assignee: New assignee (optional)
            milestone: New milestone (optional)
            description: New description (optional)
            estimate: New estimate in hours (optional)

        Returns:
            Dictionary of updates ready to apply to an issue
        """
        updates = {}

        if title:
            updates["title"] = title
        if priority:
            updates["priority"] = Priority(priority)
        if status:
            updates["status"] = Status(status)
        if assignee is not None:
            assignee_value = self.resolve_assignee_for_update(assignee)
            updates["assignee"] = assignee_value
        if milestone:
            updates["milestone"] = milestone
        if description:
            updates["description"] = description
        if estimate is not None:
            updates["estimated_hours"] = estimate

        return updates

    # ─────────────────────────────────────────────────────────────────────────
    # Assignee Resolution for Updates
    # ─────────────────────────────────────────────────────────────────────────

    def resolve_assignee_for_update(self, assignee: str):
        """Resolve and validate assignee for update operation.

        Args:
            assignee: Assignee to resolve

        Returns:
            - Resolved assignee string
            - None for unassignment (empty string)
            - False if validation failed
        """
        # Convert empty string to None for proper unassignment
        if assignee == "":
            return None

        # Validate assignee
        is_valid, result = self.core.validate_assignee(assignee)
        if not is_valid:
            raise ValidationError(
                domain_message=f"Assignee validation failed: {result}",
                user_message=f"Invalid assignee: {result}",
            )
        elif result and "Warning:" in result:
            self._console.print(f"⚠️  {result}", style="bold yellow")
            return assignee
        else:
            canonical_assignee = self.core.team.get_canonical_assignee(assignee)
            if canonical_assignee != assignee:
                self._console.print(
                    f"🔄 Resolved '{assignee}' to '{canonical_assignee}'",
                    style="dim",
                )
            return canonical_assignee

    # ─────────────────────────────────────────────────────────────────────────
    # Display Results
    # ─────────────────────────────────────────────────────────────────────────

    def display_update_result(
        self, updated_issue, updates: dict, reason: str | None = None
    ) -> None:
        """Display the results of an issue update.

        Args:
            updated_issue: The updated issue object
            updates: Dictionary of fields that were updated
            reason: Optional reason/comment for the update
        """
        self._console.print(
            f"✅ Updated issue: {updated_issue.title}", style="bold green"
        )
        self._console.print(f"   ID: {updated_issue.id}", style="cyan")

        # Show what was updated
        for field, value in updates.items():
            if field == "estimated_hours":
                display_value = updated_issue.estimated_time_display
                self._console.print(f"   estimate: {display_value}", style="cyan")
            elif field in DISPLAYABLE_UPDATE_FIELDS:
                # Format enum values to show just the string value
                display_value = value.value if hasattr(value, "value") else value
                self._console.print(f"   {field}: {display_value}", style="cyan")

        if reason:
            self._console.print(f"   reason: {reason}", style="dim")
