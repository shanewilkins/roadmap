"""Data visualization module for roadmap CLI application.

This module provides comprehensive visualization capabilities for generating
charts and graphs from issue/milestone data for stakeholder reporting.
"""

import warnings
from datetime import datetime, timedelta
from pathlib import Path

# Suppress matplotlib warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

import matplotlib.dates as mdates

# Visualization libraries
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from matplotlib.patches import Circle
from plotly.subplots import make_subplots

from .data_utils import DataAnalyzer, DataFrameAdapter

# Core data structures
from .models import Issue, Milestone, Status

# Set style configurations
plt.style.use("default")
sns.set_palette("husl")


class VisualizationError(Exception):
    """Exception raised for visualization generation errors."""

    pass


class ChartGenerator:
    """Generates various types of charts for roadmap data visualization."""

    def __init__(self, artifacts_dir: Path):
        """Initialize chart generator.

        Args:
            artifacts_dir: Directory to save generated charts
        """
        self.artifacts_dir = artifacts_dir
        self.charts_dir = artifacts_dir / "charts"
        self.charts_dir.mkdir(exist_ok=True)

        # Configure matplotlib for better output
        plt.rcParams["figure.figsize"] = (12, 8)
        plt.rcParams["figure.dpi"] = 100
        plt.rcParams["savefig.dpi"] = 300
        plt.rcParams["savefig.bbox"] = "tight"
        plt.rcParams["font.size"] = 10

    def generate_status_distribution_chart(
        self, issues: list[Issue], chart_type: str = "pie", output_format: str = "png"
    ) -> Path:
        """Generate status distribution chart.

        Args:
            issues: List of issues to analyze
            chart_type: Type of chart ('pie', 'bar', 'donut')
            output_format: Output format ('png', 'html', 'svg')

        Returns:
            Path to generated chart file
        """
        if not issues:
            raise VisualizationError("No issues provided for status distribution chart")

        # Count issues by status
        status_counts = {}
        for issue in issues:
            status = issue.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Define colors for each status
        status_colors = {
            "todo": "#94a3b8",  # Slate gray
            "in-progress": "#f59e0b",  # Amber
            "blocked": "#ef4444",  # Red
            "review": "#3b82f6",  # Blue
            "done": "#10b981",  # Green
        }

        filename = f"status_distribution_{chart_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if output_format == "html":
            # Create interactive Plotly chart
            labels = list(status_counts.keys())
            values = list(status_counts.values())
            colors = [status_colors.get(label, "#6b7280") for label in labels]

            if chart_type == "pie" or chart_type == "donut":
                hole = 0.3 if chart_type == "donut" else 0
                fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=labels,
                            values=values,
                            hole=hole,
                            marker_colors=colors,
                            textinfo="label+percent+value",
                            textposition="auto",
                            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
                        )
                    ]
                )

                fig.update_layout(
                    title={
                        "text": f"Issue Status Distribution ({sum(values)} total issues)",
                        "x": 0.5,
                        "xanchor": "center",
                        "font": {"size": 16},
                    },
                    font={"family": "Arial, sans-serif", "size": 12},
                    showlegend=True,
                    legend={"orientation": "v", "yanchor": "middle", "y": 0.5},
                    margin={"t": 60, "b": 40, "l": 40, "r": 40},
                    height=500,
                )

            else:  # bar chart
                fig = go.Figure(
                    data=[
                        go.Bar(
                            x=labels,
                            y=values,
                            marker_color=colors,
                            text=values,
                            textposition="auto",
                            hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",
                        )
                    ]
                )

                fig.update_layout(
                    title={
                        "text": f"Issue Status Distribution ({sum(values)} total issues)",
                        "x": 0.5,
                        "xanchor": "center",
                        "font": {"size": 16},
                    },
                    xaxis_title="Status",
                    yaxis_title="Number of Issues",
                    font={"family": "Arial, sans-serif", "size": 12},
                    margin={"t": 60, "b": 40, "l": 40, "r": 40},
                    height=500,
                )

            output_path = self.charts_dir / f"{filename}.html"

            # Create properly structured HTML with validation compliance
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Status Distribution Chart - Roadmap CLI</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f8f9fa;
        }}
        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .chart-title {{
            color: #333;
            margin-bottom: 20px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="chart-container">
        <h1 class="chart-title">Issue Status Distribution</h1>
        <div id="chart-content">
            {fig.to_html(include_plotlyjs=True, div_id="chart-content", config={'displayModeBar': False})}
        </div>
    </div>
</body>
</html>"""

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

        else:
            # Create matplotlib chart
            fig, ax = plt.subplots(figsize=(10, 8))

            labels = list(status_counts.keys())
            values = list(status_counts.values())
            colors = [status_colors.get(label, "#6b7280") for label in labels]

            if chart_type == "pie" or chart_type == "donut":
                pie_result = ax.pie(
                    values,
                    labels=labels,
                    autopct="%1.1f%%",
                    colors=colors,
                    startangle=90,
                    pctdistance=0.85 if chart_type == "donut" else 0.6,
                )

                # Extract autotexts from pie result
                if len(pie_result) >= 3:
                    wedges, texts, autotexts = pie_result  # type: ignore[misc]
                else:
                    wedges, texts = pie_result[:2]  # type: ignore[misc]
                    autotexts = []

                if chart_type == "donut":
                    # Add center circle for donut
                    centre_circle = Circle((0, 0), 0.50, fc="white")
                    ax.add_artist(centre_circle)

                # Enhance text appearance
                for autotext in autotexts:
                    autotext.set_color("white")
                    autotext.set_fontweight("bold")
                    autotext.set_fontsize(10)

            else:  # bar chart
                bars = ax.bar(labels, values, color=colors)
                ax.set_xlabel("Status", fontsize=12)
                ax.set_ylabel("Number of Issues", fontsize=12)

                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{int(height)}",
                        ha="center",
                        va="bottom",
                        fontweight="bold",
                    )

            plt.title(
                f"Issue Status Distribution ({sum(values)} total issues)",
                fontsize=14,
                fontweight="bold",
                pad=20,
            )
            plt.tight_layout()

            # Save based on format
            if output_format == "svg":
                output_path = self.charts_dir / f"{filename}.svg"
                plt.savefig(output_path, format="svg", bbox_inches="tight")
            else:
                output_path = self.charts_dir / f"{filename}.png"
                plt.savefig(output_path, format="png", bbox_inches="tight")

            plt.close()

        return output_path

    def generate_burndown_chart(
        self,
        issues: list[Issue],
        milestone_name: str | None = None,
        output_format: str = "png",
    ) -> Path:
        """Generate burndown chart showing work remaining over time.

        Args:
            issues: List of issues to analyze
            milestone_name: Optional milestone name to filter issues
            output_format: Output format ('png', 'html', 'svg')

        Returns:
            Path to generated chart file
        """
        # Filter issues if milestone specified
        if milestone_name:
            issues = [i for i in issues if i.milestone == milestone_name]

        if not issues:
            raise VisualizationError("No issues found for burndown chart")

        # Convert to DataFrame for easier analysis
        issues_df = DataFrameAdapter.issues_to_dataframe(issues)

        # Calculate burndown data
        burndown_data = self._calculate_burndown_data(issues_df)

        filename = "burndown_chart"
        if milestone_name:
            filename += f"_{milestone_name.replace(' ', '_')}"
        filename += f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if output_format == "html":
            # Interactive Plotly burndown chart
            fig = go.Figure()

            # Ideal burndown line
            if burndown_data["dates"]:
                fig.add_trace(
                    go.Scatter(
                        x=burndown_data["dates"],
                        y=burndown_data["ideal_remaining"],
                        mode="lines",
                        name="Ideal Burndown",
                        line={"color": "gray", "dash": "dash", "width": 2},
                        hovertemplate="Date: %{x}<br>Ideal Remaining: %{y} issues<extra></extra>",
                    )
                )

                # Actual burndown line
                fig.add_trace(
                    go.Scatter(
                        x=burndown_data["dates"],
                        y=burndown_data["actual_remaining"],
                        mode="lines+markers",
                        name="Actual Burndown",
                        line={"color": "#3b82f6", "width": 3},
                        marker={"size": 6},
                        hovertemplate="Date: %{x}<br>Actual Remaining: %{y} issues<extra></extra>",
                    )
                )

            fig.update_layout(
                title={
                    "text": "Burndown Chart"
                    + (f" - {milestone_name}" if milestone_name else ""),
                    "x": 0.5,
                    "xanchor": "center",
                    "font": {"size": 16},
                },
                xaxis_title="Date",
                yaxis_title="Issues Remaining",
                font={"family": "Arial, sans-serif", "size": 12},
                hovermode="x unified",
                margin={"t": 60, "b": 40, "l": 60, "r": 40},
                height=500,
            )

            output_path = self.charts_dir / f"{filename}.html"
            fig.write_html(str(output_path))

        else:
            # Matplotlib burndown chart
            fig, ax = plt.subplots(figsize=(12, 8))

            if burndown_data["dates"]:
                # Plot ideal burndown
                ax.plot(
                    burndown_data["dates"],
                    burndown_data["ideal_remaining"],
                    "gray",
                    linestyle="--",
                    linewidth=2,
                    label="Ideal Burndown",
                    alpha=0.7,
                )

                # Plot actual burndown
                ax.plot(
                    burndown_data["dates"],
                    burndown_data["actual_remaining"],
                    "#3b82f6",
                    linewidth=3,
                    marker="o",
                    markersize=4,
                    label="Actual Burndown",
                )

                # Format dates on x-axis
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
                ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
                fig.autofmt_xdate()

            ax.set_xlabel("Date", fontsize=12)
            ax.set_ylabel("Issues Remaining", fontsize=12)
            ax.set_title(
                "Burndown Chart" + (f" - {milestone_name}" if milestone_name else ""),
                fontsize=14,
                fontweight="bold",
            )
            ax.legend()
            ax.grid(True, alpha=0.3)

            plt.tight_layout()

            if output_format == "svg":
                output_path = self.charts_dir / f"{filename}.svg"
                plt.savefig(output_path, format="svg", bbox_inches="tight")
            else:
                output_path = self.charts_dir / f"{filename}.png"
                plt.savefig(output_path, format="png", bbox_inches="tight")

            plt.close()

        return output_path

    def generate_velocity_chart(
        self, issues: list[Issue], period: str = "W", output_format: str = "png"
    ) -> Path:
        """Generate velocity trend chart.

        Args:
            issues: List of issues to analyze
            period: Time period for grouping ('D', 'W', 'M')
            output_format: Output format ('png', 'html', 'svg')

        Returns:
            Path to generated chart file
        """
        if not issues:
            raise VisualizationError("No issues provided for velocity chart")

        # Convert to DataFrame and analyze velocity
        issues_df = DataFrameAdapter.issues_to_dataframe(issues)
        velocity_df = DataAnalyzer.analyze_velocity_trends(issues_df, period)

        # Convert Period objects to strings for plotting
        velocity_df = velocity_df.copy()
        velocity_df["completion_period"] = velocity_df["completion_period"].astype(str)

        if velocity_df.empty:
            raise VisualizationError("No velocity data available")

        filename = f"velocity_chart_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if output_format == "html":
            # Interactive Plotly velocity chart
            fig = make_subplots(
                rows=2,
                cols=1,
                subplot_titles=("Issues Completed", "Velocity Score"),
                vertical_spacing=0.12,
            )

            # Issues completed over time
            fig.add_trace(
                go.Scatter(
                    x=velocity_df["completion_period"],
                    y=velocity_df["issues_completed"],
                    mode="lines+markers",
                    name="Issues Completed",
                    line={"color": "#10b981", "width": 3},
                    marker={"size": 6},
                    hovertemplate="Period: %{x}<br>Issues: %{y}<extra></extra>",
                ),
                row=1,
                col=1,
            )

            # Velocity score over time
            fig.add_trace(
                go.Scatter(
                    x=velocity_df["completion_period"],
                    y=velocity_df["velocity_score"],
                    mode="lines+markers",
                    name="Velocity Score",
                    line={"color": "#3b82f6", "width": 3},
                    marker={"size": 6},
                    hovertemplate="Period: %{x}<br>Score: %{y:.1f}<extra></extra>",
                ),
                row=2,
                col=1,
            )

            fig.update_layout(
                title={
                    "text": f"Team Velocity Trends ({period} periods)",
                    "x": 0.5,
                    "xanchor": "center",
                    "font": {"size": 16},
                },
                font={"family": "Arial, sans-serif", "size": 12},
                showlegend=False,
                height=600,
                margin={"t": 80, "b": 40, "l": 60, "r": 40},
            )

            fig.update_xaxes(title_text="Period", row=2, col=1)
            fig.update_yaxes(title_text="Issues", row=1, col=1)
            fig.update_yaxes(title_text="Score", row=2, col=1)

            output_path = self.charts_dir / f"{filename}.html"
            fig.write_html(str(output_path))

        else:
            # Matplotlib velocity chart
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

            # Convert periods to strings for matplotlib
            periods_str = [str(p) for p in velocity_df["completion_period"]]

            # Issues completed
            ax1.plot(
                periods_str,
                velocity_df["issues_completed"],
                "o-",
                color="#10b981",
                linewidth=2,
                markersize=6,
            )
            ax1.set_ylabel("Issues Completed", fontsize=12)
            ax1.set_title(
                f"Team Velocity Trends ({period} periods)",
                fontsize=14,
                fontweight="bold",
            )
            ax1.grid(True, alpha=0.3)

            # Velocity score
            ax2.plot(
                periods_str,
                velocity_df["velocity_score"],
                "o-",
                color="#3b82f6",
                linewidth=2,
                markersize=6,
            )
            ax2.set_xlabel("Period", fontsize=12)
            ax2.set_ylabel("Velocity Score", fontsize=12)
            ax2.grid(True, alpha=0.3)

            # Format dates
            for ax in [ax1, ax2]:
                # Rotate x-axis labels for better readability
                ax.tick_params(axis="x", rotation=45)

            plt.tight_layout()

            if output_format == "svg":
                output_path = self.charts_dir / f"{filename}.svg"
                plt.savefig(output_path, format="svg", bbox_inches="tight")
            else:
                output_path = self.charts_dir / f"{filename}.png"
                plt.savefig(output_path, format="png", bbox_inches="tight")

            plt.close()

        return output_path

    def generate_milestone_progress_chart(
        self,
        milestones: list[Milestone],
        issues: list[Issue],
        output_format: str = "png",
    ) -> Path:
        """Generate milestone progress overview chart.

        Args:
            milestones: List of milestones to visualize
            issues: List of issues for calculating progress
            output_format: Output format ('png', 'html', 'svg')

        Returns:
            Path to generated chart file
        """
        if not milestones:
            raise VisualizationError("No milestones provided for progress chart")

        # Calculate progress for each milestone
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

        filename = f"milestone_progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if output_format == "html":
            # Interactive Plotly progress chart
            names = [m["name"] for m in milestone_data]
            progress_values = [m["progress"] for m in milestone_data]

            # Color based on progress
            colors = []
            for p in progress_values:
                if p >= 100:
                    colors.append("#10b981")  # Green for complete
                elif p >= 75:
                    colors.append("#3b82f6")  # Blue for near complete
                elif p >= 50:
                    colors.append("#f59e0b")  # Yellow for in progress
                elif p >= 25:
                    colors.append("#f97316")  # Orange for started
                else:
                    colors.append("#ef4444")  # Red for not started

            fig = go.Figure(
                data=[
                    go.Bar(
                        y=names,
                        x=progress_values,
                        orientation="h",
                        marker_color=colors,
                        text=[f"{p:.1f}%" for p in progress_values],
                        textposition="auto",
                        hovertemplate="<b>%{y}</b><br>Progress: %{x:.1f}%<br>"
                        + "Completed: %{customdata[0]}/{customdata[1]} issues<extra></extra>",
                        customdata=[
                            [m["completed"], m["total"]] for m in milestone_data
                        ],
                    )
                ]
            )

            fig.update_layout(
                title={
                    "text": "Milestone Progress Overview",
                    "x": 0.5,
                    "xanchor": "center",
                    "font": {"size": 16},
                },
                xaxis_title="Progress (%)",
                yaxis_title="Milestone",
                font={"family": "Arial, sans-serif", "size": 12},
                margin={"t": 60, "b": 40, "l": 150, "r": 40},
                height=max(400, len(names) * 50),
            )

            fig.update_xaxes(range=[0, 100])

            output_path = self.charts_dir / f"{filename}.html"
            fig.write_html(str(output_path))

        else:
            # Matplotlib progress chart
            fig, ax = plt.subplots(figsize=(12, max(6, len(milestone_data) * 0.8)))

            names = [m["name"] for m in milestone_data]
            progress_values = [m["progress"] for m in milestone_data]

            # Color based on progress
            colors = []
            for p in progress_values:
                if p >= 100:
                    colors.append("#10b981")  # Green
                elif p >= 75:
                    colors.append("#3b82f6")  # Blue
                elif p >= 50:
                    colors.append("#f59e0b")  # Yellow
                elif p >= 25:
                    colors.append("#f97316")  # Orange
                else:
                    colors.append("#ef4444")  # Red

            bars = ax.barh(names, progress_values, color=colors)

            # Add progress labels
            for _i, (bar, data) in enumerate(zip(bars, milestone_data, strict=False)):
                width = bar.get_width()
                ax.text(
                    width + 1,
                    bar.get_y() + bar.get_height() / 2,
                    f"{data['progress']:.1f}% ({data['completed']}/{data['total']})",
                    ha="left",
                    va="center",
                    fontsize=10,
                )

            ax.set_xlabel("Progress (%)", fontsize=12)
            ax.set_ylabel("Milestone", fontsize=12)
            ax.set_title("Milestone Progress Overview", fontsize=14, fontweight="bold")
            ax.set_xlim(0, 110)
            ax.grid(True, axis="x", alpha=0.3)

            plt.tight_layout()

            if output_format == "svg":
                output_path = self.charts_dir / f"{filename}.svg"
                plt.savefig(output_path, format="svg", bbox_inches="tight")
            else:
                output_path = self.charts_dir / f"{filename}.png"
                plt.savefig(output_path, format="png", bbox_inches="tight")

            plt.close()

        return output_path

    def generate_team_workload_chart(
        self, issues: list[Issue], output_format: str = "png"
    ) -> Path:
        """Generate team workload distribution chart.

        Args:
            issues: List of issues to analyze
            output_format: Output format ('png', 'html', 'svg')

        Returns:
            Path to generated chart file
        """
        if not issues:
            raise VisualizationError("No issues provided for team workload chart")

        # Analyze team performance
        issues_df = DataFrameAdapter.issues_to_dataframe(issues)
        team_df = DataAnalyzer.analyze_team_performance(issues_df)

        if team_df.empty:
            raise VisualizationError("No team workload data available")

        filename = f"team_workload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if output_format == "html":
            # Interactive Plotly team workload chart
            fig = make_subplots(
                rows=1,
                cols=2,
                subplot_titles=("Issues by Assignee", "Estimated Hours by Assignee"),
                specs=[[{"type": "bar"}, {"type": "bar"}]],
            )

            # Issues count
            fig.add_trace(
                go.Bar(
                    x=team_df.index,
                    y=team_df["total_issues"],
                    name="Total Issues",
                    marker_color="#3b82f6",
                    text=team_df["total_issues"],
                    textposition="auto",
                    hovertemplate="<b>%{x}</b><br>Issues: %{y}<extra></extra>",
                ),
                row=1,
                col=1,
            )

            # Estimated hours
            fig.add_trace(
                go.Bar(
                    x=team_df.index,
                    y=team_df["total_estimated_hours"],
                    name="Estimated Hours",
                    marker_color="#10b981",
                    text=[f"{h:.1f}h" for h in team_df["total_estimated_hours"]],
                    textposition="auto",
                    hovertemplate="<b>%{x}</b><br>Hours: %{y:.1f}<extra></extra>",
                ),
                row=1,
                col=2,
            )

            fig.update_layout(
                title={
                    "text": "Team Workload Distribution",
                    "x": 0.5,
                    "xanchor": "center",
                    "font": {"size": 16},
                },
                font={"family": "Arial, sans-serif", "size": 12},
                showlegend=False,
                height=500,
                margin={"t": 80, "b": 40, "l": 60, "r": 40},
            )

            fig.update_xaxes(title_text="Team Member", row=1, col=1)
            fig.update_xaxes(title_text="Team Member", row=1, col=2)
            fig.update_yaxes(title_text="Issues", row=1, col=1)
            fig.update_yaxes(title_text="Hours", row=1, col=2)

            output_path = self.charts_dir / f"{filename}.html"
            fig.write_html(str(output_path))

        else:
            # Matplotlib team workload chart
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

            # Issues count
            bars1 = ax1.bar(team_df.index, team_df["total_issues"], color="#3b82f6")
            ax1.set_xlabel("Team Member", fontsize=12)
            ax1.set_ylabel("Number of Issues", fontsize=12)
            ax1.set_title("Issues by Assignee", fontsize=12, fontweight="bold")

            # Add value labels
            for bar in bars1:
                height = bar.get_height()
                ax1.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{int(height)}",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                )

            # Estimated hours
            bars2 = ax2.bar(
                team_df.index, team_df["total_estimated_hours"], color="#10b981"
            )
            ax2.set_xlabel("Team Member", fontsize=12)
            ax2.set_ylabel("Estimated Hours", fontsize=12)
            ax2.set_title("Estimated Hours by Assignee", fontsize=12, fontweight="bold")

            # Add value labels
            for bar in bars2:
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{height:.1f}h",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                )

            # Rotate x-axis labels if needed
            for ax in [ax1, ax2]:
                ax.tick_params(axis="x", rotation=45)

            plt.suptitle("Team Workload Distribution", fontsize=14, fontweight="bold")
            plt.tight_layout()

            if output_format == "svg":
                output_path = self.charts_dir / f"{filename}.svg"
                plt.savefig(output_path, format="svg", bbox_inches="tight")
            else:
                output_path = self.charts_dir / f"{filename}.png"
                plt.savefig(output_path, format="png", bbox_inches="tight")

            plt.close()

        return output_path

    def _calculate_burndown_data(self, issues_df: pd.DataFrame) -> dict[str, list]:
        """Calculate burndown chart data."""
        # Filter completed issues
        completed_issues = issues_df[issues_df["is_completed"]].copy()

        if completed_issues.empty:
            return {"dates": [], "ideal_remaining": [], "actual_remaining": []}

        # Get date range
        start_date = completed_issues["created"].min().date()
        end_date = datetime.now().date()

        # Generate daily date range
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)

        total_issues = len(issues_df)

        # Calculate ideal burndown (linear)
        ideal_remaining = []
        for i, date in enumerate(dates):
            remaining = total_issues - (i * total_issues / len(dates))
            ideal_remaining.append(max(0, remaining))

        # Calculate actual burndown
        actual_remaining = []
        for date in dates:
            completed_by_date = len(
                completed_issues[completed_issues["updated"].dt.date <= date]
            )
            remaining = total_issues - completed_by_date
            actual_remaining.append(max(0, remaining))

        return {
            "dates": dates,
            "ideal_remaining": ideal_remaining,
            "actual_remaining": actual_remaining,
        }

    def generate_milestone_progression_chart(
        self, milestone_data: list[dict], output_dir: Path
    ) -> Path:
        """Generate milestone progression flow chart with issue type distribution.

        Args:
            milestone_data: List of milestone statistics dictionaries
            output_dir: Directory to save the chart

        Returns:
            Path to the generated chart file
        """
        try:
            # Create figure with subplots
            fig = make_subplots(
                rows=2,
                cols=1,
                subplot_titles=(
                    "Milestone Progression & Completion",
                    "Issue Type Distribution by Milestone",
                ),
                vertical_spacing=0.12,
                row_heights=[0.6, 0.4],
            )

            # Extract data for progression chart
            milestones = [m["milestone"] for m in milestone_data]
            completions = [m["completion"] for m in milestone_data]
            bugs = [m["bugs"] for m in milestone_data]
            features = [m["features"] for m in milestone_data]
            tasks = [m["tasks"] for m in milestone_data]

            # Progress line chart
            fig.add_trace(
                go.Scatter(
                    x=milestones,
                    y=completions,
                    mode="lines+markers",
                    name="Completion %",
                    line={"color": "#2E7D32", "width": 3},
                    marker={"size": 8, "color": "#4CAF50"},
                    hovertemplate="<b>%{x}</b><br>Completion: %{y:.1f}%<extra></extra>",
                ),
                row=1,
                col=1,
            )

            # Issue type stacked bar chart
            fig.add_trace(
                go.Bar(
                    x=milestones,
                    y=bugs,
                    name="Bugs",
                    marker_color="#F44336",
                    hovertemplate="<b>%{x}</b><br>Bugs: %{y}<extra></extra>",
                ),
                row=2,
                col=1,
            )

            fig.add_trace(
                go.Bar(
                    x=milestones,
                    y=features,
                    name="Features",
                    marker_color="#2196F3",
                    hovertemplate="<b>%{x}</b><br>Features: %{y}<extra></extra>",
                ),
                row=2,
                col=1,
            )

            fig.add_trace(
                go.Bar(
                    x=milestones,
                    y=tasks,
                    name="Tasks",
                    marker_color="#FF9800",
                    hovertemplate="<b>%{x}</b><br>Tasks: %{y}<extra></extra>",
                ),
                row=2,
                col=1,
            )

            # Update layout
            fig.update_layout(
                title={
                    "text": "Project Milestone Progression & Technical Debt Analysis",
                    "x": 0.5,
                    "xanchor": "center",
                    "font": {"size": 16, "color": "#1F2937"},
                },
                height=700,
                showlegend=True,
                legend={
                    "orientation": "h",
                    "yanchor": "bottom",
                    "y": 1.02,
                    "xanchor": "right",
                    "x": 1,
                },
                plot_bgcolor="white",
                paper_bgcolor="white",
            )

            # Update x-axes
            fig.update_xaxes(title_text="Milestones", row=1, col=1)
            fig.update_xaxes(title_text="Milestones", row=2, col=1)

            # Update y-axes
            fig.update_yaxes(
                title_text="Completion Percentage", row=1, col=1, range=[0, 100]
            )
            fig.update_yaxes(title_text="Number of Issues", row=2, col=1)

            # Make the second subplot a stacked bar chart
            fig.update_layout(barmode="stack")

            # Save chart
            output_path = output_dir / "milestone_progression_chart.html"
            fig.write_html(
                str(output_path), config={"displayModeBar": True, "responsive": True}
            )

            return output_path

        except Exception as e:
            raise VisualizationError(
                f"Failed to generate milestone progression chart: {e}"
            )

    def generate_project_health_dashboard(
        self, health_data: dict, output_dir: Path
    ) -> Path:
        """Generate comprehensive project health dashboard.

        Args:
            health_data: Dictionary containing project health metrics
            output_dir: Directory to save the dashboard

        Returns:
            Path to the generated dashboard file
        """
        try:
            # Create subplots for health metrics
            fig = make_subplots(
                rows=2,
                cols=2,
                subplot_titles=(
                    "Project Completion Rate",
                    "Technical Debt Ratio",
                    "Team Workload Distribution",
                    "Issue Type Breakdown",
                ),
                specs=[
                    [{"type": "indicator"}, {"type": "indicator"}],
                    [{"type": "bar"}, {"type": "pie"}],
                ],
                vertical_spacing=0.15,
                horizontal_spacing=0.15,
            )

            # Project completion gauge
            completion_rate = health_data["completion_rate"]
            completion_color = (
                "green"
                if completion_rate > 70
                else "orange"
                if completion_rate > 40
                else "red"
            )

            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=completion_rate,
                    title={"text": "Overall Progress"},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": [None, 100]},
                        "bar": {"color": completion_color},
                        "steps": [
                            {"range": [0, 40], "color": "lightgray"},
                            {"range": [40, 70], "color": "yellow"},
                            {"range": [70, 100], "color": "lightgreen"},
                        ],
                        "threshold": {
                            "line": {"color": "red", "width": 4},
                            "thickness": 0.75,
                            "value": 90,
                        },
                    },
                ),
                row=1,
                col=1,
            )

            # Technical debt gauge
            tech_debt = health_data["tech_debt_ratio"]
            debt_color = (
                "red" if tech_debt > 40 else "orange" if tech_debt > 20 else "green"
            )

            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=tech_debt,
                    title={"text": "Tech Debt (% Open Bugs)"},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": [None, 100]},
                        "bar": {"color": debt_color},
                        "steps": [
                            {"range": [0, 20], "color": "lightgreen"},
                            {"range": [20, 40], "color": "yellow"},
                            {"range": [40, 100], "color": "lightcoral"},
                        ],
                        "threshold": {
                            "line": {"color": "darkred", "width": 4},
                            "thickness": 0.75,
                            "value": 50,
                        },
                    },
                ),
                row=1,
                col=2,
            )

            # Team workload bar chart
            workload_data = health_data["team_workload"]
            if workload_data:
                members = list(workload_data.keys())
                loads = list(workload_data.values())

                fig.add_trace(
                    go.Bar(
                        x=members,
                        y=loads,
                        name="Open Issues",
                        marker_color="#3F51B5",
                        hovertemplate="<b>%{x}</b><br>Open Issues: %{y}<extra></extra>",
                    ),
                    row=2,
                    col=1,
                )

            # Issue type pie chart
            issue_types = health_data["issue_types"]
            if issue_types:
                labels = list(issue_types.keys())
                values = list(issue_types.values())
                colors = ["#F44336", "#2196F3", "#FF9800", "#4CAF50", "#9C27B0"]

                fig.add_trace(
                    go.Pie(
                        labels=labels,
                        values=values,
                        name="Issue Types",
                        marker_colors=colors[: len(labels)],
                        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
                    ),
                    row=2,
                    col=2,
                )

            # Update layout
            fig.update_layout(
                title={
                    "text": "Project Health Dashboard",
                    "x": 0.5,
                    "xanchor": "center",
                    "font": {"size": 18, "color": "#1F2937"},
                },
                height=800,
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
            )

            # Update axes for bar chart
            fig.update_xaxes(title_text="Team Members", row=2, col=1)
            fig.update_yaxes(title_text="Open Issues", row=2, col=1)

            # Save dashboard
            output_path = output_dir / "project_health_dashboard.html"
            fig.write_html(
                str(output_path), config={"displayModeBar": True, "responsive": True}
            )

            return output_path

        except Exception as e:
            raise VisualizationError(
                f"Failed to generate project health dashboard: {e}"
            )


class DashboardGenerator:
    """Generates comprehensive HTML dashboards for stakeholder reporting."""

    def __init__(self, artifacts_dir: Path):
        """Initialize dashboard generator.

        Args:
            artifacts_dir: Directory to save generated dashboards
        """
        self.artifacts_dir = artifacts_dir
        self.dashboards_dir = artifacts_dir / "dashboards"
        self.dashboards_dir.mkdir(exist_ok=True)
        self.chart_generator = ChartGenerator(artifacts_dir)

    def generate_stakeholder_dashboard(
        self, issues: list[Issue], milestones: list[Milestone]
    ) -> Path:
        """Generate comprehensive stakeholder dashboard.

        Args:
            issues: List of issues to include
            milestones: List of milestones to include

        Returns:
            Path to generated dashboard HTML file
        """
        if not issues:
            raise VisualizationError("No issues provided for dashboard")

        # Generate individual charts as HTML components
        status_chart = self.chart_generator.generate_status_distribution_chart(
            issues, chart_type="donut", output_format="html"
        )

        milestone_chart = self.chart_generator.generate_milestone_progress_chart(
            milestones, issues, output_format="html"
        )

        velocity_chart = self.chart_generator.generate_velocity_chart(
            issues, period="W", output_format="html"
        )

        team_chart = self.chart_generator.generate_team_workload_chart(
            issues, output_format="html"
        )

        # Calculate summary metrics
        total_issues = len(issues)
        completed_issues = len([i for i in issues if i.status == Status.DONE])
        in_progress_issues = len([i for i in issues if i.status == Status.IN_PROGRESS])
        blocked_issues = len([i for i in issues if i.status == Status.BLOCKED])
        completion_rate = (
            (completed_issues / total_issues * 100) if total_issues > 0 else 0
        )

        # Calculate milestone metrics
        active_milestones = len([m for m in milestones if m.status.value == "active"])
        len([m for m in milestones if m.status.value == "completed"])

        # Read chart HTML content
        def read_chart_content(chart_path: Path) -> str:
            with open(chart_path, encoding="utf-8") as f:
                content = f.read()
                # Extract the plotly div content
                start = content.find("<div>")
                end = content.find("</body>")
                if start != -1 and end != -1:
                    return content[start:end]
                return content

        status_content = read_chart_content(status_chart)
        milestone_content = read_chart_content(milestone_chart)
        velocity_content = read_chart_content(velocity_chart)
        team_content = read_chart_content(team_chart)

        # Generate dashboard HTML
        dashboard_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Roadmap Dashboard - Stakeholder Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8fafc;
            color: #334155;
            line-height: 1.6;
        }}
        .dashboard-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            text-align: center;
        }}
        .dashboard-title {{
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0 0 0.5rem 0;
        }}
        .dashboard-subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
            margin: 0;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .metric-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #3b82f6;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            color: #1e293b;
            margin: 0;
        }}
        .metric-label {{
            color: #64748b;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin: 0.5rem 0 0 0;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }}
        .chart-container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .chart-title {{
            padding: 1.5rem;
            border-bottom: 1px solid #e2e8f0;
            font-size: 1.25rem;
            font-weight: 600;
            color: #1e293b;
            margin: 0;
        }}
        .chart-content {{
            padding: 1rem;
        }}
        .footer {{
            text-align: center;
            margin-top: 3rem;
            padding: 2rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .footer-text {{
            color: #64748b;
            font-size: 0.875rem;
        }}
        .status-indicators {{
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin-top: 1rem;
        }}
        .status-indicator {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: #f1f5f9;
            border-radius: 6px;
            font-size: 0.875rem;
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}
        .status-done {{ background-color: #10b981; }}
        .status-progress {{ background-color: #f59e0b; }}
        .status-blocked {{ background-color: #ef4444; }}
    </style>
</head>
<body>
    <div class="dashboard-header">
        <h1 class="dashboard-title">📊 Roadmap Dashboard</h1>
        <p class="dashboard-subtitle">Stakeholder Report - Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-value">{total_issues}</div>
            <div class="metric-label">Total Issues</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{completion_rate:.1f}%</div>
            <div class="metric-label">Completion Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{active_milestones}</div>
            <div class="metric-label">Active Milestones</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{in_progress_issues}</div>
            <div class="metric-label">In Progress</div>
        </div>
    </div>

    <div class="status-indicators">
        <div class="status-indicator">
            <div class="status-dot status-done"></div>
            <span>{completed_issues} Completed</span>
        </div>
        <div class="status-indicator">
            <div class="status-dot status-progress"></div>
            <span>{in_progress_issues} In Progress</span>
        </div>
        <div class="status-indicator">
            <div class="status-dot status-blocked"></div>
            <span>{blocked_issues} Blocked</span>
        </div>
    </div>

    <div class="charts-grid">
        <div class="chart-container">
            <h3 class="chart-title">📋 Issue Status Distribution</h3>
            <div class="chart-content">
                {status_content}
            </div>
        </div>

        <div class="chart-container">
            <h3 class="chart-title">🎯 Milestone Progress</h3>
            <div class="chart-content">
                {milestone_content}
            </div>
        </div>

        <div class="chart-container">
            <h3 class="chart-title">📈 Team Velocity</h3>
            <div class="chart-content">
                {velocity_content}
            </div>
        </div>

        <div class="chart-container">
            <h3 class="chart-title">👥 Team Workload</h3>
            <div class="chart-content">
                {team_content}
            </div>
        </div>
    </div>

    <div class="footer">
        <p class="footer-text">
            This dashboard provides a comprehensive overview of project progress and team performance.<br>
            For detailed analysis and raw data, please refer to the exported analytics reports.
        </p>
        <p class="footer-text">
            Generated by Roadmap CLI • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>
        """

        # Save dashboard
        filename = (
            f"stakeholder_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        output_path = self.dashboards_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(dashboard_html)

        # Clean up temporary chart files
        for chart_file in [status_chart, milestone_chart, velocity_chart, team_chart]:
            try:
                chart_file.unlink()
            except:
                pass

        return output_path
