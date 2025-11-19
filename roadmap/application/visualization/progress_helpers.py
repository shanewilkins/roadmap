"""
Helper functions for milestone progress chart generation.
"""

from datetime import datetime
from typing import Any

from roadmap.domain import Issue, Milestone, Status


class MilestoneProgressCalculator:
    """Calculate milestone progress statistics."""

    @staticmethod
    def calculate_milestone_data(
        milestones: list[Milestone], issues: list[Issue]
    ) -> list[dict[str, Any]]:
        """
        Calculate progress data for each milestone.

        Returns:
            List of milestone data dictionaries with name, progress, completed, total, due_date
        """
        milestone_data = []
        for milestone in milestones:
            milestone_issues = [i for i in issues if i.milestone == milestone.name]
            total_issues = len(milestone_issues)
            completed_issues = len(
                [i for i in milestone_issues if i.status == Status.DONE]
            )
            progress = (
                (completed_issues / total_issues * 100) if total_issues > 0 else 0
            )

            milestone_data.append(
                {
                    "name": milestone.name,
                    "progress": progress,
                    "completed": completed_issues,
                    "total": total_issues,
                    "due_date": milestone.due_date,
                }
            )

        # Sort by due date
        milestone_data.sort(key=lambda x: x["due_date"] or datetime.max.date())
        return milestone_data


class ProgressColorMapper:
    """Map progress values to colors."""

    @staticmethod
    def get_progress_color(progress: float) -> str:
        """
        Get color for a given progress percentage.

        Args:
            progress: Progress percentage (0-100)

        Returns:
            Hex color code
        """
        if progress >= 100:
            return "#10b981"  # Green for complete
        elif progress >= 75:
            return "#3b82f6"  # Blue for near complete
        elif progress >= 50:
            return "#f59e0b"  # Yellow for in progress
        elif progress >= 25:
            return "#f97316"  # Orange for started
        else:
            return "#ef4444"  # Red for not started

    @classmethod
    def get_colors_for_progress_list(cls, progress_values: list[float]) -> list[str]:
        """Get list of colors for a list of progress values."""
        return [cls.get_progress_color(p) for p in progress_values]
