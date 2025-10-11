"""
Predictive Intelligence Engine for Roadmap CLI Tool

This module implements machine learning and statistical algorithms to provide
predictive insights, intelligent forecasting, and AI-powered recommendations
for project management and development workflow optimization.

Classes:
    IssueEstimator: ML-powered time estimation for issues
    RiskPredictor: Proactive risk assessment and mitigation
    DeadlineForecaster: Intelligent deadline prediction
    ResourceOptimizer: Smart resource allocation recommendations
    TrendAnalyzer: Predictive trend analysis and forecasting
"""

import json
import math
import random
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .analytics import DeveloperMetrics, GitHistoryAnalyzer
from .core import RoadmapCore
from .models import Issue, Priority, Status


class RiskLevel(Enum):
    """Risk severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceLevel(Enum):
    """Prediction confidence levels."""

    LOW = "low"  # 0-60%
    MEDIUM = "medium"  # 60-80%
    HIGH = "high"  # 80-95%
    VERY_HIGH = "very_high"  # 95%+


@dataclass
class EstimationResult:
    """Result of issue time estimation."""

    issue_id: str
    estimated_hours: float
    confidence_level: ConfidenceLevel
    confidence_score: float
    factors_considered: List[str]
    similar_issues: List[str]
    complexity_score: float
    uncertainty_range: Tuple[float, float]  # (min_hours, max_hours)


@dataclass
class RiskAssessment:
    """Risk prediction result."""

    risk_id: str
    risk_type: str
    risk_level: RiskLevel
    probability: float
    impact_score: float
    description: str
    indicators: List[str]
    mitigation_suggestions: List[str]
    affected_issues: List[str]
    deadline_impact_days: Optional[int]


@dataclass
class DeadlineForecast:
    """Deadline prediction result."""

    target_date: datetime
    predicted_completion: datetime
    confidence_level: ConfidenceLevel
    delay_probability: float
    critical_path_issues: List[str]
    resource_constraints: List[str]
    optimization_suggestions: List[str]
    scenario_analysis: Dict[str, datetime]  # best/worst/likely case


@dataclass
class ResourceRecommendation:
    """Resource optimization suggestion."""

    recommendation_type: str
    priority: Priority
    description: str
    impact_assessment: str
    implementation_effort: str
    expected_benefits: List[str]
    affected_developers: List[str]
    timeline_improvement: Optional[float]


class IssueEstimator:
    """Machine learning-powered issue time estimation."""

    def __init__(
        self, core: RoadmapCore, analyzer: Optional[GitHistoryAnalyzer] = None
    ):
        self.core = core
        self.analyzer = analyzer or GitHistoryAnalyzer(core)
        self._historical_data = self._load_historical_data()
        self._complexity_weights = self._initialize_complexity_weights()

    def estimate_issue_time(
        self, issue: Issue, developer: Optional[str] = None
    ) -> EstimationResult:
        """Estimate completion time for an issue using ML algorithms."""

        # Analyze issue complexity
        complexity_score = self._calculate_complexity_score(issue)

        # Find similar historical issues
        similar_issues = self._find_similar_issues(issue, limit=10)

        # Calculate base estimation from historical data
        base_estimate = self._calculate_base_estimate(issue, similar_issues)

        # Apply developer-specific adjustments
        developer_factor = (
            self._get_developer_factor(developer, issue) if developer else 1.0
        )

        # Apply complexity and priority adjustments
        complexity_factor = self._get_complexity_factor(complexity_score)
        priority_factor = self._get_priority_factor(issue.priority)

        # Calculate final estimate
        estimated_hours = (
            base_estimate * developer_factor * complexity_factor * priority_factor
        )

        # Calculate uncertainty range
        uncertainty = self._calculate_uncertainty(similar_issues, complexity_score)
        min_hours = estimated_hours * (1 - uncertainty)
        max_hours = estimated_hours * (1 + uncertainty)

        # Determine confidence level
        confidence_score = self._calculate_confidence(
            similar_issues, complexity_score, developer
        )
        confidence_level = self._score_to_confidence_level(confidence_score)

        # Identify factors considered
        factors = self._identify_estimation_factors(issue, developer, similar_issues)

        return EstimationResult(
            issue_id=issue.id,
            estimated_hours=round(estimated_hours, 1),
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            factors_considered=factors,
            similar_issues=[i.id for i in similar_issues],
            complexity_score=complexity_score,
            uncertainty_range=(round(min_hours, 1), round(max_hours, 1)),
        )

    def batch_estimate_issues(self, issues: List[Issue]) -> List[EstimationResult]:
        """Estimate time for multiple issues efficiently."""
        return [self.estimate_issue_time(issue) for issue in issues]

    def _calculate_complexity_score(self, issue: Issue) -> float:
        """Calculate issue complexity score (0-10 scale)."""
        score = 0.0

        # Content length factor (using content instead of description)
        content_length = len(issue.content) if issue.content else 0
        score += min(content_length / 500, 2.0)  # Max 2 points

        # Priority factor
        priority_scores = {
            Priority.LOW: 1,
            Priority.MEDIUM: 2,
            Priority.HIGH: 3,
            Priority.CRITICAL: 4,
        }
        score += priority_scores.get(issue.priority, 1)

        # Dependencies factor (using depends_on instead of dependencies)
        if hasattr(issue, "depends_on") and issue.depends_on:
            score += min(len(issue.depends_on) * 0.5, 2.0)  # Max 2 points

        # Keywords indicating complexity
        complex_keywords = [
            "algorithm",
            "integration",
            "database",
            "api",
            "security",
            "performance",
            "optimization",
            "refactor",
            "architecture",
        ]
        content_lower = (issue.content or "").lower()
        keyword_matches = sum(
            1 for keyword in complex_keywords if keyword in content_lower
        )
        score += min(keyword_matches * 0.5, 2.0)  # Max 2 points

        return min(score, 10.0)

    def _find_similar_issues(self, issue: Issue, limit: int = 10) -> List[Issue]:
        """Find historically similar issues using text similarity and metadata."""
        all_issues = self.core.list_issues()
        completed_issues = [i for i in all_issues if i.status == Status.DONE]

        if not completed_issues:
            return []

        # Calculate similarity scores
        similarities = []
        for completed_issue in completed_issues:
            similarity = self._calculate_issue_similarity(issue, completed_issue)
            similarities.append((similarity, completed_issue))

        # Sort by similarity and return top matches
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in similarities[:limit]]

    def _calculate_issue_similarity(self, issue1: Issue, issue2: Issue) -> float:
        """Calculate similarity score between two issues."""
        score = 0.0

        # Priority similarity
        if issue1.priority == issue2.priority:
            score += 0.3

        # Title/content text similarity (simplified)
        text1 = f"{issue1.title} {issue1.content or ''}".lower()
        text2 = f"{issue2.title} {issue2.content or ''}".lower()

        # Simple word overlap similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        if words1 and words2:
            overlap = len(words1.intersection(words2))
            union = len(words1.union(words2))
            score += (overlap / union) * 0.4

        # Assignee similarity
        if hasattr(issue1, "assignee") and hasattr(issue2, "assignee"):
            if (
                issue1.assignee
                and issue2.assignee
                and issue1.assignee == issue2.assignee
            ):
                score += 0.3

        return score

    def _calculate_base_estimate(
        self, issue: Issue, similar_issues: List[Issue]
    ) -> float:
        """Calculate base time estimate from similar issues."""
        if not similar_issues:
            # Fallback estimation based on priority
            priority_hours = {
                Priority.LOW: 4.0,
                Priority.MEDIUM: 8.0,
                Priority.HIGH: 16.0,
                Priority.CRITICAL: 24.0,
            }
            return priority_hours.get(issue.priority, 8.0)

        # Use historical completion times if available
        completion_times = []
        for similar_issue in similar_issues:
            # Try to get actual completion time from git commits or estimates
            estimated_time = self._get_issue_completion_time(similar_issue)
            if estimated_time:
                completion_times.append(estimated_time)

        if completion_times:
            # Use weighted average with more weight on more similar issues
            weights = [1.0 / (i + 1) for i in range(len(completion_times))]
            weighted_avg = sum(t * w for t, w in zip(completion_times, weights)) / sum(
                weights
            )
            return weighted_avg

        # Fallback to priority-based estimation
        return self._calculate_base_estimate(issue, [])

    def _get_issue_completion_time(self, issue: Issue) -> Optional[float]:
        """Extract actual completion time for an issue."""
        # Check if issue has git commits with timing data
        if hasattr(issue, "git_commits") and issue.git_commits:
            commit_dates = []
            for commit in issue.git_commits:
                if isinstance(commit, dict) and "date" in commit:
                    try:
                        commit_date = datetime.fromisoformat(commit["date"])
                        commit_dates.append(commit_date)
                    except (ValueError, TypeError):
                        continue

            if len(commit_dates) >= 2:
                # Calculate time from first to last commit
                time_span = max(commit_dates) - min(commit_dates)
                return time_span.total_seconds() / 3600  # Convert to hours

        # Check if issue has estimated time
        if hasattr(issue, "estimated_time") and issue.estimated_time:
            return float(issue.estimated_time)

        # Fallback estimation based on content length and priority
        content_factor = len(issue.content) / 100 if issue.content else 1.0
        priority_factor = {
            Priority.LOW: 1,
            Priority.MEDIUM: 2,
            Priority.HIGH: 3,
            Priority.CRITICAL: 4,
        }
        return min(content_factor * priority_factor.get(issue.priority, 2), 40.0)

    def _get_developer_factor(self, developer: str, issue: Issue) -> float:
        """Get developer-specific adjustment factor."""
        try:
            # Get developer metrics
            metrics = self.analyzer.analyze_developer_productivity(developer, 90)

            # Adjust based on productivity score
            productivity_factor = metrics.productivity_score / 100

            # Adjust based on specialization match
            specialization_bonus = 1.0
            if metrics.specialization_areas:
                issue_text = f"{issue.title} {issue.content or ''}".lower()
                for specialization in metrics.specialization_areas:
                    if specialization.lower() in issue_text:
                        specialization_bonus = 0.8  # 20% faster for specialized work
                        break

            return max(
                0.5, min(2.0, (2.0 - productivity_factor) * specialization_bonus)
            )

        except Exception:
            return 1.0  # Default factor if analysis fails

    def _get_complexity_factor(self, complexity_score: float) -> float:
        """Get time adjustment factor based on complexity."""
        # Linear scaling from 0.8x (simple) to 2.0x (very complex)
        return 0.8 + (complexity_score / 10.0) * 1.2

    def _get_priority_factor(self, priority: Priority) -> float:
        """Get time adjustment factor based on priority."""
        # Higher priority often means more careful work and testing
        factors = {
            Priority.LOW: 0.9,
            Priority.MEDIUM: 1.0,
            Priority.HIGH: 1.1,
            Priority.CRITICAL: 1.3,
        }
        return factors.get(priority, 1.0)

    def _calculate_uncertainty(
        self, similar_issues: List[Issue], complexity_score: float
    ) -> float:
        """Calculate estimation uncertainty as a percentage."""
        base_uncertainty = 0.3  # 30% base uncertainty

        # Reduce uncertainty with more similar issues
        similarity_factor = max(0.1, 1.0 - (len(similar_issues) * 0.05))

        # Increase uncertainty with higher complexity
        complexity_factor = 1.0 + (complexity_score / 20.0)

        return min(0.8, base_uncertainty * similarity_factor * complexity_factor)

    def _calculate_confidence(
        self,
        similar_issues: List[Issue],
        complexity_score: float,
        developer: Optional[str],
    ) -> float:
        """Calculate prediction confidence score (0-100)."""
        confidence = 50.0  # Base confidence

        # Increase confidence with more similar issues
        confidence += min(len(similar_issues) * 5, 30)

        # Decrease confidence with higher complexity
        confidence -= complexity_score * 2

        # Increase confidence if developer is specified and has good metrics
        if developer:
            try:
                metrics = self.analyzer.analyze_developer_productivity(developer, 90)
                if metrics.total_commits > 10:  # Experienced developer
                    confidence += 10
            except Exception:
                pass

        return max(0, min(100, confidence))

    def _score_to_confidence_level(self, score: float) -> ConfidenceLevel:
        """Convert confidence score to confidence level."""
        if score >= 95:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 80:
            return ConfidenceLevel.HIGH
        elif score >= 60:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _identify_estimation_factors(
        self, issue: Issue, developer: Optional[str], similar_issues: List[Issue]
    ) -> List[str]:
        """Identify factors that influenced the estimation."""
        factors = []

        if similar_issues:
            factors.append(f"Based on {len(similar_issues)} similar historical issues")

        if developer:
            factors.append(f"Adjusted for developer: {developer}")

        complexity = self._calculate_complexity_score(issue)
        if complexity > 7:
            factors.append("High complexity issue")
        elif complexity < 3:
            factors.append("Low complexity issue")

        if issue.priority in [Priority.HIGH, Priority.CRITICAL]:
            factors.append("High priority requiring extra care")

        return factors

    def _load_historical_data(self) -> Dict[str, Any]:
        """Load historical estimation data for ML training."""
        # This could load from a dedicated analytics database
        # For now, we'll use the existing issue data
        return {}

    def _initialize_complexity_weights(self) -> Dict[str, float]:
        """Initialize ML weights for complexity calculation."""
        return {
            "description_length": 0.2,
            "priority": 0.3,
            "dependencies": 0.2,
            "keywords": 0.3,
        }


class RiskPredictor:
    """Proactive risk assessment and prediction system."""

    def __init__(
        self, core: RoadmapCore, analyzer: Optional[GitHistoryAnalyzer] = None
    ):
        self.core = core
        self.analyzer = analyzer or GitHistoryAnalyzer(core)
        self.risk_patterns = self._initialize_risk_patterns()

    def assess_project_risks(self, days_ahead: int = 30) -> List[RiskAssessment]:
        """Assess potential project risks for the coming period."""
        risks = []

        # Analyze different risk categories
        risks.extend(self._assess_deadline_risks(days_ahead))
        risks.extend(self._assess_resource_risks())
        risks.extend(self._assess_quality_risks())
        risks.extend(self._assess_dependency_risks())
        risks.extend(self._assess_team_risks())

        # Sort by risk level and probability
        risks.sort(key=lambda r: (r.risk_level.value, -r.probability))

        return risks

    def predict_issue_risks(self, issue: Issue) -> List[RiskAssessment]:
        """Predict risks specific to an individual issue."""
        risks = []

        # Complexity-based risk
        if self._is_high_complexity_issue(issue):
            risks.append(self._create_complexity_risk(issue))

        # Dependency risk
        if hasattr(issue, "depends_on") and issue.depends_on:
            risks.append(self._create_dependency_risk(issue))

        # Assignee risk
        if hasattr(issue, "assignee") and issue.assignee:
            assignee_risk = self._assess_assignee_risk(issue, issue.assignee)
            if assignee_risk:
                risks.append(assignee_risk)

        return risks

    def _assess_deadline_risks(self, days_ahead: int) -> List[RiskAssessment]:
        """Assess risks related to missing deadlines."""
        risks = []

        # Get upcoming deadlines
        issues = self.core.list_issues()
        upcoming_issues = [
            issue
            for issue in issues
            if (
                issue.status in [Status.TODO, Status.IN_PROGRESS]
                and hasattr(issue, "due_date")
                and issue.due_date
            )
        ]

        if not upcoming_issues:
            return risks

        # Analyze workload vs. capacity
        total_estimated_work = sum(
            self._estimate_remaining_work(issue) for issue in upcoming_issues
        )

        # Get team capacity estimation
        team_capacity = self._estimate_team_capacity(days_ahead)

        if total_estimated_work > team_capacity * 1.2:  # 20% buffer
            risks.append(
                RiskAssessment(
                    risk_id="deadline_overload",
                    risk_type="Deadline Risk",
                    risk_level=RiskLevel.HIGH,
                    probability=0.8,
                    impact_score=8.0,
                    description="Current workload exceeds team capacity, deadline misses likely",
                    indicators=[
                        f"Estimated work: {total_estimated_work:.1f} hours",
                        f"Team capacity: {team_capacity:.1f} hours",
                        f"Overload: {((total_estimated_work / team_capacity - 1) * 100):.1f}%",
                    ],
                    mitigation_suggestions=[
                        "Prioritize critical issues and defer non-essential work",
                        "Consider adding temporary resources or extending deadlines",
                        "Break down large issues into smaller, manageable tasks",
                    ],
                    affected_issues=[issue.id for issue in upcoming_issues],
                    deadline_impact_days=int(
                        (total_estimated_work - team_capacity) / 8
                    ),
                )
            )

        return risks

    def _assess_resource_risks(self) -> List[RiskAssessment]:
        """Assess risks related to resource allocation and availability."""
        risks = []

        # Single point of failure risk
        if self.analyzer.git_integration.is_git_repository():
            try:
                team_insights = self.analyzer.generate_team_insights(30)

                if team_insights.total_developers == 1:
                    risks.append(
                        RiskAssessment(
                            risk_id="single_developer",
                            risk_type="Resource Risk",
                            risk_level=RiskLevel.HIGH,
                            probability=0.9,
                            impact_score=9.0,
                            description="Single developer dependency creates high risk",
                            indicators=["Only one active developer in the project"],
                            mitigation_suggestions=[
                                "Add additional team members",
                                "Cross-train existing developer",
                                "Document critical knowledge and processes",
                            ],
                            affected_issues=[],
                            deadline_impact_days=None,
                        )
                    )

                # Analyze workload distribution
                if "workload_distribution" in team_insights.collaboration_patterns:
                    distribution = team_insights.collaboration_patterns[
                        "workload_distribution"
                    ]
                    if (
                        max(distribution.values()) > 0.7
                    ):  # One person doing >70% of work
                        risks.append(
                            RiskAssessment(
                                risk_id="workload_imbalance",
                                risk_type="Resource Risk",
                                risk_level=RiskLevel.MEDIUM,
                                probability=0.7,
                                impact_score=6.0,
                                description="Uneven workload distribution across team members",
                                indicators=[
                                    "Workload concentration in single developer"
                                ],
                                mitigation_suggestions=[
                                    "Redistribute tasks more evenly",
                                    "Provide mentoring for less active team members",
                                    "Review task assignment strategy",
                                ],
                                affected_issues=[],
                                deadline_impact_days=None,
                            )
                        )

            except Exception:
                pass  # Skip if Git analysis fails

        return risks

    def _assess_quality_risks(self) -> List[RiskAssessment]:
        """Assess risks related to code quality and technical debt."""
        risks = []

        try:
            quality_trends = self.analyzer.analyze_code_quality_trends(90)

            # High bug ratio risk
            if quality_trends.get("bug_fix_ratio", 0) > 0.4:
                risks.append(
                    RiskAssessment(
                        risk_id="high_bug_ratio",
                        risk_type="Quality Risk",
                        risk_level=RiskLevel.MEDIUM,
                        probability=0.8,
                        impact_score=6.0,
                        description="High proportion of bug fixes indicates quality issues",
                        indicators=[
                            f"Bug fix ratio: {quality_trends['bug_fix_ratio']*100:.1f}%"
                        ],
                        mitigation_suggestions=[
                            "Increase code review requirements",
                            "Add more comprehensive testing",
                            "Schedule dedicated quality improvement time",
                        ],
                        affected_issues=[],
                        deadline_impact_days=None,
                    )
                )

            # Large commits risk
            if quality_trends.get("large_commits_ratio", 0) > 0.3:
                risks.append(
                    RiskAssessment(
                        risk_id="large_commits",
                        risk_type="Quality Risk",
                        risk_level=RiskLevel.LOW,
                        probability=0.6,
                        impact_score=4.0,
                        description="Frequent large commits may indicate poor planning",
                        indicators=[
                            f"Large commits: {quality_trends['large_commits_ratio']*100:.1f}%"
                        ],
                        mitigation_suggestions=[
                            "Encourage smaller, more frequent commits",
                            "Break down large features into smaller tasks",
                            "Implement feature flag development practices",
                        ],
                        affected_issues=[],
                        deadline_impact_days=None,
                    )
                )

        except Exception:
            pass  # Skip if quality analysis fails

        return risks

    def _assess_dependency_risks(self) -> List[RiskAssessment]:
        """Assess risks related to issue dependencies."""
        risks = []

        issues = self.core.list_issues()

        # Find issues with many dependencies
        high_dependency_issues = [
            issue
            for issue in issues
            if (
                hasattr(issue, "depends_on")
                and issue.depends_on
                and len(issue.depends_on) > 3
            )
        ]

        if high_dependency_issues:
            risks.append(
                RiskAssessment(
                    risk_id="complex_dependencies",
                    risk_type="Dependency Risk",
                    risk_level=RiskLevel.MEDIUM,
                    probability=0.7,
                    impact_score=7.0,
                    description="Issues with complex dependency chains may cause delays",
                    indicators=[
                        f"{len(high_dependency_issues)} issues with 4+ dependencies"
                    ],
                    mitigation_suggestions=[
                        "Simplify dependency chains where possible",
                        "Prioritize dependency resolution",
                        "Create parallel work streams to reduce blocking",
                    ],
                    affected_issues=[issue.id for issue in high_dependency_issues],
                    deadline_impact_days=None,
                )
            )

        return risks

    def _assess_team_risks(self) -> List[RiskAssessment]:
        """Assess risks related to team dynamics and collaboration."""
        risks = []

        try:
            team_insights = self.analyzer.generate_team_insights(30)

            # Low collaboration risk
            if team_insights.total_developers > 1:
                collaboration_score = team_insights.collaboration_patterns.get(
                    "avg_collaboration_score", 0
                )
                if collaboration_score < 30:
                    risks.append(
                        RiskAssessment(
                            risk_id="low_collaboration",
                            risk_type="Team Risk",
                            risk_level=RiskLevel.MEDIUM,
                            probability=0.6,
                            impact_score=5.0,
                            description="Low team collaboration may lead to knowledge silos",
                            indicators=[
                                f"Low collaboration score: {collaboration_score}"
                            ],
                            mitigation_suggestions=[
                                "Encourage pair programming sessions",
                                "Implement mandatory code reviews",
                                "Schedule regular team knowledge sharing",
                            ],
                            affected_issues=[],
                            deadline_impact_days=None,
                        )
                    )

        except Exception:
            pass  # Skip if team analysis fails

        return risks

    def _is_high_complexity_issue(self, issue: Issue) -> bool:
        """Determine if an issue is high complexity."""
        estimator = IssueEstimator(self.core, self.analyzer)
        complexity = estimator._calculate_complexity_score(issue)
        return complexity > 7.0

    def _create_complexity_risk(self, issue: Issue) -> RiskAssessment:
        """Create a risk assessment for a complex issue."""
        return RiskAssessment(
            risk_id=f"complexity_{issue.id}",
            risk_type="Complexity Risk",
            risk_level=RiskLevel.MEDIUM,
            probability=0.7,
            impact_score=6.0,
            description=f"Issue '{issue.title}' has high complexity and may take longer than expected",
            indicators=[
                "High complexity score",
                "Multiple technical components involved",
            ],
            mitigation_suggestions=[
                "Break down into smaller sub-tasks",
                "Assign to experienced developer",
                "Plan for additional testing and review time",
            ],
            affected_issues=[issue.id],
            deadline_impact_days=None,
        )

    def _create_dependency_risk(self, issue: Issue) -> RiskAssessment:
        """Create a risk assessment for dependency-heavy issue."""
        dep_count = len(issue.depends_on) if hasattr(issue, "depends_on") else 0

        return RiskAssessment(
            risk_id=f"dependency_{issue.id}",
            risk_type="Dependency Risk",
            risk_level=RiskLevel.MEDIUM if dep_count < 5 else RiskLevel.HIGH,
            probability=0.6,
            impact_score=5.0 + min(dep_count, 5),
            description=f"Issue '{issue.title}' has {dep_count} dependencies that may cause delays",
            indicators=[f"{dep_count} dependencies", "Potential blocking chain"],
            mitigation_suggestions=[
                "Prioritize dependency resolution",
                "Create parallel workstreams where possible",
                "Establish clear dependency timeline",
            ],
            affected_issues=[issue.id],
            deadline_impact_days=dep_count * 2,
        )

    def _assess_assignee_risk(
        self, issue: Issue, assignee: str
    ) -> Optional[RiskAssessment]:
        """Assess risk based on assignee workload and performance."""
        try:
            metrics = self.analyzer.analyze_developer_productivity(assignee, 30)

            # Check if developer is overloaded
            if metrics.avg_commits_per_day > 5:  # High activity might indicate overload
                return RiskAssessment(
                    risk_id=f"overload_{assignee}_{issue.id}",
                    risk_type="Assignee Risk",
                    risk_level=RiskLevel.MEDIUM,
                    probability=0.5,
                    impact_score=5.0,
                    description=f"Developer {assignee} may be overloaded",
                    indicators=[
                        f"High activity: {metrics.avg_commits_per_day:.1f} commits/day"
                    ],
                    mitigation_suggestions=[
                        "Consider redistributing some tasks",
                        "Monitor developer workload carefully",
                        "Provide additional support if needed",
                    ],
                    affected_issues=[issue.id],
                    deadline_impact_days=None,
                )

        except Exception:
            pass

        return None

    def _estimate_remaining_work(self, issue: Issue) -> float:
        """Estimate remaining work hours for an issue."""
        estimator = IssueEstimator(self.core, self.analyzer)

        if issue.status == Status.TODO:
            estimation = estimator.estimate_issue_time(issue)
            return estimation.estimated_hours
        elif issue.status == Status.IN_PROGRESS:
            estimation = estimator.estimate_issue_time(issue)
            return estimation.estimated_hours * 0.6  # Assume 40% complete
        else:
            return 0.0

    def _estimate_team_capacity(self, days: int) -> float:
        """Estimate total team capacity in hours for the given period."""
        try:
            team_insights = self.analyzer.generate_team_insights(30)

            # Estimate based on current team velocity
            daily_capacity_per_dev = 6  # 6 productive hours per day per developer
            total_capacity = (
                team_insights.total_developers * daily_capacity_per_dev * days
            )

            # Adjust based on historical productivity
            productivity_factor = team_insights.avg_team_velocity / 100
            return total_capacity * productivity_factor

        except Exception:
            # Fallback estimation
            return days * 6  # Assume single developer, 6 hours/day

    def _initialize_risk_patterns(self) -> Dict[str, Any]:
        """Initialize risk detection patterns and thresholds."""
        return {
            "deadline_buffer": 0.2,  # 20% buffer for deadline risks
            "quality_thresholds": {
                "bug_ratio": 0.3,
                "large_commits": 0.25,
                "complexity_threshold": 7.0,
            },
            "team_thresholds": {"collaboration_minimum": 30, "workload_balance": 0.7},
        }


class DeadlineForecaster:
    """Intelligent deadline prediction and scenario analysis."""

    def __init__(
        self,
        core: RoadmapCore,
        estimator: Optional[IssueEstimator] = None,
        risk_predictor: Optional[RiskPredictor] = None,
    ):
        self.core = core
        self.estimator = estimator or IssueEstimator(core)
        self.risk_predictor = risk_predictor or RiskPredictor(core)

    def forecast_project_completion(
        self, target_date: Optional[datetime] = None
    ) -> DeadlineForecast:
        """Forecast project completion date with scenario analysis."""

        # Get all remaining work
        remaining_issues = [
            issue
            for issue in self.core.list_issues()
            if issue.status in [Status.TODO, Status.IN_PROGRESS]
        ]

        if not remaining_issues:
            return self._create_no_work_forecast(target_date)

        # Estimate total remaining work
        total_work_estimates = self.estimator.batch_estimate_issues(remaining_issues)
        total_hours = sum(est.estimated_hours for est in total_work_estimates)

        # Analyze critical path
        critical_path = self._identify_critical_path(remaining_issues)

        # Assess risks that could impact timeline
        risks = self.risk_predictor.assess_project_risks(90)
        timeline_risks = [r for r in risks if r.deadline_impact_days]

        # Calculate completion predictions
        predictions = self._calculate_completion_scenarios(
            total_hours, timeline_risks, remaining_issues
        )

        # Determine most likely completion date
        predicted_completion = predictions["likely"]

        # Calculate delay probability if target date is specified
        delay_probability = 0.0
        if target_date:
            delay_probability = self._calculate_delay_probability(
                target_date, predicted_completion, predictions
            )

        # Generate optimization suggestions
        optimization_suggestions = self._generate_optimization_suggestions(
            remaining_issues, total_work_estimates, risks
        )

        # Identify resource constraints
        resource_constraints = self._identify_resource_constraints(risks)

        return DeadlineForecast(
            target_date=target_date or predicted_completion,
            predicted_completion=predicted_completion,
            confidence_level=self._calculate_forecast_confidence(
                total_work_estimates, risks
            ),
            delay_probability=delay_probability,
            critical_path_issues=[issue.id for issue in critical_path],
            resource_constraints=resource_constraints,
            optimization_suggestions=optimization_suggestions,
            scenario_analysis=predictions,
        )

    def forecast_milestone_completion(
        self, milestone_issues: List[str]
    ) -> DeadlineForecast:
        """Forecast completion of a specific milestone."""
        issues = [
            issue
            for issue in self.core.list_issues()
            if issue.id in milestone_issues
            and issue.status in [Status.TODO, Status.IN_PROGRESS]
        ]

        # Temporarily focus on just these issues
        temp_core = self._create_scoped_core(issues)
        temp_forecaster = DeadlineForecaster(
            temp_core, self.estimator, self.risk_predictor
        )

        return temp_forecaster.forecast_project_completion()

    def _identify_critical_path(self, issues: List[Issue]) -> List[Issue]:
        """Identify the critical path through remaining issues."""
        # For now, use a simple heuristic: highest priority + longest estimated time
        # In a more sophisticated implementation, this would analyze dependencies

        estimates = self.estimator.batch_estimate_issues(issues)
        issue_priorities = {
            Priority.CRITICAL: 4,
            Priority.HIGH: 3,
            Priority.MEDIUM: 2,
            Priority.LOW: 1,
        }

        # Score issues by priority and estimated time
        scored_issues = []
        for issue, estimate in zip(issues, estimates):
            priority_score = issue_priorities.get(issue.priority, 1)
            time_score = estimate.estimated_hours / 10  # Normalize hours
            total_score = priority_score * 2 + time_score
            scored_issues.append((total_score, issue))

        # Sort by score and take top 30% as critical path
        scored_issues.sort(key=lambda x: x[0], reverse=True)
        critical_count = max(1, len(scored_issues) // 3)

        return [item[1] for item in scored_issues[:critical_count]]

    def _calculate_completion_scenarios(
        self, total_hours: float, risks: List[RiskAssessment], issues: List[Issue]
    ) -> Dict[str, datetime]:
        """Calculate best/worst/likely case completion scenarios."""

        # Estimate team capacity (hours per day)
        base_daily_capacity = (
            6  # 6 productive hours per day (assuming single developer)
        )

        # Best case: 20% faster than estimated
        best_case_days = (total_hours * 0.8) / base_daily_capacity
        best_case = datetime.now() + timedelta(days=best_case_days)

        # Worst case: account for all risks + 50% buffer
        risk_days = sum(r.deadline_impact_days or 0 for r in risks)
        worst_case_days = (total_hours * 1.5) / base_daily_capacity + risk_days
        worst_case = datetime.now() + timedelta(days=worst_case_days)

        # Likely case: moderate optimism with some risk impact
        likely_multiplier = 1.1  # 10% optimism buffer
        partial_risk_days = risk_days * 0.3  # 30% of identified risks materialize
        likely_case_days = (
            total_hours * likely_multiplier
        ) / base_daily_capacity + partial_risk_days
        likely_case = datetime.now() + timedelta(days=likely_case_days)

        return {"best": best_case, "worst": worst_case, "likely": likely_case}

    def _calculate_delay_probability(
        self,
        target_date: datetime,
        predicted_date: datetime,
        scenarios: Dict[str, datetime],
    ) -> float:
        """Calculate probability of missing target date."""

        if predicted_date <= target_date:
            # Even likely case meets target
            days_buffer = (target_date - predicted_date).days
            if days_buffer > 7:
                return 0.1  # Very low probability
            else:
                return 0.2  # Low probability but cutting it close
        else:
            # Likely case misses target
            days_over = (predicted_date - target_date).days
            if scenarios["best"] > target_date:
                return 0.9  # Even best case misses - very high probability
            elif days_over < 7:
                return 0.6  # Moderate probability
            else:
                return 0.8  # High probability

    def _generate_optimization_suggestions(
        self,
        issues: List[Issue],
        estimates: List[EstimationResult],
        risks: List[RiskAssessment],
    ) -> List[str]:
        """Generate suggestions to optimize timeline."""
        suggestions = []

        # Analyze estimates for optimization opportunities
        high_uncertainty = [
            e for e in estimates if e.confidence_level in [ConfidenceLevel.LOW]
        ]
        if high_uncertainty:
            suggestions.append(
                f"Break down {len(high_uncertainty)} uncertain issues into smaller tasks"
            )

        # Analyze risks for mitigation
        high_risks = [
            r for r in risks if r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]
        if high_risks:
            suggestions.append(
                f"Address {len(high_risks)} high-priority risks immediately"
            )

        # Priority optimization
        low_priority_issues = [i for i in issues if i.priority == Priority.LOW]
        if low_priority_issues:
            suggestions.append(
                f"Consider deferring {len(low_priority_issues)} low-priority issues"
            )

        # Parallelization opportunities
        if len(issues) > 3:
            suggestions.append(
                "Look for opportunities to parallelize independent work streams"
            )

        return suggestions

    def _identify_resource_constraints(self, risks: List[RiskAssessment]) -> List[str]:
        """Identify resource-related constraints affecting timeline."""
        constraints = []

        for risk in risks:
            if risk.risk_type == "Resource Risk":
                constraints.append(risk.description)
            elif "resource" in risk.description.lower():
                constraints.append(risk.description)

        if not constraints:
            constraints.append("No significant resource constraints identified")

        return constraints

    def _calculate_forecast_confidence(
        self, estimates: List[EstimationResult], risks: List[RiskAssessment]
    ) -> ConfidenceLevel:
        """Calculate overall confidence in the forecast."""

        # Average confidence from estimates
        estimate_confidence = statistics.mean(
            self._confidence_level_to_score(e.confidence_level) for e in estimates
        )

        # Adjust for risks
        high_risk_count = len(
            [r for r in risks if r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]
        )
        risk_penalty = high_risk_count * 10

        final_score = max(0, estimate_confidence - risk_penalty)

        return self._score_to_confidence_level(final_score)

    def _confidence_level_to_score(self, level: ConfidenceLevel) -> float:
        """Convert confidence level to numeric score."""
        mapping = {
            ConfidenceLevel.LOW: 30,
            ConfidenceLevel.MEDIUM: 50,
            ConfidenceLevel.HIGH: 75,
            ConfidenceLevel.VERY_HIGH: 90,
        }
        return mapping.get(level, 30)

    def _score_to_confidence_level(self, score: float) -> ConfidenceLevel:
        """Convert numeric score to confidence level."""
        if score >= 85:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 70:
            return ConfidenceLevel.HIGH
        elif score >= 50:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _create_no_work_forecast(
        self, target_date: Optional[datetime]
    ) -> DeadlineForecast:
        """Create forecast when no work remains."""
        completion_date = datetime.now()

        return DeadlineForecast(
            target_date=target_date or completion_date,
            predicted_completion=completion_date,
            confidence_level=ConfidenceLevel.VERY_HIGH,
            delay_probability=0.0,
            critical_path_issues=[],
            resource_constraints=[],
            optimization_suggestions=["All work completed!"],
            scenario_analysis={
                "best": completion_date,
                "worst": completion_date,
                "likely": completion_date,
            },
        )

    def _create_scoped_core(self, issues: List[Issue]) -> RoadmapCore:
        """Create a temporary core instance scoped to specific issues."""
        # This is a simplified implementation
        # In practice, you might want a more sophisticated scoping mechanism
        return self.core


class PredictiveReportGenerator:
    """Generate comprehensive predictive intelligence reports."""

    def __init__(self, core: RoadmapCore):
        self.core = core
        self.estimator = IssueEstimator(core)
        self.risk_predictor = RiskPredictor(core)
        self.forecaster = DeadlineForecaster(core, self.estimator, self.risk_predictor)

    def generate_intelligence_report(
        self, target_date: Optional[datetime] = None, save_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive predictive intelligence report."""

        try:
            # Get all active issues
            active_issues = [
                issue
                for issue in self.core.list_issues()
                if issue.status in [Status.TODO, Status.IN_PROGRESS]
            ]

            # Generate predictions and assessments
            deadline_forecast = self.forecaster.forecast_project_completion(target_date)
            risk_assessments = self.risk_predictor.assess_project_risks(30)
            issue_estimates = self.estimator.batch_estimate_issues(active_issues)

            # Compile report
            report = {
                "report_generated": datetime.now().isoformat(),
                "target_date": target_date.isoformat() if target_date else None,
                "project_forecast": {
                    "predicted_completion": deadline_forecast.predicted_completion.isoformat(),
                    "confidence_level": deadline_forecast.confidence_level.value,
                    "delay_probability": deadline_forecast.delay_probability,
                    "scenario_analysis": {
                        scenario: date.isoformat()
                        for scenario, date in deadline_forecast.scenario_analysis.items()
                    },
                },
                "risk_analysis": {
                    "total_risks_identified": len(risk_assessments),
                    "high_priority_risks": len(
                        [
                            r
                            for r in risk_assessments
                            if r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
                        ]
                    ),
                    "risk_breakdown": self._summarize_risks(risk_assessments),
                    "top_risks": [self._risk_to_dict(r) for r in risk_assessments[:5]],
                },
                "work_estimates": {
                    "total_issues": len(active_issues),
                    "total_estimated_hours": sum(
                        e.estimated_hours for e in issue_estimates
                    ),
                    "average_confidence": (
                        statistics.mean(
                            self._confidence_to_score(e.confidence_level)
                            for e in issue_estimates
                        )
                        if issue_estimates
                        else 0
                    ),
                    "high_uncertainty_issues": len(
                        [
                            e
                            for e in issue_estimates
                            if e.confidence_level == ConfidenceLevel.LOW
                        ]
                    ),
                },
                "optimization_recommendations": deadline_forecast.optimization_suggestions,
                "resource_constraints": deadline_forecast.resource_constraints,
                "critical_path": deadline_forecast.critical_path_issues,
                "detailed_estimates": [
                    self._estimate_to_dict(e) for e in issue_estimates
                ],
            }

            # Save to file if requested
            if save_file:
                self._save_report_to_file(report, save_file)

            return report

        except Exception as e:
            return {
                "error": f"Failed to generate intelligence report: {str(e)}",
                "report_generated": datetime.now().isoformat(),
            }

    def _summarize_risks(self, risks: List[RiskAssessment]) -> Dict[str, int]:
        """Summarize risks by type and level."""
        summary = {}

        # By risk level
        for level in RiskLevel:
            summary[f"{level.value}_risk_count"] = len(
                [r for r in risks if r.risk_level == level]
            )

        # By risk type
        risk_types = set(r.risk_type for r in risks)
        for risk_type in risk_types:
            summary[f'{risk_type.lower().replace(" ", "_")}_count'] = len(
                [r for r in risks if r.risk_type == risk_type]
            )

        return summary

    def _risk_to_dict(self, risk: RiskAssessment) -> Dict[str, Any]:
        """Convert risk assessment to dictionary."""
        return {
            "risk_id": risk.risk_id,
            "type": risk.risk_type,
            "level": risk.risk_level.value,
            "probability": risk.probability,
            "impact_score": risk.impact_score,
            "description": risk.description,
            "indicators": risk.indicators,
            "mitigation_suggestions": risk.mitigation_suggestions,
            "affected_issues_count": len(risk.affected_issues),
            "deadline_impact_days": risk.deadline_impact_days,
        }

    def _estimate_to_dict(self, estimate: EstimationResult) -> Dict[str, Any]:
        """Convert estimation result to dictionary."""
        return {
            "issue_id": estimate.issue_id,
            "estimated_hours": estimate.estimated_hours,
            "confidence_level": estimate.confidence_level.value,
            "confidence_score": estimate.confidence_score,
            "factors_considered": estimate.factors_considered,
            "similar_issues_count": len(estimate.similar_issues),
            "complexity_score": estimate.complexity_score,
            "uncertainty_range": {
                "min_hours": estimate.uncertainty_range[0],
                "max_hours": estimate.uncertainty_range[1],
            },
        }

    def _confidence_to_score(self, level: ConfidenceLevel) -> float:
        """Convert confidence level to numeric score."""
        mapping = {
            ConfidenceLevel.LOW: 30,
            ConfidenceLevel.MEDIUM: 50,
            ConfidenceLevel.HIGH: 75,
            ConfidenceLevel.VERY_HIGH: 90,
        }
        return mapping.get(level, 30)

    def _save_report_to_file(self, report: Dict[str, Any], filename: str) -> str:
        """Save report to JSON file."""
        if not filename.endswith(".json"):
            filename += ".json"

        # Add timestamp if not in filename
        if "intelligence_report" not in filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"intelligence_report_{timestamp}.json"

        file_path = Path(filename)
        with open(file_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        return str(file_path.absolute())
