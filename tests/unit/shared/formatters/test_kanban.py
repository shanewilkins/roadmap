"""Unit tests for kanban board functionality."""

from datetime import datetime, timedelta
from typing import cast
from unittest.mock import Mock, patch

from roadmap.core.domain import Issue, Priority, Status
from roadmap.shared.formatters.kanban import KanbanLayout, KanbanOrganizer
from tests.factories import IssueBuilder


class TestKanbanOrganizer:
    """Test kanban issue organization."""

    def create_issue(self, status=Status.TODO, due_date=None, **kwargs):
        """Helper to create a test issue."""
        builder = IssueBuilder().with_status(status).with_due_date(due_date)
        if "title" in kwargs:
            builder = builder.with_title(kwargs["title"])
        if "priority" in kwargs:
            builder = builder.with_priority(kwargs["priority"])
        return builder.build()

    def test_categorize_issues_empty_list(self):
        """categorize_issues should handle empty list."""
        result = KanbanOrganizer.categorize_issues([])

        assert result == {
            "overdue": [],
            "blocked": [],
            "in_progress": [],
            "not_started": [],
            "closed": [],
        }

    def test_categorize_issues_done(self):
        """categorize_issues should categorize done issues."""
        issue = self.create_issue(status=Status.CLOSED)

        result = KanbanOrganizer.categorize_issues([issue])

        assert len(result["closed"]) == 1
        assert result["closed"][0] == issue
        assert len(result["overdue"]) == 0
        assert len(result["blocked"]) == 0
        assert len(result["in_progress"]) == 0
        assert len(result["not_started"]) == 0

    def test_categorize_issues_blocked(self):
        """categorize_issues should categorize blocked issues."""
        issue = self.create_issue(status=Status.BLOCKED)

        result = KanbanOrganizer.categorize_issues([issue])

        assert len(result["blocked"]) == 1
        assert result["blocked"][0] == issue

    def test_categorize_issues_in_progress(self):
        """categorize_issues should categorize in-progress issues."""
        issue = self.create_issue(status=Status.IN_PROGRESS)

        result = KanbanOrganizer.categorize_issues([issue])

        assert len(result["in_progress"]) == 1
        assert result["in_progress"][0] == issue

    def test_categorize_issues_not_started(self):
        """categorize_issues should categorize todo issues."""
        issue = self.create_issue(status=Status.TODO)

        result = KanbanOrganizer.categorize_issues([issue])

        assert len(result["not_started"]) == 1
        assert result["not_started"][0] == issue

    def test_categorize_issues_overdue(self):
        """categorize_issues should categorize overdue issues."""
        yesterday = datetime.now() - timedelta(days=1)
        issue = self.create_issue(status=Status.TODO, due_date=yesterday)

        result = KanbanOrganizer.categorize_issues([issue])

        assert len(result["overdue"]) == 1
        assert result["overdue"][0] == issue

    def test_categorize_issues_not_overdue_if_done(self):
        """categorize_issues should not mark done issues as overdue."""
        yesterday = datetime.now() - timedelta(days=1)
        issue = self.create_issue(status=Status.CLOSED, due_date=yesterday)

        result = KanbanOrganizer.categorize_issues([issue])

        assert len(result["closed"]) == 1
        assert len(result["overdue"]) == 0

    def test_categorize_issues_future_due_date_not_overdue(self):
        """categorize_issues should not mark future due dates as overdue."""
        tomorrow = datetime.now() + timedelta(days=1)
        issue = self.create_issue(status=Status.TODO, due_date=tomorrow)

        result = KanbanOrganizer.categorize_issues([issue])

        assert len(result["not_started"]) == 1
        assert len(result["overdue"]) == 0

    def test_categorize_issues_multiple(self):
        """categorize_issues should handle multiple issues correctly."""
        yesterday = datetime.now() - timedelta(days=1)
        issues = [
            self.create_issue(status=Status.CLOSED, title="Done issue"),
            self.create_issue(status=Status.BLOCKED, title="Blocked issue"),
            self.create_issue(status=Status.IN_PROGRESS, title="In progress issue"),
            self.create_issue(status=Status.TODO, title="Not started issue"),
            self.create_issue(
                status=Status.TODO, due_date=yesterday, title="Overdue issue"
            ),
        ]

        result = KanbanOrganizer.categorize_issues(cast(list, issues))

        assert len(result["closed"]) == 1
        assert len(result["blocked"]) == 1
        assert len(result["in_progress"]) == 1
        assert len(result["not_started"]) == 1
        assert len(result["overdue"]) == 1

    def test_create_column_definitions_with_color(self):
        """create_column_definitions should create columns with colors."""
        categories = {
            "overdue": [Mock()],
            "blocked": [],
            "in_progress": [Mock(), Mock()],
            "not_started": [],
            "closed": [Mock()],
        }

        result = KanbanOrganizer.create_column_definitions(categories, no_color=False)

        assert len(result) == 5

    def test_create_column_definitions_overdue_column(self):
        """create_column_definitions should format overdue column correctly."""
        categories = {
            "overdue": [Mock()],
            "blocked": [],
            "in_progress": [],
            "not_started": [],
            "closed": [],
        }

        result = KanbanOrganizer.create_column_definitions(categories, no_color=False)

        assert result[0][0] == "🚨 Overdue"
        assert result[0][1] == categories["overdue"]
        assert result[0][2] == "bold red"

    def test_create_column_definitions_blocked_column(self):
        """create_column_definitions should format blocked column correctly."""
        categories = {
            "overdue": [],
            "blocked": [],
            "in_progress": [],
            "not_started": [],
            "closed": [],
        }

        result = KanbanOrganizer.create_column_definitions(categories, no_color=False)

        assert result[1][0] == "🚫 Blocked"
        assert result[1][2] == "bold yellow"

    def test_create_column_definitions_in_progress_column(self):
        """create_column_definitions should format in-progress column correctly."""
        categories = {
            "overdue": [],
            "blocked": [],
            "in_progress": [Mock(), Mock()],
            "not_started": [],
            "closed": [],
        }

        result = KanbanOrganizer.create_column_definitions(categories, no_color=False)

        assert result[2][0] == "🔄 In Progress"
        assert result[2][2] == "bold blue"

    def test_create_column_definitions_not_started_column(self):
        """create_column_definitions should format not-started column correctly."""
        categories = {
            "overdue": [],
            "blocked": [],
            "in_progress": [],
            "not_started": [],
            "closed": [],
        }

        result = KanbanOrganizer.create_column_definitions(categories, no_color=False)

        assert result[3][0] == "⏸️  Not Started"
        assert result[3][2] == "dim white"

    def test_create_column_definitions_closed_column(self):
        """create_column_definitions should format closed column correctly."""
        categories = {
            "overdue": [],
            "blocked": [],
            "in_progress": [],
            "not_started": [],
            "closed": [Mock()],
        }

        result = KanbanOrganizer.create_column_definitions(categories, no_color=False)

        assert result[4][0] == "✅ Closed"
        assert result[4][2] == "bold green"

    def test_create_column_definitions_no_color(self):
        """create_column_definitions should use white when no_color=True."""
        categories = {
            "overdue": [],
            "blocked": [],
            "in_progress": [],
            "not_started": [],
            "closed": [],
        }

        result = KanbanOrganizer.create_column_definitions(categories, no_color=True)

        assert len(result) == 5
        # All styles should be white
        for _, _, style in result:
            assert style == "white"


class TestKanbanLayout:
    """Test kanban board layout."""

    def create_issue(self, title="Test Issue", priority=Priority.MEDIUM):
        """Helper to create a test issue."""
        return IssueBuilder().with_title(title).with_priority(priority).build()

    def test_calculate_column_width_default(self):
        """calculate_column_width should return reasonable default."""
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.return_value = Mock(columns=100)

            result = KanbanLayout.calculate_column_width(3)

            # (100 - 5) // 3 = 31
            assert result == 31

    def test_calculate_column_width_minimum(self):
        """calculate_column_width should enforce minimum width of 30."""
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.return_value = Mock(columns=50)

            result = KanbanLayout.calculate_column_width(10)

            # Would be 4, but minimum is 30
            assert result == 30

    def test_calculate_column_width_fallback_on_error(self):
        """calculate_column_width should fallback to 35 on error."""
        with patch("shutil.get_terminal_size", side_effect=Exception("No terminal")):
            result = KanbanLayout.calculate_column_width(3)

            assert result == 35

    def test_format_issue_cell_none_issue(self):
        """format_issue_cell should handle None issue."""
        result = KanbanLayout.format_issue_cell(cast(Issue, None), 30, False)

        assert result == " " * 30

    def test_format_issue_cell_compact_mode(self):
        """format_issue_cell should format issue in compact mode."""
        issue = self.create_issue(title="Short Title")

        result = KanbanLayout.format_issue_cell(issue, 30, compact=True)

        assert result.startswith("• Short Title")
        assert len(result) == 30

    def test_format_issue_cell_full_mode_medium_priority(self):
        """format_issue_cell should show priority emoji in full mode."""
        issue = self.create_issue(title="Medium Task", priority=Priority.MEDIUM)

        result = KanbanLayout.format_issue_cell(issue, 30, compact=False)

        assert "🟡" in result
        assert "Medium Task" in result

    def test_format_issue_cell_full_mode_critical_priority(self):
        """format_issue_cell should show critical priority emoji."""
        issue = self.create_issue(title="Critical Bug", priority=Priority.CRITICAL)

        result = KanbanLayout.format_issue_cell(issue, 30, compact=False)

        assert "🔴" in result
        assert "Critical Bug" in result

    def test_format_issue_cell_full_mode_high_priority(self):
        """format_issue_cell should show high priority emoji."""
        issue = self.create_issue(title="High Priority", priority=Priority.HIGH)

        result = KanbanLayout.format_issue_cell(issue, 30, compact=False)

        assert "🟠" in result
        assert "High Priority" in result

    def test_format_issue_cell_full_mode_low_priority(self):
        """format_issue_cell should show low priority emoji."""
        issue = self.create_issue(title="Low Priority", priority=Priority.LOW)

        result = KanbanLayout.format_issue_cell(issue, 30, compact=False)

        assert "⚪" in result
        assert "Low Priority" in result

    def test_format_issue_cell_truncates_long_title(self):
        """format_issue_cell should truncate titles that are too long."""
        long_title = "A" * 100
        issue = self.create_issue(title=long_title)

        result = KanbanLayout.format_issue_cell(issue, 30, compact=True)

        # Max title length is col_width - 4 = 26
        assert len(result) == 30
        assert result.count("A") <= 26

    def test_format_issue_cell_preserves_exact_width(self):
        """format_issue_cell should always return exact column width in compact mode."""
        issue = self.create_issue(title="Test")

        for width in [20, 30, 40, 50]:
            result_compact = KanbanLayout.format_issue_cell(issue, width, compact=True)
            # Compact mode preserves width accurately
            assert len(result_compact) == width
