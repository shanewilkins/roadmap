"""Presentation for the canonical daily planning summary."""

import click

from roadmap.application.contracts import DailySummary
from roadmap.domain.aggregates import Issue


class DailySummaryPresenter:
    def render(self, data: DailySummary) -> None:
        milestone = data.milestone.milestone
        due = f" (due {milestone.due_at.value:%Y-%m-%d})" if milestone.due_at else ""
        click.echo(f"Daily Summary - {data.current_user}")
        click.echo(f"Upcoming Milestone: {milestone.name}{due}")
        if not data.has_issues:
            click.echo(f"No issues assigned to you in {milestone.name}")
            return
        self._section("In Progress", data.in_progress)
        self._section("Overdue", data.overdue)
        self._section("Blocked", data.blocked)
        self._section("Up Next (High Priority)", data.up_next)
        self._section("Completed Today", data.completed_today)
        click.echo(
            "Summary: "
            f"{len(data.in_progress)} in progress; "
            f"{len(data.overdue)} overdue; "
            f"{len(data.blocked)} blocked; "
            f"{len(data.completed_today)} completed today"
        )

    @staticmethod
    def _section(title: str, issues: tuple[Issue, ...]) -> None:
        click.echo(f"\n{title}")
        if not issues:
            click.echo("  None")
            return
        for issue in issues:
            click.echo(
                f"  {issue.id}: {issue.title} "
                f"[{issue.priority.value}; {issue.status.value}]"
            )
