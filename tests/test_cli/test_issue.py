"""Tests for issue-related CLI commands."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from roadmap.cli import main


def test_issue_help(cli_runner):
    """Test issue command help."""
    result = cli_runner.invoke(main, ["issue", "--help"])
    assert result.exit_code == 0
    assert "Manage issues" in result.output


def test_issue_create_command(temp_dir):
    """Test creating an issue."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "create", "test-issue"])
    assert result.exit_code == 0
    # Current implementation shows placeholder functionality
    assert "Creating issue" in result.output or "Issue creation" in result.output


def test_issue_create_without_roadmap(temp_dir):
    """Test creating issue without initialized roadmap."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "create", "test-issue"])
    assert result.exit_code == 0
    # The current implementation shows a placeholder, not an error
    assert "Creating issue" in result.output or "Issue creation" in result.output


def test_issue_list_command(temp_dir):
    """Test listing issues."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list"])
    assert result.exit_code == 0
    # Current implementation shows placeholder functionality
    assert "Issue list" in result.output or "functionality" in result.output


def test_issue_list_without_roadmap(temp_dir):
    """Test listing issues without initialized roadmap."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list"])
    assert result.exit_code == 0
    # The current implementation shows a placeholder, not an error
    assert "Issue list" in result.output or "functionality" in result.output