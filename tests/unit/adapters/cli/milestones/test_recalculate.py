"""Tests for the canonical milestone progress report command."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from click.testing import CliRunner

from roadmap.adapters.cli.milestones.recalculate import (
    recalculate_milestone_progress,
)
from tests.unit.common.formatters.test_ansi_utilities import strip_ansi


def _summary(name: str, progress: float, closed: int = 0, total: int = 0):
    return SimpleNamespace(
        milestone=SimpleNamespace(name=name),
        progress=progress,
        closed_count=closed,
        issue_count=total,
    )


def _invoke(planning, *arguments: str):
    core = SimpleNamespace(planning=planning)
    return CliRunner().invoke(
        recalculate_milestone_progress,
        list(arguments),
        obj={"core": core},
    )


def test_recalculate_specific_milestone_reports_derived_progress():
    planning = MagicMock()
    planning.milestone.return_value = _summary("v1-0", 62.5)

    result = _invoke(planning, "v1-0")
    output = strip_ansi(result.output)

    assert result.exit_code == 0
    assert "v1-0: 62.5%" in output
    planning.milestone.assert_called_once_with("v1-0")


def test_recalculate_all_milestones_reports_snapshot():
    planning = MagicMock()
    planning.snapshot.return_value.milestones = (
        _summary("v1-0", 25.0),
        _summary("v2-0", 75.0),
    )

    result = _invoke(planning)
    output = strip_ansi(result.output)

    assert result.exit_code == 0
    assert "v1-0: 25.0%" in output
    assert "v2-0: 75.0%" in output


def test_count_based_recalculation_uses_closed_issue_count():
    planning = MagicMock()
    planning.milestone.return_value = _summary("v1-0", 12.5, closed=2, total=5)

    result = _invoke(planning, "v1-0", "--method", "count_based")
    output = strip_ansi(result.output)

    assert result.exit_code == 0
    assert "v1-0: 40.0%" in output


def test_recalculate_translates_application_failure():
    planning = MagicMock()
    planning.milestone.side_effect = ValueError("Milestone 'missing' was not found")

    result = _invoke(planning, "missing")
    output = strip_ansi(result.output)

    assert result.exit_code != 0
    assert "not found" in output
