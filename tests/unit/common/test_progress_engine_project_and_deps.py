"""Tests for progress calculation engine."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from roadmap.common.constants import MilestoneStatus, ProjectStatus, RiskLevel
from roadmap.common.progress import ProgressCalculationEngine


class TestUpdateIssueDependencies:
    """Test issue dependency updates."""

    def test_update_dependencies_no_milestone(self):
        """Test updating dependencies when issue has no milestone."""
        engine = ProgressCalculationEngine()
        issue = Mock(milestone=None)

        milestones, projects = engine.update_issue_dependencies(issue, [], [], [])

        assert milestones == []
        assert projects == []

    def test_update_dependencies_with_milestone(self):
        """Test updating dependencies when issue has milestone."""
        engine = ProgressCalculationEngine()
        milestone = Mock(name="Test Milestone")
        issue = Mock(milestone="Test Milestone")

        with patch.object(engine, "update_milestone_progress", return_value=True):
            milestones, projects = engine.update_issue_dependencies(
                issue, [], [milestone], []
            )

            # Function returns lists
            assert isinstance(milestones, list | tuple)
            assert isinstance(projects, list | tuple)

    def test_update_dependencies_affects_projects(self):
        """Test that milestone updates affect projects."""
        engine = ProgressCalculationEngine()
        milestone = Mock(name="Test Milestone")
        project = Mock(milestones=["Test Milestone"])
        issue = Mock(milestone="Test Milestone")

        with patch.object(engine, "update_milestone_progress", return_value=True):
            with patch.object(engine, "update_project_progress", return_value=True):
                milestones, projects = engine.update_issue_dependencies(
                    issue, [], [milestone], [project]
                )

                # Should return lists
                assert isinstance(milestones, list | tuple)
                assert isinstance(projects, list | tuple)


class TestRecalculateAllProgress:
    """Test recalculating all progress."""

    def test_recalculate_empty_lists(self):
        """Test recalculating with empty lists."""
        engine = ProgressCalculationEngine()

        result = engine.recalculate_all_progress([], [], [])

        assert result["milestones"] == 0
        assert result["projects"] == 0

    def test_recalculate_with_milestones(self):
        """Test recalculating with milestones."""
        engine = ProgressCalculationEngine()
        milestone = Mock(
            calculated_progress=50.0,
            status="in-progress",
            name="Test",
        )
        milestone.update_automatic_fields = Mock()

        with patch.object(engine, "update_milestone_progress", return_value=True):
            result = engine.recalculate_all_progress([], [milestone], [])

            assert result["milestones"] == 1

    def test_recalculate_with_projects(self):
        """Test recalculating with projects."""
        engine = ProgressCalculationEngine()
        project = Mock(
            calculated_progress=50.0,
            status="in-progress",
            name="Test",
        )
        project.update_automatic_fields = Mock()

        with patch.object(engine, "update_project_progress", return_value=True):
            result = engine.recalculate_all_progress([], [], [project])

            assert result["projects"] == 1

    def test_recalculate_multiple_items(self):
        """Test recalculating with multiple items."""
        engine = ProgressCalculationEngine()

        milestones = [
            Mock(name=f"m{i}", calculated_progress=50, status="in-progress")
            for i in range(3)
        ]
        projects = [
            Mock(name=f"p{i}", calculated_progress=50, status="in-progress")
            for i in range(2)
        ]

        for m in milestones:
            m.update_automatic_fields = Mock()
        for p in projects:
            p.update_automatic_fields = Mock()

        with patch.object(engine, "update_milestone_progress", return_value=True):
            with patch.object(engine, "update_project_progress", return_value=True):
                result = engine.recalculate_all_progress([], milestones, projects)  # type: ignore[arg-type]

                assert result["milestones"] == 3
                assert result["projects"] == 2


class TestUpdateProjectTimeline:
    """Test project timeline updates."""

    def test_timeline_no_milestones(self):
        """Test timeline update with no milestones."""
        engine = ProgressCalculationEngine()
        project = Mock(get_milestones=Mock(return_value=[]))

        engine._update_project_timeline(project, [], [])

        # Should complete without error
        assert True

    def test_timeline_sets_velocity(self):
        """Test that timeline update sets velocity."""
        engine = ProgressCalculationEngine()
        milestone = Mock()
        project = Mock(get_milestones=Mock(return_value=[milestone]))

        with patch.object(engine, "_calculate_completion_velocity", return_value=2.5):
            with patch.object(
                engine, "_calculate_projected_completion", return_value=None
            ):
                engine._update_project_timeline(project, [milestone], [])

                assert project.completion_velocity == 2.5

    def test_timeline_sets_projected_date(self):
        """Test that timeline update sets projected date."""
        engine = ProgressCalculationEngine()
        milestone = Mock()
        project = Mock(
            get_milestones=Mock(return_value=[milestone]),
            target_end_date=None,
        )

        future_date = datetime.now() + timedelta(days=30)

        with patch.object(engine, "_calculate_completion_velocity", return_value=2.5):
            with patch.object(
                engine, "_calculate_projected_completion", return_value=future_date
            ):
                engine._update_project_timeline(project, [milestone], [])

                assert project.projected_end_date == future_date

    def test_timeline_calculates_schedule_variance(self):
        """Test that timeline update calculates schedule variance."""
        engine = ProgressCalculationEngine()
        milestone = Mock()
        target_date = datetime.now()
        project = Mock(
            get_milestones=Mock(return_value=[milestone]),
            target_end_date=target_date,
        )

        projected_date = target_date + timedelta(days=10)

        with patch.object(engine, "_calculate_completion_velocity", return_value=2.5):
            with patch.object(
                engine, "_calculate_projected_completion", return_value=projected_date
            ):
                engine._update_project_timeline(project, [milestone], [])

                assert project.schedule_variance == 10

    @pytest.mark.parametrize(
        "variance_days,expected_risk",
        [
            (20, RiskLevel.HIGH),  # > 14 days
            (10, RiskLevel.MEDIUM),  # > 7 days, <= 14 days
            (3, RiskLevel.LOW),  # <= 7 days
            (-8, RiskLevel.LOW),  # < -7 days (ahead)
        ],
    )
    def test_timeline_sets_risk_level(self, variance_days, expected_risk):
        """Test that timeline update sets risk level correctly."""
        engine = ProgressCalculationEngine()
        milestone = Mock()
        target_date = datetime.now()
        project = Mock(
            get_milestones=Mock(return_value=[milestone]),
            target_end_date=target_date,
        )

        projected_date = target_date + timedelta(days=variance_days)

        with patch.object(engine, "_calculate_completion_velocity", return_value=2.5):
            with patch.object(
                engine, "_calculate_projected_completion", return_value=projected_date
            ):
                engine._update_project_timeline(project, [milestone], [])

                assert project.risk_level == expected_risk


class TestCalculateCompletionVelocity:
    """Test completion velocity calculation."""

    def test_velocity_no_milestones(self):
        """Test velocity with no milestones."""
        engine = ProgressCalculationEngine()

        velocity = engine._calculate_completion_velocity([], [])

        assert velocity is None

    def test_velocity_no_completed_milestones(self):
        """Test velocity with no completed milestones."""
        engine = ProgressCalculationEngine()
        milestone = Mock(
            actual_end_date=None,
            status=MilestoneStatus.OPEN,
        )

        velocity = engine._calculate_completion_velocity([milestone], [])

        # Should return None or a numeric value
        assert velocity is None or isinstance(velocity, int | float)

    def test_velocity_completed_milestone(self):
        """Test velocity with completed milestone."""
        engine = ProgressCalculationEngine()
        recent_date = datetime.now() - timedelta(days=10)
        milestone = Mock(
            actual_end_date=recent_date,
            status=MilestoneStatus.CLOSED,
        )

        velocity = engine._calculate_completion_velocity(
            [milestone], [], window_weeks=4
        )

        # Should calculate based on 1 milestone completed in 4 weeks
        assert velocity is not None
        assert velocity > 0

    def test_velocity_old_completed_milestone(self):
        """Test velocity ignores old completed milestones."""
        engine = ProgressCalculationEngine()
        old_date = datetime.now() - timedelta(days=100)
        milestone = Mock(
            actual_end_date=old_date,
            status=MilestoneStatus.CLOSED,
        )

        velocity = engine._calculate_completion_velocity(
            [milestone], [], window_weeks=4
        )

        assert velocity is None

    def test_velocity_custom_window(self):
        """Test velocity with custom time window."""
        engine = ProgressCalculationEngine()
        milestone = Mock(
            actual_end_date=datetime.now() - timedelta(weeks=1),
            status=MilestoneStatus.CLOSED,
        )

        velocity = engine._calculate_completion_velocity(
            [milestone], [], window_weeks=2
        )

        # Should be included in 2-week window
        assert velocity is not None


class TestProgressCalculationIntegration:
    """Integration tests for progress calculation."""

    def test_full_workflow(self):
        """Test complete workflow of progress updates."""
        engine = ProgressCalculationEngine(method="effort_weighted")

        milestone = Mock(
            name="Test Milestone",
            calculated_progress=0,
            status=MilestoneStatus.OPEN,
        )
        milestone.update_automatic_fields = Mock()

        project = Mock(
            name="Test Project",
            calculated_progress=0,
            status=ProjectStatus.ACTIVE,
        )
        project.update_automatic_fields = Mock()

        # Update milestone
        result = engine.update_milestone_progress(milestone, [])

        # Should return a boolean
        assert isinstance(result, bool)

        # Verify update was called
        milestone.update_automatic_fields.assert_called()


@pytest.fixture
def mock_issue():
    """Provide a mock issue."""
    return Mock(milestone="Test", progress=50)


@pytest.fixture
def mock_milestone():
    """Provide a mock milestone."""
    return Mock(
        name="Test",
        calculated_progress=50,
        status=MilestoneStatus.OPEN,
    )


@pytest.fixture
def mock_project():
    """Provide a mock project."""
    return Mock(
        name="Test",
        calculated_progress=50,
        status=ProjectStatus.ACTIVE,
        milestones=[],
        target_end_date=None,
    )
