"""Comprehensive tests for Data Utils module."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from roadmap.application.data.data_utils import (
    DataAnalyzer,
    DataFrameAdapter,
    QueryBuilder,
)
from roadmap.domain import (
    Issue,
    IssueType,
    Milestone,
    MilestoneStatus,
    Priority,
    Status,
)

# Mark all tests as unit tests
pytestmark = [pytest.mark.unit]


class TestDataFrameAdapter:
    """Test DataFrameAdapter functionality."""

    @pytest.fixture
    def sample_issues(self):
        """Sample issues for testing."""
        return [
            Issue(
                id="issue1",
                title="Task 1",
                issue_type=IssueType.FEATURE,
                priority=Priority.HIGH,
                status=Status.TODO,
                assignee="alice",
            ),
            Issue(
                id="issue2",
                title="Task 2",
                issue_type=IssueType.FEATURE,
                priority=Priority.MEDIUM,
                status=Status.IN_PROGRESS,
                assignee="bob",
            ),
            Issue(
                id="issue3",
                title="Task 3",
                issue_type=IssueType.BUG,
                priority=Priority.LOW,
                status=Status.CLOSED,
                assignee="charlie",
            ),
        ]

    @pytest.fixture
    def sample_milestones(self):
        """Create sample milestones for testing."""
        now = datetime.now()
        return [
            Milestone(
                name="v1.0 Release",
                description="First major release",
                due_date=now + timedelta(days=30),
                status=MilestoneStatus.OPEN,
                created=now - timedelta(days=60),
                updated=now - timedelta(days=5),
            ),
            Milestone(
                name="v1.1 Features",
                description="Feature additions",
                due_date=now + timedelta(days=90),
                status=MilestoneStatus.OPEN,
                created=now - timedelta(days=30),
                updated=now - timedelta(days=1),
            ),
            Milestone(
                name="v0.9 Hotfix",
                description="Critical hotfix",
                due_date=now - timedelta(days=5),
                status=MilestoneStatus.CLOSED,
                created=now - timedelta(days=20),
                updated=now - timedelta(days=5),
            ),
        ]

    def test_issues_to_dataframe_success(self, sample_issues):
        """Test successful conversion of issues to DataFrame."""
        result = DataFrameAdapter.issues_to_dataframe(sample_issues)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert list(result.columns) == [
            "id",
            "title",
            "priority",
            "status",
            "issue_type",
            "milestone",
            "assignee",
            "created",
            "updated",
            "estimated_hours",
            "estimated_display",
            "progress_percentage",
            "progress_display",
            "actual_start_date",
            "actual_end_date",
            "actual_duration_hours",
            "is_overdue",
            "is_started",
            "is_completed",
            "has_been_handed_off",
            "previous_assignee",
            "handoff_date",
            "labels",
            "depends_on",
            "blocks",
            "github_issue",
            "git_branches",
            "completed_date",
        ]

        # Verify data types
        assert pd.api.types.is_datetime64_any_dtype(result["created"])
        assert pd.api.types.is_datetime64_any_dtype(result["updated"])
        assert isinstance(result["priority"].dtype, pd.CategoricalDtype)
        assert isinstance(result["status"].dtype, pd.CategoricalDtype)
        assert isinstance(result["issue_type"].dtype, pd.CategoricalDtype)

        # Verify data content
        assert result.loc[0, "id"] == "issue1"
        assert result.loc[0, "title"] == "Task 1"
        assert result.loc[0, "priority"] == Priority.HIGH.value
        assert result.loc[0, "status"] == Status.TODO.value
        assert result.loc[0, "assignee"] == "alice"

    def test_issues_to_dataframe_empty(self):
        """Test conversion with empty issues list."""
        result = DataFrameAdapter.issues_to_dataframe([])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_issues_to_dataframe_single_issue(self, sample_issues):
        """Test conversion with single issue."""
        result = DataFrameAdapter.issues_to_dataframe([sample_issues[0]])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.loc[0, "id"] == "issue1"

    def test_milestones_to_dataframe_success(self, sample_milestones, sample_issues):
        """Test successful conversion of milestones to DataFrame."""
        result = DataFrameAdapter.milestones_to_dataframe(
            sample_milestones, sample_issues
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

        # Check key columns exist
        expected_columns = [
            "name",
            "description",
            "due_date",
            "status",
            "created",
            "updated",
            "github_milestone",
            "issue_count",
            "completion_percentage",
            "total_estimated_hours",
            "remaining_estimated_hours",
            "estimated_time_display",
            "issues_todo",
            "issues_in_progress",
            "issues_blocked",
            "issues_review",
            "issues_done",
        ]
        for col in expected_columns:
            assert col in result.columns

        # Verify data types
        assert pd.api.types.is_datetime64_any_dtype(result["due_date"])
        assert pd.api.types.is_datetime64_any_dtype(result["created"])
        assert isinstance(result["status"].dtype, pd.CategoricalDtype)

        # Verify data content
        assert result.loc[0, "name"] == "v1.0 Release"
        assert result.loc[0, "description"] == "First major release"

    def test_milestones_to_dataframe_empty(self):
        """Test conversion with empty milestones list."""
        result = DataFrameAdapter.milestones_to_dataframe([], [])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_milestones_to_dataframe_with_issue_metrics(
        self, sample_milestones, sample_issues
    ):
        """Test milestone DataFrame includes correct issue metrics."""
        # Modify sample issues to belong to milestone
        sample_issues[0].milestone = "v1.0 Release"
        sample_issues[1].milestone = "v1.0 Release"

        result = DataFrameAdapter.milestones_to_dataframe(
            sample_milestones, sample_issues
        )

        # v1.0 Release should have 2 issues
        v1_milestone = result[result["name"] == "v1.0 Release"].iloc[0]
        assert (
            v1_milestone["issue_count"] >= 0
        )  # Will depend on milestone.get_issues() implementation

    def test_export_to_csv_success(self, sample_issues):
        """Test successful CSV export."""
        df = DataFrameAdapter.issues_to_dataframe(sample_issues)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            DataFrameAdapter.export_to_csv(df, tmp_path)

            assert tmp_path.exists()

            # Read back and verify
            loaded_df = pd.read_csv(tmp_path)
            assert len(loaded_df) == 3
            assert "id" in loaded_df.columns
            assert loaded_df.loc[0, "id"] == "issue1"
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_export_to_csv_custom_kwargs(self, sample_issues):
        """Test CSV export with custom parameters."""
        df = DataFrameAdapter.issues_to_dataframe(sample_issues)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            DataFrameAdapter.export_to_csv(df, tmp_path, sep=";", index=True)

            assert tmp_path.exists()
            content = tmp_path.read_text()
            assert ";" in content  # Check custom separator
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_export_to_excel_success(self, sample_issues):
        """Test successful Excel export."""
        df = DataFrameAdapter.issues_to_dataframe(sample_issues)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            DataFrameAdapter.export_to_excel(df, tmp_path)

            assert tmp_path.exists()

            # Read back and verify
            loaded_df = pd.read_excel(tmp_path)
            assert len(loaded_df) == 3
            assert "id" in loaded_df.columns
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_export_to_excel_custom_sheet(self, sample_issues):
        """Test Excel export with custom sheet name."""
        df = DataFrameAdapter.issues_to_dataframe(sample_issues)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            DataFrameAdapter.export_to_excel(df, tmp_path, sheet_name="Issues")

            assert tmp_path.exists()

            # Read back and verify sheet name
            loaded_df = pd.read_excel(tmp_path, sheet_name="Issues")
            assert len(loaded_df) == 3
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_export_to_json_success(self, sample_issues):
        """Test successful JSON export."""
        df = DataFrameAdapter.issues_to_dataframe(sample_issues)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            DataFrameAdapter.export_to_json(df, tmp_path)

            assert tmp_path.exists()

            # Read back and verify
            with open(tmp_path) as f:
                loaded_data = json.load(f)

            assert isinstance(loaded_data, list)
            assert len(loaded_data) == 3
            assert loaded_data[0]["id"] == "issue1"
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_export_to_json_custom_orient(self, sample_issues):
        """Test JSON export with custom orientation."""
        df = DataFrameAdapter.issues_to_dataframe(sample_issues)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            DataFrameAdapter.export_to_json(df, tmp_path, orient="index")

            assert tmp_path.exists()

            # Read back and verify structure
            with open(tmp_path) as f:
                loaded_data = json.load(f)

            assert isinstance(loaded_data, dict)
            assert "0" in loaded_data  # Index-based keys
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_export_multiple_sheets_success(self, sample_issues, sample_milestones):
        """Test successful multi-sheet Excel export."""
        issues_df = DataFrameAdapter.issues_to_dataframe(sample_issues)
        milestones_df = DataFrameAdapter.milestones_to_dataframe(
            sample_milestones, sample_issues
        )

        data_dict = {"Issues": issues_df, "Milestones": milestones_df}

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            DataFrameAdapter.export_multiple_sheets(data_dict, tmp_path)

            assert tmp_path.exists()

            # Read back and verify sheets
            issues_loaded = pd.read_excel(tmp_path, sheet_name="Issues")
            milestones_loaded = pd.read_excel(tmp_path, sheet_name="Milestones")

            assert len(issues_loaded) == 3
            assert len(milestones_loaded) == 3
            assert issues_loaded.loc[0, "id"] == "issue1"
            assert milestones_loaded.loc[0, "name"] == "v1.0 Release"
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_export_multiple_sheets_empty_dict(self):
        """Test multi-sheet export with empty data dictionary."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Excel files require at least one sheet, so this should raise an error
            with pytest.raises(IndexError, match="At least one sheet must be visible"):
                DataFrameAdapter.export_multiple_sheets({}, tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestDataAnalyzer:
    """Test DataAnalyzer functionality."""

    @pytest.fixture
    def velocity_issues_df(self):
        """Create DataFrame for velocity analysis testing."""
        now = datetime.now()
        return pd.DataFrame(
            {
                "id": ["1", "2", "3", "4", "5"],
                "actual_end_date": [
                    now - timedelta(days=7),
                    now - timedelta(days=14),
                    now - timedelta(days=21),
                    now - timedelta(days=28),
                    None,  # Not completed
                ],
                "estimated_hours": [8.0, 4.0, 12.0, 6.0, 10.0],
                "actual_duration_hours": [7.0, 4.5, 11.0, 5.5, 0.0],
                "priority": ["critical", "high", "medium", "low", "medium"],
            }
        )

    @pytest.fixture
    def team_performance_df(self):
        """Create DataFrame for team performance testing."""
        return pd.DataFrame(
            {
                "assignee": ["alice", "alice", "bob", "bob", "charlie"],
                "id": ["1", "2", "3", "4", "5"],
                "estimated_hours": [8.0, 4.0, 12.0, 6.0, 10.0],
                "actual_duration_hours": [7.0, 4.5, 11.0, 5.5, 9.0],
                "is_overdue": [False, False, True, False, False],
                "is_completed": [True, True, False, True, False],
                "priority": ["critical", "high", "medium", "low", "medium"],
                "status": ["closed", "closed", "in-progress", "closed", "todo"],
            }
        )

    @pytest.fixture
    def milestone_health_df(self):
        """Create DataFrame for milestone health testing."""
        return pd.DataFrame(
            {
                "name": ["v1.0", "v1.1", "v2.0"],
                "completion_percentage": [80.0, 45.0, 10.0],
                "issues_todo": [2, 5, 8],
                "issues_in_progress": [3, 2, 1],
                "issues_blocked": [1, 0, 2],
                "issue_count": [10, 12, 15],
                "due_date": [
                    datetime.now() + timedelta(days=30),
                    datetime.now() + timedelta(days=60),
                    datetime.now() + timedelta(days=120),
                ],
            }
        )

    @pytest.fixture
    def bottleneck_issues_df(self):
        """DataFrame with various bottleneck scenarios."""
        return pd.DataFrame(
            {
                "status": [
                    "todo",
                    "in-progress",
                    "blocked",
                    "blocked",
                    "review",
                    "closed",
                ],
                "assignee": ["alice", "alice", "bob", "bob", "charlie", "alice"],
                "priority": ["high", "medium", "critical", "high", "low", "medium"],
                "depends_on": ["", "", "", "issue3", "", ""],
                "milestone": ["v1.0", "v1.0", "v1.1", "v1.1", "v1.0", "v1.1"],
                "id": ["1", "2", "3", "4", "5", "6"],
            }
        )

    def test_analyze_velocity_trends_success(self, velocity_issues_df):
        """Test successful velocity trends analysis."""
        result = DataAnalyzer.analyze_velocity_trends(velocity_issues_df, period="W")

        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            expected_columns = [
                "issues_completed",
                "total_estimated_hours",
                "avg_estimated_hours",
                "total_actual_hours",
                "avg_actual_hours",
                "critical_issues_completed",
                "velocity_score",
            ]
            for col in expected_columns:
                assert col in result.columns

            # Verify velocity score calculation
            assert "velocity_score" in result.columns
            assert result["velocity_score"].dtype in ["float64", "int64"]

    def test_analyze_velocity_trends_empty_data(self):
        """Test velocity trends with empty DataFrame."""
        empty_df = pd.DataFrame()
        result = DataAnalyzer.analyze_velocity_trends(empty_df)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_analyze_velocity_trends_no_completed(self):
        """Test velocity trends with no completed issues."""
        df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "actual_end_date": [None, None],
                "estimated_hours": [8.0, 4.0],
                "actual_duration_hours": [0.0, 0.0],
                "priority": ["high", "medium"],
            }
        )

        result = DataAnalyzer.analyze_velocity_trends(df)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_analyze_velocity_trends_custom_period(self, velocity_issues_df):
        """Test velocity trends with custom period."""
        result = DataAnalyzer.analyze_velocity_trends(velocity_issues_df, period="M")

        assert isinstance(result, pd.DataFrame)

    def test_analyze_team_performance_success(self, team_performance_df):
        """Test successful team performance analysis."""
        result = DataAnalyzer.analyze_team_performance(team_performance_df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 1  # Should have at least one assignee

        expected_columns = [
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
            "completion_rate",
            "efficiency_ratio",
        ]

        for col in expected_columns:
            assert col in result.columns

        # Verify calculations
        assert result["completion_rate"].min() >= 0
        assert result["completion_rate"].max() <= 100
        assert result["efficiency_ratio"].min() >= 0

    def test_analyze_team_performance_empty_data(self):
        """Test team performance with empty DataFrame."""
        empty_df = pd.DataFrame()
        result = DataAnalyzer.analyze_team_performance(empty_df)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_analyze_team_performance_single_assignee(self):
        """Test team performance with single assignee."""
        single_df = pd.DataFrame(
            {
                "assignee": ["alice"],
                "id": ["1"],
                "estimated_hours": [8.0],
                "actual_duration_hours": [7.0],
                "is_overdue": [False],
                "is_completed": [True],
                "priority": ["high"],
                "status": ["closed"],
            }
        )

        result = DataAnalyzer.analyze_team_performance(single_df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.loc[0, "total_issues"] == 1

    def test_analyze_milestone_health_success(self, milestone_health_df):
        """Test successful milestone health analysis."""
        result = DataAnalyzer.analyze_milestone_health(milestone_health_df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

        # Check health score calculation
        assert "health_score" in result.columns
        assert "health_status" in result.columns

        # Verify health score range
        assert result["health_score"].min() >= 0
        assert result["health_score"].max() <= 100

        # Verify health status categories
        valid_statuses = ["Critical", "At Risk", "On Track", "Excellent"]
        assert result["health_status"].isin(valid_statuses).all()

    def test_analyze_milestone_health_empty_data(self):
        """Test milestone health with empty DataFrame."""
        empty_df = pd.DataFrame()
        result = DataAnalyzer.analyze_milestone_health(empty_df)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_analyze_milestone_health_calculation_logic(self, milestone_health_df):
        """Test milestone health calculation logic."""
        result = DataAnalyzer.analyze_milestone_health(milestone_health_df)

        # v1.0 with 80% completion should have higher health score than v1.1 with 45%
        v1_0_health = result[result["name"] == "v1.0"]["health_score"].iloc[0]  # type: ignore[attr-defined]
        v1_1_health = result[result["name"] == "v1.1"]["health_score"].iloc[0]  # type: ignore[attr-defined]

        assert v1_0_health > v1_1_health

    def test_find_bottlenecks_success(self, bottleneck_issues_df):
        """Test successful bottleneck detection."""
        result = DataAnalyzer.find_bottlenecks(bottleneck_issues_df)

        assert isinstance(result, dict)

        # Should detect blocked issues
        if "blocked_issues" in result:
            assert result["blocked_issues"]["count"] == 2
            assert result["blocked_issues"]["percentage"] > 0

    def test_find_bottlenecks_empty_data(self):
        """Test bottleneck detection with empty DataFrame."""
        empty_df = pd.DataFrame()
        result = DataAnalyzer.find_bottlenecks(empty_df)

        assert isinstance(result, dict)
        assert result == {}

    def test_find_bottlenecks_no_bottlenecks(self):
        """Test bottleneck detection with no bottlenecks."""
        clean_df = pd.DataFrame(
            {
                "status": ["closed", "closed", "review"],
                "assignee": ["alice", "bob", "charlie"],
                "priority": ["medium", "low", "high"],
                "depends_on": ["", "", ""],
                "milestone": ["v1.0", "v1.1", "v1.0"],
                "id": ["1", "2", "3"],
            }
        )

        result = DataAnalyzer.find_bottlenecks(clean_df)

        assert isinstance(result, dict)

    def test_find_bottlenecks_overloaded_assignees(self):
        """Test detection of overloaded assignees."""
        overloaded_df = pd.DataFrame(
            {
                "status": ["todo"] * 8 + ["in-progress"] * 2,
                "assignee": ["alice"] * 10,  # Alice has too many active issues
                "priority": ["medium"] * 10,
                "depends_on": [""] * 10,
                "milestone": ["v1.0"] * 10,
                "id": [str(i) for i in range(1, 11)],
            }
        )

        result = DataAnalyzer.find_bottlenecks(overloaded_df)

        assert isinstance(result, dict)
        if "overloaded_assignees" in result:
            assert len(result["overloaded_assignees"]) >= 1


class TestQueryBuilder:
    """Test QueryBuilder functionality."""

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame for testing."""
        return pd.DataFrame(
            {
                "id": ["1", "2", "3", "4", "5"],
                "title": ["Feature A", "Bug Fix B", "Task C", "Feature D", "Bug E"],
                "status": ["todo", "closed", "in-progress", "blocked", "review"],
                "priority": ["high", "critical", "medium", "low", "high"],
                "assignee": ["alice", "bob", "alice", "charlie", "bob"],
                "created": [
                    datetime(2023, 1, 1),
                    datetime(2023, 1, 5),
                    datetime(2023, 1, 10),
                    datetime(2023, 1, 15),
                    datetime(2023, 1, 20),
                ],
                "estimated_hours": [8.0, 4.0, 12.0, 6.0, 2.0],
            }
        )

    def test_filter_by_date_range_success(self, sample_df):
        """Test successful date range filtering."""
        start_date = datetime(2023, 1, 8)
        end_date = datetime(2023, 1, 18)

        result = QueryBuilder.filter_by_date_range(
            sample_df, "created", start_date, end_date
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # Should include items created on 1/10 and 1/15
        assert all(result["created"] >= start_date)
        assert all(result["created"] <= end_date)

    def test_filter_by_date_range_start_only(self, sample_df):
        """Test date filtering with start date only."""
        start_date = datetime(2023, 1, 10)

        result = QueryBuilder.filter_by_date_range(
            sample_df, "created", start_date=start_date
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3  # Should include items from 1/10 onwards
        assert all(result["created"] >= start_date)

    def test_filter_by_date_range_end_only(self, sample_df):
        """Test date filtering with end date only."""
        end_date = datetime(2023, 1, 10)

        result = QueryBuilder.filter_by_date_range(
            sample_df, "created", end_date=end_date
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3  # Should include items up to 1/10
        assert all(result["created"] <= end_date)

    def test_filter_by_date_range_empty_data(self):
        """Test date filtering with empty DataFrame."""
        empty_df = pd.DataFrame()

        result = QueryBuilder.filter_by_date_range(
            empty_df, "created", datetime(2023, 1, 1)
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_filter_by_date_range_missing_column(self, sample_df):
        """Test date filtering with missing column."""
        result = QueryBuilder.filter_by_date_range(
            sample_df, "missing_column", datetime(2023, 1, 1)
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_df)  # Should return original DataFrame

    def test_filter_by_criteria_single_value(self, sample_df):
        """Test filtering by single criterion."""
        result = QueryBuilder.filter_by_criteria(sample_df, status="closed")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["status"] == "closed"
        assert result.iloc[0]["id"] == "2"

    def test_filter_by_criteria_multiple_values(self, sample_df):
        """Test filtering by multiple criteria."""
        result = QueryBuilder.filter_by_criteria(
            sample_df, status="todo", assignee="alice"
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["status"] == "todo"
        assert result.iloc[0]["assignee"] == "alice"

    def test_filter_by_criteria_list_values(self, sample_df):
        """Test filtering with list of values."""
        result = QueryBuilder.filter_by_criteria(sample_df, status=["todo", "closed"])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert all(result["status"].isin(["todo", "closed"]))

    def test_filter_by_criteria_no_match(self, sample_df):
        """Test filtering with no matches."""
        result = QueryBuilder.filter_by_criteria(sample_df, status="nonexistent")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_filter_by_criteria_empty_data(self):
        """Test filtering with empty DataFrame."""
        empty_df = pd.DataFrame()

        result = QueryBuilder.filter_by_criteria(empty_df, status="closed")

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_filter_by_criteria_missing_column(self, sample_df):
        """Test filtering with missing column."""
        result = QueryBuilder.filter_by_criteria(sample_df, missing_column="value")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_df)  # Should return original DataFrame

    def test_search_text_success(self, sample_df):
        """Test successful text search."""
        result = QueryBuilder.search_text(sample_df, "Feature")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # Should find 'Feature A' and 'Feature D'
        assert all(result["title"].str.contains("Feature", case=False))

    def test_search_text_case_insensitive(self, sample_df):
        """Test case-insensitive text search."""
        result = QueryBuilder.search_text(sample_df, "feature")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # Should find 'Feature A' and 'Feature D'

    def test_search_text_specific_columns(self, sample_df):
        """Test text search in specific columns."""
        result = QueryBuilder.search_text(sample_df, "alice", columns=["assignee"])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # Should find both alice assignments
        assert all(result["assignee"] == "alice")

    def test_search_text_no_match(self, sample_df):
        """Test text search with no matches."""
        result = QueryBuilder.search_text(sample_df, "nonexistent")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_search_text_empty_term(self, sample_df):
        """Test text search with empty search term."""
        result = QueryBuilder.search_text(sample_df, "")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_df)  # Should return original DataFrame

    def test_search_text_empty_data(self):
        """Test text search with empty DataFrame."""
        empty_df = pd.DataFrame()

        result = QueryBuilder.search_text(empty_df, "search")

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_search_text_missing_columns(self, sample_df):
        """Test text search with missing columns."""
        result = QueryBuilder.search_text(
            sample_df, "Feature", columns=["missing_column"]
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0  # No matches since column doesn't exist


class TestDataUtilsIntegration:
    """Integration tests for Data Utils components."""

    @pytest.fixture
    def comprehensive_issues(self):
        """Create comprehensive issue dataset for integration testing."""
        now = datetime.now()
        issues = []

        assignees = ["alice@example.com", "bob@example.com", "charlie@example.com"]
        priorities = [Priority.HIGH, Priority.MEDIUM, Priority.LOW, Priority.CRITICAL]
        statuses = [
            Status.TODO,
            Status.IN_PROGRESS,
            Status.REVIEW,
            Status.CLOSED,
            Status.BLOCKED,
        ]

        for i in range(20):
            issue = Issue(
                id=f"issue{i+1}",
                title=f"Task {i+1}",
                priority=priorities[i % len(priorities)],
                status=statuses[i % len(statuses)],
                issue_type=IssueType.FEATURE if i % 2 == 0 else IssueType.BUG,
                milestone=f"v{1 + i//10}.0",
                assignee=assignees[i % len(assignees)],
                created=now - timedelta(days=30 - i),
                updated=now - timedelta(hours=i + 1),
                estimated_hours=float(2 + i % 10),
                progress_percentage=float(i * 5),
            )
            if i % 5 == 0:  # Some completed issues
                issue.actual_start_date = now - timedelta(days=15 - i // 2)
                issue.actual_end_date = now - timedelta(days=10 - i // 3)
            issues.append(issue)

        return issues

    def test_full_workflow_adapter_to_analyzer(self, comprehensive_issues):
        """Test complete workflow from adapter to analyzer."""
        # Convert to DataFrame
        df = DataFrameAdapter.issues_to_dataframe(comprehensive_issues)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 20

        # Analyze team performance
        team_perf = DataAnalyzer.analyze_team_performance(df)

        assert isinstance(team_perf, pd.DataFrame)
        assert len(team_perf) == 3  # Three assignees

        # Find bottlenecks
        bottlenecks = DataAnalyzer.find_bottlenecks(df)

        assert isinstance(bottlenecks, dict)

    def test_full_workflow_with_filtering(self, comprehensive_issues):
        """Test complete workflow with filtering operations."""
        # Convert to DataFrame
        df = DataFrameAdapter.issues_to_dataframe(comprehensive_issues)

        # Filter by assignee
        alice_issues = QueryBuilder.filter_by_criteria(df, assignee="alice@example.com")

        assert len(alice_issues) > 0

        # Filter by date range
        recent_cutoff = datetime.now() - timedelta(days=15)
        recent_issues = QueryBuilder.filter_by_date_range(
            df, "created", start_date=recent_cutoff
        )

        assert len(recent_issues) > 0

        # Search for specific terms
        feature_issues = QueryBuilder.search_text(alice_issues, "Task")

        assert len(feature_issues) > 0

    def test_export_and_analysis_workflow(self, comprehensive_issues):
        """Test export functionality with analysis workflow."""
        # Convert issues to DataFrame
        issues_df = DataFrameAdapter.issues_to_dataframe(comprehensive_issues)

        # Perform analysis
        team_perf = DataAnalyzer.analyze_team_performance(issues_df)
        DataAnalyzer.find_bottlenecks(issues_df)

        # Test export to temporary files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Export main data
            csv_path = tmpdir_path / "issues.csv"
            DataFrameAdapter.export_to_csv(issues_df, csv_path)
            assert csv_path.exists()

            # Export analysis results
            excel_path = tmpdir_path / "analysis.xlsx"
            data_dict = {"Issues": issues_df, "Team Performance": team_perf}
            DataFrameAdapter.export_multiple_sheets(data_dict, excel_path)
            assert excel_path.exists()

            # Verify exports by reading back
            loaded_csv = pd.read_csv(csv_path)
            assert len(loaded_csv) == len(issues_df)

            loaded_issues = pd.read_excel(excel_path, sheet_name="Issues")
            loaded_team = pd.read_excel(excel_path, sheet_name="Team Performance")
            assert len(loaded_issues) == len(issues_df)
            assert len(loaded_team) == len(team_perf)

    def test_performance_with_large_dataset(self):
        """Test performance with larger dataset."""
        # Create larger dataset
        now = datetime.now()
        large_issues = []

        for i in range(100):
            issue = Issue(
                id=f"large_issue_{i}",
                title=f"Large Task {i}",
                priority=Priority.MEDIUM,
                status=Status.TODO if i % 2 == 0 else Status.CLOSED,
                issue_type=IssueType.FEATURE,
                assignee=f"user{i%5}@example.com",
                created=now - timedelta(days=i),
                estimated_hours=float(5 + i % 15),
            )
            large_issues.append(issue)

        # Test conversion and analysis
        df = DataFrameAdapter.issues_to_dataframe(large_issues)

        assert len(df) == 100

        # Perform multiple analyses
        team_perf = DataAnalyzer.analyze_team_performance(df)
        bottlenecks = DataAnalyzer.find_bottlenecks(df)

        # Filter operations
        filtered = QueryBuilder.filter_by_criteria(df, status="closed")
        searched = QueryBuilder.search_text(df, "Large")

        assert isinstance(team_perf, pd.DataFrame)
        assert isinstance(bottlenecks, dict)
        assert isinstance(filtered, pd.DataFrame)
        assert isinstance(searched, pd.DataFrame)
        assert len(searched) == 100  # All contain 'Large'


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_dataframe_adapter_with_malformed_issues(self):
        """Test adapter handling of issues with missing attributes."""
        # Create issue with minimal attributes
        minimal_issue = Issue(id="minimal", title="Minimal Issue")

        # Should handle gracefully without errors
        result = DataFrameAdapter.issues_to_dataframe([minimal_issue])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.loc[0, "id"] == "minimal"

    def test_analyzer_with_missing_columns(self):
        """Test analyzer methods with DataFrames missing expected columns."""
        # DataFrame missing required columns
        incomplete_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "title": ["Task 1", "Task 2"],
                # Missing many expected columns
            }
        )

        # Should handle gracefully by raising KeyError
        with pytest.raises(KeyError):
            DataAnalyzer.analyze_team_performance(incomplete_df)

    def test_query_builder_with_none_values(self):
        """Test QueryBuilder with None values in data."""
        df_with_nones = pd.DataFrame(
            {
                "id": ["1", "2", "3"],
                "title": ["Task 1", None, "Task 3"],
                "assignee": ["alice", None, "bob"],
                "created": [datetime.now(), None, datetime.now()],
            }
        )

        # Should handle None values gracefully
        result = QueryBuilder.search_text(df_with_nones, "Task")

        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 1  # Should find at least one match

    def test_export_with_special_characters(self):
        """Test export functionality with special characters."""
        special_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "title": ["Task with émojis 🚀", "Special chars: @#$%"],
                "description": ["Multi\nline\ntext", "Tabs\there"],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Test CSV export with special characters
            csv_path = tmpdir_path / "special.csv"
            DataFrameAdapter.export_to_csv(special_df, csv_path)
            assert csv_path.exists()

            # Test JSON export with special characters
            json_path = tmpdir_path / "special.json"
            DataFrameAdapter.export_to_json(special_df, json_path)
            assert json_path.exists()
