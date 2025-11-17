"""
Unified Data Processing Framework for Roadmap CLI

This module provides centralized data transformation, filtering, and aggregation
utilities to eliminate duplicate data processing patterns across the codebase.

Key Features:
- Centralized data transformation utilities for issues, milestones, and projects
- Consistent filtering and aggregation patterns
- Reusable data processing pipelines
- Performance-optimized operations
- Integration with pandas for advanced analytics
"""

import statistics
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from .models import (
    Issue,
    IssueType,
    Priority,
    Status,
)


class DataProcessor:
    """Main data processing utility class."""

    @staticmethod
    def filter_issues(
        issues: list[Issue],
        milestone: str | None = None,
        status: Status | None = None,
        priority: Priority | None = None,
        issue_type: IssueType | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        date_range: tuple[datetime, datetime] | None = None,
        custom_filter: Callable[[Issue], bool] | None = None,
    ) -> list[Issue]:
        """Filter issues based on multiple criteria."""
        filtered_issues = issues

        # Apply basic filters
        if milestone is not None:
            filtered_issues = [i for i in filtered_issues if i.milestone == milestone]

        if status is not None:
            filtered_issues = [i for i in filtered_issues if i.status == status]

        if priority is not None:
            filtered_issues = [i for i in filtered_issues if i.priority == priority]

        if issue_type is not None:
            filtered_issues = [i for i in filtered_issues if i.issue_type == issue_type]

        if assignee is not None:
            filtered_issues = [i for i in filtered_issues if i.assignee == assignee]

        # Label filtering (issue must have all specified labels)
        if labels:
            filtered_issues = [
                i
                for i in filtered_issues
                if i.labels and all(label in i.labels for label in labels)
            ]

        # Date range filtering (based on created date)
        if date_range:
            start_date, end_date = date_range
            filtered_issues = [
                i for i in filtered_issues if start_date <= i.created <= end_date
            ]

        # Custom filter function
        if custom_filter:
            filtered_issues = [i for i in filtered_issues if custom_filter(i)]

        return filtered_issues

    @staticmethod
    def group_issues_by_field(
        issues: list[Issue], field: str
    ) -> dict[str, list[Issue]]:
        """Group issues by a specific field."""
        groups = defaultdict(list)

        for issue in issues:
            if hasattr(issue, field):
                value = getattr(issue, field)
                if value is None:
                    value = "None"
                elif isinstance(value, Priority | Status | IssueType):
                    value = value.value
                elif isinstance(value, list):
                    value = ",".join(value) if value else "Empty"
                groups[str(value)].append(issue)
            else:
                groups["Unknown"].append(issue)

        return dict(groups)

    @staticmethod
    def calculate_issue_statistics(issues: list[Issue]) -> dict[str, Any]:
        """Calculate comprehensive statistics for a list of issues."""
        if not issues:
            return {
                "total": 0,
                "by_status": {},
                "by_priority": {},
                "by_type": {},
                "by_assignee": {},
                "completion_rate": 0.0,
                "estimated_hours": {"total": 0, "average": 0},
                "actual_hours": {"total": 0, "average": 0},
                "progress": {"average": 0, "distribution": {}},
            }

        total = len(issues)

        # Count by status
        by_status = Counter(issue.status.value for issue in issues)
        completed = by_status.get(Status.DONE.value, 0)
        completion_rate = (completed / total * 100) if total > 0 else 0

        # Count by priority
        by_priority = Counter(issue.priority.value for issue in issues)

        # Count by type
        by_type = Counter(issue.issue_type.value for issue in issues)

        # Count by assignee
        by_assignee = Counter(issue.assignee or "Unassigned" for issue in issues)

        # Calculate time estimates
        estimated_hours = [
            i.estimated_hours for i in issues if i.estimated_hours is not None
        ]
        total_estimated = sum(estimated_hours) if estimated_hours else 0
        avg_estimated = statistics.mean(estimated_hours) if estimated_hours else 0

        # Calculate actual hours (for completed issues)
        actual_hours = [
            i.actual_duration_hours
            for i in issues
            if i.actual_duration_hours is not None
        ]
        total_actual = sum(actual_hours) if actual_hours else 0
        avg_actual = statistics.mean(actual_hours) if actual_hours else 0

        # Calculate progress statistics
        progress_values = [
            i.progress_percentage for i in issues if i.progress_percentage is not None
        ]
        avg_progress = statistics.mean(progress_values) if progress_values else 0

        # Progress distribution
        progress_ranges = {
            "0%": 0,
            "1-25%": 0,
            "26-50%": 0,
            "51-75%": 0,
            "76-99%": 0,
            "100%": 0,
        }

        for progress in progress_values:
            if progress == 0:
                progress_ranges["0%"] += 1
            elif progress == 100:
                progress_ranges["100%"] += 1
            elif progress <= 25:
                progress_ranges["1-25%"] += 1
            elif progress <= 50:
                progress_ranges["26-50%"] += 1
            elif progress <= 75:
                progress_ranges["51-75%"] += 1
            else:
                progress_ranges["76-99%"] += 1

        return {
            "total": total,
            "by_status": dict(by_status),
            "by_priority": dict(by_priority),
            "by_type": dict(by_type),
            "by_assignee": dict(by_assignee),
            "completion_rate": round(completion_rate, 2),
            "estimated_hours": {
                "total": total_estimated,
                "average": round(avg_estimated, 2),
            },
            "actual_hours": {"total": total_actual, "average": round(avg_actual, 2)},
            "progress": {
                "average": round(avg_progress, 2),
                "distribution": progress_ranges,
            },
        }

    @staticmethod
    def calculate_milestone_progress(
        milestone_name: str, issues: list[Issue]
    ) -> dict[str, Any]:
        """Calculate progress statistics for a specific milestone."""
        milestone_issues = DataProcessor.filter_issues(issues, milestone=milestone_name)
        stats = DataProcessor.calculate_issue_statistics(milestone_issues)

        # Add milestone-specific calculations
        total_issues = len(milestone_issues)
        completed_issues = len([i for i in milestone_issues if i.status == Status.DONE])
        progress_percentage = (
            (completed_issues / total_issues * 100) if total_issues > 0 else 0
        )

        return {
            "milestone": milestone_name,
            "total_issues": total_issues,
            "completed_issues": completed_issues,
            "progress_percentage": round(progress_percentage, 2),
            "statistics": stats,
        }

    @staticmethod
    def analyze_team_performance(issues: list[Issue]) -> dict[str, Any]:
        """Analyze team performance metrics from issues."""
        assignee_stats = {}

        # Group issues by assignee
        by_assignee = DataProcessor.group_issues_by_field(issues, "assignee")

        for assignee, assignee_issues in by_assignee.items():
            if assignee == "None":
                continue

            stats = DataProcessor.calculate_issue_statistics(assignee_issues)

            # Calculate additional performance metrics
            completed_issues = [i for i in assignee_issues if i.status == Status.DONE]
            avg_completion_time = 0

            if completed_issues:
                completion_times = []
                for issue in completed_issues:
                    if issue.actual_start_date and issue.actual_end_date:
                        duration = (
                            issue.actual_end_date - issue.actual_start_date
                        ).total_seconds() / 3600
                        completion_times.append(duration)

                if completion_times:
                    avg_completion_time = statistics.mean(completion_times)

            assignee_stats[assignee] = {
                "total_assigned": len(assignee_issues),
                "completed": len(completed_issues),
                "completion_rate": stats["completion_rate"],
                "avg_completion_time_hours": round(avg_completion_time, 2),
                "estimated_vs_actual": {
                    "estimated": stats["estimated_hours"]["total"],
                    "actual": stats["actual_hours"]["total"],
                    "accuracy": _calculate_estimation_accuracy(
                        stats["estimated_hours"]["total"],
                        stats["actual_hours"]["total"],
                    ),
                },
            }

        return assignee_stats

    @staticmethod
    def _calculate_estimation_accuracy(estimated: float, actual: float) -> float:
        """Calculate estimation accuracy percentage."""
        if estimated == 0 or actual == 0:
            return 0.0

        # Calculate accuracy as inverse of the relative error
        relative_error = abs(estimated - actual) / estimated
        accuracy = max(0, 100 * (1 - relative_error))
        return round(accuracy, 2)

    @staticmethod
    def analyze_velocity_trends(
        issues: list[Issue], period_days: int = 30
    ) -> dict[str, Any]:
        """Analyze velocity trends over time periods."""
        if not issues:
            return {"periods": [], "average_velocity": 0}

        # Get completed issues with completion dates
        completed_issues = [
            i
            for i in issues
            if i.status == Status.DONE and i.actual_end_date is not None
        ]

        if not completed_issues:
            return {"periods": [], "average_velocity": 0}

        # Sort by completion date
        completed_issues.sort(key=lambda x: x.actual_end_date or datetime.min)

        # Create time periods
        start_date = completed_issues[0].actual_end_date
        end_date = completed_issues[-1].actual_end_date

        periods = []
        current_date = start_date

        while current_date and end_date and current_date <= end_date:
            period_end = current_date + timedelta(days=period_days)
            period_issues = [
                i
                for i in completed_issues
                if i.actual_end_date and current_date <= i.actual_end_date < period_end
            ]

            period_stats = {
                "start_date": current_date,
                "end_date": period_end,
                "issues_completed": len(period_issues),
                "story_points": sum(i.estimated_hours or 0 for i in period_issues),
                "velocity": len(period_issues) / (period_days / 7),  # Issues per week
            }

            periods.append(period_stats)
            current_date = period_end

        # Calculate average velocity
        velocities = [p["velocity"] for p in periods if p["velocity"] > 0]
        avg_velocity = statistics.mean(velocities) if velocities else 0

        return {
            "periods": periods,
            "average_velocity": round(avg_velocity, 2),
            "period_days": period_days,
        }

    @staticmethod
    def identify_bottlenecks(issues: list[Issue]) -> dict[str, Any]:
        """Identify potential bottlenecks in the workflow."""
        bottlenecks = {
            "long_running_issues": [],
            "blocked_issues": [],
            "overdue_issues": [],
            "high_priority_backlog": [],
            "assignee_overload": {},
        }

        now = datetime.now()

        for issue in issues:
            # Long-running issues (started but not completed, running > 30 days)
            if (
                issue.status == Status.IN_PROGRESS
                and issue.actual_start_date
                and (now - issue.actual_start_date).days > 30
            ):
                bottlenecks["long_running_issues"].append(
                    {
                        "id": issue.id,
                        "title": issue.title,
                        "days_running": (now - issue.actual_start_date).days,
                        "assignee": issue.assignee,
                    }
                )

            # Blocked issues
            if issue.status == Status.BLOCKED:
                bottlenecks["blocked_issues"].append(
                    {
                        "id": issue.id,
                        "title": issue.title,
                        "assignee": issue.assignee,
                        "milestone": issue.milestone,
                    }
                )

            # Overdue issues (with due dates in the past)
            if hasattr(issue, "due_date") and issue.due_date and issue.due_date < now:
                bottlenecks["overdue_issues"].append(
                    {
                        "id": issue.id,
                        "title": issue.title,
                        "due_date": issue.due_date,
                        "days_overdue": (now - issue.due_date).days,
                        "assignee": issue.assignee,
                    }
                )

            # High priority backlog
            if (
                issue.priority in [Priority.CRITICAL, Priority.HIGH]
                and issue.status == Status.TODO
            ):
                bottlenecks["high_priority_backlog"].append(
                    {
                        "id": issue.id,
                        "title": issue.title,
                        "priority": issue.priority.value,
                        "assignee": issue.assignee,
                    }
                )

        # Analyze assignee workload
        assignee_workload = defaultdict(int)
        for issue in issues:
            if issue.assignee and issue.status in [Status.TODO, Status.IN_PROGRESS]:
                assignee_workload[issue.assignee] += 1

        # Flag overloaded assignees (>10 active issues)
        for assignee, count in assignee_workload.items():
            if count > 10:
                bottlenecks["assignee_overload"][assignee] = {
                    "active_issues": count,
                    "status": "overloaded",
                }

        return bottlenecks

    @staticmethod
    def generate_burndown_data(
        issues: list[Issue], milestone: str | None = None
    ) -> dict[str, Any]:
        """Generate burndown chart data for issues or a specific milestone."""
        if milestone:
            filtered_issues = DataProcessor.filter_issues(issues, milestone=milestone)
        else:
            filtered_issues = issues

        if not filtered_issues:
            return {"dates": [], "remaining": [], "ideal": []}

        # Get all relevant dates
        dates = []
        for issue in filtered_issues:
            if issue.created:
                dates.append(issue.created.date())
            if issue.actual_end_date:
                dates.append(issue.actual_end_date.date())

        if not dates:
            return {"dates": [], "remaining": [], "ideal": []}

        start_date = min(dates)
        end_date = max(dates)

        # Generate daily data points
        current_date = start_date
        burndown_data = {"dates": [], "remaining": [], "ideal": []}
        total_issues = len(filtered_issues)

        while current_date <= end_date:
            # Count remaining issues at this date
            remaining = len(
                [
                    i
                    for i in filtered_issues
                    if not (
                        i.actual_end_date and i.actual_end_date.date() <= current_date
                    )
                ]
            )

            # Calculate ideal burndown (linear)
            days_elapsed = (current_date - start_date).days
            total_days = (end_date - start_date).days or 1
            ideal_remaining = total_issues * (1 - days_elapsed / total_days)

            burndown_data["dates"].append(current_date.isoformat())
            burndown_data["remaining"].append(remaining)
            burndown_data["ideal"].append(max(0, int(ideal_remaining)))

            current_date += timedelta(days=1)

        return burndown_data

    @staticmethod
    def transform_to_dataframe(issues: list[Issue]) -> pd.DataFrame:
        """Transform issues to pandas DataFrame for advanced analysis."""
        if not issues:
            return pd.DataFrame()

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
                "progress_percentage": issue.progress_percentage,
                "actual_start_date": issue.actual_start_date,
                "actual_end_date": issue.actual_end_date,
                "actual_duration_hours": issue.actual_duration_hours,
                "is_completed": issue.status == Status.DONE,
                "is_overdue": getattr(issue, "is_overdue", False),
                "labels": ",".join(issue.labels) if issue.labels else "",
                "depends_on": ",".join(issue.depends_on) if issue.depends_on else "",
                "blocks": ",".join(issue.blocks) if issue.blocks else "",
            }
            records.append(record)

        df = pd.DataFrame(records)

        # Convert data types for better analysis
        df["priority"] = pd.Categorical(
            df["priority"], categories=["low", "medium", "high", "critical"]
        )
        df["status"] = pd.Categorical(
            df["status"],
            categories=["todo", "in-progress", "blocked", "review", "done"],
        )
        df["issue_type"] = pd.Categorical(df["issue_type"])
        df["created"] = pd.to_datetime(df["created"])
        df["updated"] = pd.to_datetime(df["updated"])

        return df

    @staticmethod
    def aggregate_by_time_period(
        issues: list[Issue], period: str = "week", date_field: str = "created"
    ) -> dict[str, dict[str, int]]:
        """Aggregate issues by time period (day/week/month)."""
        if not issues:
            return {}

        aggregation = defaultdict(lambda: defaultdict(int))

        for issue in issues:
            date_value = getattr(issue, date_field, None)
            if not date_value:
                continue

            # Determine time period key
            if period == "day":
                period_key = date_value.date().isoformat()
            elif period == "week":
                # Get Monday of the week
                monday = date_value.date() - timedelta(days=date_value.weekday())
                period_key = monday.isoformat()
            elif period == "month":
                period_key = date_value.strftime("%Y-%m")
            else:
                raise ValueError(f"Unsupported period: {period}")

            # Aggregate by status
            aggregation[period_key][issue.status.value] += 1
            aggregation[period_key]["total"] += 1

        return dict(aggregation)


# Global data processor instance
default_processor = DataProcessor()
