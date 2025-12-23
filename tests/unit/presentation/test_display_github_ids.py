"""Unit tests for display GitHub IDs feature."""

from unittest.mock import Mock

import pytest
from rich.table import Table

from roadmap.shared.formatters.tables.issue_table import IssueTableFormatter


@pytest.fixture
def mock_issue_with_github():
    """Create a mock issue with GitHub ID."""
    return Mock(
        id="test-123",
        title="Test Issue",
        github_issue=456,
        priority=Mock(value="high"),
        status=Mock(value="todo"),
        progress_display="0%",
        progress_percentage=0,
        assignee="shane",
        estimated_time_display="5h",
        estimated_hours=5,
        milestone_name="v0.8",
        is_backlog=False,
    )


@pytest.fixture
def mock_issue_without_github():
    """Create a mock issue without GitHub ID."""
    return Mock(
        id="test-456",
        title="Another Issue",
        github_issue=None,
        priority=Mock(value="medium"),
        status=Mock(value="in_progress"),
        progress_display="50%",
        progress_percentage=50,
        assignee=None,
        estimated_time_display="3h",
        estimated_hours=3,
        milestone_name="backlog",
        is_backlog=True,
    )


@pytest.fixture
def formatter_with_table(request):
    """Create formatter and table with columns."""
    formatter = IssueTableFormatter()
    show_github_ids = getattr(request, "param", True)
    formatter.show_github_ids = show_github_ids

    table = Table()
    for col in formatter.columns_config:
        table.add_column(col["name"], style=col["style"], width=col["width"])
    if show_github_ids:
        table.add_column(
            formatter.github_id_column["name"],
            style=formatter.github_id_column["style"],
            width=formatter.github_id_column["width"],
        )
    return formatter, table


class TestGitHubIDTableFormatting:
    """Test GitHub ID display in table formatting."""

    def test_table_columns_with_github_ids(self, mock_issue_with_github):
        """Test GitHub ID column is included when flag is True."""
        formatter = IssueTableFormatter()
        formatter.show_github_ids = True
        table = formatter.create_table()

        assert table.columns is not None
        column_titles = [col.header for col in table.columns]
        assert "GitHub #" in column_titles

    def test_table_columns_without_github_ids(self, mock_issue_with_github):
        """Test GitHub ID column is excluded when flag is False."""
        formatter = IssueTableFormatter()
        formatter.show_github_ids = False
        table = formatter.create_table()

        assert table.columns is not None
        column_titles = [col.header for col in table.columns]
        assert "GitHub #" not in column_titles

    @pytest.mark.parametrize("show_ids,has_github", [
        (True, True),
        (True, False),
        (False, True),
    ])
    def test_add_row_variations(self, mock_issue_with_github, mock_issue_without_github, show_ids, has_github):
        """Test add_row with various configurations."""
        formatter = IssueTableFormatter()
        formatter.show_github_ids = show_ids

        table = Table()
        for col in formatter.columns_config:
            table.add_column(col["name"], style=col["style"], width=col["width"])
        if show_ids:
            table.add_column(
                formatter.github_id_column["name"],
                style=formatter.github_id_column["style"],
                width=formatter.github_id_column["width"],
            )

        issue = mock_issue_with_github if has_github else mock_issue_without_github
        formatter.add_row(table, issue)

        assert len(table.rows) == 1

    def test_multiple_issues_mixed_ids(self, mock_issue_with_github, mock_issue_without_github):
        """Test formatting multiple issues with mixed GitHub ID presence."""
        formatter = IssueTableFormatter()
        formatter.show_github_ids = True

        table = Table()
        for col in formatter.columns_config:
            table.add_column(col["name"], style=col["style"], width=col["width"])
        table.add_column(
            formatter.github_id_column["name"],
            style=formatter.github_id_column["style"],
            width=formatter.github_id_column["width"],
        )

        formatter.add_row(table, mock_issue_with_github)
        formatter.add_row(table, mock_issue_without_github)

        assert len(table.rows) == 2


class TestGitHubIDTableDataConversion:
    """Test GitHub ID handling in table data conversion."""

    @pytest.mark.parametrize("show_github_ids", [True, False])
    def test_issues_to_table_data_with_flag(self, mock_issue_with_github, show_github_ids):
        """Test issues_to_table_data respects show_github_ids flag."""
        issues = [mock_issue_with_github]

        table_data = IssueTableFormatter.issues_to_table_data(
            issues,
            title="Issues",
            description="test",
            show_github_ids=show_github_ids,
        )

        assert table_data is not None
        assert table_data.title == "Issues"
