"""CLI tests for milestone close convenience command."""

from click.testing import CliRunner

import pytest

from roadmap.cli import main


@pytest.mark.unit
def test_milestone_close_convenience(cli_runner, initialized_roadmap):
    runner = cli_runner

    # Create a milestone first
    result = runner.invoke(main, ["milestone", "create", "v.0.2.0", "--description", "desc", "--due-date", "2025-10-18"])
    assert result.exit_code == 0
    assert "Created milestone" in result.output or "Created milestone" in result.output

    # Close it with force flag
    result = runner.invoke(main, ["milestone", "close", "v.0.2.0", "--force"])
    assert result.exit_code == 0
    assert "Closed milestone" in result.output

    # Verify CLI shows milestone as closed when listing
    result = runner.invoke(main, ["milestone", "list"])
    assert result.exit_code == 0
    assert "closed" in result.output.lower()
