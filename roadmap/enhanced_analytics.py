"""Enhanced analytics module with pandas integration for improved performance and capabilities."""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from .core import RoadmapCore
from .data_utils import DataAnalyzer, DataFrameAdapter
from .git_integration import GitIntegration


class EnhancedAnalyzer:
    """Enhanced analytics with pandas-powered performance and advanced capabilities."""

    def __init__(self, roadmap_core: RoadmapCore):
        self.core = roadmap_core
        self.git_integration = GitIntegration()
        self.data_adapter = DataFrameAdapter()
        self.analyzer = DataAnalyzer()

    def get_issues_dataframe(self) -> pd.DataFrame:
        """Get issues as a pandas DataFrame for analysis."""
        issues = self.core.list_issues()
        return self.data_adapter.issues_to_dataframe(issues)

    def get_milestones_dataframe(self) -> pd.DataFrame:
        """Get milestones as a pandas DataFrame for analysis."""
        milestones = self.core.list_milestones()
        issues = self.core.list_issues()
        return self.data_adapter.milestones_to_dataframe(milestones, issues)

    def analyze_completion_trends(
        self, period: str = "W", months: int = 6
    ) -> pd.DataFrame:
        """Analyze issue completion trends over time using pandas.

        Args:
            period: Pandas period string ('D', 'W', 'M', 'Q')
            months: Number of months of history to analyze

        Returns:
            DataFrame with completion trend analysis
        """
        df = self.get_issues_dataframe()

        if df.empty:
            return pd.DataFrame()

        # Filter to completed issues with completion dates
        completed_df = df[
            (df["status"] == "done") & (df["actual_end_date"].notna())
        ].copy()

        if completed_df.empty:
            return pd.DataFrame()

        # Filter to specified time range
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        completed_df = completed_df[completed_df["actual_end_date"] >= cutoff_date]

        if completed_df.empty:
            return pd.DataFrame()

        # Group by time period
        completed_df["completion_period"] = completed_df[
            "actual_end_date"
        ].dt.to_period(period)

        trend_analysis = (
            completed_df.groupby("completion_period")
            .agg(
                {
                    "id": "count",  # Issues completed
                    "estimated_hours": ["sum", "mean"],
                    "actual_duration_hours": ["sum", "mean"],
                    "priority": [
                        lambda x: (x == "critical").sum(),
                        lambda x: (x == "high").sum(),
                        lambda x: (x == "medium").sum(),
                        lambda x: (x == "low").sum(),
                    ],
                    "issue_type": [
                        lambda x: (x == "feature").sum(),
                        lambda x: (x == "bug").sum(),
                        lambda x: (x == "other").sum(),
                    ],
                }
            )
            .round(2)
        )

        # Flatten column names
        trend_analysis.columns = [
            "issues_completed",
            "total_estimated_hours",
            "avg_estimated_hours",
            "total_actual_hours",
            "avg_actual_hours",
            "critical_issues",
            "high_issues",
            "medium_issues",
            "low_issues",
            "features",
            "bugs",
            "other_issues",
        ]

        # Calculate efficiency ratio
        trend_analysis["efficiency_ratio"] = (
            trend_analysis["total_estimated_hours"]
            / trend_analysis["total_actual_hours"].replace(0, 1)
        ).round(2)

        # Calculate velocity score
        trend_analysis["velocity_score"] = (
            trend_analysis["issues_completed"] * 10
            + trend_analysis["total_actual_hours"] * 0.1
            + trend_analysis["critical_issues"] * 5
        ).round(1)

        return trend_analysis.reset_index()

    def analyze_workload_distribution(self) -> pd.DataFrame:
        """Analyze workload distribution across team members."""
        df = self.get_issues_dataframe()

        if df.empty:
            return pd.DataFrame()

        # Group by assignee and analyze workload
        workload_analysis = (
            df.groupby("assignee")
            .agg(
                {
                    "id": "count",  # Total issues
                    "estimated_hours": ["sum", "mean", "count"],
                    "actual_duration_hours": ["sum", "mean"],
                    "status": [
                        lambda x: (x == "todo").sum(),
                        lambda x: (x == "in-progress").sum(),
                        lambda x: (x == "blocked").sum(),
                        lambda x: (x == "review").sum(),
                        lambda x: (x == "done").sum(),
                    ],
                    "priority": [
                        lambda x: (x == "critical").sum(),
                        lambda x: (x == "high").sum(),
                    ],
                    "is_overdue": "sum",
                    "progress_percentage": "mean",
                }
            )
            .round(2)
        )

        # Flatten column names
        workload_analysis.columns = [
            "total_issues",
            "total_estimated_hours",
            "avg_estimated_hours",
            "issues_with_estimates",
            "total_actual_hours",
            "avg_actual_hours",
            "todo_issues",
            "in_progress_issues",
            "blocked_issues",
            "review_issues",
            "done_issues",
            "critical_issues",
            "high_priority_issues",
            "overdue_issues",
            "avg_progress",
        ]

        # Calculate derived metrics
        workload_analysis["completion_rate"] = (
            workload_analysis["done_issues"] / workload_analysis["total_issues"] * 100
        ).round(1)

        workload_analysis["active_issues"] = (
            workload_analysis["todo_issues"] + workload_analysis["in_progress_issues"]
        )

        workload_analysis["workload_score"] = (
            workload_analysis["active_issues"] * 2
            + workload_analysis["critical_issues"] * 3
            + workload_analysis["blocked_issues"] * 1.5
        ).round(1)

        # Sort by workload score descending
        workload_analysis = workload_analysis.sort_values(
            "workload_score", ascending=False
        )

        return workload_analysis.reset_index()

    def analyze_milestone_progress(self) -> pd.DataFrame:
        """Analyze milestone progress and health metrics."""
        milestones_df = self.get_milestones_dataframe()

        if milestones_df.empty:
            return pd.DataFrame()

        # Enhanced milestone analysis using the DataAnalyzer
        health_df = self.analyzer.analyze_milestone_health(milestones_df)

        # Add additional time-based analysis
        current_date = datetime.now()

        health_df["days_until_due"] = (health_df["due_date"] - current_date).dt.days

        health_df["is_overdue"] = health_df["days_until_due"] < 0
        health_df["urgency_level"] = pd.cut(
            health_df["days_until_due"],
            bins=[-float("inf"), 0, 7, 30, float("inf")],
            labels=["Overdue", "Critical", "Soon", "Planned"],
        )

        # Calculate estimated completion date based on current velocity
        health_df["estimated_completion_days"] = (
            health_df["remaining_estimated_hours"] / 8  # Assuming 8 hours per day
        ).round(1)

        health_df["estimated_completion_date"] = current_date + pd.to_timedelta(
            health_df["estimated_completion_days"], unit="D"
        )

        # Risk assessment
        health_df["delivery_risk"] = "Low"
        health_df.loc[
            health_df["estimated_completion_date"] > health_df["due_date"],
            "delivery_risk",
        ] = "High"
        health_df.loc[
            (
                health_df["estimated_completion_date"]
                > health_df["due_date"] - pd.Timedelta(days=7)
            )
            & (health_df["estimated_completion_date"] <= health_df["due_date"]),
            "delivery_risk",
        ] = "Medium"

        return health_df

    def analyze_issue_lifecycle(self) -> pd.DataFrame:
        """Analyze issue lifecycle patterns and bottlenecks."""
        df = self.get_issues_dataframe()

        if df.empty:
            return pd.DataFrame()

        # Calculate time in each status (simplified analysis)
        lifecycle_analysis = (
            df.groupby("status")
            .agg(
                {
                    "id": "count",
                    "estimated_hours": ["sum", "mean"],
                    "actual_duration_hours": ["mean", "count"],
                    "created": lambda x: (datetime.now() - x).dt.days.mean(),
                    "updated": lambda x: (datetime.now() - x).dt.days.mean(),
                    "is_overdue": "sum",
                    "priority": lambda x: (x.isin(["critical", "high"])).sum(),
                }
            )
            .round(2)
        )

        # Flatten column names
        lifecycle_analysis.columns = [
            "issue_count",
            "total_estimated_hours",
            "avg_estimated_hours",
            "avg_actual_hours",
            "issues_with_actual_time",
            "avg_days_since_created",
            "avg_days_since_updated",
            "overdue_count",
            "high_priority_count",
        ]

        # Calculate bottleneck indicators
        total_issues = lifecycle_analysis["issue_count"].sum()
        lifecycle_analysis["percentage_of_total"] = (
            lifecycle_analysis["issue_count"] / total_issues * 100
        ).round(1)

        # Identify potential bottlenecks (statuses with high percentage and old issues)
        lifecycle_analysis["bottleneck_score"] = (
            lifecycle_analysis["percentage_of_total"] * 0.5
            + lifecycle_analysis["avg_days_since_updated"] * 0.3
            + lifecycle_analysis["overdue_count"] * 2
        ).round(1)

        return lifecycle_analysis.reset_index()

    def analyze_velocity_consistency(self, weeks: int = 12) -> dict[str, Any]:
        """Analyze velocity consistency and predictability."""
        velocity_df = self.analyzer.analyze_velocity_trends(
            self.get_issues_dataframe(), period="W"
        )

        if velocity_df.empty:
            return {"error": "No velocity data available", "weeks_analyzed": 0}

        # Limit to specified number of weeks
        velocity_df = velocity_df.tail(weeks)

        # Calculate consistency metrics
        velocity_scores = velocity_df["velocity_score"]
        issues_completed = velocity_df["issues_completed"]

        analysis = {
            "weeks_analyzed": len(velocity_df),
            "avg_velocity_score": velocity_scores.mean().round(2),
            "velocity_std_dev": velocity_scores.std().round(2),
            "velocity_coefficient_of_variation": (
                velocity_scores.std() / velocity_scores.mean()
            ).round(3),
            "avg_issues_per_week": issues_completed.mean().round(1),
            "issues_std_dev": issues_completed.std().round(2),
            "consistency_rating": "Unknown",
            "trend_direction": "Stable",
            "recent_weeks_performance": velocity_df.tail(4)["velocity_score"].tolist(),
        }

        # Determine consistency rating
        cv = analysis["velocity_coefficient_of_variation"]
        if cv < 0.2:
            analysis["consistency_rating"] = "Very Consistent"
        elif cv < 0.4:
            analysis["consistency_rating"] = "Moderately Consistent"
        elif cv < 0.6:
            analysis["consistency_rating"] = "Inconsistent"
        else:
            analysis["consistency_rating"] = "Highly Variable"

        # Determine trend direction
        if len(velocity_scores) >= 4:
            recent_avg = velocity_scores.tail(4).mean()
            earlier_avg = velocity_scores.head(4).mean()

            if recent_avg > earlier_avg * 1.1:
                analysis["trend_direction"] = "Improving"
            elif recent_avg < earlier_avg * 0.9:
                analysis["trend_direction"] = "Declining"
            else:
                analysis["trend_direction"] = "Stable"

        return analysis

    def generate_productivity_insights(self, days: int = 30) -> dict[str, Any]:
        """Generate comprehensive productivity insights using pandas analytics."""
        df = self.get_issues_dataframe()

        if df.empty:
            return {"error": "No issues data available"}

        # Filter to recent data
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_df = df[df["created"] >= cutoff_date]

        insights = {
            "analysis_period_days": days,
            "total_issues": len(df),
            "recent_issues": len(recent_df),
            "summary": {},
            "team_performance": {},
            "bottlenecks": {},
            "recommendations": [],
        }

        # Summary metrics
        insights["summary"] = {
            "completion_rate": (df["status"] == "done").mean() * 100,
            "avg_estimated_hours": df["estimated_hours"].mean(),
            "total_estimated_work": df["estimated_hours"].sum(),
            "overdue_percentage": df["is_overdue"].mean() * 100,
            "blocked_percentage": (df["status"] == "blocked").mean() * 100,
        }

        # Team performance using our enhanced analyzer
        team_perf_df = self.analyze_workload_distribution()
        if not team_perf_df.empty:
            insights["team_performance"] = {
                "top_performer": (
                    team_perf_df.iloc[0]["assignee"] if len(team_perf_df) > 0 else None
                ),
                "most_overloaded": team_perf_df.loc[
                    team_perf_df["workload_score"].idxmax(), "assignee"
                ],
                "highest_completion_rate": team_perf_df.loc[
                    team_perf_df["completion_rate"].idxmax(), "assignee"
                ],
                "team_size": len(team_perf_df),
            }

        # Bottlenecks using DataAnalyzer
        bottlenecks = self.analyzer.find_bottlenecks(df)
        insights["bottlenecks"] = bottlenecks

        # Generate recommendations
        recommendations = []

        if insights["summary"]["blocked_percentage"] > 10:
            recommendations.append(
                "High percentage of blocked issues - review and resolve blockers"
            )

        if insights["summary"]["overdue_percentage"] > 15:
            recommendations.append(
                "Many overdue issues - review time estimates and priorities"
            )

        if insights["summary"]["completion_rate"] < 50:
            recommendations.append(
                "Low completion rate - consider breaking down large issues"
            )

        if "overloaded_assignees" in bottlenecks:
            recommendations.append(
                "Some team members are overloaded - redistribute work"
            )

        insights["recommendations"] = recommendations

        return insights

    def compare_periods(
        self, period1_days: int = 30, period2_days: int = 60
    ) -> dict[str, Any]:
        """Compare productivity metrics between two time periods."""
        df = self.get_issues_dataframe()

        if df.empty:
            return {"error": "No issues data available"}

        current_date = datetime.now()

        # Define periods
        period1_start = current_date - timedelta(days=period1_days)
        period2_start = current_date - timedelta(days=period2_days)
        period2_end = current_date - timedelta(days=period1_days)

        # Filter data for each period
        period1_df = df[
            (df["created"] >= period1_start) & (df["created"] <= current_date)
        ]
        period2_df = df[
            (df["created"] >= period2_start) & (df["created"] <= period2_end)
        ]

        def calculate_period_metrics(period_df: pd.DataFrame) -> dict[str, float]:
            if period_df.empty:
                return {}

            return {
                "total_issues": len(period_df),
                "completed_issues": (period_df["status"] == "done").sum(),
                "completion_rate": (period_df["status"] == "done").mean() * 100,
                "avg_estimated_hours": period_df["estimated_hours"].mean(),
                "overdue_percentage": period_df["is_overdue"].mean() * 100,
                "blocked_percentage": (period_df["status"] == "blocked").mean() * 100,
                "critical_issues": (period_df["priority"] == "critical").sum(),
                "high_priority_issues": (period_df["priority"] == "high").sum(),
            }

        period1_metrics = calculate_period_metrics(period1_df)
        period2_metrics = calculate_period_metrics(period2_df)

        # Calculate changes
        changes = {}
        for key in period1_metrics:
            if key in period2_metrics and period2_metrics[key] != 0:
                change = (
                    (period1_metrics[key] - period2_metrics[key]) / period2_metrics[key]
                ) * 100
                changes[f"{key}_change_percent"] = round(change, 1)

        return {
            "period1_metrics": period1_metrics,
            "period2_metrics": period2_metrics,
            "changes": changes,
            "period1_description": f"Last {period1_days} days",
            "period2_description": f"Previous {period2_days - period1_days} days",
        }
