"""Visualization service - handles chart and dashboard generation.

The VisualizationService orchestrates visualization operations:
- Chart generation (status, burndown, velocity, workload, milestone, etc.)
- Dashboard creation for stakeholders
- Chart persistence and management

Service depends on:
- ChartGenerator from visualization package
- DashboardGenerator from visualization package
- Issue and Milestone domain models
"""

from pathlib import Path
from typing import Any

from roadmap.application.visualization import (
    ChartGenerator,
    DashboardGenerator,
)
from roadmap.domain.issue import Issue
from roadmap.domain.milestone import Milestone
from roadmap.infrastructure.storage import StateManager


class VisualizationService:
    """Service for chart and dashboard generation."""

    def __init__(self, db: StateManager, artifacts_dir: Path):
        """Initialize visualization service.

        Args:
            db: State manager for database operations
            artifacts_dir: Directory for chart/dashboard artifacts
        """
        self.db = db
        self.artifacts_dir = artifacts_dir
        self.chart_generator = ChartGenerator(artifacts_dir)
        self.dashboard_generator = DashboardGenerator(artifacts_dir)

    # Chart generation methods

    def generate_status_chart(
        self,
        issues: list[Issue],
        chart_type: str = "pie",
        output_format: str = "png",
    ) -> Path:
        """Generate status distribution chart.

        Args:
            issues: Issues to visualize
            chart_type: Type of chart ('pie', 'bar', 'donut')
            output_format: Output format ('png', 'html', 'svg')

        Returns:
            Path to generated chart
        """
        return self.chart_generator.generate_status_distribution_chart(
            issues, chart_type=chart_type, output_format=output_format
        )

    def generate_burndown_chart(
        self,
        issues: list[Issue],
        milestone_name: str | None = None,
        output_format: str = "png",
    ) -> Path:
        """Generate burndown chart.

        Args:
            issues: Issues to analyze
            milestone_name: Optional milestone filter
            output_format: Output format

        Returns:
            Path to generated chart
        """
        return self.chart_generator.generate_burndown_chart(
            issues, milestone_name=milestone_name, output_format=output_format
        )

    def generate_velocity_chart(
        self, issues: list[Issue], period: str = "W", output_format: str = "png"
    ) -> Path:
        """Generate velocity chart.

        Args:
            issues: Issues to analyze
            period: Period granularity ('D' for daily, 'W' for weekly, 'M' for monthly)
            output_format: Output format

        Returns:
            Path to generated chart
        """
        return self.chart_generator.generate_velocity_chart(
            issues, period=period, output_format=output_format
        )

    def generate_milestone_chart(
        self,
        milestones: list[Milestone],
        issues: list[Issue],
        output_format: str = "png",
    ) -> Path:
        """Generate milestone progress chart.

        Args:
            milestones: Milestones to visualize
            issues: Associated issues for progress calculation
            output_format: Output format

        Returns:
            Path to generated chart
        """
        return self.chart_generator.generate_milestone_progress_chart(
            milestones, issues, output_format=output_format
        )

    def generate_workload_chart(
        self, issues: list[Issue], output_format: str = "png"
    ) -> Path:
        """Generate team workload chart.

        Args:
            issues: Issues with assignee information
            output_format: Output format

        Returns:
            Path to generated chart
        """
        return self.chart_generator.generate_team_workload_chart(
            issues, output_format=output_format
        )

    def generate_milestone_progression_chart(self, milestone_data: list[dict]) -> Path:
        """Generate milestone progression flow chart.

        Args:
            milestone_data: List of milestone statistics dictionaries

        Returns:
            Path to generated chart
        """
        return self.chart_generator.generate_milestone_progression_chart(
            milestone_data, self.artifacts_dir
        )

    def generate_project_health_dashboard(self, health_data: dict) -> Path:
        """Generate project health dashboard.

        Args:
            health_data: Dictionary containing project health metrics

        Returns:
            Path to generated dashboard
        """
        return self.chart_generator.generate_project_health_dashboard(
            health_data, self.artifacts_dir
        )

    # Dashboard generation methods

    def generate_stakeholder_dashboard(
        self, issues: list[Issue], milestones: list[Milestone]
    ) -> Path:
        """Generate comprehensive stakeholder dashboard.

        Args:
            issues: Issues to include
            milestones: Milestones to include

        Returns:
            Path to generated dashboard HTML
        """
        return self.dashboard_generator.generate_stakeholder_dashboard(
            issues, milestones
        )

    # Statistics and analytics

    def get_chart_statistics(self, issues: list[Issue]) -> dict[str, Any]:
        """Get visualization statistics for issues.

        Args:
            issues: Issues to analyze

        Returns:
            Dict with visualization metrics
        """
        from roadmap.domain.issue import Status

        return {
            "total_issues": len(issues),
            "completed": len([i for i in issues if i.status == Status.DONE]),
            "in_progress": len([i for i in issues if i.status == Status.IN_PROGRESS]),
            "blocked": len([i for i in issues if i.status == Status.BLOCKED]),
            "todo": len([i for i in issues if i.status == Status.TODO]),
        }
