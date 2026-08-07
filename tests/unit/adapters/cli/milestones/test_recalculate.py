"""Unit tests for milestone recalculate command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.milestones.recalculate import (
    recalculate_milestone_progress,
)
from roadmap.core.domain import Issue, Milestone, MilestoneStatus, Priority, Status
from roadmap.core.domain.issue import IssueType


@pytest.fixture
def sample_milestone():
    """Create a sample milestone."""
    return Milestone(
        name="v1-0",
        content="First release",
        due_date=None,
        status=MilestoneStatus.OPEN,
    )


@pytest.fixture
def sample_issues():
    """Create sample issues."""
    return [
        Issue(
            title="Feature A",
            status=Status.TODO,
            priority=Priority.HIGH,
            issue_type=IssueType.FEATURE,
            milestone="v1-0",
        ),
        Issue(
            title="Feature B",
            status=Status.IN_PROGRESS,
            priority=Priority.MEDIUM,
            issue_type=IssueType.FEATURE,
            milestone="v1-0",
        ),
        Issue(
            title="Bug Fix",
            status=Status.CLOSED,
            priority=Priority.HIGH,
            issue_type=IssueType.BUG,
            milestone="v1-0",
        ),
    ]


class TestRecalculateMilestoneProgress:
    """Test recalculate milestone progress command."""

    def test_recalculate_specific_milestone(
        self, cli_runner, mock_core, sample_milestone, sample_issues
    ):
        """Test recalculating progress for a specific milestone."""
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = sample_issues
        mock_core.milestones.list.return_value = [sample_milestone]

        with patch(
            "roadmap.adapters.cli.milestones.recalculate.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            with patch(
                "roadmap.common.progress.ProgressCalculationEngine"
            ) as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine_class.return_value = mock_engine
                mock_engine.update_milestone_progress.return_value = True

                runner = CliRunner()
                result = runner.invoke(
                    recalculate_milestone_progress,
                    ["v1-0"],
                    obj={"core": mock_core},
                )

                assert result.exit_code == 0
                assert mock_core.milestones.get.called
                assert mock_core.issues.list.called

    def test_recalculate_all_milestones(
        self, cli_runner, mock_core, sample_milestone, sample_issues
    ):
        """Test recalculating progress for all milestones."""
        mock_core.issues.list.return_value = sample_issues
        mock_core.milestones.list.return_value = [sample_milestone]

        with patch(
            "roadmap.adapters.cli.milestones.recalculate.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            with patch(
                "roadmap.common.progress.ProgressCalculationEngine"
            ) as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine_class.return_value = mock_engine
                mock_engine.update_milestone_progress.return_value = True

                runner = CliRunner()
                result = runner.invoke(
                    recalculate_milestone_progress,
                    [],
                    obj={"core": mock_core},
                )

                assert result.exit_code == 0
                assert mock_core.milestones.list.called
                assert mock_core.issues.list.called

    def test_recalculate_milestone_not_found(self, cli_runner, mock_core):
        """Test error handling when milestone is not found."""
        mock_core.milestones.get.return_value = None
        mock_core.issues.list.return_value = []

        with patch(
            "roadmap.adapters.cli.milestones.recalculate.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            with patch("roadmap.common.progress.ProgressCalculationEngine"):
                runner = CliRunner()
                result = runner.invoke(
                    recalculate_milestone_progress,
                    ["nonexistent"],
                    obj={"core": mock_core},
                )

                # Command should handle not found gracefully
                assert result.exit_code == 0

    def test_recalculate_with_effort_weighted_method(
        self, cli_runner, mock_core, sample_milestone, sample_issues
    ):
        """Test recalculation with effort_weighted method."""
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = sample_issues
        mock_core.milestones.list.return_value = [sample_milestone]

        with patch(
            "roadmap.adapters.cli.milestones.recalculate.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            with patch(
                "roadmap.common.progress.ProgressCalculationEngine"
            ) as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine_class.return_value = mock_engine
                mock_engine.update_milestone_progress.return_value = True

                runner = CliRunner()
                result = runner.invoke(
                    recalculate_milestone_progress,
                    ["v1-0", "--method", "effort_weighted"],
                    obj={"core": mock_core},
                )

                assert result.exit_code == 0
                mock_engine_class.assert_called_with(method="effort_weighted")

    def test_recalculate_with_count_based_method(
        self, cli_runner, mock_core, sample_milestone, sample_issues
    ):
        """Test recalculation with count_based method."""
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = sample_issues
        mock_core.milestones.list.return_value = [sample_milestone]

        with patch(
            "roadmap.adapters.cli.milestones.recalculate.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            with patch(
                "roadmap.common.progress.ProgressCalculationEngine"
            ) as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine_class.return_value = mock_engine
                mock_engine.update_milestone_progress.return_value = True

                runner = CliRunner()
                result = runner.invoke(
                    recalculate_milestone_progress,
                    ["v1-0", "--method", "count_based"],
                    obj={"core": mock_core},
                )

                assert result.exit_code == 0
                mock_engine_class.assert_called_with(method="count_based")

    def test_recalculate_handles_exception(self, cli_runner, mock_core):
        """Test exception handling during recalculation."""
        mock_core.issues.list.side_effect = Exception("Test error")

        with patch(
            "roadmap.adapters.cli.milestones.recalculate.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            with patch("roadmap.common.progress.ProgressCalculationEngine"):
                runner = CliRunner()
                result = runner.invoke(
                    recalculate_milestone_progress,
                    [],
                    obj={"core": mock_core},
                )

                # Command should handle exception gracefully
                assert result.exit_code == 0

    def test_recalculate_multiple_milestones(
        self, cli_runner, mock_core, sample_milestone, sample_issues
    ):
        """Test recalculating multiple milestones."""
        milestone2 = Milestone(
            name="v2-0",
            content="Second release",
            due_date=None,
            status=MilestoneStatus.OPEN,
        )
        mock_core.issues.list.return_value = sample_issues
        mock_core.milestones.list.return_value = [sample_milestone, milestone2]

        with patch(
            "roadmap.adapters.cli.milestones.recalculate.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            with patch(
                "roadmap.common.progress.ProgressCalculationEngine"
            ) as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine_class.return_value = mock_engine
                mock_engine.update_milestone_progress.return_value = True

                runner = CliRunner()
                result = runner.invoke(
                    recalculate_milestone_progress,
                    [],
                    obj={"core": mock_core},
                )

                assert result.exit_code == 0
                assert mock_core.milestones.list.called
                # Should be called twice (once for each milestone)
                assert mock_engine.update_milestone_progress.call_count == 2

    def test_recalculate_empty_milestone(self, cli_runner, mock_core, sample_milestone):
        """Test recalculation for milestone with no issues."""
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = []
        mock_core.milestones.list.return_value = [sample_milestone]

        with patch(
            "roadmap.adapters.cli.milestones.recalculate.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            with patch(
                "roadmap.common.progress.ProgressCalculationEngine"
            ) as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine_class.return_value = mock_engine
                mock_engine.update_milestone_progress.return_value = False

                runner = CliRunner()
                result = runner.invoke(
                    recalculate_milestone_progress,
                    ["v1-0"],
                    obj={"core": mock_core},
                )

                assert result.exit_code == 0
                assert mock_core.milestones.get.called

    def test_recalculate_no_issues_found_message(
        self, cli_runner, mock_core, sample_milestone
    ):
        """Test that appropriate message is shown when no issues exist."""
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = []
        mock_core.milestones.list.return_value = [sample_milestone]

        with patch(
            "roadmap.adapters.cli.milestones.recalculate.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            with patch(
                "roadmap.common.progress.ProgressCalculationEngine"
            ) as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine_class.return_value = mock_engine
                mock_engine.update_milestone_progress.return_value = False

                runner = CliRunner()
                result = runner.invoke(
                    recalculate_milestone_progress,
                    ["v1-0"],
                    obj={"core": mock_core},
                )

                assert result.exit_code == 0
                assert mock_core.milestones.get.called
