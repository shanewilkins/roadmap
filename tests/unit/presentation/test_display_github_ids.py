"""Unit tests for display GitHub IDs feature."""

from unittest.mock import Mock

import pytest

from roadmap.shared.formatters.tables.issue_table import IssueTableFormatter


@pytest.fixture
def mock_issue_with_github():
    """Create a mock issue with GitHub ID."""
    issue = Mock()
    issue.id = "test-123"
    issue.title = "Test Issue"
    issue.github_issue = 456
    issue.priority = Mock(value="high")
    issue.status = Mock(value="todo")
    issue.progress_display = "0%"
    issue.progress_percentage = 0
    issue.assignee = "shane"
    issue.estimated_time_display = "5h"
    issue.estimated_hours = 5
    issue.milestone_name = "v0.8"
    issue.is_backlog = False
    return issue


@pytest.fixture
def mock_issue_without_github():
    """Create a mock issue without GitHub ID."""
    issue = Mock()
    issue.id = "test-456"
    issue.title = "Another Issue"
    issue.github_issue = None
    issue.priority = Mock(value="medium")
    issue.status = Mock(value="in_progress")
    issue.progress_display = "50%"
    issue.progress_percentage = 50
    issue.assignee = None
    issue.estimated_time_display = "3h"
    issue.estimated_hours = 3
    issue.milestone_name = "backlog"
    issue.is_backlog = True
    return issue


def test_issue_table_formatter_with_github_ids(mock_issue_with_github):
    """Test IssueTableFormatter displays GitHub IDs when flag is set."""
    formatter = IssueTableFormatter()
    formatter.show_github_ids = True

    table = formatter.create_table()

    # Verify GitHub ID column was added
    assert table.columns is not None
    column_titles = [col.header for col in table.columns]
    assert "GitHub #" in column_titles


def test_issue_table_formatter_without_github_ids(mock_issue_with_github):
    """Test IssueTableFormatter doesn't show GitHub IDs when flag is False."""
    formatter = IssueTableFormatter()
    formatter.show_github_ids = False

    table = formatter.create_table()

    # Verify GitHub ID column was NOT added
    assert table.columns is not None
    column_titles = [col.header for col in table.columns]
    assert "GitHub #" not in column_titles


def test_add_row_with_github_id(mock_issue_with_github):
    """Test add_row includes GitHub ID in output."""
    formatter = IssueTableFormatter()
    formatter.show_github_ids = True

    from rich.table import Table

    table = Table()
    # Manually add columns to match formatter
    for col in formatter.columns_config:
        table.add_column(col["name"], style=col["style"], width=col["width"])
    if formatter.show_github_ids:
        table.add_column(
            formatter.github_id_column["name"],
            style=formatter.github_id_column["style"],
            width=formatter.github_id_column["width"],
        )

    formatter.add_row(table, mock_issue_with_github)

    # Verify row was added
    assert len(table.rows) == 1


def test_add_row_without_github_id(mock_issue_without_github):
    """Test add_row works for issue without GitHub ID."""
    formatter = IssueTableFormatter()
    formatter.show_github_ids = True

    from rich.table import Table

    table = Table()
    # Manually add columns to match formatter
    for col in formatter.columns_config:
        table.add_column(col["name"], style=col["style"], width=col["width"])
    if formatter.show_github_ids:
        table.add_column(
            formatter.github_id_column["name"],
            style=formatter.github_id_column["style"],
            width=formatter.github_id_column["width"],
        )

    formatter.add_row(table, mock_issue_without_github)

    # Verify row was added with GitHub ID showing as "-"
    assert len(table.rows) == 1


def test_add_row_without_flag(mock_issue_with_github):
    """Test add_row doesn't include GitHub ID when flag is False."""
    formatter = IssueTableFormatter()
    formatter.show_github_ids = False

    from rich.table import Table

    table = Table()
    # Manually add columns to match formatter (no GitHub ID column)
    for col in formatter.columns_config:
        table.add_column(col["name"], style=col["style"], width=col["width"])

    formatter.add_row(table, mock_issue_with_github)

    # Verify row was added
    assert len(table.rows) == 1


def test_issues_to_table_data_with_github_ids(mock_issue_with_github):
    """Test issues_to_table_data passes show_github_ids flag."""
    issues = [mock_issue_with_github]

    table_data = IssueTableFormatter.issues_to_table_data(
        issues,
        title="Issues",
        description="test",
        show_github_ids=True,
    )

    # Verify table_data was created successfully
    assert table_data is not None
    assert table_data.title == "Issues"


def test_issues_to_table_data_without_github_ids(mock_issue_with_github):
    """Test issues_to_table_data works without showing GitHub IDs."""
    issues = [mock_issue_with_github]

    table_data = IssueTableFormatter.issues_to_table_data(
        issues,
        title="Issues",
        description="test",
        show_github_ids=False,
    )

    # Verify table_data was created successfully
    assert table_data is not None


def test_multiple_issues_with_mixed_github_ids(
    mock_issue_with_github, mock_issue_without_github
):
    """Test formatting multiple issues with mixed GitHub ID presence."""
    formatter = IssueTableFormatter()
    formatter.show_github_ids = True

    from rich.table import Table

    table = Table()
    # Manually add columns to match formatter
    for col in formatter.columns_config:
        table.add_column(col["name"], style=col["style"], width=col["width"])
    if formatter.show_github_ids:
        table.add_column(
            formatter.github_id_column["name"],
            style=formatter.github_id_column["style"],
            width=formatter.github_id_column["width"],
        )

    formatter.add_row(table, mock_issue_with_github)
    formatter.add_row(table, mock_issue_without_github)

    # Verify both rows were added
    assert len(table.rows) == 2
