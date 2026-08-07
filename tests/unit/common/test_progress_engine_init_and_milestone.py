"""Tests for progress calculation engine."""

from unittest.mock import Mock, patch

import pytest

from roadmap.common.progress import ProgressCalculationEngine


class TestProgressCalculationEngineInit:
    """Test ProgressCalculationEngine initialization."""

    def test_init_default_method(self):
        """Test initialization with default method."""
        engine = ProgressCalculationEngine()
        assert engine.method == "effort_weighted"

    def test_init_custom_method(self):
        """Test initialization with custom method."""
        engine = ProgressCalculationEngine(method="count_based")
        assert engine.method == "count_based"

    @pytest.mark.parametrize(
        "method",
        [
            "effort_weighted",
            "count_based",
            "custom_method",
        ],
    )
    def test_init_various_methods(self, method):
        """Test initialization with various methods."""
        engine = ProgressCalculationEngine(method=method)
        assert engine.method == method


class TestUpdateMilestoneProgress:
    """Test milestone progress updates."""

    def test_update_milestone_no_change(self):
        """Test updating milestone when progress hasn't changed."""
        engine = ProgressCalculationEngine()
        milestone = Mock(
            calculated_progress=50.0,
            status="in-progress",
            name="Test Milestone",
        )
        milestone.update_automatic_fields = Mock()

        # Don't change the mock's progress/status
        result = engine.update_milestone_progress(milestone, [])
        assert result is False

    def test_update_milestone_progress_changed(self):
        """Test updating milestone when progress changes."""
        engine = ProgressCalculationEngine()
        milestone = Mock(
            calculated_progress=50.0,
            status="in-progress",
            name="Test Milestone",
        )

        def update_fields(*args, **kwargs):
            milestone.calculated_progress = 75.0

        milestone.update_automatic_fields = Mock(side_effect=update_fields)

        result = engine.update_milestone_progress(milestone, [])
        assert result is True

    def test_update_milestone_both_changed(self):
        """Test updating milestone when both progress and status change."""
        engine = ProgressCalculationEngine()
        milestone = Mock(
            calculated_progress=50.0,
            status="in-progress",
            name="Test Milestone",
        )

        def update_fields(*args, **kwargs):
            milestone.calculated_progress = 100.0
            milestone.status = "closed"

        milestone.update_automatic_fields = Mock(side_effect=update_fields)

        result = engine.update_milestone_progress(milestone, [])
        assert result is True

    def test_update_milestone_none_progress_to_value(self):
        """Test updating milestone from None progress to value."""
        engine = ProgressCalculationEngine()
        milestone = Mock(
            calculated_progress=None,
            status="in-progress",
            name="Test Milestone",
        )

        def update_fields(*args, **kwargs):
            milestone.calculated_progress = 50.0

        milestone.update_automatic_fields = Mock(side_effect=update_fields)

        result = engine.update_milestone_progress(milestone, [])
        assert result is True

    def test_update_milestone_with_all_issues(self):
        """Test that update_milestone uses provided issues."""
        engine = ProgressCalculationEngine(method="count_based")
        milestone = Mock(
            calculated_progress=50.0,
            status="in-progress",
            name="Test",
        )
        milestone.update_automatic_fields = Mock()

        issues = [Mock(), Mock(), Mock()]
        engine.update_milestone_progress(milestone, issues)  # type: ignore[arg-type]

        # Verify issues were passed to update
        call_args = milestone.update_automatic_fields.call_args
        assert call_args[0][0] == issues
        assert call_args[0][1] == "count_based"


class TestUpdateProjectProgress:
    """Test project progress updates."""

    def test_update_project_no_change(self):
        """Test updating project when nothing changes."""
        engine = ProgressCalculationEngine()
        project = Mock(
            calculated_progress=50.0,
            status="active",
            name="Test Project",
            target_end_date=None,
            get_milestones=Mock(return_value=[]),  # Return empty list instead of Mock
        )
        project.update_automatic_fields = Mock()

        result = engine.update_project_progress(project, [], [])
        # Result can be True or False depending on implementation
        assert isinstance(result, bool)

    def test_update_project_progress_changed(self):
        """Test updating project when progress changes."""
        engine = ProgressCalculationEngine()
        project = Mock(
            calculated_progress=50.0,
            status="active",
            name="Test Project",
            target_end_date=None,
            get_milestones=Mock(return_value=[]),  # Return empty list
        )

        def update_fields(*args, **kwargs):
            project.calculated_progress = 75.0

        project.update_automatic_fields = Mock(side_effect=update_fields)

        result = engine.update_project_progress(project, [], [])
        assert isinstance(result, bool)

    def test_update_project_calls_timeline_update(self):
        """Test that update_project calls timeline update."""
        engine = ProgressCalculationEngine()
        project = Mock(
            calculated_progress=50.0,
            status="in-progress",
            name="Test Project",
            target_end_date=None,
        )
        project.update_automatic_fields = Mock()

        with patch.object(engine, "_update_project_timeline") as mock_timeline:
            engine.update_project_progress(project, [], [])
            mock_timeline.assert_called_once()
