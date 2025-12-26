"""Tests for critical path analysis command."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.analysis.commands import critical_path
from roadmap.adapters.cli.analysis.presenter import CriticalPathPresenter
from roadmap.core.domain.issue import Issue, Priority, Status
from roadmap.core.services.critical_path_calculator import (
    CriticalPathResult,
    PathNode,
)

# mock_core fixture provided by tests.fixtures.mocks module
# No local override needed - uses centralized mock_core_simple


@pytest.fixture
def sample_issues():
    """Create sample issues with dependencies."""
    return [
        Issue(
            id="GH-1",
            title="Setup infrastructure",
            priority=Priority.HIGH,
            status=Status.IN_PROGRESS,
            estimated_hours=8.0,
            depends_on=[],
            blocks=["GH-2"],
        ),
        Issue(
            id="GH-2",
            title="Implement API",
            priority=Priority.HIGH,
            status=Status.TODO,
            estimated_hours=16.0,
            depends_on=["GH-1"],
            blocks=["GH-3"],
        ),
        Issue(
            id="GH-3",
            title="Write tests",
            priority=Priority.MEDIUM,
            status=Status.TODO,
            estimated_hours=8.0,
            depends_on=["GH-2"],
            blocks=[],
        ),
        Issue(
            id="GH-4",
            title="Deploy",
            priority=Priority.LOW,
            status=Status.CLOSED,
            estimated_hours=2.0,
            depends_on=[],
            blocks=[],
        ),
    ]


@pytest.fixture
def critical_path_result():
    """Create a sample CriticalPathResult."""
    nodes = [
        PathNode(
            issue_id="GH-1",
            issue_title="Setup infrastructure",
            duration_hours=8.0,
            dependencies=[],
            is_critical=True,
            slack_time=0.0,
        ),
        PathNode(
            issue_id="GH-2",
            issue_title="Implement API",
            duration_hours=16.0,
            dependencies=["GH-1"],
            is_critical=True,
            slack_time=2.0,
        ),
        PathNode(
            issue_id="GH-3",
            issue_title="Write tests",
            duration_hours=8.0,
            dependencies=["GH-2"],
            is_critical=True,
            slack_time=4.0,
        ),
    ]

    return CriticalPathResult(
        critical_path=nodes,
        total_duration=32.0,
        critical_issue_ids=["GH-1", "GH-2", "GH-3"],
        blocking_issues={
            "GH-1": ["GH-2"],
            "GH-2": ["GH-3"],
            "GH-3": [],
        },
        project_end_date=datetime(2026, 1, 10),
        issues_by_criticality={"critical": ["GH-1", "GH-2", "GH-3"], "normal": []},
    )


class TestCriticalPathPresenter:
    """Test CriticalPathPresenter for formatting output."""

    def test_format_critical_path_with_graph(self, critical_path_result):
        """Test formatting critical path with dependency graph."""
        presenter = CriticalPathPresenter()
        output = presenter.format_critical_path(critical_path_result)

        assert "Critical Path Analysis" in output
        assert "GH-1" in output
        assert "GH-2" in output
        assert "GH-3" in output
        assert "Setup infrastructure" in output

    def test_format_critical_path_includes_summary(self, critical_path_result):
        """Test that output includes summary section."""
        presenter = CriticalPathPresenter()
        output = presenter.format_critical_path(critical_path_result)

        assert "Summary" in output
        assert "32.0 hours" in output
        assert "3" in output  # critical issues count

    def test_format_critical_path_with_milestone(self, critical_path_result):
        """Test formatting with milestone context."""
        presenter = CriticalPathPresenter()
        output = presenter.format_critical_path(critical_path_result, milestone="v1.0")

        assert "v1.0" in output

    def test_format_critical_path_empty(self):
        """Test formatting empty critical path."""
        presenter = CriticalPathPresenter()
        result = CriticalPathResult(
            critical_path=[],
            total_duration=0.0,
            critical_issue_ids=[],
            blocking_issues={},
        )

        output = presenter.format_critical_path(result)

        assert "No critical path" in output or "independent" in output

    def test_risk_assessment_high(self, critical_path_result):
        """Test risk assessment for high risk."""
        presenter = CriticalPathPresenter()
        result = critical_path_result
        # Modify to have minimal slack
        for node in result.critical_path:
            node.slack_time = 1.0

        output = presenter.format_critical_path(result)
        assert "HIGH" in output

    def test_risk_assessment_medium(self, critical_path_result):
        """Test risk assessment for medium risk."""
        presenter = CriticalPathPresenter()
        result = critical_path_result
        # Medium slack (between 4 and 12)
        for node in result.critical_path:
            node.slack_time = 8.0

        output = presenter.format_critical_path(result)
        assert "MEDIUM" in output

    def test_risk_assessment_low(self, critical_path_result):
        """Test risk assessment for low risk."""
        presenter = CriticalPathPresenter()
        result = critical_path_result
        # High slack
        for node in result.critical_path:
            node.slack_time = 20.0

        output = presenter.format_critical_path(result)
        assert "LOW" in output

    def test_format_shows_blockers(self, critical_path_result):
        """Test that output shows top blockers."""
        presenter = CriticalPathPresenter()
        output = presenter.format_critical_path(critical_path_result)

        assert "Blockers" in output or "blocks" in output.lower()

    def test_business_days_calculation(self, critical_path_result):
        """Test that business days are calculated from hours."""
        presenter = CriticalPathPresenter()
        output = presenter.format_critical_path(critical_path_result)

        # 32 hours = 4 business days
        assert "4" in output or "business day" in output.lower()


class TestCriticalPathCommand:
    """Test critical path CLI command."""

    def test_command_no_core(self):
        """Test command when core is not initialized."""
        runner = CliRunner()

        with patch("roadmap.adapters.cli.analysis.commands._get_core") as mock_get_core:
            mock_get_core.return_value = None
            result = runner.invoke(critical_path, [])
            # When core is None, the command will print an error message
            assert "initialized" in result.output.lower() or result.exit_code == 0

    def test_command_filters_closed_by_default(self, sample_issues):
        """Test that closed issues are filtered out by default."""
        runner = CliRunner()

        mock_core = Mock()
        mock_core.is_initialized.return_value = True
        mock_core.issue_manager.get_all_issues.return_value = sample_issues
        mock_core.config_manager.get_config.return_value = Mock(
            behavior=Mock(include_closed_in_critical_path=False)
        )

        with patch("roadmap.adapters.cli.analysis.commands._get_core") as mock_get_core:
            mock_get_core.return_value = mock_core

            with patch(
                "roadmap.adapters.cli.analysis.commands.CriticalPathCalculator"
            ) as mock_calc_class:
                mock_calc = Mock()
                mock_calc_class.return_value = mock_calc
                mock_calc.calculate_critical_path.return_value = CriticalPathResult(
                    critical_path=[],
                    total_duration=0.0,
                    critical_issue_ids=[],
                    blocking_issues={},
                )

                runner.invoke(critical_path, [])

                # Get the issues passed to calculator
                call_args = mock_calc.calculate_critical_path.call_args
                passed_issues = call_args[0][0]

                # Should not include closed issue (GH-4)
                assert len(passed_issues) == 3
                assert all(i.status != Status.CLOSED for i in passed_issues)

    def test_command_includes_closed_with_flag(self, sample_issues):
        """Test that closed issues are included with --include-closed flag."""
        runner = CliRunner()

        mock_core = Mock()
        mock_core.is_initialized.return_value = True
        mock_core.issue_manager.get_all_issues.return_value = sample_issues
        mock_core.config_manager.get_config.return_value = Mock(
            behavior=Mock(include_closed_in_critical_path=False)
        )

        with patch("roadmap.adapters.cli.analysis.commands._get_core") as mock_get_core:
            mock_get_core.return_value = mock_core

            with patch(
                "roadmap.adapters.cli.analysis.commands.CriticalPathCalculator"
            ) as mock_calc_class:
                mock_calc = Mock()
                mock_calc_class.return_value = mock_calc
                mock_calc.calculate_critical_path.return_value = CriticalPathResult(
                    critical_path=[],
                    total_duration=0.0,
                    critical_issue_ids=[],
                    blocking_issues={},
                )

                runner.invoke(critical_path, ["--include-closed"])

                # Get the issues passed to calculator
                call_args = mock_calc.calculate_critical_path.call_args
                passed_issues = call_args[0][0]

                # Should include closed issue
                assert len(passed_issues) == 4

    def test_command_filters_by_milestone(self):
        """Test filtering by milestone."""
        runner = CliRunner()
        sample_with_milestone = [
            Issue(
                id="GH-5",
                title="Feature A",
                priority=Priority.MEDIUM,
                status=Status.TODO,
                estimated_hours=5.0,
                milestone="v1.0",
                depends_on=[],
            ),
            Issue(
                id="GH-6",
                title="Feature B",
                priority=Priority.MEDIUM,
                status=Status.TODO,
                estimated_hours=5.0,
                milestone="v1.1",
                depends_on=[],
            ),
        ]

        mock_core = Mock()
        mock_core.is_initialized.return_value = True
        mock_core.issue_manager.get_all_issues.return_value = sample_with_milestone
        mock_core.config_manager.get_config.return_value = Mock(
            behavior=Mock(include_closed_in_critical_path=False)
        )

        with patch("roadmap.adapters.cli.analysis.commands._get_core") as mock_get_core:
            mock_get_core.return_value = mock_core

            with patch(
                "roadmap.adapters.cli.analysis.commands.CriticalPathCalculator"
            ) as mock_calc_class:
                mock_calc = Mock()
                mock_calc_class.return_value = mock_calc
                mock_calc.calculate_critical_path.return_value = CriticalPathResult(
                    critical_path=[],
                    total_duration=0.0,
                    critical_issue_ids=[],
                    blocking_issues={},
                )

                runner.invoke(critical_path, ["--milestone", "v1.0"])

                call_args = mock_calc.calculate_critical_path.call_args
                passed_issues = call_args[0][0]

                assert len(passed_issues) == 1
                assert passed_issues[0].milestone == "v1.0"

    def test_command_export_json(self, sample_issues, tmp_path):
        """Test exporting to JSON."""
        runner = CliRunner()

        mock_core = Mock()
        mock_core.is_initialized.return_value = True
        mock_core.issue_manager.get_all_issues.return_value = sample_issues
        mock_core.config_manager.get_config.return_value = Mock(
            behavior=Mock(include_closed_in_critical_path=False)
        )

        output_file = tmp_path / "critical_path.json"

        with patch("roadmap.adapters.cli.analysis.commands._get_core") as mock_get_core:
            mock_get_core.return_value = mock_core

            with patch(
                "roadmap.adapters.cli.analysis.commands.CriticalPathCalculator"
            ) as mock_calc_class:
                mock_calc = Mock()
                mock_calc_class.return_value = mock_calc
                result = CriticalPathResult(
                    critical_path=[
                        PathNode(
                            issue_id="GH-1",
                            issue_title="Task 1",
                            duration_hours=8.0,
                            is_critical=True,
                        )
                    ],
                    total_duration=8.0,
                    critical_issue_ids=["GH-1"],
                    blocking_issues={},
                )
                mock_calc.calculate_critical_path.return_value = result

                runner.invoke(
                    critical_path,
                    ["--export", "json", "--output", str(output_file)],
                )

                assert output_file.exists()
                data = json.loads(output_file.read_text())
                assert "critical_path" in data
                assert "summary" in data

    def test_command_export_csv(self, sample_issues, tmp_path):
        """Test exporting to CSV."""
        runner = CliRunner()

        mock_core = Mock()
        mock_core.is_initialized.return_value = True
        mock_core.issue_manager.get_all_issues.return_value = sample_issues
        mock_core.config_manager.get_config.return_value = Mock(
            behavior=Mock(include_closed_in_critical_path=False)
        )

        output_file = tmp_path / "critical_path.csv"

        with patch("roadmap.adapters.cli.analysis.commands._get_core") as mock_get_core:
            mock_get_core.return_value = mock_core

            with patch(
                "roadmap.adapters.cli.analysis.commands.CriticalPathCalculator"
            ) as mock_calc_class:
                mock_calc = Mock()
                mock_calc_class.return_value = mock_calc
                result = CriticalPathResult(
                    critical_path=[],
                    total_duration=0.0,
                    critical_issue_ids=[],
                    blocking_issues={},
                )
                mock_calc.calculate_critical_path.return_value = result

                runner.invoke(
                    critical_path,
                    ["--export", "csv", "--output", str(output_file)],
                )

                assert output_file.exists()
                content = output_file.read_text()
                assert "issue_id" in content
                assert "title" in content
