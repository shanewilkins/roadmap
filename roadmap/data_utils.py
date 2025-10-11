"""Data utilities for pandas DataFrame integration and advanced data manipulation."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from .models import Issue, IssueType, Milestone, MilestoneStatus, Priority, Status


class DataFrameAdapter:
    """Adapter for converting roadmap data to pandas DataFrames and handling exports."""

    @staticmethod
    def issues_to_dataframe(issues: List[Issue]) -> pd.DataFrame:
        """Convert a list of Issue objects to a pandas DataFrame.

        Args:
            issues: List of Issue objects

        Returns:
            DataFrame with issue data optimized for analysis and export
        """
        if not issues:
            return pd.DataFrame()

        # Convert issues to dictionary records
        records = []
        for issue in issues:
            record = {
                "id": issue.id,
                "title": issue.title,
                "priority": issue.priority.value,
                "status": issue.status.value,
                "issue_type": issue.issue_type.value,
                "milestone": issue.milestone or "Backlog",
                "assignee": issue.assignee or "Unassigned",
                "created": issue.created,
                "updated": issue.updated,
                "estimated_hours": issue.estimated_hours,
                "estimated_display": issue.estimated_time_display,
                "progress_percentage": issue.progress_percentage,
                "progress_display": issue.progress_display,
                "actual_start_date": issue.actual_start_date,
                "actual_end_date": issue.actual_end_date,
                "actual_duration_hours": issue.actual_duration_hours,
                "is_overdue": issue.is_overdue,
                "is_started": issue.is_started,
                "is_completed": issue.is_completed,
                "has_been_handed_off": issue.has_been_handed_off,
                "previous_assignee": issue.previous_assignee,
                "handoff_date": issue.handoff_date,
                "labels": ",".join(issue.labels) if issue.labels else "",
                "depends_on": ",".join(issue.depends_on) if issue.depends_on else "",
                "blocks": ",".join(issue.blocks) if issue.blocks else "",
                "github_issue": issue.github_issue,
                "git_branches": (
                    ",".join(issue.git_branches) if issue.git_branches else ""
                ),
                "completed_date": issue.completed_date,
            }
            records.append(record)

        df = pd.DataFrame(records)

        # Optimize data types
        df["created"] = pd.to_datetime(df["created"])
        df["updated"] = pd.to_datetime(df["updated"])
        df["actual_start_date"] = pd.to_datetime(df["actual_start_date"])
        df["actual_end_date"] = pd.to_datetime(df["actual_end_date"])
        df["handoff_date"] = pd.to_datetime(df["handoff_date"])

        # Create categorical columns for better performance and memory usage
        df["priority"] = pd.Categorical(
            df["priority"], categories=[p.value for p in Priority]
        )
        df["status"] = pd.Categorical(
            df["status"], categories=[s.value for s in Status]
        )
        df["issue_type"] = pd.Categorical(
            df["issue_type"], categories=[t.value for t in IssueType]
        )

        return df

    @staticmethod
    def milestones_to_dataframe(
        milestones: List[Milestone], issues: List[Issue]
    ) -> pd.DataFrame:
        """Convert a list of Milestone objects to a pandas DataFrame.

        Args:
            milestones: List of Milestone objects
            issues: List of Issue objects for calculating milestone metrics

        Returns:
            DataFrame with milestone data and calculated metrics
        """
        if not milestones:
            return pd.DataFrame()

        records = []
        for milestone in milestones:
            milestone_issues = milestone.get_issues(issues)

            record = {
                "name": milestone.name,
                "description": milestone.description,
                "due_date": milestone.due_date,
                "status": milestone.status.value,
                "created": milestone.created,
                "updated": milestone.updated,
                "github_milestone": milestone.github_milestone,
                "issue_count": milestone.get_issue_count(issues),
                "completion_percentage": milestone.get_completion_percentage(issues),
                "total_estimated_hours": milestone.get_total_estimated_hours(issues),
                "remaining_estimated_hours": milestone.get_remaining_estimated_hours(
                    issues
                ),
                "estimated_time_display": milestone.get_estimated_time_display(issues),
                "issues_todo": len(
                    [i for i in milestone_issues if i.status == Status.TODO]
                ),
                "issues_in_progress": len(
                    [i for i in milestone_issues if i.status == Status.IN_PROGRESS]
                ),
                "issues_blocked": len(
                    [i for i in milestone_issues if i.status == Status.BLOCKED]
                ),
                "issues_review": len(
                    [i for i in milestone_issues if i.status == Status.REVIEW]
                ),
                "issues_done": len(
                    [i for i in milestone_issues if i.status == Status.DONE]
                ),
            }
            records.append(record)

        df = pd.DataFrame(records)

        # Optimize data types
        df["due_date"] = pd.to_datetime(df["due_date"])
        df["created"] = pd.to_datetime(df["created"])
        df["updated"] = pd.to_datetime(df["updated"])
        df["status"] = pd.Categorical(
            df["status"], categories=[s.value for s in MilestoneStatus]
        )

        return df

    @staticmethod
    def export_to_csv(df: pd.DataFrame, filepath: Path, **kwargs) -> None:
        """Export DataFrame to CSV format.

        Args:
            df: DataFrame to export
            filepath: Output file path
            **kwargs: Additional arguments for pandas.to_csv()
        """
        default_kwargs = {"index": False, "date_format": "%Y-%m-%d %H:%M:%S"}
        default_kwargs.update(kwargs)

        df.to_csv(filepath, **default_kwargs)

    @staticmethod
    def export_to_excel(
        df: pd.DataFrame, filepath: Path, sheet_name: str = "Sheet1", **kwargs
    ) -> None:
        """Export DataFrame to Excel format.

        Args:
            df: DataFrame to export
            filepath: Output file path
            sheet_name: Excel sheet name
            **kwargs: Additional arguments for pandas.to_excel()
        """
        default_kwargs = {"index": False, "sheet_name": sheet_name}
        default_kwargs.update(kwargs)

        df.to_excel(filepath, **default_kwargs)

    @staticmethod
    def export_to_json(df: pd.DataFrame, filepath: Path, **kwargs) -> None:
        """Export DataFrame to JSON format.

        Args:
            df: DataFrame to export
            filepath: Output file path
            **kwargs: Additional arguments for pandas.to_json()
        """
        default_kwargs = {"orient": "records", "date_format": "iso", "indent": 2}
        default_kwargs.update(kwargs)

        df.to_json(filepath, **default_kwargs)

    @staticmethod
    def export_multiple_sheets(
        data_dict: Dict[str, pd.DataFrame], filepath: Path, **kwargs
    ) -> None:
        """Export multiple DataFrames to an Excel file with multiple sheets.

        Args:
            data_dict: Dictionary mapping sheet names to DataFrames
            filepath: Output file path
            **kwargs: Additional arguments for ExcelWriter
        """
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            for sheet_name, df in data_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)


class DataAnalyzer:
    """Advanced data analysis utilities using pandas for roadmap insights."""

    @staticmethod
    def analyze_velocity_trends(
        issues_df: pd.DataFrame, period: str = "W"
    ) -> pd.DataFrame:
        """Analyze velocity trends over time.

        Args:
            issues_df: DataFrame with issue data
            period: Pandas period string ('D', 'W', 'M', 'Q', 'Y')

        Returns:
            DataFrame with velocity metrics by period
        """
        if issues_df.empty or "actual_end_date" not in issues_df.columns:
            return pd.DataFrame()

        completed_issues = issues_df[issues_df["actual_end_date"].notna()].copy()

        if completed_issues.empty:
            return pd.DataFrame()

        # Group by time period
        completed_issues["completion_period"] = completed_issues[
            "actual_end_date"
        ].dt.to_period(period)

        velocity_metrics = (
            completed_issues.groupby("completion_period")
            .agg(
                {
                    "id": "count",  # Issues completed
                    "estimated_hours": ["sum", "mean"],
                    "actual_duration_hours": ["sum", "mean"],
                    "priority": lambda x: (
                        x == "critical"
                    ).sum(),  # Critical issues completed
                }
            )
            .round(2)
        )

        # Flatten column names
        velocity_metrics.columns = [
            "issues_completed",
            "total_estimated_hours",
            "avg_estimated_hours",
            "total_actual_hours",
            "avg_actual_hours",
            "critical_issues_completed",
        ]

        # Calculate velocity score
        velocity_metrics["velocity_score"] = (
            velocity_metrics["issues_completed"] * 10
            + velocity_metrics["total_actual_hours"] * 0.1
        )

        return velocity_metrics.reset_index()

    @staticmethod
    def analyze_team_performance(issues_df: pd.DataFrame) -> pd.DataFrame:
        """Analyze team performance metrics by assignee.

        Args:
            issues_df: DataFrame with issue data

        Returns:
            DataFrame with team performance metrics
        """
        if issues_df.empty:
            return pd.DataFrame()

        team_metrics = (
            issues_df.groupby("assignee")
            .agg(
                {
                    "id": "count",  # Total issues
                    "estimated_hours": ["sum", "mean"],
                    "actual_duration_hours": ["sum", "mean", "count"],
                    "is_overdue": "sum",
                    "is_completed": "sum",
                    "priority": lambda x: (x == "critical").sum(),
                    "status": lambda x: (x == "in-progress").sum(),
                }
            )
            .round(2)
        )

        # Flatten column names
        team_metrics.columns = [
            "total_issues",
            "total_estimated_hours",
            "avg_estimated_hours",
            "total_actual_hours",
            "avg_actual_hours",
            "completed_issues",
            "overdue_issues",
            "issues_completed",
            "critical_issues",
            "active_issues",
        ]

        # Ensure numeric columns are properly typed
        numeric_columns = [
            "total_issues",
            "total_estimated_hours",
            "avg_estimated_hours",
            "total_actual_hours",
            "avg_actual_hours",
            "completed_issues",
            "overdue_issues",
            "issues_completed",
            "critical_issues",
            "active_issues",
        ]
        for col in numeric_columns:
            team_metrics[col] = pd.to_numeric(
                team_metrics[col], errors="coerce"
            ).fillna(0)

        # Calculate performance metrics
        team_metrics["completion_rate"] = (
            team_metrics["issues_completed"]
            / team_metrics["total_issues"].replace(0, 1)
            * 100
        ).round(1)

        team_metrics["efficiency_ratio"] = (
            team_metrics["total_estimated_hours"]
            / team_metrics["total_actual_hours"].replace(0, 1)
        ).round(2)

        return team_metrics.reset_index()

    @staticmethod
    def analyze_milestone_health(milestones_df: pd.DataFrame) -> pd.DataFrame:
        """Analyze milestone health and progress metrics.

        Args:
            milestones_df: DataFrame with milestone data

        Returns:
            DataFrame with milestone health analysis
        """
        if milestones_df.empty:
            return pd.DataFrame()

        health_df = milestones_df.copy()

        # Calculate health score (0-100)
        health_df["health_score"] = 0

        # Completion percentage (50% weight)
        health_df["health_score"] += health_df["completion_percentage"] * 0.5

        # Progress momentum (30% weight) - based on in-progress vs todo ratio
        total_active = health_df["issues_todo"] + health_df["issues_in_progress"]
        progress_momentum = (
            health_df["issues_in_progress"] / total_active.replace(0, 1)
        ) * 30
        health_df["health_score"] += progress_momentum

        # Blocking factor (20% weight) - penalty for blocked issues
        blocking_penalty = (
            health_df["issues_blocked"] / health_df["issue_count"].replace(0, 1)
        ) * 20
        health_df["health_score"] -= blocking_penalty

        health_df["health_score"] = health_df["health_score"].clip(0, 100).round(1)

        # Categorize health
        health_df["health_status"] = pd.cut(
            health_df["health_score"],
            bins=[0, 30, 60, 85, 100],
            labels=["Critical", "At Risk", "On Track", "Excellent"],
            include_lowest=True,
        )

        return health_df

    @staticmethod
    def find_bottlenecks(issues_df: pd.DataFrame) -> Dict[str, Any]:
        """Identify potential bottlenecks in the workflow.

        Args:
            issues_df: DataFrame with issue data

        Returns:
            Dictionary with bottleneck analysis
        """
        if issues_df.empty:
            return {}

        bottlenecks = {}

        # Status bottlenecks
        status_counts = issues_df["status"].value_counts()
        if "blocked" in status_counts and status_counts["blocked"] > 0:
            bottlenecks["blocked_issues"] = {
                "count": int(status_counts["blocked"]),
                "percentage": round(status_counts["blocked"] / len(issues_df) * 100, 1),
            }

        # Assignee bottlenecks (people with too many active issues)
        active_issues = issues_df[issues_df["status"].isin(["todo", "in-progress"])]
        assignee_loads = active_issues.groupby("assignee").size()
        high_load_threshold = assignee_loads.mean() + assignee_loads.std()

        overloaded_assignees = assignee_loads[assignee_loads > high_load_threshold]
        if not overloaded_assignees.empty:
            bottlenecks["overloaded_assignees"] = overloaded_assignees.to_dict()

        # Milestone bottlenecks (milestones with many blocked issues)
        milestone_blocked = (
            issues_df[issues_df["status"] == "blocked"].groupby("milestone").size()
        )
        if not milestone_blocked.empty:
            bottlenecks["milestone_blockers"] = milestone_blocked.to_dict()

        # Dependency bottlenecks (issues blocking multiple other issues)
        if "blocks" in issues_df.columns:
            blocking_issues = issues_df[issues_df["blocks"] != ""]
            if not blocking_issues.empty:
                bottlenecks["dependency_blockers"] = len(blocking_issues)

        return bottlenecks


class QueryBuilder:
    """Advanced query builder for filtering and analyzing DataFrame data."""

    @staticmethod
    def filter_by_date_range(
        df: pd.DataFrame,
        date_column: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Filter DataFrame by date range.

        Args:
            df: DataFrame to filter
            date_column: Name of the date column
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Filtered DataFrame
        """
        if df.empty or date_column not in df.columns:
            return df

        mask = pd.Series(True, index=df.index)

        if start_date:
            mask &= df[date_column] >= start_date

        if end_date:
            mask &= df[date_column] <= end_date

        return df[mask]

    @staticmethod
    def filter_by_criteria(df: pd.DataFrame, **criteria) -> pd.DataFrame:
        """Filter DataFrame by multiple criteria.

        Args:
            df: DataFrame to filter
            **criteria: Filter criteria as keyword arguments

        Returns:
            Filtered DataFrame
        """
        if df.empty:
            return df

        mask = pd.Series(True, index=df.index)

        for column, value in criteria.items():
            if column not in df.columns:
                continue

            if isinstance(value, (list, tuple)):
                mask &= df[column].isin(value)
            else:
                mask &= df[column] == value

        return df[mask]

    @staticmethod
    def search_text(
        df: pd.DataFrame, search_term: str, columns: List[str] = None
    ) -> pd.DataFrame:
        """Search for text across specified columns.

        Args:
            df: DataFrame to search
            search_term: Text to search for
            columns: List of columns to search (defaults to all text columns)

        Returns:
            Filtered DataFrame with matching rows
        """
        if df.empty or not search_term:
            return df

        if columns is None:
            # Search all text/object columns
            columns = df.select_dtypes(include=["object"]).columns.tolist()

        # Create search mask
        mask = pd.Series(False, index=df.index)

        for column in columns:
            if column in df.columns:
                mask |= (
                    df[column]
                    .astype(str)
                    .str.contains(search_term, case=False, na=False)
                )

        return df[mask]
