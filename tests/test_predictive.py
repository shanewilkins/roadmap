"""Comprehensive tests for predictive intelligence functionality."""

import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.core import RoadmapCore
from roadmap.models import Issue, Priority, Status
from roadmap.predictive import (
    ConfidenceLevel,
    DeadlineForecast,
    DeadlineForecaster,
    EstimationResult,
    IssueEstimator,
    PredictiveReportGenerator,
    RiskAssessment,
    RiskLevel,
    RiskPredictor,
)

pytestmark = pytest.mark.unit


class TestIssueEstimator:
    """Test ML-powered issue estimation functionality."""

    @pytest.fixture
    def temp_roadmap(self):
        """Create a temporary roadmap for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Initialize roadmap
            core = RoadmapCore()
            core.initialize()

            yield temp_dir, core

    def test_estimator_initialization(self, temp_roadmap):
        """Test IssueEstimator initialization."""
        _, core = temp_roadmap

        estimator = IssueEstimator(core)

        assert estimator.core == core
        assert estimator.analyzer is not None
        assert isinstance(estimator._complexity_weights, dict)

    def test_complexity_score_calculation(self, temp_roadmap):
        """Test complexity score calculation."""
        _, core = temp_roadmap
        estimator = IssueEstimator(core)

        # Simple issue
        simple_issue = Issue(
            id="simple",
            title="Simple task",
            content="Basic functionality",
            priority=Priority.LOW,
        )
        score1 = estimator._calculate_complexity_score(simple_issue)

        # Complex issue
        complex_issue = Issue(
            id="complex",
            title="Complex algorithm implementation",
            content="Implement complex algorithm with database integration, API calls, "
            "performance optimization, and security considerations. This requires "
            "architectural changes and refactoring of existing code.",
            priority=Priority.CRITICAL,
            depends_on=["dep1", "dep2", "dep3"],
        )
        score2 = estimator._calculate_complexity_score(complex_issue)

        assert 0 <= score1 <= 10
        assert 0 <= score2 <= 10
        assert score2 > score1  # Complex issue should have higher score

    def test_issue_similarity_calculation(self, temp_roadmap):
        """Test issue similarity calculation."""
        _, core = temp_roadmap
        estimator = IssueEstimator(core)

        issue1 = Issue(
            id="1",
            title="API implementation",
            content="Implement REST API endpoints",
            priority=Priority.HIGH,
            assignee="Alice",
        )

        # Similar issue
        issue2 = Issue(
            id="2",
            title="API testing",
            content="Create tests for REST API endpoints",
            priority=Priority.HIGH,
            assignee="Alice",
        )

        # Different issue
        issue3 = Issue(
            id="3",
            title="Update documentation",
            content="Fix typos in README",
            priority=Priority.LOW,
            assignee="Bob",
        )

        similarity1 = estimator._calculate_issue_similarity(issue1, issue2)
        similarity2 = estimator._calculate_issue_similarity(issue1, issue3)

        assert 0 <= similarity1 <= 1
        assert 0 <= similarity2 <= 1
        assert similarity1 > similarity2  # Similar issues should have higher similarity

    def test_estimate_issue_time(self, temp_roadmap):
        """Test individual issue time estimation."""
        _, core = temp_roadmap

        # Create some historical issues
        completed_issue1 = Issue(
            id="hist1",
            title="API work",
            content="API implementation",
            status=Status.DONE,
            priority=Priority.MEDIUM,
        )
        completed_issue2 = Issue(
            id="hist2",
            title="Database task",
            content="Database optimization",
            status=Status.DONE,
            priority=Priority.HIGH,
        )

        # Save historical issues
        from roadmap.parser import IssueParser

        IssueParser.save_issue_file(
            completed_issue1, core.issues_dir / completed_issue1.filename
        )
        IssueParser.save_issue_file(
            completed_issue2, core.issues_dir / completed_issue2.filename
        )

        estimator = IssueEstimator(core)

        # Test issue to estimate
        test_issue = Issue(
            id="test",
            title="New API feature",
            content="Implement new API endpoints with authentication",
            priority=Priority.HIGH,
        )

        result = estimator.estimate_issue_time(test_issue)

        # Verify estimation result
        assert isinstance(result, EstimationResult)
        assert result.issue_id == "test"
        assert result.estimated_hours > 0
        assert isinstance(result.confidence_level, ConfidenceLevel)
        assert 0 <= result.confidence_score <= 100
        assert isinstance(result.factors_considered, list)
        assert len(result.factors_considered) > 0
        assert isinstance(result.uncertainty_range, tuple)
        assert len(result.uncertainty_range) == 2
        assert result.uncertainty_range[0] < result.uncertainty_range[1]

    def test_batch_estimate_issues(self, temp_roadmap):
        """Test batch estimation of multiple issues."""
        _, core = temp_roadmap
        estimator = IssueEstimator(core)

        issues = [
            Issue(id="1", title="Task 1", content="Simple task", priority=Priority.LOW),
            Issue(
                id="2",
                title="Task 2",
                content="Medium complexity",
                priority=Priority.MEDIUM,
            ),
            Issue(
                id="3",
                title="Task 3",
                content="Complex algorithm work",
                priority=Priority.HIGH,
            ),
        ]

        results = estimator.batch_estimate_issues(issues)

        assert len(results) == 3
        assert all(isinstance(r, EstimationResult) for r in results)
        assert all(r.estimated_hours > 0 for r in results)

        # Verify IDs match
        result_ids = [r.issue_id for r in results]
        expected_ids = [i.id for i in issues]
        assert result_ids == expected_ids

    def test_developer_factor_calculation(self, temp_roadmap):
        """Test developer-specific adjustment factors."""
        _, core = temp_roadmap

        with patch("roadmap.predictive.GitHistoryAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_metrics = Mock()
            mock_metrics.productivity_score = 80.0
            mock_metrics.specialization_areas = ["Python", "API"]
            mock_analyzer.analyze_developer_productivity.return_value = mock_metrics
            mock_analyzer_class.return_value = mock_analyzer

            estimator = IssueEstimator(core, mock_analyzer)

            # Test issue with matching specialization
            api_issue = Issue(
                id="api",
                title="Python API development",
                content="Build Python REST API",
                priority=Priority.MEDIUM,
            )

            factor = estimator._get_developer_factor("Alice", api_issue)

            assert 0.5 <= factor <= 2.0
            assert factor < 1.0  # Should be faster due to specialization match

    def test_confidence_level_conversion(self, temp_roadmap):
        """Test confidence score to level conversion."""
        _, core = temp_roadmap
        estimator = IssueEstimator(core)

        # Test various confidence scores
        assert estimator._score_to_confidence_level(95) == ConfidenceLevel.VERY_HIGH
        assert estimator._score_to_confidence_level(85) == ConfidenceLevel.HIGH
        assert estimator._score_to_confidence_level(70) == ConfidenceLevel.MEDIUM
        assert estimator._score_to_confidence_level(40) == ConfidenceLevel.LOW
        assert estimator._score_to_confidence_level(0) == ConfidenceLevel.LOW


class TestRiskPredictor:
    """Test predictive risk assessment functionality."""

    @pytest.fixture
    def temp_roadmap(self):
        """Create a temporary roadmap for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            core = RoadmapCore()
            core.initialize()

            yield temp_dir, core

    def test_predictor_initialization(self, temp_roadmap):
        """Test RiskPredictor initialization."""
        _, core = temp_roadmap

        predictor = RiskPredictor(core)

        assert predictor.core == core
        assert predictor.analyzer is not None
        assert isinstance(predictor.risk_patterns, dict)

    @patch("roadmap.predictive.GitHistoryAnalyzer")
    def test_assess_project_risks(self, mock_analyzer_class, temp_roadmap):
        """Test project risk assessment."""
        _, core = temp_roadmap

        # Mock analyzer
        mock_analyzer = Mock()
        mock_team_insights = Mock()
        mock_team_insights.total_developers = 1
        mock_team_insights.collaboration_patterns = {"avg_collaboration_score": 20}
        mock_analyzer.generate_team_insights.return_value = mock_team_insights
        mock_analyzer.analyze_code_quality_trends.return_value = {
            "bug_fix_ratio": 0.5,
            "large_commits_ratio": 0.4,
        }
        mock_analyzer.git_integration.is_git_repository.return_value = True
        mock_analyzer_class.return_value = mock_analyzer

        predictor = RiskPredictor(core, mock_analyzer)
        risks = predictor.assess_project_risks(30)

        assert isinstance(risks, list)
        assert all(isinstance(r, RiskAssessment) for r in risks)

        # Should identify single developer risk
        single_dev_risks = [
            r for r in risks if "single developer" in r.description.lower()
        ]
        assert len(single_dev_risks) > 0

        # Should identify quality risks
        quality_risks = [r for r in risks if r.risk_type == "Quality Risk"]
        assert len(quality_risks) > 0

    def test_predict_issue_risks(self, temp_roadmap):
        """Test individual issue risk prediction."""
        _, core = temp_roadmap
        predictor = RiskPredictor(core)

        # High complexity issue
        complex_issue = Issue(
            id="complex",
            title="Complex system integration",
            content="Integrate multiple systems with complex data transformation algorithms "
            "requiring performance optimization and security hardening",
            priority=Priority.CRITICAL,
            depends_on=["dep1", "dep2", "dep3", "dep4", "dep5"],
            assignee="Alice",
        )

        risks = predictor.predict_issue_risks(complex_issue)

        assert isinstance(risks, list)
        assert all(isinstance(r, RiskAssessment) for r in risks)

        # Should identify complexity risk
        complexity_risks = [r for r in risks if "complexity" in r.risk_type.lower()]
        assert len(complexity_risks) > 0

        # Should identify dependency risk
        dependency_risks = [r for r in risks if "dependency" in r.risk_type.lower()]
        assert len(dependency_risks) > 0

    def test_risk_level_assessment(self, temp_roadmap):
        """Test risk level determination."""
        _, core = temp_roadmap
        predictor = RiskPredictor(core)

        # Test complexity risk creation
        high_complexity_issue = Issue(
            id="high_comp",
            title="Algorithm optimization",
            content="Complex algorithm implementation with performance requirements",
            priority=Priority.HIGH,
        )

        risk = predictor._create_complexity_risk(high_complexity_issue)

        assert isinstance(risk, RiskAssessment)
        assert risk.risk_level in [
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]
        assert 0 <= risk.probability <= 1
        assert risk.impact_score > 0
        assert len(risk.mitigation_suggestions) > 0

    def test_dependency_risk_assessment(self, temp_roadmap):
        """Test dependency-based risk assessment."""
        _, core = temp_roadmap
        predictor = RiskPredictor(core)

        # Issue with many dependencies
        dep_issue = Issue(
            id="deps",
            title="Integration task",
            content="Task with multiple dependencies",
            depends_on=["dep1", "dep2", "dep3", "dep4"],
        )

        risk = predictor._create_dependency_risk(dep_issue)

        assert isinstance(risk, RiskAssessment)
        assert risk.risk_type == "Dependency Risk"
        assert "4 dependencies" in risk.description
        assert len(risk.mitigation_suggestions) > 0
        assert risk.deadline_impact_days is not None


class TestDeadlineForecaster:
    """Test deadline forecasting functionality."""

    @pytest.fixture
    def temp_roadmap_with_issues(self):
        """Create a temporary roadmap with test issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            core = RoadmapCore()
            core.initialize()

            # Create test issues
            issues = [
                Issue(
                    id="1",
                    title="Task 1",
                    content="First task",
                    priority=Priority.HIGH,
                    status=Status.TODO,
                ),
                Issue(
                    id="2",
                    title="Task 2",
                    content="Second task",
                    priority=Priority.MEDIUM,
                    status=Status.TODO,
                ),
                Issue(
                    id="3",
                    title="Task 3",
                    content="Third task",
                    priority=Priority.LOW,
                    status=Status.IN_PROGRESS,
                ),
            ]

            # Save issues
            from roadmap.parser import IssueParser

            for issue in issues:
                IssueParser.save_issue_file(issue, core.issues_dir / issue.filename)

            yield temp_dir, core, issues

    def test_forecaster_initialization(self, temp_roadmap_with_issues):
        """Test DeadlineForecaster initialization."""
        _, core, _ = temp_roadmap_with_issues

        forecaster = DeadlineForecaster(core)

        assert forecaster.core == core
        assert forecaster.estimator is not None
        assert forecaster.risk_predictor is not None

    def test_project_completion_forecast(self, temp_roadmap_with_issues):
        """Test project completion forecasting."""
        _, core, _ = temp_roadmap_with_issues

        target_date = datetime.now() + timedelta(days=30)
        forecaster = DeadlineForecaster(core)

        forecast = forecaster.forecast_project_completion(target_date)

        assert isinstance(forecast, DeadlineForecast)
        assert forecast.target_date == target_date
        assert isinstance(forecast.predicted_completion, datetime)
        assert isinstance(forecast.confidence_level, ConfidenceLevel)
        assert 0 <= forecast.delay_probability <= 1
        assert isinstance(forecast.critical_path_issues, list)
        assert isinstance(forecast.optimization_suggestions, list)
        assert isinstance(forecast.scenario_analysis, dict)

        # Verify scenario analysis
        scenarios = forecast.scenario_analysis
        assert "best" in scenarios
        assert "worst" in scenarios
        assert "likely" in scenarios
        assert all(isinstance(date, datetime) for date in scenarios.values())
        assert scenarios["best"] <= scenarios["likely"] <= scenarios["worst"]

    def test_milestone_completion_forecast(self, temp_roadmap_with_issues):
        """Test milestone-specific forecasting."""
        _, core, issues = temp_roadmap_with_issues

        forecaster = DeadlineForecaster(core)
        milestone_issues = [issues[0].id, issues[1].id]

        forecast = forecaster.forecast_milestone_completion(milestone_issues)

        assert isinstance(forecast, DeadlineForecast)
        assert isinstance(forecast.predicted_completion, datetime)
        # Critical path should only include milestone issues
        assert all(
            issue_id in milestone_issues for issue_id in forecast.critical_path_issues
        )

    def test_no_work_forecast(self, temp_roadmap_with_issues):
        """Test forecasting when no work remains."""
        _, core, issues = temp_roadmap_with_issues

        # Mark all issues as done
        from roadmap.parser import IssueParser

        for issue in issues:
            issue.status = Status.DONE
            IssueParser.save_issue_file(issue, core.issues_dir / issue.filename)

        forecaster = DeadlineForecaster(core)
        forecast = forecaster.forecast_project_completion()

        assert isinstance(forecast, DeadlineForecast)
        assert forecast.confidence_level == ConfidenceLevel.VERY_HIGH
        assert forecast.delay_probability == 0.0
        assert len(forecast.critical_path_issues) == 0
        assert "completed" in forecast.optimization_suggestions[0].lower()

    def test_critical_path_identification(self, temp_roadmap_with_issues):
        """Test critical path analysis."""
        _, core, issues = temp_roadmap_with_issues

        forecaster = DeadlineForecaster(core)
        critical_path = forecaster._identify_critical_path(issues)

        assert isinstance(critical_path, list)
        assert all(isinstance(issue, Issue) for issue in critical_path)
        assert len(critical_path) <= len(issues)

        # Critical path should prioritize high-priority items
        if len(critical_path) > 1:
            high_priority_in_path = any(
                issue.priority in [Priority.HIGH, Priority.CRITICAL]
                for issue in critical_path
            )
            assert high_priority_in_path

    def test_scenario_calculation(self, temp_roadmap_with_issues):
        """Test completion scenario calculations."""
        _, core, _ = temp_roadmap_with_issues

        forecaster = DeadlineForecaster(core)

        # Mock risk assessment
        mock_risks = [
            Mock(deadline_impact_days=2),
            Mock(deadline_impact_days=None),
            Mock(deadline_impact_days=5),
        ]

        scenarios = forecaster._calculate_completion_scenarios(40.0, mock_risks, [])

        assert isinstance(scenarios, dict)
        assert "best" in scenarios
        assert "worst" in scenarios
        assert "likely" in scenarios

        # Verify temporal ordering
        assert scenarios["best"] <= scenarios["likely"] <= scenarios["worst"]

        # Verify risk impact
        best_to_worst_days = (scenarios["worst"] - scenarios["best"]).days
        assert best_to_worst_days > 7  # Should account for risk impacts


class TestPredictiveReportGenerator:
    """Test comprehensive predictive report generation."""

    @pytest.fixture
    def temp_roadmap_with_data(self):
        """Create a roadmap with comprehensive test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            core = RoadmapCore()
            core.initialize()

            # Create diverse test issues
            issues = [
                Issue(
                    id="feat1",
                    title="Feature A",
                    content="New feature implementation",
                    priority=Priority.HIGH,
                    status=Status.TODO,
                ),
                Issue(
                    id="bug1",
                    title="Critical Bug",
                    content="Fix login issue",
                    priority=Priority.CRITICAL,
                    status=Status.IN_PROGRESS,
                ),
                Issue(
                    id="task1",
                    title="Refactoring",
                    content="Code cleanup",
                    priority=Priority.MEDIUM,
                    status=Status.TODO,
                ),
                Issue(
                    id="done1",
                    title="Completed",
                    content="Finished work",
                    priority=Priority.LOW,
                    status=Status.DONE,
                ),
            ]

            # Save issues
            from roadmap.parser import IssueParser

            for issue in issues:
                IssueParser.save_issue_file(issue, core.issues_dir / issue.filename)

            yield temp_dir, core, issues

    def test_generator_initialization(self, temp_roadmap_with_data):
        """Test PredictiveReportGenerator initialization."""
        _, core, _ = temp_roadmap_with_data

        generator = PredictiveReportGenerator(core)

        assert generator.core == core
        assert isinstance(generator.estimator, IssueEstimator)
        assert isinstance(generator.risk_predictor, RiskPredictor)
        assert isinstance(generator.forecaster, DeadlineForecaster)

    def test_intelligence_report_generation(self, temp_roadmap_with_data):
        """Test comprehensive intelligence report generation."""
        _, core, _ = temp_roadmap_with_data

        generator = PredictiveReportGenerator(core)
        target_date = datetime.now() + timedelta(days=30)

        report = generator.generate_intelligence_report(target_date)

        # Verify report structure
        assert "error" not in report
        assert "report_generated" in report
        assert "target_date" in report
        assert "project_forecast" in report
        assert "risk_analysis" in report
        assert "work_estimates" in report
        assert "optimization_recommendations" in report
        assert "detailed_estimates" in report

        # Verify project forecast
        forecast = report["project_forecast"]
        assert "predicted_completion" in forecast
        assert "confidence_level" in forecast
        assert "delay_probability" in forecast
        assert "scenario_analysis" in forecast

        # Verify risk analysis
        risk_analysis = report["risk_analysis"]
        assert "total_risks_identified" in risk_analysis
        assert "high_priority_risks" in risk_analysis
        assert "risk_breakdown" in risk_analysis
        assert "top_risks" in risk_analysis

        # Verify work estimates
        estimates = report["work_estimates"]
        assert "total_issues" in estimates
        assert "total_estimated_hours" in estimates
        assert "average_confidence" in estimates

        # Verify detailed estimates are at top level
        assert "detailed_estimates" in report

    def test_report_file_saving(self, temp_roadmap_with_data, tmp_path):
        """Test saving reports to files."""
        _, core, _ = temp_roadmap_with_data

        generator = PredictiveReportGenerator(core)
        filename = str(tmp_path / "test_intelligence_report.json")

        report = generator.generate_intelligence_report(save_file=filename)

        # Verify file was created
        assert Path(filename).exists()

        # Verify file content
        import json

        with open(filename) as f:
            saved_report = json.load(f)

        assert saved_report["report_generated"] == report["report_generated"]
        assert "project_forecast" in saved_report
        assert "risk_analysis" in saved_report

    def test_error_handling(self, temp_roadmap_with_data):
        """Test error handling in report generation."""
        _, core, _ = temp_roadmap_with_data

        generator = PredictiveReportGenerator(core)

        # Mock a component to raise an exception
        with patch.object(
            generator.forecaster,
            "forecast_project_completion",
            side_effect=Exception("Test error"),
        ):
            report = generator.generate_intelligence_report()

        assert "error" in report
        assert "Test error" in report["error"]
        assert "report_generated" in report


class TestPredictiveIntegration:
    """Integration tests for predictive intelligence features."""

    @pytest.fixture
    def real_project_setup(self):
        """Create a realistic project scenario for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Initialize Git repo
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], check=True
            )

            # Initialize roadmap
            core = RoadmapCore()
            core.initialize()

            # Create realistic project issues
            issues = [
                Issue(
                    id="api-auth",
                    title="Implement API Authentication",
                    content="Design and implement JWT-based authentication system for REST API. "
                    "Includes user registration, login, token refresh, and middleware integration.",
                    priority=Priority.HIGH,
                    status=Status.TODO,
                    assignee="Alice",
                    depends_on=["db-setup"],
                ),
                Issue(
                    id="db-setup",
                    title="Database Schema Setup",
                    content="Create initial database schema with user tables, indexes, and migrations.",
                    priority=Priority.CRITICAL,
                    status=Status.IN_PROGRESS,
                    assignee="Bob",
                ),
                Issue(
                    id="frontend-ui",
                    title="User Interface Components",
                    content="Build React components for user dashboard with responsive design.",
                    priority=Priority.MEDIUM,
                    status=Status.TODO,
                    assignee="Alice",
                    depends_on=["api-auth"],
                ),
                Issue(
                    id="testing",
                    title="Integration Testing",
                    content="Comprehensive test suite for API endpoints and UI components.",
                    priority=Priority.MEDIUM,
                    status=Status.TODO,
                    depends_on=["api-auth", "frontend-ui"],
                ),
                Issue(
                    id="docs",
                    title="Documentation Update",
                    content="Update API documentation and user guides.",
                    priority=Priority.LOW,
                    status=Status.TODO,
                ),
            ]

            # Save issues
            from roadmap.parser import IssueParser

            for issue in issues:
                IssueParser.save_issue_file(issue, core.issues_dir / issue.filename)

            # Create some commits
            Path("README.md").write_text("# Test Project")
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

            yield temp_dir, core, issues

    def test_full_predictive_workflow(self, real_project_setup):
        """Test complete predictive intelligence workflow."""
        _, core, issues = real_project_setup

        # 1. Issue Estimation
        estimator = IssueEstimator(core)
        active_issues = [
            i for i in issues if i.status in [Status.TODO, Status.IN_PROGRESS]
        ]
        estimates = estimator.batch_estimate_issues(active_issues)

        assert len(estimates) == len(active_issues)
        assert all(e.estimated_hours > 0 for e in estimates)

        total_hours = sum(e.estimated_hours for e in estimates)
        assert total_hours > 0

        # 2. Risk Assessment
        risk_predictor = RiskPredictor(core)
        risks = risk_predictor.assess_project_risks(30)

        assert len(risks) > 0
        high_priority_risks = [
            r for r in risks if r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]

        # Should identify dependency risks due to issue dependencies
        dependency_risks = [r for r in risks if "dependency" in r.risk_type.lower()]

        # 3. Deadline Forecasting
        forecaster = DeadlineForecaster(core, estimator, risk_predictor)
        target_date = datetime.now() + timedelta(days=45)
        forecast = forecaster.forecast_project_completion(target_date)

        assert isinstance(forecast.predicted_completion, datetime)
        assert forecast.predicted_completion > datetime.now()

        # Critical path should include high-priority dependencies
        critical_issues = [
            core.get_issue(iid)
            for iid in forecast.critical_path_issues
            if core.get_issue(iid)
        ]
        high_priority_in_critical = any(
            issue.priority in [Priority.HIGH, Priority.CRITICAL]
            for issue in critical_issues
        )

        # 4. Comprehensive Report
        generator = PredictiveReportGenerator(core)
        report = generator.generate_intelligence_report(target_date)

        assert "error" not in report
        assert report["work_estimates"]["total_issues"] == len(active_issues)
        assert report["work_estimates"]["total_estimated_hours"] == total_hours
        assert report["risk_analysis"]["total_risks_identified"] == len(risks)

    def test_predictive_accuracy_validation(self, real_project_setup):
        """Test predictive model accuracy and consistency."""
        _, core, issues = real_project_setup

        estimator = IssueEstimator(core)

        # Test estimation consistency
        test_issue = issues[0]  # API auth issue

        # Multiple estimates should be consistent
        estimates = [estimator.estimate_issue_time(test_issue) for _ in range(5)]

        estimated_hours = [e.estimated_hours for e in estimates]
        confidence_scores = [e.confidence_score for e in estimates]

        # Estimates should be identical (deterministic algorithm)
        assert len(set(estimated_hours)) == 1, "Estimates should be deterministic"
        assert len(set(confidence_scores)) == 1, "Confidence should be deterministic"

        # Test developer-specific adjustments
        estimate_alice = estimator.estimate_issue_time(test_issue, "Alice")
        estimate_bob = estimator.estimate_issue_time(test_issue, "Bob")

        # Should produce different estimates for different developers
        # (assuming different productivity profiles)
        assert isinstance(estimate_alice, EstimationResult)
        assert isinstance(estimate_bob, EstimationResult)

    def test_scenario_planning_accuracy(self, real_project_setup):
        """Test scenario planning and forecast accuracy."""
        _, core, issues = real_project_setup

        forecaster = DeadlineForecaster(core)

        # Test different target dates
        near_target = datetime.now() + timedelta(days=15)  # Aggressive
        medium_target = datetime.now() + timedelta(days=30)  # Moderate
        far_target = datetime.now() + timedelta(days=60)  # Conservative

        forecast_near = forecaster.forecast_project_completion(near_target)
        forecast_medium = forecaster.forecast_project_completion(medium_target)
        forecast_far = forecaster.forecast_project_completion(far_target)

        # Delay probability should decrease with longer target dates
        assert forecast_near.delay_probability >= forecast_medium.delay_probability
        assert forecast_medium.delay_probability >= forecast_far.delay_probability

        # All forecasts should have valid scenario analysis
        for forecast in [forecast_near, forecast_medium, forecast_far]:
            scenarios = forecast.scenario_analysis
            assert scenarios["best"] <= scenarios["likely"] <= scenarios["worst"]

            # Time spans should be reasonable
            span_days = (scenarios["worst"] - scenarios["best"]).days
            assert 1 <= span_days <= 90  # Reasonable uncertainty range


if __name__ == "__main__":
    pytest.main([__file__])
