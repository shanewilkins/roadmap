"""
Unit tests for MilestoneListPresenter.

Tests cover:
- Rendering milestone tables
- Formatting milestone data
- Styling milestone information
- Empty state handling
"""

from unittest.mock import MagicMock, patch

from roadmap.adapters.cli.presentation.milestone_list_presenter import (
    MilestoneListPresenter,
    MilestoneTablePresenter,
)


class TestMilestoneTablePresenter:
    """Tests for milestone table rendering."""

    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_display_milestone_table_empty(self, mock_console):
        """Test displaying empty milestone table."""
        MilestoneTablePresenter.display_milestone_table(
            [], {}, {}, lambda x: ("-", None)
        )

        mock_console.print.assert_called_once()

    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_display_milestone_table_single_milestone(self, mock_console):
        """Test displaying table with single milestone."""
        mock_ms = MagicMock()
        mock_ms.name = "v1.0"
        mock_ms.description = "First release"
        mock_ms.status.value = "open"

        progress = {"v1.0": {"total": 10, "completed": 5}}
        estimates = {"v1.0": "40 hours"}

        def get_due_date(ms):
            return ("2025-12-31", None)

        MilestoneTablePresenter.display_milestone_table(
            [mock_ms], progress, estimates, get_due_date
        )

        mock_console.print.assert_called_once()

    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_display_milestone_table_multiple_milestones(self, mock_console):
        """Test displaying table with multiple milestones."""
        mock_ms1 = MagicMock()
        mock_ms1.name = "v1.0"
        mock_ms1.description = "First"
        mock_ms1.status.value = "open"

        mock_ms2 = MagicMock()
        mock_ms2.name = "v2.0"
        mock_ms2.description = "Second"
        mock_ms2.status.value = "open"

        progress = {
            "v1.0": {"total": 10, "completed": 5},
            "v2.0": {"total": 20, "completed": 20},
        }
        estimates = {"v1.0": "40 hours", "v2.0": "80 hours"}

        def get_due_date(ms):
            return ("2025-12-31", None)

        MilestoneTablePresenter.display_milestone_table(
            [mock_ms1, mock_ms2], progress, estimates, get_due_date
        )

        mock_console.print.assert_called_once()

    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_display_milestone_table_with_overdue_styling(self, mock_console):
        """Test displaying table with overdue styling."""
        mock_ms = MagicMock()
        mock_ms.name = "v1.0"
        mock_ms.description = "First release"
        mock_ms.status.value = "open"

        progress = {"v1.0": {"total": 10, "completed": 5}}
        estimates = {"v1.0": "40 hours"}

        def get_due_date(ms):
            return ("2025-10-15", "bold red")

        MilestoneTablePresenter.display_milestone_table(
            [mock_ms], progress, estimates, get_due_date
        )

        mock_console.print.assert_called_once()

    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_display_milestone_table_missing_data(self, mock_console):
        """Test displaying table with missing progress/estimate data."""
        mock_ms = MagicMock()
        mock_ms.name = "v1.0"
        mock_ms.description = "First release"
        mock_ms.status.value = "open"

        progress = {}  # Missing progress for v1.0
        estimates = {}  # Missing estimate for v1.0

        def get_due_date(ms):
            return ("-", None)

        MilestoneTablePresenter.display_milestone_table(
            [mock_ms], progress, estimates, get_due_date
        )

        mock_console.print.assert_called_once()

    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_display_milestone_table_exception(self, mock_console):
        """Test handling exceptions during table display."""
        MilestoneTablePresenter.display_milestone_table([], {}, {}, None)

        # Should call console.print for error message
        assert mock_console.print.call_count >= 1


class TestMilestoneListPresenter:
    """Tests for milestone list presentation."""

    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_show_empty_state(self, mock_console):
        """Test displaying empty state."""
        MilestoneListPresenter.show_empty_state()

        # Should print twice (message + instruction)
        assert mock_console.print.call_count == 2

    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_show_no_upcoming_milestones(self, mock_console):
        """Test displaying no upcoming milestones message."""
        MilestoneListPresenter.show_no_upcoming_milestones()

        assert mock_console.print.call_count == 2

    @patch(
        "roadmap.adapters.cli.presentation.milestone_list_presenter.MilestoneTablePresenter.display_milestone_table"
    )
    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_show_milestones_list_empty(self, mock_console, mock_table):
        """Test showing milestones list when empty."""
        milestones_data = {
            "has_data": False,
            "milestones": [],
            "progress": {},
            "estimates": {},
        }

        MilestoneListPresenter.show_milestones_list(
            milestones_data, lambda x: ("-", None)
        )

        # Should show empty state, not table
        assert mock_console.print.call_count == 2
        mock_table.assert_not_called()

    @patch(
        "roadmap.adapters.cli.presentation.milestone_list_presenter.MilestoneTablePresenter.display_milestone_table"
    )
    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_show_milestones_list_with_data(self, mock_console, mock_table):
        """Test showing milestones list with data."""
        mock_ms = MagicMock()
        milestones_data = {
            "has_data": True,
            "milestones": [mock_ms],
            "progress": {"v1.0": {"total": 10, "completed": 5}},
            "estimates": {"v1.0": "40 hours"},
        }

        MilestoneListPresenter.show_milestones_list(
            milestones_data, lambda x: ("2025-12-31", None)
        )

        # Should call table display
        mock_table.assert_called_once()

    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_show_error(self, mock_console):
        """Test displaying error message."""
        error_msg = "Database connection failed"

        MilestoneListPresenter.show_error(error_msg)

        mock_console.print.assert_called_once()
        call_args = str(mock_console.print.call_args)
        assert "Failed" in call_args or "error" in call_args.lower()

    @patch(
        "roadmap.adapters.cli.presentation.milestone_list_presenter.MilestoneTablePresenter.display_milestone_table"
    )
    @patch("roadmap.adapters.cli.presentation.milestone_list_presenter.console")
    def test_show_milestones_list_with_multiple(self, mock_console, mock_table):
        """Test showing milestones list with multiple milestones."""
        mock_ms1 = MagicMock()
        mock_ms1.name = "v1.0"
        mock_ms2 = MagicMock()
        mock_ms2.name = "v2.0"

        milestones_data = {
            "has_data": True,
            "milestones": [mock_ms1, mock_ms2],
            "progress": {
                "v1.0": {"total": 10, "completed": 5},
                "v2.0": {"total": 20, "completed": 20},
            },
            "estimates": {"v1.0": "40 hours", "v2.0": "80 hours"},
        }

        MilestoneListPresenter.show_milestones_list(
            milestones_data, lambda x: ("2025-12-31", None)
        )

        mock_table.assert_called_once()
        call_args = mock_table.call_args
        assert len(call_args[0][0]) == 2  # Two milestones
