"""Interactive conflict resolution with rich UI for user choices."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from structlog import get_logger

if TYPE_CHECKING:
    from roadmap.core.domain.issue import Issue
    from roadmap.core.services.sync.sync_conflict_resolver import Conflict

logger = get_logger(__name__)


class InteractiveConflictResolver:
    """Provides interactive UI for resolving sync conflicts."""

    def __init__(self, console: Console | None = None):
        """Initialize interactive conflict resolver.

        Args:
            console: Rich console for output (creates new one if None)
        """
        self.console = console or Console()

    def resolve_interactively(
        self,
        conflicts: list[Conflict],
        issues_by_id: dict[str, Issue],
    ) -> dict[str, dict[str, str]]:
        """Resolve conflicts interactively with user input.

        Args:
            conflicts: List of conflicts to resolve
            issues_by_id: Dictionary mapping issue IDs to Issue objects

        Returns:
            Dictionary of resolutions: {issue_id: {field: resolution_strategy}}
        """
        if not conflicts:
            return {}

        self.console.print(
            "\n[bold cyan]═══ Interactive Conflict Resolution ═══[/bold cyan]\n"
        )
        self.console.print(
            f"Found [yellow]{len(conflicts)}[/yellow] conflicts that need your attention.\n"
        )

        resolutions = {}

        for i, conflict in enumerate(conflicts, 1):
            self.console.print(
                f"[bold]Conflict {i}/{len(conflicts)}[/bold]",
                style="cyan",
            )
            self.console.print()

            issue = issues_by_id.get(conflict.issue_id)
            if not issue:
                logger.warning(
                    "conflict_issue_not_found",
                    issue_id=conflict.issue_id,
                    action="resolve_conflict",
                )
                continue

            # Display conflict context
            self._display_conflict_context(conflict, issue)

            # Resolve each conflicting field
            issue_resolutions = {}
            for field in conflict.field_names:
                resolution = self._resolve_field_conflict(conflict, field)
                issue_resolutions[field] = resolution

            resolutions[conflict.issue_id] = issue_resolutions

            # Show confirmation
            if i < len(conflicts):
                if not Confirm.ask(
                    "\n[dim]Continue to next conflict?[/dim]", default=True
                ):
                    self.console.print(
                        "[yellow]Remaining conflicts will use default strategy[/yellow]"
                    )
                    break
                self.console.print("\n" + "─" * 60 + "\n")

        return resolutions

    def _display_conflict_context(self, conflict: Conflict, issue: Issue) -> None:
        """Display context information about the conflict."""
        # Issue header
        header_text = Text()
        header_text.append(f"#{issue.id}", style="bold cyan")
        header_text.append(" • ", style="dim")
        header_text.append(issue.title, style="bold white")

        self.console.print(Panel(header_text, border_style="cyan", padding=(0, 2)))
        self.console.print()

        # Conflict summary
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column(style="dim", width=20)
        summary_table.add_column()

        summary_table.add_row("Conflicting Fields:", ", ".join(conflict.field_names))

        if conflict.local_updated and conflict.remote_updated:
            summary_table.add_row(
                "Last Updated:",
                f"Local: {conflict.local_updated.isoformat()[:10]} | Remote: {conflict.remote_updated.isoformat()[:10]}",
            )

        self.console.print(summary_table)
        self.console.print()

    def _resolve_field_conflict(self, conflict: Conflict, field: str) -> str:
        """Resolve a single field conflict interactively.

        Args:
            conflict: Conflict object
            field: Field name to resolve

        Returns:
            Resolution strategy chosen by user
        """
        # Get values from the conflict's local and remote issues
        local_value = getattr(conflict.local_issue, field, "[dim]<none>[/dim]")
        remote_value = conflict.remote_issue.get(field, "[dim]<none>[/dim]")
        base_value = None  # Base value not currently stored in Conflict

        self.console.print(f"[bold yellow]Field:[/bold yellow] [cyan]{field}[/cyan]")
        self.console.print()

        # Show values side-by-side
        comparison_table = Table(show_header=True, box=None, padding=(0, 2))
        comparison_table.add_column("Version", style="bold", width=12)
        comparison_table.add_column("Value", width=50)

        if base_value is not None:
            comparison_table.add_row(
                "[dim]Baseline[/dim]",
                self._format_value_for_display(base_value, field),
            )

        comparison_table.add_row(
            "[blue]Local[/blue]",
            self._format_value_for_display(local_value, field),
        )

        comparison_table.add_row(
            "[magenta]Remote[/magenta]",
            self._format_value_for_display(remote_value, field),
        )

        self.console.print(comparison_table)
        self.console.print()

        # Present resolution options
        options = {
            "1": ("LOCAL", "Keep local version (blue)"),
            "2": ("REMOTE", "Keep remote version (magenta)"),
            "3": ("VIEW_DIFF", "View detailed diff"),
        }

        # Add merge option for mergeable fields
        if self._is_mergeable_field(field, local_value, remote_value):
            options["4"] = ("MERGE", "Attempt automatic merge")
            options["5"] = ("MANUAL", "Edit manually")
        else:
            options["4"] = ("MANUAL", "Edit manually")

        options["s"] = ("SKIP", "Skip (keep flagged for review)")

        # Display options
        self.console.print("[bold]Choose resolution:[/bold]")
        for key, (strategy, description) in options.items():
            self.console.print(f"  {key}. {description}")
        self.console.print()

        # Get user choice
        while True:
            choice = Prompt.ask(
                "Your choice",
                choices=list(options.keys()),
                default="1",
            )

            strategy = options[choice][0]

            if strategy == "VIEW_DIFF":
                self._show_detailed_diff(field, local_value, remote_value, base_value)
                continue  # Ask again after showing diff

            if strategy == "MANUAL":
                manual_value = self._get_manual_edit(field, local_value, remote_value)
                if manual_value is not None:
                    # Store manual value for later application
                    return f"MANUAL:{manual_value}"
                continue  # Ask again if manual edit cancelled

            return strategy

    def _format_value_for_display(self, value: Any, field: str) -> str:
        """Format a value for display in comparison table.

        Args:
            value: Value to format
            field: Field name (for context)

        Returns:
            Formatted string for display
        """
        if value is None or value == "[dim]<none>[/dim]":
            return "[dim]<none>[/dim]"

        # Truncate long values
        value_str = str(value)
        if len(value_str) > 47:
            return value_str[:44] + "..."

        return value_str

    def _is_mergeable_field(
        self, field: str, local_value: Any, remote_value: Any
    ) -> bool:
        """Check if a field can be automatically merged.

        Args:
            field: Field name
            local_value: Local value
            remote_value: Remote value

        Returns:
            True if field is mergeable
        """
        # Lists can often be merged
        if isinstance(local_value, list) and isinstance(remote_value, list):
            return True

        # Tags, labels, etc. can be merged
        mergeable_fields = {"tags", "labels", "assignees", "dependencies"}
        if field in mergeable_fields:
            return True

        return False

    def _show_detailed_diff(
        self,
        field: str,
        local_value: Any,
        remote_value: Any,
        base_value: Any,
    ) -> None:
        """Show detailed diff of values.

        Args:
            field: Field name
            local_value: Local value
            remote_value: Remote value
            base_value: Baseline value
        """
        self.console.print("\n[bold]Detailed Diff:[/bold]\n")

        # Format values for syntax highlighting
        local_formatted = self._format_value_for_diff(local_value)
        remote_formatted = self._format_value_for_diff(remote_value)

        # Display side-by-side if possible
        diff_table = Table.grid(padding=(0, 2))
        diff_table.add_column("Local", style="blue", width=40)
        diff_table.add_column("Remote", style="magenta", width=40)

        if base_value is not None:
            base_formatted = self._format_value_for_diff(base_value)
            self.console.print(
                Panel(
                    Syntax(base_formatted, "yaml", theme="monokai", line_numbers=False),
                    title="[dim]Baseline[/dim]",
                    border_style="dim",
                )
            )
            self.console.print()

        # Show local and remote side by side
        self.console.print("[bold blue]Local:[/bold blue]")
        self.console.print(
            Syntax(local_formatted, "yaml", theme="monokai", line_numbers=False)
        )
        self.console.print()

        self.console.print("[bold magenta]Remote:[/bold magenta]")
        self.console.print(
            Syntax(remote_formatted, "yaml", theme="monokai", line_numbers=False)
        )
        self.console.print()

    def _format_value_for_diff(self, value: Any) -> str:
        """Format value for syntax-highlighted diff display."""
        if isinstance(value, (list, dict)):
            import json

            return json.dumps(value, indent=2)
        return str(value)

    def _get_manual_edit(
        self,
        field: str,
        local_value: Any,
        remote_value: Any,
    ) -> str | None:
        """Get manual edit from user.

        Args:
            field: Field name
            local_value: Local value
            remote_value: Remote value

        Returns:
            Manually edited value or None if cancelled
        """
        self.console.print("\n[bold]Manual Edit:[/bold]")
        self.console.print(
            "[dim]Enter the value you want to use, or press Ctrl+C to cancel[/dim]\n"
        )

        self.console.print(f"Current local:  {local_value}")
        self.console.print(f"Current remote: {remote_value}")
        self.console.print()

        try:
            manual_value = Prompt.ask(f"Enter value for '{field}'")
            if manual_value:
                return manual_value
            return None
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Manual edit cancelled[/yellow]")
            return None

    def show_conflict_summary(
        self,
        conflicts: list[Conflict],
        resolutions: dict[str, dict[str, str]],
    ) -> None:
        """Show summary of conflict resolutions.

        Args:
            conflicts: Original list of conflicts
            resolutions: Resolutions chosen by user
        """
        self.console.print(
            "\n[bold cyan]═══ Conflict Resolution Summary ═══[/bold cyan]\n"
        )

        summary_table = Table(show_header=True)
        summary_table.add_column("Issue ID", style="cyan", width=15)
        summary_table.add_column("Field", width=20)
        summary_table.add_column("Resolution", width=20)

        for conflict in conflicts:
            issue_resolutions = resolutions.get(conflict.issue_id, {})
            for field in conflict.field_names:
                resolution = issue_resolutions.get(field, "SKIP")
                resolution_display = resolution
                if resolution.startswith("MANUAL:"):
                    resolution_display = "MANUAL"

                summary_table.add_row(
                    conflict.issue_id[:12],
                    field,
                    resolution_display,
                )

        self.console.print(summary_table)
        self.console.print()

        # Show statistics
        total_fields = sum(len(c.field_names) for c in conflicts)
        resolved_fields = sum(
            len([r for r in resolutions.get(c.issue_id, {}).values() if r != "SKIP"])
            for c in conflicts
        )

        self.console.print(
            f"[green]Resolved:[/green] {resolved_fields}/{total_fields} fields"
        )
        self.console.print()
