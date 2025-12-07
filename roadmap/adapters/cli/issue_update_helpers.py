"""
DEPRECATED: Use roadmap.core.services.IssueUpdateService instead.

This module is kept for backward compatibility with tests.
All business logic has been moved to IssueUpdateService.
"""

from roadmap.core.domain import Priority, Status

__all__ = ["IssueUpdateBuilder", "IssueUpdateDisplay"]


class IssueUpdateBuilder:
    """DEPRECATED: Use IssueUpdateService.build_update_dict instead."""

    @staticmethod
    def build_updates(
        title=None,
        priority=None,
        status=None,
        assignee=None,
        milestone=None,
        description=None,
        estimate=None,
        core=None,
        console=None,
    ):
        """DEPRECATED: Use IssueUpdateService.build_update_dict instead."""
        # Keep original implementation for test compatibility
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
            if assignee_value is not False:
                updates["assignee"] = assignee_value
        if milestone:
            updates["milestone"] = milestone
        if description:
            updates["description"] = description
        if estimate is not None:
            updates["estimated_hours"] = estimate
        return updates

    @staticmethod
    def _resolve_assignee(assignee, core, console):
        """DEPRECATED: Use IssueUpdateService.resolve_assignee_for_update instead."""
        if assignee == "":
            return None
        is_valid, result = core.validate_assignee(assignee)
        if not is_valid:
            console.print(f"❌ Invalid assignee: {result}", style="bold red")
            return False
        elif result and "Warning:" in result:
            console.print(f"⚠️  {result}", style="bold yellow")
            return assignee
        else:
            canonical_assignee = core.team.get_canonical_assignee(assignee)
            if canonical_assignee != assignee:
                console.print(
                    f"🔄 Resolved '{assignee}' to '{canonical_assignee}'", style="dim"
                )
            return canonical_assignee


class IssueUpdateDisplay:
    """DEPRECATED: Use IssueUpdateService.display_update_result instead."""

    @staticmethod
    def show_update_result(updated_issue, updates, reason, console):
        """DEPRECATED: Use IssueUpdateService.display_update_result instead."""
        console.print(f"✅ Updated issue: {updated_issue.title}", style="bold green")
        console.print(f"   ID: {updated_issue.id}", style="cyan")
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
                display_value = value.value if hasattr(value, "value") else value
                console.print(f"   {field}: {display_value}", style="cyan")
        if reason:
            console.print(f"   reason: {reason}", style="dim")
