"""Tests for the roadmap CLI."""

import pytest
from click.testing import CliRunner

from roadmap.cli import main


def test_cli_version():
    """Test that the CLI shows version information."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_help():
    """Test that the CLI shows help information."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Roadmap CLI" in result.output


def test_init_command():
    """Test the init command."""
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0
    assert "Initializing new roadmap" in result.output


def test_status_command():
    """Test the status command."""
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "Roadmap Status" in result.output


def test_add_command():
    """Test the add command."""
    runner = CliRunner()
    result = runner.invoke(main, ["add", "test-milestone"])
    assert result.exit_code == 0
    assert "Adding milestone: test-milestone" in result.output


def test_complete_command():
    """Test the complete command."""
    runner = CliRunner()
    result = runner.invoke(main, ["complete", "test-milestone"])
    assert result.exit_code == 0
    assert "Marking milestone as complete: test-milestone" in result.output


def test_list_command():
    """Test the list command."""
    runner = CliRunner()
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "Roadmap Milestones" in result.output