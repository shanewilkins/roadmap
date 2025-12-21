"""Sync report data model and formatting."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from roadmap.common.console import get_console

console = get_console()


@dataclass
class IssueChange:
    """Represents changes to a single issue during sync."""

    issue_id: str
    title: str
    local_changes: dict[str, Any] = field(default_factory=dict)
    github_changes: dict[str, Any] = field(default_factory=dict)
    has_conflict: bool = False
    last_sync_time: datetime | None = None

    def get_conflict_description(self) -> str:
        """Get human-readable conflict description."""
        if not self.has_conflict:
            return ""

        local_desc = ", ".join(f"{k}: {v}" for k, v in self.local_changes.items())
        github_desc = ", ".join(f"{k}: {v}" for k, v in self.github_changes.items())
        return f"Local ({local_desc}) vs GitHub ({github_desc})"

    def get_change_description(self) -> str:
        """Get human-readable change description."""
        if self.local_changes and self.github_changes:
            return f"Local: {self.local_changes} | GitHub: {self.github_changes}"
        elif self.local_changes:
            return f"Local: {self.local_changes}"
        elif self.github_changes:
            return f"GitHub: {self.github_changes}"
        return "No changes"


@dataclass
class SyncReport:
    """Complete sync operation report."""

    total_issues: int = 0
    issues_up_to_date: int = 0
    issues_updated: int = 0
    conflicts_detected: int = 0
    changes: list[IssueChange] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    error: str | None = None

    def display_brief(self) -> None:
        """Display brief sync summary."""
        if self.error:
            console.print(f"❌ Sync failed: {self.error}", style="bold red")
            return

        console.print("\n📊 Sync Report", style="bold cyan")
        console.print(f"   Total issues: {self.total_issues}")
        console.print(f"   Up-to-date: {self.issues_up_to_date}")
        console.print(f"   Updated: {self.issues_updated}")

        if self.conflicts_detected > 0:
            console.print(
                f"   ⚠️  Conflicts: {self.conflicts_detected}",
                style="bold yellow",
            )
            console.print(
                "       Use --force-local or --force-github to resolve",
                style="dim yellow",
            )

    def display_verbose(self) -> None:
        """Display detailed sync information."""
        if self.error:
            console.print(f"❌ Sync failed: {self.error}", style="bold red")
            return

        console.print("\n📊 Detailed Sync Report", style="bold cyan")
        console.print(f"   Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"   Total issues: {self.total_issues}")
        console.print(f"   Up-to-date: {self.issues_up_to_date}")
        console.print(f"   Updated: {self.issues_updated}")

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
        return self.issues_updated > 0 or self.conflicts_detected > 0
