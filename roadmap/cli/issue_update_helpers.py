"""
Helper classes for issue update operations.
"""

from roadmap.domain import Priority, Status


class IssueUpdateBuilder:
    """Build update dictionary from CLI parameters."""

    @staticmethod
    def build_updates(
        title: str | None,
        priority: str | None,
        status: str | None,
        assignee: str | None,
        milestone: str | None,
        description: str | None,
        estimate: float | None,
        core,
        console,
    ) -> dict:
        """
        Build update dictionary from provided parameters.

        Returns:
            Dictionary of updates to apply to the issue
        """
        updates = {}

        if title:
            updates["title"] = title
        if priority:
            updates["priority"] = Priority(priority)
        if status:
            updates["status"] = Status(status)
        if assignee is not None:
            assignee_value = IssueUpdateBuilder._resolve_assignee(
                assignee, core, console
            )
            if assignee_value is not False:  # False means validation failed
                updates["assignee"] = assignee_value
        if milestone:
            updates["milestone"] = milestone
        if description:
            updates["description"] = description
        if estimate is not None:
            updates["estimated_hours"] = estimate

        return updates

    @staticmethod
    def _resolve_assignee(assignee: str, core, console):
        """
        Resolve and validate assignee.

        Returns:
            - Resolved assignee string
            - None for unassignment (empty string)
            - False if validation failed
        """
        # Convert empty string to None for proper unassignment
        if assignee == "":
            return None

        # Validate assignee
        is_valid, result = core.validate_assignee(assignee)
        if not is_valid:
            console.print(f"❌ Invalid assignee: {result}", style="bold red")
            return False
        elif result and "Warning:" in result:
            console.print(f"⚠️  {result}", style="bold yellow")
            return assignee
        else:
            canonical_assignee = core.get_canonical_assignee(assignee)
            if canonical_assignee != assignee:
                console.print(
                    f"🔄 Resolved '{assignee}' to '{canonical_assignee}'",
                    style="dim",
                )
            return canonical_assignee


class IssueUpdateDisplay:
    """Display issue update results."""

    @staticmethod
    def show_update_result(updated_issue, updates: dict, reason: str | None, console):
        """Display the results of an issue update."""
        console.print(f"✅ Updated issue: {updated_issue.title}", style="bold green")
        console.print(f"   ID: {updated_issue.id}", style="cyan")

        # Show what was updated
        for field, value in updates.items():
            if field == "estimated_hours":
                display_value = updated_issue.estimated_time_display
                console.print(f"   estimate: {display_value}", style="cyan")
            elif field in [
                "title",
                "priority",
                "status",
                "assignee",
                "milestone",
                "description",
            ]:
                # Format enum values to show just the string value
                display_value = value.value if hasattr(value, "value") else value
                console.print(f"   {field}: {display_value}", style="cyan")

        if reason:
            console.print(f"   reason: {reason}", style="dim")
