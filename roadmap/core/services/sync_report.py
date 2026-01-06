"""Sync report data model and formatting."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from roadmap.common.console import get_console
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_state import IssueBaseState

console = get_console()


@dataclass
class IssueChange:
    """Represents changes to a single issue during sync - three-way aware.

    Tracks baseline, local, and remote states to provide complete context
    for three-way merge analysis.
    """

    issue_id: str
    title: str

    # Three-way states (optional for backward compatibility)
    baseline_state: IssueBaseState | None = None  # State at last sync
    local_state: Issue | None = None  # Current local state (None if only in remote)
    remote_state: dict[str, Any] | None = (
        None  # Current remote state (None if only in local)
    )

    # Analyzed changes (what changed from baseline)
    local_changes: dict[str, Any] = field(default_factory=dict)  # baseline → local
    remote_changes: dict[str, Any] = field(default_factory=dict)  # baseline → remote

    # Conflict analysis
    conflict_type: str = (
        "no_change"  # "both_changed", "local_only", "remote_only", "no_change"
    )
    has_conflict: bool = False
    flagged_conflicts: dict[str, Any] = field(default_factory=dict)

    # Legacy fields for backward compatibility
    github_changes: dict[str, Any] = field(default_factory=dict)
    last_sync_time: datetime | None = None

    def get_conflict_description(self) -> str:
        """Get human-readable conflict description including three-way context."""
        if not self.has_conflict:
            return ""

        parts = []

        if self.baseline_state:
            parts.append(
                f"Baseline: {self.baseline_state.status if hasattr(self.baseline_state, 'status') else 'unknown'}"
            )

        if self.local_changes:
            local_desc = ", ".join(f"{k}: {v}" for k, v in self.local_changes.items())
            parts.append(f"Local: {local_desc}")

        # Support both new remote_changes and legacy github_changes
        changes_to_show = self.remote_changes or self.github_changes
        if changes_to_show:
            remote_desc = ", ".join(f"{k}: {v}" for k, v in changes_to_show.items())
            label = "Remote" if self.remote_changes else "GitHub"
            parts.append(f"{label}: {remote_desc}")

        return " → ".join(parts)

    def get_change_description(self) -> str:
        """Get human-readable change description."""
        # Support both new and legacy fields
        local_chgs = self.local_changes
        remote_chgs = self.remote_changes or self.github_changes

        if local_chgs and remote_chgs:
            remote_label = "Remote" if self.remote_changes else "GitHub"
            return f"Local: {local_chgs} | {remote_label}: {remote_chgs}"
        elif local_chgs:
            return f"Local: {local_chgs}"
        elif remote_chgs:
            remote_label = "Remote" if self.remote_changes else "GitHub"
            return f"{remote_label}: {remote_chgs}"
        return "No changes"

    def is_three_way_conflict(self) -> bool:
        """Check if both local and remote changed from baseline."""
        return bool(self.local_changes and self.remote_changes)

    def is_local_only_change(self) -> bool:
        """Check if only local changed from baseline."""
        return bool(self.local_changes and not self.remote_changes)

    def is_remote_only_change(self) -> bool:
        """Check if only remote changed from baseline."""
        return bool(self.remote_changes and not self.local_changes)


@dataclass
class SyncReport:
    """Complete sync operation report."""

    # Local items
    total_issues: int = 0
    active_issues: int = 0
    archived_issues: int = 0
    total_milestones: int = 0
    active_milestones: int = 0
    archived_milestones: int = 0

    # Remote items
    remote_total_issues: int = 0
    remote_open_issues: int = 0
    remote_closed_issues: int = 0
    remote_total_milestones: int = 0

    # Sync analysis statistics (three-way merge results)
    issues_up_to_date: int = 0  # No changes in baseline, local, or remote
    issues_needs_push: int = 0  # Local changes that need to be pushed
    issues_needs_pull: int = 0  # Remote changes that need to be pulled
    conflicts_detected: int = 0  # Issues with changes in both directions

    # Sync application statistics (after applying changes)
    issues_pushed: int = 0  # Issues successfully pushed to remote
    issues_pulled: int = 0  # Issues successfully pulled from remote

    changes: list[IssueChange] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    error: str | None = None

    def display_brief(self) -> None:
        """Display brief sync summary with local and remote item breakdown tables."""
        if self.error:
            console.print(f"❌ Sync failed: {self.error}", style="bold red")
            return

        console.print("\n📊 Sync Report", style="bold cyan")

        # Create items tables
        from rich.table import Table

        # Local table - ACTIVE || ARCHIVED || TOTAL format with colors
        local_table = Table(
            title="Local Items",
            show_header=True,
            header_style="bold cyan",
            border_style="cyan",
        )
        local_table.add_column("Type", style="cyan")
        local_table.add_column("Active", justify="right", style="green")
        local_table.add_column("Archived", justify="right", style="yellow")
        local_table.add_column("Total", justify="right", style="bold cyan")

        local_table.add_row(
            "Issues",
            str(self.active_issues),
            str(self.archived_issues),
            str(self.total_issues),
        )
        local_table.add_row(
            "Milestones",
            str(self.active_milestones),
            str(self.archived_milestones),
            str(self.total_milestones),
        )

        # Remote table with colors
        remote_table = Table(
            title="Remote Items",
            show_header=True,
            header_style="bold yellow",
            border_style="yellow",
        )
        remote_table.add_column("Type", style="yellow")
        remote_table.add_column("Open", justify="right", style="green")
        remote_table.add_column("Closed", justify="right", style="red")
        remote_table.add_column("Total", justify="right", style="bold yellow")

        remote_table.add_row(
            "Issues",
            str(self.remote_open_issues),
            str(self.remote_closed_issues),
            str(self.remote_total_issues),
        )
        remote_table.add_row("Milestones", "—", "—", str(self.remote_total_milestones))

        # Display tables side by side using renderables
        from rich.columns import Columns

        columns = Columns([local_table, remote_table], equal=True, expand=True)
        console.print(columns)

        # Sync analysis summary
        console.print("\n📈 Sync Analysis", style="bold cyan")
        console.print(f"   ✓ Up-to-date: {self.issues_up_to_date}", style="green")
        console.print(f"   📤 Needs Push: {self.issues_needs_push}", style="blue")
        console.print(f"   📥 Needs Pull: {self.issues_needs_pull}", style="magenta")

        if self.conflicts_detected > 0:
            console.print(
                f"   ⚠️  Potential Conflicts: {self.conflicts_detected}",
                style="bold red",
            )
            console.print(
                "       Use --force-local or --force-github to resolve",
                style="dim red",
            )
        else:
            console.print(
                f"   ✓ Potential Conflicts: {self.conflicts_detected}", style="green"
            )

        # Applied changes summary (if not dry-run)
        if self.issues_pushed > 0 or self.issues_pulled > 0:
            console.print("\n✨ Applied Changes", style="bold green")
            if self.issues_pushed > 0:
                console.print(f"   Pushed: {self.issues_pushed}", style="green")
            if self.issues_pulled > 0:
                console.print(f"   Pulled: {self.issues_pulled}", style="green")

    def display_verbose(self) -> None:
        """Display detailed sync information."""
        if self.error:
            console.print(f"❌ Sync failed: {self.error}", style="bold red")
            return

        console.print("\n📊 Detailed Sync Report", style="bold cyan")
        console.print(f"   Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        # Create items tables
        from rich.columns import Columns
        from rich.table import Table

        # Local table - ACTIVE || ARCHIVED || TOTAL format
        local_table = Table(
            title="Local Items", show_header=True, header_style="bold cyan"
        )
        local_table.add_column("Type", style="cyan")
        local_table.add_column("Active", justify="right")
        local_table.add_column("Archived", justify="right")
        local_table.add_column("Total", justify="right")

        local_table.add_row(
            "Issues",
            str(self.active_issues),
            str(self.archived_issues),
            str(self.total_issues),
        )
        local_table.add_row(
            "Milestones",
            str(self.active_milestones),
            str(self.archived_milestones),
            str(self.total_milestones),
        )

        # Remote table
        remote_table = Table(
            title="Remote Items", show_header=True, header_style="bold yellow"
        )
        remote_table.add_column("Type", style="yellow")
        remote_table.add_column("Open", justify="right")
        remote_table.add_column("Closed", justify="right")
        remote_table.add_column("Total", justify="right")

        remote_table.add_row(
            "Issues",
            str(self.remote_open_issues),
            str(self.remote_closed_issues),
            str(self.remote_total_issues),
        )
        remote_table.add_row("Milestones", "—", "—", str(self.remote_total_milestones))

        # Display tables side by side
        columns = Columns([local_table, remote_table], equal=True, expand=True)
        console.print(columns)

        console.print(f"   Up-to-date: {self.issues_up_to_date}")
        console.print(f"   Needs Push: {self.issues_needs_push}")
        console.print(f"   Needs Pull: {self.issues_needs_pull}")

        # Show which issues are up-to-date
        if self.issues_up_to_date > 0:
            up_to_date_issues = [
                c for c in self.changes if c.conflict_type == "no_change"
            ]
            if up_to_date_issues:
                console.print("   \n   Up-to-date issues:", style="bold green")
                for change in up_to_date_issues:
                    console.print(
                        f"      • {change.issue_id}: {change.title}", style="dim green"
                    )

        if self.issues_pushed > 0:
            console.print(f"   📤 Pushed: {self.issues_pushed}", style="green")
        if self.issues_pulled > 0:
            console.print(f"   📥 Pulled: {self.issues_pulled}", style="green")

        if self.conflicts_detected > 0:
            console.print(
                f"   ⚠️  Conflicts: {self.conflicts_detected}",
                style="bold yellow",
            )

        if not self.changes:
            console.print("   No changes to display", style="dim")
            return

        console.print("\n   Issue Changes:", style="cyan")
        for change in self.changes:
            if change.has_conflict:
                console.print(
                    f"   🔴 {change.issue_id} - {change.title[:40]}",
                    style="bold red",
                )
                console.print(
                    f"      {change.get_conflict_description()}",
                    style="dim red",
                )
            elif change.local_changes or change.github_changes:
                console.print(
                    f"   🟢 {change.issue_id} - {change.title[:40]}",
                    style="bold green",
                )
                console.print(
                    f"      {change.get_change_description()}",
                    style="dim green",
                )

    def has_conflicts(self) -> bool:
        """Check if there are any conflicts."""
        return self.conflicts_detected > 0

    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return (
            self.issues_needs_push > 0
            or self.issues_needs_pull > 0
            or self.conflicts_detected > 0
        )
