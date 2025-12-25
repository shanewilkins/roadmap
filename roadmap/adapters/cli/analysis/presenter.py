"""Presenter for critical path analysis output."""

from roadmap.core.services.critical_path_calculator import CriticalPathResult


class CriticalPathPresenter:
    """Formats critical path analysis for CLI display."""

    def format_critical_path(
        self, result: CriticalPathResult, milestone: str | None = None
    ) -> str:
        """Format critical path as ASCII graph with summary.

        Args:
            result: CriticalPathResult from calculator
            milestone: Optional milestone name for context

        Returns:
            Formatted string with dependency graph and summary
        """
        lines = []

        # Title
        title = "🎯 Critical Path Analysis"
        if milestone:
            title += f" - {milestone}"
        lines.append(f"\n{title}")
        lines.append("=" * len(title))
        lines.append("")

        # Dependency graph
        if result.critical_path:
            lines.extend(self._format_dependency_graph(result.critical_path))
        else:
            lines.append("(No critical path - all issues independent)")

        lines.append("")

        # Summary
        lines.extend(self._format_summary(result))

        return "\n".join(lines)

    def _format_dependency_graph(self, critical_path: list) -> list[str]:
        """Format the critical path as an ASCII dependency graph."""
        lines = ["📊 Critical Path (Longest Dependency Chain):", ""]

        for i, node in enumerate(critical_path):
            # Draw the node
            prefix = "  " if i > 0 else ""
            connector = "└─ " if i > 0 else ""

            duration_str = f"{node.duration_hours:.1f}h"
            slack_str = (
                f"(slack: {node.slack_time:.1f}h)" if node.slack_time > 0 else ""
            )

            line = f"{prefix}{connector}{node.issue_id}: {node.issue_title[:40]:<40} [{duration_str:>6}] {slack_str}"
            lines.append(line)

            # Add vertical connector if not last
            if i < len(critical_path) - 1:
                lines.append("  │")

        return lines

    def _format_summary(self, result: CriticalPathResult) -> list[str]:
        """Format the summary section."""
        lines = ["📈 Summary", "─" * 50]

        # Duration and count
        lines.append(f"Total Duration:      {result.total_duration:.1f} hours")
        if result.total_duration >= 8:
            business_days = result.total_duration / 8.0
            lines.append(f"                    ~{business_days:.1f} business days")

        lines.append(f"Critical Issues:     {len(result.critical_issue_ids)}")

        # Risk assessment
        risk_level = self._assess_risk(result)
        lines.append(f"Risk Level:          {risk_level}")

        # Top blockers
        if result.blocking_issues:
            blockers = [
                (issue_id, len(blocked))
                for issue_id, blocked in result.blocking_issues.items()
                if len(blocked) > 0
            ]
            blockers.sort(key=lambda x: x[1], reverse=True)

            if blockers:
                lines.append("")
                lines.append("🔴 Top Blockers (most dependent issues):")
                for issue_id, count in blockers[:3]:
                    lines.append(
                        f"  • {issue_id} blocks {count} issue{'s' if count != 1 else ''}"
                    )

        # Project end date
        if result.project_end_date:
            date_str = result.project_end_date.strftime("%b %d, %Y")
            lines.append(f"Estimated Complete:  {date_str}")

        return lines

    def _assess_risk(self, result: CriticalPathResult) -> str:
        """Assess risk level based on critical path metrics."""
        if not result.critical_issue_ids:
            return "🟢 LOW (no critical path)"

        # Calculate risk based on slack time and duration
        avg_slack = (
            sum(n.slack_time for n in result.critical_path) / len(result.critical_path)
            if result.critical_path
            else 0
        )

        # Heuristic: if average slack is low relative to duration, risk is high
        if avg_slack < 4:  # Less than half a business day
            return "🔴 HIGH (minimal slack time)"
        elif avg_slack < 12:  # Less than 1.5 business days
            return "🟡 MEDIUM (some slack available)"
        else:
            return "🟢 LOW (adequate slack time)"
