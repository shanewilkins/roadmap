"""Tests for project-related CLI commands."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from roadmap.cli import main


def test_project_help(cli_runner):
    """Test project command help."""
    result = cli_runner.invoke(main, ["project", "--help"])
    assert result.exit_code == 0
    assert "project" in result.output.lower()


def test_project_create_command(temp_dir):
    """Test project create command."""
    runner = CliRunner()
    result = runner.invoke(main, ["project", "create", "test-project"])
    assert result.exit_code == 0
    # Should handle gracefully with current implementation


def test_project_list_command(temp_dir):
    """Test project list command."""
    runner = CliRunner()
    result = runner.invoke(main, ["project", "list"])
    assert result.exit_code == 0
    # Should handle gracefully with current implementation