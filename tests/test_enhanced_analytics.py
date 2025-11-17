"""Comprehensive tests for Enhanced Analytics module."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from roadmap.enhanced_analytics import EnhancedAnalyzer
from roadmap.models import Issue, Milestone, MilestoneStatus, Priority, Status

# Mark all tests as unit tests
pytestmark = pytest.mark.unit


class TestEnhancedAnalyzerInitialization:
    """Test EnhancedAnalyzer initialization and basic functionality."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore for testing."""
        return Mock()

    @pytest.fixture
    def enhanced_analyzer(self, mock_core):
        """Create EnhancedAnalyzer for testing."""
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            return EnhancedAnalyzer(mock_core)

    def test_initialization_success(self, mock_core):
        """Test successful initialization of EnhancedAnalyzer."""
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            analyzer = EnhancedAnalyzer(mock_core)

        assert analyzer.core == mock_core
        assert analyzer.git_integration is not None
        assert analyzer.data_adapter is not None
        assert analyzer.analyzer is not None

    def test_initialization_with_none_core(self):
        """Test initialization with None core."""
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            analyzer = EnhancedAnalyzer(None)

        assert analyzer.core is None


class TestDataFrameGeneration:
    """Test DataFrame generation methods."""

    @pytest.fixture
    def enhanced_analyzer(self):
        """Create EnhancedAnalyzer with mocked dependencies."""
        mock_core = Mock()
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            return EnhancedAnalyzer(mock_core)

    @pytest.fixture
    def sample_issues(self):
        """Create sample issues for testing."""
        return [
            Issue(
                id="issue1",
                title="Feature Implementation",
                content="Implement new feature",
                priority=Priority.HIGH,
                status=Status.IN_PROGRESS,
                estimated_hours=8.0,
                assignee="alice@example.com",
            ),
            Issue(
                id="issue2",
                title="Bug Fix",
                content="Fix critical bug",
                priority=Priority.CRITICAL,
                status=Status.DONE,
                estimated_hours=4.0,
                assignee="bob@example.com",
            ),
        ]

    @pytest.fixture
    def sample_milestones(self):
        """Create sample milestones for testing."""
        return [
            Milestone(
                name="v1.0 Release",
                description="First major release",
                due_date=datetime.now() + timedelta(days=30),
                status=MilestoneStatus.OPEN,
            ),
            Milestone(
                name="v1.1 Features",
                description="Feature additions",
                due_date=datetime.now() + timedelta(days=60),
                status=MilestoneStatus.OPEN,
            ),
        ]

    def test_get_issues_dataframe_success(self, enhanced_analyzer, sample_issues):
        """Test successful issues DataFrame generation."""
        enhanced_analyzer.core.list_issues.return_value = sample_issues
        mock_df = pd.DataFrame(
            {"id": ["issue1", "issue2"], "title": ["Feature", "Bug"]}
        )
        enhanced_analyzer.data_adapter.issues_to_dataframe.return_value = mock_df

        result = enhanced_analyzer.get_issues_dataframe()

        assert isinstance(result, pd.DataFrame)
        enhanced_analyzer.core.list_issues.assert_called_once()
        enhanced_analyzer.data_adapter.issues_to_dataframe.assert_called_once_with(
            sample_issues
        )

    def test_get_issues_dataframe_empty(self, enhanced_analyzer):
        """Test issues DataFrame generation with no issues."""
        enhanced_analyzer.core.list_issues.return_value = []
        mock_df = pd.DataFrame()
        enhanced_analyzer.data_adapter.issues_to_dataframe.return_value = mock_df

        result = enhanced_analyzer.get_issues_dataframe()

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_get_milestones_dataframe_success(
        self, enhanced_analyzer, sample_milestones, sample_issues
    ):
        """Test successful milestones DataFrame generation."""
        enhanced_analyzer.core.list_milestones.return_value = sample_milestones
        enhanced_analyzer.core.list_issues.return_value = sample_issues
        mock_df = pd.DataFrame({"name": ["v1.0", "v1.1"], "status": ["open", "open"]})
        enhanced_analyzer.data_adapter.milestones_to_dataframe.return_value = mock_df

        result = enhanced_analyzer.get_milestones_dataframe()

        assert isinstance(result, pd.DataFrame)
        enhanced_analyzer.core.list_milestones.assert_called_once()
        enhanced_analyzer.core.list_issues.assert_called_once()


class TestCompletionTrends:
    """Test completion trends analysis."""

    @pytest.fixture
    def enhanced_analyzer(self):
        """Create EnhancedAnalyzer with mocked dependencies."""
        mock_core = Mock()
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            return EnhancedAnalyzer(mock_core)

    @pytest.fixture
    def mock_completion_df(self):
        """Create mock completion trends DataFrame."""
        dates = pd.date_range(start="2023-01-01", periods=4, freq="W")
        return pd.DataFrame(
            {
                "completion_period": dates.to_period("W"),
                "issues_completed": [3, 5, 2, 4],
                "total_estimated_hours": [24.0, 40.0, 16.0, 32.0],
                "avg_estimated_hours": [8.0, 8.0, 8.0, 8.0],
                "velocity_score": [30.0, 50.0, 20.0, 40.0],
            }
        )

    def test_analyze_completion_trends_success(
        self, enhanced_analyzer, mock_completion_df
    ):
        """Test successful completion trends analysis."""
        # Mock issues DataFrame with required columns for completion trends
        now = datetime.now()
        mock_issues_df = pd.DataFrame(
            {
                "id": ["1", "2", "3"],
                "status": ["done", "done", "todo"],
                "actual_end_date": [
                    now - timedelta(days=7),
                    now - timedelta(days=14),
                    None,
                ],
                "estimated_hours": [8.0, 12.0, 6.0],
                "actual_duration_hours": [7.0, 11.0, 0.0],
                "issue_type": ["bug", "feature", "task"],
                "priority": ["high", "medium", "low"],
            }
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=mock_issues_df)

        result = enhanced_analyzer.analyze_completion_trends(period="W", months=3)

        assert isinstance(result, pd.DataFrame)
        enhanced_analyzer.get_issues_dataframe.assert_called_once()

    def test_analyze_completion_trends_empty_data(self, enhanced_analyzer):
        """Test completion trends analysis with empty data."""
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=pd.DataFrame())

        result = enhanced_analyzer.analyze_completion_trends()

        assert isinstance(result, pd.DataFrame)

    def test_analyze_completion_trends_custom_period(self, enhanced_analyzer):
        """Test completion trends analysis with custom period."""
        now = datetime.now()
        mock_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "status": ["done", "done"],
                "actual_end_date": [now - timedelta(days=30), now - timedelta(days=60)],
                "estimated_hours": [8.0, 12.0],
                "actual_duration_hours": [7.5, 11.0],
                "issue_type": ["bug", "feature"],
                "priority": ["high", "medium"],
            }
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=mock_df)

        result = enhanced_analyzer.analyze_completion_trends(period="M", months=6)

        assert isinstance(result, pd.DataFrame)


class TestWorkloadDistribution:
    """Test workload distribution analysis."""

    @pytest.fixture
    def enhanced_analyzer(self):
        """Create EnhancedAnalyzer with mocked dependencies."""
        mock_core = Mock()
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            return EnhancedAnalyzer(mock_core)

    @pytest.fixture
    def mock_workload_df(self):
        """Create mock workload DataFrame."""
        return pd.DataFrame(
            {
                "assignee": ["alice@example.com", "bob@example.com"],
                "total_issues": [5, 3],
                "total_estimated_hours": [40.0, 24.0],
                "completion_rate": [80.0, 66.7],
                "workload_score": [12.5, 8.0],
            }
        )

    def test_analyze_workload_distribution_success(
        self, enhanced_analyzer, mock_workload_df
    ):
        """Test successful workload distribution analysis."""
        # Create realistic workload DataFrame with all required columns
        workload_df = pd.DataFrame(
            {
                "id": ["1", "2", "3", "4"],
                "assignee": ["alice", "alice", "bob", "bob"],
                "estimated_hours": [8.0, 12.0, 6.0, 4.0],
                "actual_duration_hours": [7.0, 11.0, 5.5, 3.5],
                "progress_percentage": [100.0, 80.0, 90.0, 100.0],
                "status": ["done", "in-progress", "review", "done"],
                "priority": ["high", "medium", "critical", "low"],
                "is_overdue": [False, True, False, False],
            }
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=workload_df)

        result = enhanced_analyzer.analyze_workload_distribution()

        assert isinstance(result, pd.DataFrame)

    def test_analyze_workload_distribution_empty_data(self, enhanced_analyzer):
        """Test workload distribution with empty data."""
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=pd.DataFrame())

        result = enhanced_analyzer.analyze_workload_distribution()

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_analyze_workload_distribution_single_assignee(self, enhanced_analyzer):
        """Test workload distribution with single assignee."""
        single_assignee_df = pd.DataFrame(
            {
                "id": ["1"],
                "assignee": ["alice@example.com"],
                "estimated_hours": [8.0],
                "actual_duration_hours": [7.0],
                "progress_percentage": [50.0],
                "status": ["todo"],
                "priority": ["medium"],
                "is_overdue": [False],
            }
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=single_assignee_df)

        result = enhanced_analyzer.analyze_workload_distribution()

        assert isinstance(result, pd.DataFrame)


class TestMilestoneProgress:
    """Test milestone progress analysis."""

    @pytest.fixture
    def enhanced_analyzer(self):
        """Create EnhancedAnalyzer with mocked dependencies."""
        mock_core = Mock()
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            return EnhancedAnalyzer(mock_core)

    def test_analyze_milestone_progress_success(self, enhanced_analyzer):
        """Test successful milestone progress analysis."""
        mock_df = pd.DataFrame(
            {
                "milestone": ["v1.0", "v1.1"],
                "total_issues": [10, 5],
                "completed_issues": [8, 2],
                "progress_percentage": [80.0, 40.0],
                "due_date": [
                    datetime.now() + timedelta(days=30),
                    datetime.now() + timedelta(days=60),
                ],
                "remaining_estimated_hours": [20.0, 40.0],
            }
        )
        enhanced_analyzer.get_milestones_dataframe = Mock(return_value=mock_df)
        enhanced_analyzer.analyzer.analyze_milestone_health = Mock(return_value=mock_df)

        result = enhanced_analyzer.analyze_milestone_progress()

        assert isinstance(result, pd.DataFrame)
        enhanced_analyzer.get_milestones_dataframe.assert_called_once()

    def test_analyze_milestone_progress_empty_data(self, enhanced_analyzer):
        """Test milestone progress with no milestones."""
        enhanced_analyzer.get_milestones_dataframe = Mock(return_value=pd.DataFrame())

        result = enhanced_analyzer.analyze_milestone_progress()

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_analyze_milestone_progress_no_issues(self, enhanced_analyzer):
        """Test milestone progress with milestones but no issues."""
        empty_milestone_df = pd.DataFrame(
            {
                "milestone": ["v1.0"],
                "total_issues": [0],
                "completed_issues": [0],
                "due_date": [datetime.now() + timedelta(days=30)],
                "remaining_estimated_hours": [0.0],
            }
        )
        enhanced_analyzer.get_milestones_dataframe = Mock(
            return_value=empty_milestone_df
        )
        enhanced_analyzer.analyzer.analyze_milestone_health = Mock(
            return_value=empty_milestone_df
        )

        result = enhanced_analyzer.analyze_milestone_progress()

        assert isinstance(result, pd.DataFrame)


class TestIssueLifecycle:
    """Test issue lifecycle analysis."""

    @pytest.fixture
    def enhanced_analyzer(self):
        """Create EnhancedAnalyzer with mocked dependencies."""
        mock_core = Mock()
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            return EnhancedAnalyzer(mock_core)

    @pytest.fixture
    def lifecycle_issues_df(self):
        """Create mock issues DataFrame for lifecycle analysis."""
        now = datetime.now()
        return pd.DataFrame(
            {
                "id": ["1", "2", "3", "4"],
                "status": ["todo", "in-progress", "review", "done"],
                "estimated_hours": [8.0, 12.0, 4.0, 6.0],
                "actual_duration_hours": [0.0, 6.0, 4.0, 6.0],
                "progress_percentage": [0.0, 50.0, 90.0, 100.0],
                "created": [now - timedelta(days=10 + i) for i in range(4)],
                "updated": [now - timedelta(days=2 + i) for i in range(4)],
                "is_overdue": [False, True, False, False],
                "priority": ["high", "medium", "low", "critical"],
            }
        )

    def test_analyze_issue_lifecycle_success(
        self, enhanced_analyzer, lifecycle_issues_df
    ):
        """Test successful issue lifecycle analysis."""
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=lifecycle_issues_df)

        with patch("roadmap.enhanced_analytics.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.now()
            result = enhanced_analyzer.analyze_issue_lifecycle()

        assert isinstance(result, pd.DataFrame)
        enhanced_analyzer.get_issues_dataframe.assert_called_once()

    def test_analyze_issue_lifecycle_empty_data(self, enhanced_analyzer):
        """Test issue lifecycle analysis with empty data."""
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=pd.DataFrame())

        result = enhanced_analyzer.analyze_issue_lifecycle()

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_analyze_issue_lifecycle_single_status(self, enhanced_analyzer):
        """Test issue lifecycle with single status."""
        now = datetime.now()
        single_status_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "status": ["todo", "todo"],
                "estimated_hours": [8.0, 4.0],
                "actual_duration_hours": [0.0, 0.0],
                "created": [now - timedelta(days=5), now - timedelta(days=3)],
                "updated": [now - timedelta(days=1), now - timedelta(hours=12)],
                "is_overdue": [False, False],
                "priority": ["medium", "low"],
            }
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=single_status_df)

        result = enhanced_analyzer.analyze_issue_lifecycle()

        assert isinstance(result, pd.DataFrame)


class TestVelocityConsistency:
    """Test velocity consistency analysis."""

    @pytest.fixture
    def enhanced_analyzer(self):
        """Create EnhancedAnalyzer with mocked dependencies."""
        mock_core = Mock()
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            return EnhancedAnalyzer(mock_core)

    @pytest.fixture
    def mock_velocity_df(self):
        """Create mock velocity DataFrame."""
        return pd.DataFrame(
            {
                "velocity_score": [45.0, 52.0, 38.0, 48.0, 55.0, 42.0],
                "issues_completed": [3, 4, 2, 3, 4, 3],
                "completion_period": pd.date_range(
                    "2023-01-01", periods=6, freq="W"
                ).to_period("W"),
            }
        )

    def test_analyze_velocity_consistency_success(
        self, enhanced_analyzer, mock_velocity_df
    ):
        """Test successful velocity consistency analysis."""
        enhanced_analyzer.analyzer.analyze_velocity_trends = Mock(
            return_value=mock_velocity_df
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=pd.DataFrame())

        result = enhanced_analyzer.analyze_velocity_consistency(weeks=6)

        assert isinstance(result, dict)
        assert "weeks_analyzed" in result
        assert "avg_velocity_score" in result
        assert "consistency_rating" in result
        enhanced_analyzer.analyzer.analyze_velocity_trends.assert_called_once()

    def test_analyze_velocity_consistency_empty_data(self, enhanced_analyzer):
        """Test velocity consistency with no data."""
        enhanced_analyzer.analyzer.analyze_velocity_trends = Mock(
            return_value=pd.DataFrame()
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=pd.DataFrame())

        result = enhanced_analyzer.analyze_velocity_consistency()

        assert isinstance(result, dict)
        assert "error" in result
        assert result["weeks_analyzed"] == 0

    def test_analyze_velocity_consistency_custom_weeks(
        self, enhanced_analyzer, mock_velocity_df
    ):
        """Test velocity consistency with custom weeks parameter."""
        enhanced_analyzer.analyzer.analyze_velocity_trends = Mock(
            return_value=mock_velocity_df
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=pd.DataFrame())

        result = enhanced_analyzer.analyze_velocity_consistency(weeks=4)

        assert isinstance(result, dict)
        assert result["weeks_analyzed"] <= 4

    def test_analyze_velocity_consistency_ratings(self, enhanced_analyzer):
        """Test velocity consistency rating calculations."""
        # Test very consistent (CV < 0.2)
        consistent_df = pd.DataFrame(
            {
                "velocity_score": [50.0, 51.0, 49.0, 50.5],
                "issues_completed": [3, 3, 3, 3],
            }
        )
        enhanced_analyzer.analyzer.analyze_velocity_trends = Mock(
            return_value=consistent_df
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=pd.DataFrame())

        result = enhanced_analyzer.analyze_velocity_consistency()

        assert result["consistency_rating"] == "Very Consistent"


class TestProductivityInsights:
    """Test productivity insights generation."""

    @pytest.fixture
    def enhanced_analyzer(self):
        """Create EnhancedAnalyzer with mocked dependencies."""
        mock_core = Mock()
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            return EnhancedAnalyzer(mock_core)

    @pytest.fixture
    def productivity_issues_df(self):
        """Create mock issues DataFrame for productivity analysis."""
        now = datetime.now()
        return pd.DataFrame(
            {
                "id": ["1", "2", "3", "4"],
                "status": ["done", "todo", "blocked", "in-progress"],
                "priority": ["high", "medium", "critical", "low"],
                "is_overdue": [False, True, False, False],
                "assignee": ["alice", "bob", "alice", "charlie"],
                "estimated_hours": [8.0, 4.0, 12.0, 6.0],
                "actual_duration_hours": [7.5, 0.0, 0.0, 3.0],
                "progress_percentage": [100.0, 0.0, 0.0, 50.0],
                "created": [now - timedelta(days=i) for i in range(1, 5)],
                "updated": [now - timedelta(hours=i) for i in range(1, 5)],
            }
        )

    def test_generate_productivity_insights_success(
        self, enhanced_analyzer, productivity_issues_df
    ):
        """Test successful productivity insights generation."""
        enhanced_analyzer.get_issues_dataframe = Mock(
            return_value=productivity_issues_df
        )
        enhanced_analyzer.analyze_workload_distribution = Mock(
            return_value=pd.DataFrame(
                {
                    "assignee": ["alice", "bob"],
                    "completion_rate": [75.0, 50.0],
                    "workload_score": [15.0, 8.0],
                }
            )
        )
        enhanced_analyzer.analyzer.find_bottlenecks = Mock(return_value={})

        result = enhanced_analyzer.generate_productivity_insights(days=30)

        assert isinstance(result, dict)
        assert "summary" in result
        assert "team_performance" in result
        assert "recommendations" in result
        enhanced_analyzer.get_issues_dataframe.assert_called_once()

    def test_generate_productivity_insights_empty_data(self, enhanced_analyzer):
        """Test productivity insights with empty data."""
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=pd.DataFrame())
        enhanced_analyzer.analyze_workload_distribution = Mock(
            return_value=pd.DataFrame()
        )
        enhanced_analyzer.analyzer.find_bottlenecks = Mock(return_value={})

        result = enhanced_analyzer.generate_productivity_insights()

        assert isinstance(result, dict)
        assert "error" in result
        assert result["error"] == "No issues data available"

    def test_generate_productivity_insights_recommendations(self, enhanced_analyzer):
        """Test productivity insights recommendation generation."""
        # Mock data that triggers recommendations
        now = datetime.now()
        high_blocked_df = pd.DataFrame(
            {
                "status": ["blocked"] * 5 + ["todo"] * 5,
                "priority": ["medium"] * 10,
                "is_overdue": [True] * 8 + [False] * 2,
                "assignee": ["alice"] * 10,
                "estimated_hours": [8.0] * 10,
                "actual_duration_hours": [0.0] * 10,
                "progress_percentage": [0.0] * 10,
                "created": [now - timedelta(days=i) for i in range(1, 11)],
            }
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=high_blocked_df)
        enhanced_analyzer.analyze_workload_distribution = Mock(
            return_value=pd.DataFrame()
        )
        enhanced_analyzer.analyzer.find_bottlenecks = Mock(
            return_value={"overloaded_assignees": ["alice"]}
        )

        result = enhanced_analyzer.generate_productivity_insights()

        assert isinstance(result, dict)
        assert "recommendations" in result
        assert len(result["recommendations"]) > 0


class TestPeriodComparison:
    """Test period comparison functionality."""

    @pytest.fixture
    def enhanced_analyzer(self):
        """Create EnhancedAnalyzer with mocked dependencies."""
        mock_core = Mock()
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            return EnhancedAnalyzer(mock_core)

    @pytest.fixture
    def comparison_issues_df(self):
        """Create mock issues DataFrame for period comparison."""
        now = datetime.now()
        return pd.DataFrame(
            {
                "id": ["1", "2", "3", "4"],
                "status": ["done", "done", "todo", "blocked"],
                "priority": ["high", "medium", "critical", "low"],
                "is_overdue": [False, False, True, False],
                "estimated_hours": [8.0, 4.0, 12.0, 6.0],
                "created": [
                    now - timedelta(days=15),  # Period 1
                    now - timedelta(days=20),  # Period 1
                    now - timedelta(days=45),  # Period 2
                    now - timedelta(days=50),  # Period 2
                ],
            }
        )

    def test_compare_periods_success(self, enhanced_analyzer, comparison_issues_df):
        """Test successful period comparison."""
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=comparison_issues_df)

        result = enhanced_analyzer.compare_periods(period1_days=30, period2_days=60)

        assert isinstance(result, dict)
        assert "period1_metrics" in result
        assert "period2_metrics" in result
        assert "changes" in result
        assert "period1_description" in result
        assert "period2_description" in result

    def test_compare_periods_empty_data(self, enhanced_analyzer):
        """Test period comparison with empty data."""
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=pd.DataFrame())

        result = enhanced_analyzer.compare_periods()

        assert isinstance(result, dict)
        assert "error" in result
        assert result["error"] == "No issues data available"

    def test_compare_periods_custom_ranges(
        self, enhanced_analyzer, comparison_issues_df
    ):
        """Test period comparison with custom date ranges."""
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=comparison_issues_df)

        result = enhanced_analyzer.compare_periods(period1_days=14, period2_days=45)

        assert isinstance(result, dict)
        assert result["period1_description"] == "Last 14 days"
        assert result["period2_description"] == "Previous 31 days"

    def test_compare_periods_no_previous_data(self, enhanced_analyzer):
        """Test period comparison when previous period has no data."""
        now = datetime.now()
        recent_only_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "status": ["done", "todo"],
                "priority": ["high", "medium"],
                "is_overdue": [False, False],
                "estimated_hours": [8.0, 4.0],
                "actual_duration_hours": [7.5, 0.0],
                "progress_percentage": [100.0, 0.0],
                "created": [now - timedelta(days=5), now - timedelta(days=3)],
            }
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=recent_only_df)

        result = enhanced_analyzer.compare_periods()

        assert isinstance(result, dict)
        assert "changes" in result


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def enhanced_analyzer(self):
        """Create EnhancedAnalyzer with mocked dependencies."""
        mock_core = Mock()
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            return EnhancedAnalyzer(mock_core)

    def test_analyze_with_core_exception(self, enhanced_analyzer):
        """Test handling of core exceptions."""
        enhanced_analyzer.core.list_issues.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            enhanced_analyzer.get_issues_dataframe()

    def test_analyze_with_pandas_exception(self, enhanced_analyzer):
        """Test handling of pandas exceptions."""
        enhanced_analyzer.get_issues_dataframe = Mock(
            side_effect=pd.errors.EmptyDataError("No data")
        )

        with pytest.raises(pd.errors.EmptyDataError):
            enhanced_analyzer.analyze_completion_trends()

    def test_analyze_velocity_with_invalid_weeks(self, enhanced_analyzer):
        """Test velocity analysis with invalid weeks parameter."""
        enhanced_analyzer.analyzer.analyze_velocity_trends = Mock(
            return_value=pd.DataFrame()
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=pd.DataFrame())

        # Should handle gracefully
        result = enhanced_analyzer.analyze_velocity_consistency(weeks=0)

        assert isinstance(result, dict)
        assert "error" in result

    def test_productivity_insights_with_malformed_data(self, enhanced_analyzer):
        """Test productivity insights with malformed data."""
        malformed_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "status": ["done", "todo"],
                # Missing 'created' column should cause KeyError
            }
        )
        enhanced_analyzer.get_issues_dataframe = Mock(return_value=malformed_df)
        enhanced_analyzer.analyze_workload_distribution = Mock(
            return_value=pd.DataFrame()
        )
        enhanced_analyzer.analyzer.find_bottlenecks = Mock(return_value={})

        # Should raise KeyError for missing 'created' column
        with pytest.raises(KeyError):
            enhanced_analyzer.generate_productivity_insights()


class TestIntegration:
    """Integration tests for Enhanced Analytics."""

    @pytest.fixture
    def enhanced_analyzer(self):
        """Create EnhancedAnalyzer with mocked dependencies."""
        mock_core = Mock()
        with (
            patch("roadmap.enhanced_analytics.GitIntegration"),
            patch("roadmap.enhanced_analytics.DataFrameAdapter"),
            patch("roadmap.enhanced_analytics.DataAnalyzer"),
        ):
            return EnhancedAnalyzer(mock_core)

    def test_full_analytics_workflow(self, enhanced_analyzer):
        """Test complete analytics workflow."""
        # Mock comprehensive dataset
        now = datetime.now()
        comprehensive_df = pd.DataFrame(
            {
                "id": [f"issue{i}" for i in range(1, 11)],
                "status": ["done"] * 5 + ["todo"] * 3 + ["in-progress"] * 2,
                "priority": ["high"] * 3 + ["medium"] * 4 + ["low"] * 3,
                "assignee": ["alice"] * 4 + ["bob"] * 3 + ["charlie"] * 3,
                "estimated_hours": [
                    8.0,
                    4.0,
                    12.0,
                    6.0,
                    10.0,
                    8.0,
                    5.0,
                    15.0,
                    7.0,
                    9.0,
                ],
                "actual_duration_hours": [
                    7.0,
                    4.0,
                    12.0,
                    6.0,
                    9.0,
                    0.0,
                    0.0,
                    0.0,
                    3.5,
                    4.0,
                ],
                "progress_percentage": [100.0] * 5 + [0.0] * 3 + [50.0] * 2,
                "is_overdue": [False] * 8 + [True] * 2,
                "created": [now - timedelta(days=i) for i in range(1, 11)],
            }
        )

        enhanced_analyzer.get_issues_dataframe = Mock(return_value=comprehensive_df)
        enhanced_analyzer.analyzer.analyze_velocity_trends = Mock(
            return_value=pd.DataFrame(
                {"velocity_score": [45.0, 50.0, 40.0], "issues_completed": [3, 4, 2]}
            )
        )
        enhanced_analyzer.analyzer.find_bottlenecks = Mock(return_value={})

        # Test multiple analysis methods work together
        workload = enhanced_analyzer.analyze_workload_distribution()
        insights = enhanced_analyzer.generate_productivity_insights()
        velocity = enhanced_analyzer.analyze_velocity_consistency()
        comparison = enhanced_analyzer.compare_periods()

        # All should return valid results
        assert isinstance(workload, pd.DataFrame)
        assert isinstance(insights, dict)
        assert isinstance(velocity, dict)
        assert isinstance(comparison, dict)

    def test_analytics_data_consistency(self, enhanced_analyzer):
        """Test data consistency across different analytics methods."""
        # Use same base data for multiple analyses
        now = datetime.now()
        consistent_df = pd.DataFrame(
            {
                "id": ["1", "2", "3"],
                "status": ["done", "todo", "in-progress"],
                "assignee": ["alice", "alice", "bob"],
                "estimated_hours": [8.0, 4.0, 6.0],
                "actual_duration_hours": [7.5, 0.0, 3.0],
                "progress_percentage": [100.0, 0.0, 50.0],
                "priority": ["high", "medium", "low"],
                "is_overdue": [False, False, True],
                "created": [now - timedelta(days=i) for i in range(1, 4)],
            }
        )

        enhanced_analyzer.get_issues_dataframe = Mock(return_value=consistent_df)
        enhanced_analyzer.analyzer.find_bottlenecks = Mock(return_value={})

        # Multiple analyses should be consistent
        enhanced_analyzer.analyze_workload_distribution()
        enhanced_analyzer.generate_productivity_insights()

        # Both should process the same base data
        assert enhanced_analyzer.get_issues_dataframe.call_count >= 2

    def test_analytics_performance_with_large_dataset(self, enhanced_analyzer):
        """Test analytics performance with larger dataset."""
        # Simulate larger dataset
        now = datetime.now()
        large_df = pd.DataFrame(
            {
                "id": [f"issue{i}" for i in range(1000)],
                "status": (
                    ["done"] * 400
                    + ["todo"] * 300
                    + ["in-progress"] * 200
                    + ["blocked"] * 100
                ),
                "assignee": [f"user{i % 10}@example.com" for i in range(1000)],
                "estimated_hours": [float(i % 20 + 1) for i in range(1000)],
                "actual_duration_hours": [
                    float((i % 20 + 1) * 0.9) for i in range(1000)
                ],
                "progress_percentage": [float(i % 101) for i in range(1000)],  # 0-100%
                "priority": (["high"] * 250 + ["medium"] * 500 + ["low"] * 250),
                "is_overdue": [i % 5 == 0 for i in range(1000)],  # 20% overdue
                "created": [now - timedelta(days=i % 365) for i in range(1000)],
            }
        )

        enhanced_analyzer.get_issues_dataframe = Mock(return_value=large_df)
        enhanced_analyzer.analyzer.find_bottlenecks = Mock(return_value={})

        # Should handle large datasets efficiently
        result = enhanced_analyzer.generate_productivity_insights()

        assert isinstance(result, dict)
        assert "summary" in result
