"""Git history analytics for tracking developer productivity and project evolution."""

import json
import os
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .core import RoadmapCore
from .git_integration import GitCommit, GitIntegration
from .models import Issue, Priority, Status


@dataclass
class DeveloperMetrics:
    """Metrics for individual developer productivity."""

    name: str
    total_commits: int
    issues_completed: int
    avg_commits_per_day: float
    avg_completion_time_hours: float
    productivity_score: float
    specialization_areas: List[str]
    collaboration_score: float


@dataclass
class ProjectVelocity:
    """Project velocity and trend analysis."""

    period: str  # "week", "month", "quarter"
    start_date: datetime
    end_date: datetime
    commits_count: int
    issues_completed: int
    lines_added: int
    lines_removed: int
    velocity_score: float
    trend_direction: str  # "increasing", "decreasing", "stable"


@dataclass
class TeamInsights:
    """High-level team performance insights."""

    total_developers: int
    avg_team_velocity: float
    bottleneck_areas: List[str]
    top_performers: List[str]
    collaboration_patterns: Dict[str, Any]
    recommended_actions: List[str]


class GitHistoryAnalyzer:
    """Analyzes Git history for productivity and project evolution insights."""

    def __init__(self, roadmap_core: RoadmapCore):
        self.core = roadmap_core
        self.git_integration = GitIntegration()

    def analyze_developer_productivity(
        self, developer: str, days: int = 30
    ) -> DeveloperMetrics:
        """Analyze individual developer productivity over specified period."""
        if not self.git_integration.is_git_repository():
            raise ValueError("Not in a Git repository")

        # Get commits for this developer
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        all_commits = self.git_integration.get_recent_commits(
            count=1000, since=since_date
        )

        dev_commits = [c for c in all_commits if c.author == developer]

        # Analyze commit patterns
        commit_frequency = self._analyze_commit_frequency(dev_commits, days)

        # Get issues completed by this developer
        issues = self.core.list_issues()
        dev_issues = [i for i in issues if i.assignee == developer]
        completed_issues = [i for i in dev_issues if i.status == Status.DONE]

        # Calculate completion times
        completion_times = []
        for issue in completed_issues:
            if hasattr(issue, "git_commits") and issue.git_commits:
                start_time = min(
                    datetime.fromisoformat(commit["date"])
                    for commit in issue.git_commits
                )
                if issue.completed_date:
                    end_time = datetime.fromisoformat(issue.completed_date)
                    duration = (end_time - start_time).total_seconds() / 3600  # hours
                    completion_times.append(duration)

        avg_completion_time = (
            statistics.mean(completion_times) if completion_times else 0
        )

        # Calculate productivity score
        productivity_score = self._calculate_productivity_score(
            len(dev_commits),
            len(completed_issues),
            commit_frequency,
            avg_completion_time,
        )

        # Analyze specialization areas
        specialization_areas = self._analyze_specialization(dev_commits, dev_issues)

        # Calculate collaboration score
        collaboration_score = self._calculate_collaboration_score(
            dev_commits, all_commits
        )

        return DeveloperMetrics(
            name=developer,
            total_commits=len(dev_commits),
            issues_completed=len(completed_issues),
            avg_commits_per_day=commit_frequency,
            avg_completion_time_hours=avg_completion_time,
            productivity_score=productivity_score,
            specialization_areas=specialization_areas,
            collaboration_score=collaboration_score,
        )

    def analyze_project_velocity(
        self, period: str = "week", num_periods: int = 12
    ) -> List[ProjectVelocity]:
        """Analyze project velocity trends over time."""
        if not self.git_integration.is_git_repository():
            raise ValueError("Not in a Git repository")

        velocities = []

        # Calculate period duration
        if period == "week":
            period_delta = timedelta(weeks=1)
        elif period == "month":
            period_delta = timedelta(days=30)
        elif period == "quarter":
            period_delta = timedelta(days=90)
        else:
            raise ValueError(f"Invalid period: {period}")

        # Analyze each period
        end_date = datetime.now()

        for i in range(num_periods):
            start_date = end_date - period_delta

            # Get commits for this period
            commits = self._get_commits_in_period(start_date, end_date)

            # Get issues completed in this period
            issues = self.core.list_issues()
            completed_issues = [
                issue
                for issue in issues
                if (
                    issue.status == Status.DONE
                    and hasattr(issue, "completed_date")
                    and issue.completed_date
                    and start_date
                    <= datetime.fromisoformat(issue.completed_date)
                    <= end_date
                )
            ]

            # Calculate metrics
            total_lines_added = sum(c.insertions for c in commits)
            total_lines_removed = sum(c.deletions for c in commits)

            # Calculate velocity score (weighted combination of metrics)
            velocity_score = self._calculate_velocity_score(
                len(commits),
                len(completed_issues),
                total_lines_added,
                total_lines_removed,
            )

            velocities.append(
                ProjectVelocity(
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    commits_count=len(commits),
                    issues_completed=len(completed_issues),
                    lines_added=total_lines_added,
                    lines_removed=total_lines_removed,
                    velocity_score=velocity_score,
                    trend_direction=self._determine_trend_direction(
                        velocities, velocity_score
                    ),
                )
            )

            end_date = start_date

        return list(reversed(velocities))  # Return chronological order

    def generate_team_insights(self, days: int = 30) -> TeamInsights:
        """Generate comprehensive team performance insights."""
        if not self.git_integration.is_git_repository():
            raise ValueError("Not in a Git repository")

        # Get all developers
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        all_commits = self.git_integration.get_recent_commits(
            count=1000, since=since_date
        )
        developers = list(set(c.author for c in all_commits))

        # Analyze each developer
        dev_metrics = []
        for dev in developers:
            try:
                metrics = self.analyze_developer_productivity(dev, days)
                dev_metrics.append(metrics)
            except Exception:
                continue  # Skip if analysis fails for this developer

        if not dev_metrics:
            raise ValueError("No developer metrics available")

        # Calculate team averages
        avg_velocity = statistics.mean(m.productivity_score for m in dev_metrics)

        # Identify top performers
        top_performers = sorted(
            dev_metrics, key=lambda m: m.productivity_score, reverse=True
        )[:3]

        # Identify bottleneck areas
        bottlenecks = self._identify_bottlenecks(dev_metrics, all_commits)

        # Analyze collaboration patterns
        collaboration_patterns = self._analyze_collaboration_patterns(
            all_commits, developers
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(dev_metrics, bottlenecks)

        return TeamInsights(
            total_developers=len(developers),
            avg_team_velocity=avg_velocity,
            bottleneck_areas=bottlenecks,
            top_performers=[p.name for p in top_performers],
            collaboration_patterns=collaboration_patterns,
            recommended_actions=recommendations,
        )

    def analyze_code_quality_trends(self, days: int = 90) -> Dict[str, Any]:
        """Analyze code quality trends from commit patterns."""
        if not self.git_integration.is_git_repository():
            raise ValueError("Not in a Git repository")

        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        commits = self.git_integration.get_recent_commits(count=1000, since=since_date)

        # Analyze commit message patterns
        fix_commits = [
            c
            for c in commits
            if any(
                keyword in c.message.lower()
                for keyword in ["fix", "bug", "error", "issue"]
            )
        ]

        feature_commits = [
            c
            for c in commits
            if any(
                keyword in c.message.lower()
                for keyword in ["feat", "feature", "add", "implement"]
            )
        ]

        refactor_commits = [
            c
            for c in commits
            if any(
                keyword in c.message.lower()
                for keyword in ["refactor", "cleanup", "improve"]
            )
        ]

        # Calculate quality metrics
        bug_fix_ratio = len(fix_commits) / len(commits) if commits else 0
        feature_ratio = len(feature_commits) / len(commits) if commits else 0
        refactor_ratio = len(refactor_commits) / len(commits) if commits else 0

        # Analyze commit sizes (indicator of code quality)
        commit_sizes = [
            c.insertions + c.deletions
            for c in commits
            if c.insertions + c.deletions > 0
        ]
        avg_commit_size = statistics.mean(commit_sizes) if commit_sizes else 0
        large_commits_ratio = (
            len([s for s in commit_sizes if s > 200]) / len(commit_sizes)
            if commit_sizes
            else 0
        )

        return {
            "period_days": days,
            "total_commits": len(commits),
            "bug_fix_ratio": bug_fix_ratio,
            "feature_ratio": feature_ratio,
            "refactor_ratio": refactor_ratio,
            "avg_commit_size": avg_commit_size,
            "large_commits_ratio": large_commits_ratio,
            "quality_score": self._calculate_quality_score(
                bug_fix_ratio, feature_ratio, refactor_ratio, large_commits_ratio
            ),
            "recommendations": self._get_quality_recommendations(
                bug_fix_ratio, large_commits_ratio, refactor_ratio
            ),
        }

    def _analyze_commit_frequency(self, commits: List[GitCommit], days: int) -> float:
        """Calculate average commits per day for a developer."""
        if not commits or days <= 0:
            return 0.0
        return len(commits) / days

    def _calculate_productivity_score(
        self,
        commits: int,
        completed_issues: int,
        commit_frequency: float,
        avg_completion_time: float,
    ) -> float:
        """Calculate a normalized productivity score (0-100)."""
        # Weighted scoring system
        commit_score = min(commits / 10, 10) * 2  # Max 20 points
        issue_score = min(completed_issues / 5, 10) * 3  # Max 30 points
        frequency_score = min(commit_frequency * 10, 10) * 2  # Max 20 points

        # Efficiency score (inverse of completion time, capped)
        if avg_completion_time > 0:
            efficiency_score = (
                min(168 / avg_completion_time, 10) * 3
            )  # Max 30 points (168 = week hours)
        else:
            efficiency_score = 15  # Default moderate score

        total_score = commit_score + issue_score + frequency_score + efficiency_score
        return min(total_score, 100)

    def _analyze_specialization(
        self, commits: List[GitCommit], issues: List[Issue]
    ) -> List[str]:
        """Identify developer's specialization areas."""
        specializations = []

        # Analyze file types from commits
        file_extensions = Counter()
        for commit in commits:
            for file_path in commit.files_changed:
                if "." in file_path:
                    ext = file_path.split(".")[-1].lower()
                    file_extensions[ext] += 1

        # Map extensions to technologies
        tech_mapping = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "java": "Java",
            "cpp": "C++",
            "c": "C",
            "html": "Frontend",
            "css": "Frontend",
            "scss": "Frontend",
            "sql": "Database",
            "md": "Documentation",
            "yaml": "DevOps",
            "yml": "DevOps",
            "dockerfile": "DevOps",
            "tf": "Infrastructure",
        }

        for ext, count in file_extensions.most_common(3):
            if ext in tech_mapping:
                specializations.append(tech_mapping[ext])

        # Analyze issue types
        issue_types = Counter(issue.issue_type.value for issue in issues)
        if issue_types:
            specializations.append(f"{issue_types.most_common(1)[0][0]} issues")

        return list(set(specializations))[:3]  # Return top 3 unique specializations

    def _calculate_collaboration_score(
        self, dev_commits: List[GitCommit], all_commits: List[GitCommit]
    ) -> float:
        """Calculate collaboration score based on shared files and timing."""
        if not dev_commits or not all_commits:
            return 0.0

        # Get files this developer has worked on
        dev_files = set()
        for commit in dev_commits:
            dev_files.update(commit.files_changed)

        # Count collaborations (other developers working on same files)
        collaborations = 0
        other_commits = [c for c in all_commits if c.author != dev_commits[0].author]

        for commit in other_commits:
            shared_files = set(commit.files_changed) & dev_files
            if shared_files:
                collaborations += len(shared_files)

        # Normalize collaboration score
        max_possible_collaborations = len(dev_files) * len(other_commits)
        if max_possible_collaborations > 0:
            return min((collaborations / max_possible_collaborations) * 100, 100)

        return 0.0

    def _get_commits_in_period(
        self, start_date: datetime, end_date: datetime
    ) -> List[GitCommit]:
        """Get commits within a specific time period."""
        all_commits = self.git_integration.get_recent_commits(count=1000)

        # Ensure timezone consistency
        def normalize_datetime(dt):
            if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
                # If datetime is timezone-aware, convert to UTC naive
                return dt.replace(tzinfo=None)
            return dt

        start_date_norm = normalize_datetime(start_date)
        end_date_norm = normalize_datetime(end_date)

        return [
            commit
            for commit in all_commits
            if start_date_norm <= normalize_datetime(commit.date) <= end_date_norm
        ]

    def _calculate_velocity_score(
        self, commits: int, issues: int, lines_added: int, lines_removed: int
    ) -> float:
        """Calculate velocity score for a time period."""
        # Weighted combination of metrics
        commit_score = min(commits / 20, 1) * 25  # Max 25 points
        issue_score = min(issues / 10, 1) * 35  # Max 35 points
        code_score = min((lines_added + lines_removed) / 1000, 1) * 25  # Max 25 points

        # Bonus for code removal (refactoring)
        refactor_bonus = (
            min(lines_removed / (lines_added + 1), 0.5) * 15
        )  # Max 15 points

        return commit_score + issue_score + code_score + refactor_bonus

    def _determine_trend_direction(
        self, previous_velocities: List[ProjectVelocity], current_score: float
    ) -> str:
        """Determine if velocity is trending up, down, or stable."""
        if len(previous_velocities) < 2:
            return "stable"

        recent_scores = [v.velocity_score for v in previous_velocities[-2:]]
        recent_scores.append(current_score)

        if len(recent_scores) >= 3:
            trend = statistics.linear_regression(
                range(len(recent_scores)), recent_scores
            ).slope
            if trend > 5:
                return "increasing"
            elif trend < -5:
                return "decreasing"

        return "stable"

    def _identify_bottlenecks(
        self, dev_metrics: List[DeveloperMetrics], commits: List[GitCommit]
    ) -> List[str]:
        """Identify potential bottleneck areas in the team."""
        bottlenecks = []

        # Low productivity developers
        low_performers = [m for m in dev_metrics if m.productivity_score < 30]
        if len(low_performers) > len(dev_metrics) * 0.3:
            bottlenecks.append("Team productivity concerns")

        # Long completion times
        long_completions = [m for m in dev_metrics if m.avg_completion_time_hours > 72]
        if long_completions:
            bottlenecks.append("Extended issue completion times")

        # Low collaboration
        low_collaboration = [m for m in dev_metrics if m.collaboration_score < 20]
        if len(low_collaboration) > len(dev_metrics) * 0.5:
            bottlenecks.append("Limited team collaboration")

        # Commit concentration (too few active developers)
        active_developers = len(set(c.author for c in commits))
        if active_developers < 2:
            bottlenecks.append("Over-reliance on single developer")

        return bottlenecks[:3]  # Return top 3 bottlenecks

    def _analyze_collaboration_patterns(
        self, commits: List[GitCommit], developers: List[str]
    ) -> Dict[str, Any]:
        """Analyze team collaboration patterns."""
        # File sharing analysis
        file_collaborations = defaultdict(set)
        for commit in commits:
            for file_path in commit.files_changed:
                file_collaborations[file_path].add(commit.author)

        # Count shared files
        shared_files = {
            path: devs for path, devs in file_collaborations.items() if len(devs) > 1
        }

        # Developer pairs analysis
        collaboration_pairs = Counter()
        for file_path, devs in shared_files.items():
            dev_list = list(devs)
            for i in range(len(dev_list)):
                for j in range(i + 1, len(dev_list)):
                    pair = tuple(sorted([dev_list[i], dev_list[j]]))
                    collaboration_pairs[pair] += 1

        return {
            "shared_files_count": len(shared_files),
            "collaboration_pairs": dict(collaboration_pairs.most_common(5)),
            "avg_collaborators_per_file": (
                statistics.mean(len(devs) for devs in file_collaborations.values())
                if file_collaborations
                else 0
            ),
        }

    def _generate_recommendations(
        self, dev_metrics: List[DeveloperMetrics], bottlenecks: List[str]
    ) -> List[str]:
        """Generate actionable recommendations for team improvement."""
        recommendations = []

        # Performance-based recommendations
        if any(m.productivity_score < 40 for m in dev_metrics):
            recommendations.append(
                "Consider pair programming or mentoring for underperforming developers"
            )

        if any(m.avg_completion_time_hours > 48 for m in dev_metrics):
            recommendations.append(
                "Break down large issues into smaller, manageable tasks"
            )

        # Collaboration recommendations
        avg_collaboration = statistics.mean(m.collaboration_score for m in dev_metrics)
        if avg_collaboration < 30:
            recommendations.append(
                "Encourage more code reviews and shared feature development"
            )

        # Specialization recommendations
        over_specialized = [m for m in dev_metrics if len(m.specialization_areas) <= 1]
        if len(over_specialized) > len(dev_metrics) * 0.4:
            recommendations.append("Cross-train team members in different technologies")

        # Bottleneck-specific recommendations
        if "Extended issue completion times" in bottlenecks:
            recommendations.append(
                "Implement time-boxing and regular progress check-ins"
            )

        if "Limited team collaboration" in bottlenecks:
            recommendations.append(
                "Schedule regular team sync meetings and code review sessions"
            )

        return recommendations[:5]  # Return top 5 recommendations

    def _calculate_quality_score(
        self,
        bug_ratio: float,
        feature_ratio: float,
        refactor_ratio: float,
        large_commits_ratio: float,
    ) -> float:
        """Calculate overall code quality score."""
        # Lower bug ratio is better
        bug_score = max(0, (0.3 - bug_ratio) / 0.3) * 30

        # Higher feature ratio is good
        feature_score = min(feature_ratio / 0.5, 1) * 25

        # Moderate refactor ratio is healthy
        refactor_score = min(refactor_ratio / 0.2, 1) * 20

        # Lower large commits ratio is better
        commit_size_score = max(0, (0.2 - large_commits_ratio) / 0.2) * 25

        return bug_score + feature_score + refactor_score + commit_size_score

    def _get_quality_recommendations(
        self, bug_ratio: float, large_commits_ratio: float, refactor_ratio: float
    ) -> List[str]:
        """Get code quality improvement recommendations."""
        recommendations = []

        if bug_ratio > 0.25:
            recommendations.append(
                "High bug fix ratio - consider more thorough testing and code reviews"
            )

        if large_commits_ratio > 0.3:
            recommendations.append(
                "Many large commits - break changes into smaller, focused commits"
            )

        if refactor_ratio < 0.1:
            recommendations.append(
                "Low refactoring activity - allocate time for code cleanup and improvement"
            )

        return recommendations


class AnalyticsReportGenerator:
    """Generates comprehensive analytics reports."""

    def __init__(self, analyzer: GitHistoryAnalyzer):
        self.analyzer = analyzer

    def generate_team_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive team analytics report."""
        try:
            insights = self.analyzer.generate_team_insights(days)
            velocity_trends = self.analyzer.analyze_project_velocity("week", 8)
            quality_trends = self.analyzer.analyze_code_quality_trends(days)

            # Get individual developer metrics
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            all_commits = self.analyzer.git_integration.get_recent_commits(
                count=1000, since=since_date
            )
            developers = list(set(c.author for c in all_commits))

            dev_reports = []
            for dev in developers:
                try:
                    metrics = self.analyzer.analyze_developer_productivity(dev, days)
                    dev_reports.append(
                        {
                            "name": metrics.name,
                            "productivity_score": metrics.productivity_score,
                            "commits": metrics.total_commits,
                            "issues_completed": metrics.issues_completed,
                            "specializations": metrics.specialization_areas,
                            "collaboration_score": metrics.collaboration_score,
                        }
                    )
                except Exception:
                    continue

            return {
                "report_generated": datetime.now().isoformat(),
                "analysis_period_days": days,
                "team_overview": {
                    "total_developers": insights.total_developers,
                    "avg_team_velocity": insights.avg_team_velocity,
                    "top_performers": insights.top_performers,
                    "bottlenecks": insights.bottleneck_areas,
                    "recommendations": insights.recommended_actions,
                },
                "velocity_trends": [
                    {
                        "period": v.period,
                        "start_date": v.start_date.isoformat(),
                        "end_date": v.end_date.isoformat(),
                        "commits": v.commits_count,
                        "issues_completed": v.issues_completed,
                        "velocity_score": v.velocity_score,
                        "trend": v.trend_direction,
                    }
                    for v in velocity_trends
                ],
                "code_quality": quality_trends,
                "developer_metrics": dev_reports,
                "collaboration_patterns": insights.collaboration_patterns,
            }
        except Exception as e:
            return {
                "error": f"Failed to generate team report: {str(e)}",
                "report_generated": datetime.now().isoformat(),
            }

    def save_report_to_file(
        self, report: Dict[str, Any], filename: Optional[str] = None
    ) -> str:
        """Save analytics report to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"team_analytics_report_{timestamp}.json"

        report_path = Path(filename)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        return str(report_path.absolute())
