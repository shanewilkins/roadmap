"""Presentation for canonical critical-path results."""

from roadmap.application.contracts import CriticalPathResult


class CriticalPathPresenter:
    def format_critical_path(
        self, result: CriticalPathResult, milestone: str | None = None
    ) -> str:
        title = "Critical Path Analysis"
        if milestone:
            title += f" - {milestone}"
        lines = [title, "", "Critical Path (Longest Dependency Chain):"]
        for index, node in enumerate(result.critical_path):
            connector = " -> " if index else ""
            lines.append(
                f"{connector}{node.issue_id}: {node.issue_title} [{node.duration_hours:.1f}h]"
            )
        lines.extend(
            (
                "",
                f"Total Duration: {result.total_duration:.1f} hours",
                f"Critical Issues: {len(result.critical_issue_ids)}",
            )
        )
        if result.project_end_at:
            lines.append(
                f"Estimated Complete: {result.project_end_at.value.strftime('%b %d, %Y')}"
            )
        return "\n".join(lines)
