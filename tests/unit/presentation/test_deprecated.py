"""Tests for deprecated CLI commands to ensure backward compatibility."""

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


@pytest.mark.skip(reason="Archived feature: capacity-forecast command moved to future/")
def test_deprecated_capacity_forecast_warning(initialized_roadmap):
    """Test that deprecated capacity-forecast shows warning."""
    runner = CliRunner()
    result = runner.invoke(main, ["capacity-forecast", "--help"])
    assert result.exit_code == 0
    assert "DEPRECATION WARNING" in result.output
    assert "roadmap team forecast-capacity" in result.output


@pytest.mark.skip(reason="Archived feature: workload-analysis command moved to future/")
def test_deprecated_workload_analysis_warning(initialized_roadmap):
    """Test that deprecated workload-analysis shows warning."""
    runner = CliRunner()
    result = runner.invoke(main, ["workload-analysis", "--help"])
    assert result.exit_code == 0
    assert "DEPRECATION WARNING" in result.output
    assert "roadmap team analyze-workload" in result.output


@pytest.mark.skip(reason="Archived feature: smart-assign command moved to future/")
def test_deprecated_smart_assign_warning(initialized_roadmap):
    """Test that deprecated smart-assign shows warning."""
    runner = CliRunner()
    # Create an issue first for testing
    issue_result = runner.invoke(main, ["issue", "create", "test-issue"])

    # Extract issue ID
    issue_id = None
    for line in issue_result.output.split("\n"):
        if "ID:" in line:
            issue_id = line.split(":")[1].strip()
            break

    if issue_id:
        result = runner.invoke(main, ["smart-assign", issue_id])
        assert result.exit_code == 0
        assert "DEPRECATION WARNING" in result.output
        assert "roadmap team assign-smart" in result.output


@pytest.mark.skip(reason="Archived feature: dashboard command moved to future/")
def test_deprecated_dashboard_warning(initialized_roadmap):
    """Test that deprecated dashboard shows warning."""
    runner = CliRunner()
    result = runner.invoke(main, ["dashboard"])
    assert result.exit_code == 0
    assert "DEPRECATION WARNING" in result.output
    assert "roadmap user show-dashboard" in result.output


@pytest.mark.skip(reason="Archived feature: notifications command moved to future/")
def test_deprecated_notifications_warning(initialized_roadmap):
    """Test that deprecated notifications shows warning."""
    runner = CliRunner()
    result = runner.invoke(main, ["notifications"])
    assert result.exit_code == 0
    assert "DEPRECATION WARNING" in result.output
    assert "roadmap user show-notifications" in result.output


@pytest.mark.skip(reason="Archived feature: deprecated commands moved to future/")
def test_deprecated_commands_still_work(initialized_roadmap):
    """Test that deprecated commands still provide functionality."""
    runner = CliRunner()

    # Test that deprecated commands actually execute their functionality
    # (not just show help)
    deprecated_commands = [
        ["capacity-forecast"],
        ["workload-analysis"],
        ["dashboard"],
        ["notifications"],
    ]

    for command in deprecated_commands:
        result = runner.invoke(main, command)
        assert result.exit_code == 0
        # Each should show the deprecation warning and then execute
        assert "DEPRECATION WARNING" in result.output
