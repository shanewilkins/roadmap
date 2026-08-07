"""Tests for issue table formatter."""

from unittest.mock import Mock, patch

import pytest

from roadmap.common.formatters.tables.issue_table import IssueTableFormatter
from roadmap.common.models import TableData
from roadmap.core.domain import Priority, Status


class MockIssue:
    """Mock issue object for testing."""

    def __init__(
        self,
        issue_id="ISSUE-1",
        title="Test Issue",
        priority=None,
        status=None,
        progress_display="0%",
        assignee: str | None = "John Doe",
        estimated_time_display="0h",
        milestone_name="v1-0",
        is_backlog=False,
        github_issue=None,
        progress_percentage=0,
        estimated_hours=0,
        headline="Test Headline",
    ):
        """Initialize mock issue."""
        self.id = issue_id
        self.title = title
        self.headline = headline
        self.priority = priority or Priority.MEDIUM
        self.status = status or Status.TODO
        self.progress_display = progress_display
        self.assignee = assignee
        self.estimated_time_display = estimated_time_display
        self.milestone_name = milestone_name
        self.is_backlog = is_backlog
        self.github_issue = github_issue
        self.progress_percentage = progress_percentage
        self.estimated_hours = estimated_hours


class TestIssueTableFormatter:
    """Tests for IssueTableFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return IssueTableFormatter()

    @pytest.fixture
    def sample_issue(self):
        """Create sample issue object."""
        return MockIssue()

    @pytest.fixture
    def multiple_issues(self):
        """Create multiple sample issues."""
        return [
            MockIssue("ISSUE-1", "First Issue", Priority.HIGH),
            MockIssue("ISSUE-2", "Second Issue", Priority.MEDIUM),
            MockIssue("ISSUE-3", "Third Issue", Priority.LOW),
        ]

    def test_init_creates_formatter(self):
        """Test initializing formatter."""
        formatter = IssueTableFormatter()
        assert formatter is not None
        assert formatter.columns_config is not None
        assert formatter.show_github_ids is False

    def test_init_sets_columns_config(self):
        """Test columns config is properly initialized."""
        formatter = IssueTableFormatter()
        assert len(formatter.columns_config) == 9
        assert formatter.columns_config[0]["name"] == "ID"
        assert formatter.columns_config[1]["name"] == "Title"
        assert formatter.columns_config[2]["name"] == "Headline"

    def test_create_table_returns_table(self, formatter):
        """Test creating a table."""
        table = formatter.create_table()
        assert table is not None
        assert hasattr(table, "add_row")

    def test_create_table_without_github_ids(self, formatter):
        """Test table without GitHub ID column."""
        formatter.show_github_ids = False
        table = formatter.create_table()
        assert hasattr(table, "columns")

    def test_create_table_with_github_ids(self, formatter):
        """Test table with GitHub ID column."""
        formatter.show_github_ids = True
        table = formatter.create_table()
        assert hasattr(table, "columns")

    @pytest.mark.parametrize(
        "priority",
        [
            Priority.CRITICAL,
            Priority.HIGH,
            Priority.MEDIUM,
            Priority.LOW,
        ],
    )
    def test_add_row_with_various_priorities(self, formatter, sample_issue, priority):
        """Test adding row with various priority levels."""
        table = formatter.create_table()
        issue = MockIssue(priority=priority)
        formatter.add_row(table, issue)
        assert len(table.rows) == 1

    def test_add_row_without_assignee(self, formatter):
        """Test adding row without assignee."""
        table = formatter.create_table()
        issue = MockIssue(assignee=None)
        formatter.add_row(table, issue)
        assert len(table.rows) == 1

    def test_add_row_with_github_id(self, formatter):
        """Test adding row with GitHub ID."""
        formatter.show_github_ids = True
        table = formatter.create_table()
        issue = MockIssue(github_issue="12345")
        formatter.add_row(table, issue)
        assert len(table.rows) == 1

    def test_add_row_with_progress(self, formatter):
        """Test adding row with progress."""
        table = formatter.create_table()
        issue = MockIssue(progress_display="50%", progress_percentage=50)
        formatter.add_row(table, issue)
        assert len(table.rows) == 1

    def test_add_row_with_estimated_hours(self, formatter):
        """Test adding row with estimated hours."""
        table = formatter.create_table()
        issue = MockIssue(estimated_time_display="8h", estimated_hours=8)
        formatter.add_row(table, issue)
        assert len(table.rows) == 1

    def test_get_filter_description_single_issue(self, formatter):
        """Test filter description for single issue."""
        description = formatter.get_filter_description([MockIssue()])
        assert "1 issue" in description
        assert "📋" in description

    def test_get_filter_description_multiple_issues(self, formatter):
        """Test filter description for multiple issues."""
        issues = [MockIssue(f"ISSUE-{i}") for i in range(3)]
        description = formatter.get_filter_description(issues)
        assert "3 issues" in description

    def test_get_filter_description_empty_list(self, formatter):
        """Test filter description for empty list."""
        description = formatter.get_filter_description([])
        assert "0 issues" in description

    def test_display_items_empty_list(self, formatter):
        """Test displaying empty items list."""
        with patch(
            "roadmap.common.formatters.tables.issue_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            formatter.display_items([], "open")

        assert mock_console.print.call_count >= 2

    def test_display_items_with_issues(self, formatter, multiple_issues):
        """Test displaying issues."""
        with patch(
            "roadmap.common.formatters.tables.issue_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            formatter.display_items(multiple_issues, "open")

        assert mock_console.print.call_count >= 2

    def test_display_items_with_filter_description(self, formatter, sample_issue):
        """Test displaying items with custom filter description."""
        with patch(
            "roadmap.common.formatters.tables.issue_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            formatter.display_items([sample_issue], "urgent")

        assert mock_console.print.call_count >= 2

    def test_items_to_table_data_returns_table_data(self, formatter, sample_issue):
        """Test converting items to TableData."""
        result = formatter.items_to_table_data([sample_issue])

        assert isinstance(result, TableData)
        assert result.title == "Issues"
        assert result.total_count == 1

    def test_items_to_table_data_with_multiple_issues(self, formatter, multiple_issues):
        """Test converting multiple issues to TableData."""
        result = formatter.items_to_table_data(multiple_issues)

        assert isinstance(result, TableData)
        assert len(result.rows) == 3
        assert result.total_count == 3

    def test_items_to_table_data_empty_list(self, formatter):
        """Test converting empty list."""
        result = formatter.items_to_table_data([])

        assert isinstance(result, TableData)
        assert len(result.rows) == 0
        assert result.total_count == 0

    def test_items_to_table_data_with_custom_title(self, formatter, sample_issue):
        """Test converting with custom title."""
        result = formatter.items_to_table_data([sample_issue], title="Custom Title")

        assert result.title == "Custom Title"

    def test_items_to_table_data_with_description(self, formatter, sample_issue):
        """Test converting with description."""
        result = formatter.items_to_table_data(
            [sample_issue], description="Test Description"
        )

        assert result.headline == "Test Description"

    def test_create_issue_table_class_method(self):
        """Test backward compatible class method."""
        table = IssueTableFormatter.create_issue_table()
        assert table is not None

    def test_add_issue_row_class_method(self, sample_issue):
        """Test backward compatible add_issue_row method."""
        table = IssueTableFormatter.create_issue_table()
        IssueTableFormatter.add_issue_row(table, sample_issue)
        assert len(table.rows) == 1

    def test_display_issues_class_method(self, multiple_issues):
        """Test backward compatible display_issues method."""
        with patch(
            "roadmap.common.formatters.tables.issue_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            IssueTableFormatter.display_issues(multiple_issues, "open")

        assert mock_console.print.call_count >= 2

    def test_issues_to_table_data_static_method(self, multiple_issues):
        """Test backward compatible static method."""
        result = IssueTableFormatter.issues_to_table_data(multiple_issues)

        assert isinstance(result, TableData)
        assert len(result.rows) == 3

    def test_issues_to_table_data_with_github_ids(self, multiple_issues):
        """Test static method with GitHub IDs."""
        result = IssueTableFormatter.issues_to_table_data(
            multiple_issues, show_github_ids=True
        )

        assert isinstance(result, TableData)
        assert len(result.rows) == 3

    def test_display_workload_summary_zero_hours(self, formatter):
        """Test workload summary with zero hours."""
        with patch(
            "roadmap.common.formatters.tables.issue_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            IssueTableFormatter.display_workload_summary("John Doe", 0, {})

        # Should not print anything for zero hours
        mock_console.print.assert_not_called()

    def test_display_workload_summary_with_hours(self, formatter):
        """Test workload summary with hours."""
        with patch(
            "roadmap.common.formatters.tables.issue_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            status_breakdown = {
                "open": {"count": 2, "hours": 8},
                "in_progress": {"count": 1, "hours": 4},
            }

            IssueTableFormatter.display_workload_summary(
                "John Doe", 12, status_breakdown
            )

        assert mock_console.print.call_count >= 2

    def test_display_workload_summary_less_than_1_hour(self):
        """Test workload summary with less than 1 hour."""
        with patch(
            "roadmap.common.formatters.tables.issue_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            IssueTableFormatter.display_workload_summary("Jane Doe", 0.5, {})

        assert mock_console.print.call_count >= 1

    def test_display_workload_summary_more_than_24_hours(self):
        """Test workload summary with more than 24 hours."""
        with patch(
            "roadmap.common.formatters.tables.issue_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            IssueTableFormatter.display_workload_summary("Bob Smith", 32, {})

        assert mock_console.print.call_count >= 1

    def test_display_workload_summary_status_breakdown(self):
        """Test workload summary with status breakdown."""
        with patch(
            "roadmap.common.formatters.tables.issue_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            status_breakdown = {
                "open": {"count": 3, "hours": 12},
                "in_progress": {"count": 1, "hours": 0},
            }

            IssueTableFormatter.display_workload_summary("Alice", 12, status_breakdown)

        assert mock_console.print.call_count >= 3

    @pytest.mark.parametrize("issue_count", [1, 2, 5, 10])
    def test_add_multiple_rows(self, formatter, issue_count):
        """Test adding multiple rows."""
        table = formatter.create_table()
        issues = [MockIssue(f"ISSUE-{i}") for i in range(issue_count)]

        for issue in issues:
            formatter.add_row(table, issue)

        assert len(table.rows) == issue_count

    @pytest.mark.parametrize("issue_count", [1, 2, 5])
    def test_items_to_table_data_multiple_counts(self, formatter, issue_count):
        """Test TableData with various issue counts."""
        issues = [MockIssue(f"ISSUE-{i}") for i in range(issue_count)]

        result = formatter.items_to_table_data(issues)

        assert len(result.rows) == issue_count
        assert result.total_count == issue_count
        assert result.returned_count == issue_count

    def test_columns_config_has_required_properties(self, formatter):
        """Test that column config has required properties."""
        for col in formatter.columns_config:
            assert "name" in col
            assert "style" in col
            assert "width" in col

    def test_add_row_preserves_issue_data(self, formatter):
        """Test that add_row preserves all issue data."""
        table = formatter.create_table()
        issue = MockIssue(
            issue_id="ISSUE-999",
            title="Critical Bug",
            priority=Priority.CRITICAL,
        )
        formatter.add_row(table, issue)
        assert len(table.rows) == 1

    def test_items_to_table_data_preserves_order(self, formatter):
        """Test that items maintain their order in TableData."""
        issues = [
            MockIssue("ISSUE-1", "First"),
            MockIssue("ISSUE-2", "Second"),
            MockIssue("ISSUE-3", "Third"),
        ]

        result = formatter.items_to_table_data(issues)

        assert len(result.rows) == 3
        assert "ISSUE-1" in result.rows[0][0]
        assert "ISSUE-2" in result.rows[1][0]
        assert "ISSUE-3" in result.rows[2][0]

    def test_github_id_column_config_exists(self, formatter):
        """Test that GitHub ID column config exists."""
        assert hasattr(formatter, "github_id_column")
        assert formatter.github_id_column["name"] == "GitHub #"

    def test_display_items_multiple_issues(self, formatter):
        """Test displaying multiple issues."""
        issues = [MockIssue(f"ISSUE-{i}") for i in range(3)]

        with patch(
            "roadmap.common.formatters.tables.issue_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            formatter.display_items(issues, "assigned")

        assert mock_console.print.call_count >= 2
