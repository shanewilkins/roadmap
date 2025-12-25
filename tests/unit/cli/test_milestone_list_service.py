"""
Unit tests for MilestoneListService.

Tests cover:
- Filtering milestones (overdue, all)
- Computing milestone progress
- Calculating time estimates
- Error handling
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from roadmap.adapters.cli.services.milestone_list_service import (
    MilestoneFilterService,
    MilestoneListService,
    MilestoneProgressService,
    MilestoneTimeEstimateService,
)
from tests.unit.domain.test_data_factory import TestDataFactory


class TestMilestoneFilterService:
    """Tests for milestone filtering."""

    def test_filter_overdue_milestones_empty(self):
        """Test filtering with empty milestone list."""
        result = MilestoneFilterService.filter_overdue_milestones([])
        assert result == []

    def test_filter_overdue_milestones_no_due_date(self):
        """Test filtering milestones without due dates."""
        mock_ms = MagicMock()
        mock_ms.due_date = None
        mock_ms.status.value = "open"

        result = MilestoneFilterService.filter_overdue_milestones([mock_ms])
        assert result == []

    def test_filter_overdue_milestones_future_due_date(self):
        """Test filtering milestones with future due dates."""
        mock_ms = MagicMock()
        mock_ms.due_date = datetime.now() + timedelta(days=10)
        mock_ms.status.value = "open"

        result = MilestoneFilterService.filter_overdue_milestones([mock_ms])
        assert result == []

    def test_filter_overdue_milestones_past_due_date(self):
        """Test filtering milestones with past due dates."""
        mock_ms = MagicMock()
        mock_ms.due_date = datetime.now() - timedelta(days=5)
        mock_ms.status.value = "open"

        result = MilestoneFilterService.filter_overdue_milestones([mock_ms])
        assert len(result) == 1
        assert result[0] == mock_ms

    def test_filter_overdue_milestones_closed_status(self):
        """Test filtering ignores closed milestones."""
        mock_ms = MagicMock()
        mock_ms.due_date = datetime.now() - timedelta(days=5)
        mock_ms.status.value = "closed"

        result = MilestoneFilterService.filter_overdue_milestones([mock_ms])
        assert result == []

    def test_filter_milestones_all(self):
        """Test filtering with overdue_only=False returns all."""
        mock_ms1 = MagicMock()
        mock_ms2 = MagicMock()
        milestones = [mock_ms1, mock_ms2]

        result = MilestoneFilterService.filter_milestones(
            milestones, overdue_only=False
        )
        assert len(result) == 2


class TestMilestoneProgressService:
    """Tests for milestone progress calculation."""

    def test_get_milestone_progress_success(self):
        """Test getting progress for a milestone."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.milestones.get_progress.return_value = {
            "total": 10,
            "completed": 7,
        }

        result = MilestoneProgressService.get_milestone_progress(mock_core, "v1.0")

        assert result["total"] == 10
        assert result["completed"] == 7
        assert result["percentage"] == 70.0

    def test_get_milestone_progress_zero_total(self):
        """Test progress with zero total issues."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.milestones.get_progress.return_value = {
            "total": 0,
            "completed": 0,
        }

        result = MilestoneProgressService.get_milestone_progress(mock_core, "v1.0")

        assert result["total"] == 0
        assert result["completed"] == 0
        assert result["percentage"] == 0

    def test_get_milestone_progress_complete(self):
        """Test progress when all issues completed."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.milestones.get_progress.return_value = {
            "total": 10,
            "completed": 10,
        }

        result = MilestoneProgressService.get_milestone_progress(mock_core, "v1.0")

        assert result["percentage"] == 100.0

    def test_get_milestone_progress_exception(self):
        """Test progress calculation handles exceptions."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.milestones.get_progress.side_effect = Exception("DB error")

        result = MilestoneProgressService.get_milestone_progress(mock_core, "v1.0")

        assert result["total"] == 0
        assert result["completed"] == 0
        assert result["percentage"] == 0

    def test_get_all_milestones_progress(self):
        """Test getting progress for multiple milestones."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)

        def progress_side_effect(name):
            if name == "v1.0":
                return {"total": 10, "completed": 5}
            else:
                return {"total": 8, "completed": 8}

        mock_core.milestones.get_progress.side_effect = progress_side_effect

        mock_ms1 = MagicMock()
        mock_ms1.name = "v1.0"
        mock_ms2 = MagicMock()
        mock_ms2.name = "v2.0"

        result = MilestoneProgressService.get_all_milestones_progress(
            mock_core, [mock_ms1, mock_ms2]
        )

        assert "v1.0" in result
        assert "v2.0" in result
        assert result["v1.0"]["percentage"] == 50.0
        assert result["v2.0"]["percentage"] == 100.0


class TestMilestoneTimeEstimateService:
    """Tests for time estimate calculations."""

    def test_get_milestone_time_estimate_success(self):
        """Test getting time estimate."""
        mock_ms = MagicMock()
        mock_ms.name = "v1.0"
        mock_ms.get_estimated_time_display.return_value = "32 hours"

        result = MilestoneTimeEstimateService.get_milestone_time_estimate(mock_ms, [])

        assert result == "32 hours"

    def test_get_milestone_time_estimate_empty(self):
        """Test time estimate when empty."""
        mock_ms = MagicMock()
        mock_ms.name = "v1.0"
        mock_ms.get_estimated_time_display.return_value = None

        result = MilestoneTimeEstimateService.get_milestone_time_estimate(mock_ms, [])

        assert result == "-"

    def test_get_milestone_time_estimate_exception(self):
        """Test time estimate handles exceptions."""
        mock_ms = MagicMock()
        mock_ms.name = "v1.0"
        mock_ms.get_estimated_time_display.side_effect = Exception("Error")

        result = MilestoneTimeEstimateService.get_milestone_time_estimate(mock_ms, [])

        assert result == "-"


class TestMilestoneListService:
    """Tests for milestone list service."""

    def test_get_milestones_list_data_empty(self):
        """Test getting milestone list data when empty."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.milestones.list.return_value = []
        mock_core.issues.list.return_value = []

        service = MilestoneListService(mock_core)
        result = service.get_milestones_list_data()

        assert not result["has_data"]
        assert result["count"] == 0
        assert result["milestones"] == []

    def test_get_milestones_list_data_with_milestones(self):
        """Test getting milestone list data with milestones."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)

        mock_ms = MagicMock()
        mock_ms.name = "v1.0"
        mock_ms.description = "First release"
        mock_ms.due_date = datetime.now() + timedelta(days=30)
        mock_ms.status.value = "open"
        mock_ms.get_estimated_time_display.return_value = "40 hours"

        mock_core.milestones.list.return_value = [mock_ms]
        mock_core.milestones.get_progress.return_value = {
            "total": 10,
            "completed": 5,
        }
        mock_core.issues.list.return_value = []

        service = MilestoneListService(mock_core)
        result = service.get_milestones_list_data()

        assert result["has_data"]
        assert result["count"] == 1
        assert "v1.0" in result["progress"]
        assert "v1.0" in result["estimates"]

    def test_get_milestones_list_data_overdue_filter(self):
        """Test getting milestone list data with overdue filter."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)

        mock_ms_past = MagicMock()
        mock_ms_past.name = "v0.9"
        mock_ms_past.due_date = datetime.now() - timedelta(days=10)
        mock_ms_past.status.value = "open"

        mock_ms_future = MagicMock()
        mock_ms_future.name = "v1.0"
        mock_ms_future.due_date = datetime.now() + timedelta(days=30)
        mock_ms_future.status.value = "open"

        mock_core.milestones.list.return_value = [mock_ms_past, mock_ms_future]
        mock_core.milestones.get_progress.return_value = {
            "total": 0,
            "completed": 0,
        }
        mock_core.issues.list.return_value = []

        service = MilestoneListService(mock_core)
        result = service.get_milestones_list_data(overdue_only=True)

        assert result["count"] == 1
        assert result["milestones"][0].name == "v0.9"

    def test_get_milestone_due_date_status_no_due_date(self):
        """Test due date status with no due date."""
        service = MilestoneListService(MagicMock())
        mock_ms = MagicMock()
        mock_ms.due_date = None

        result = service.get_milestone_due_date_status(mock_ms)

        assert result == ("-", None)

    def test_get_milestone_due_date_status_overdue(self):
        """Test due date status for overdue milestone."""
        service = MilestoneListService(MagicMock())
        mock_ms = MagicMock()
        mock_ms.due_date = datetime.now() - timedelta(days=5)
        mock_ms.status.value = "open"

        result = service.get_milestone_due_date_status(mock_ms)

        assert result[1] == "bold red"

    def test_get_milestone_due_date_status_due_soon(self):
        """Test due date status for milestone due soon."""
        service = MilestoneListService(MagicMock())
        mock_ms = MagicMock()
        mock_ms.due_date = datetime.now() + timedelta(days=3)
        mock_ms.status.value = "open"

        result = service.get_milestone_due_date_status(mock_ms)

        assert result[1] == "yellow"

    def test_get_milestone_due_date_status_normal(self):
        """Test due date status for normal milestone."""
        service = MilestoneListService(MagicMock())
        mock_ms = MagicMock()
        mock_ms.due_date = datetime.now() + timedelta(days=30)
        mock_ms.status.value = "open"

        result = service.get_milestone_due_date_status(mock_ms)

        assert result[1] is None

    def test_get_milestones_list_data_exception(self):
        """Test handling of exceptions."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.milestones.list.side_effect = Exception("DB error")

        service = MilestoneListService(mock_core)
        result = service.get_milestones_list_data()

        assert not result["has_data"]
        assert result["count"] == 0
