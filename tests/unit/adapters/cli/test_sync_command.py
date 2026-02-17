"""Tests for the top-level sync command."""

from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.sync import sync
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_core():
    """Create a mock RoadmapCore instance."""
    mock = Mock()
    mock.roadmap_dir = "/fake/roadmap"
    return mock


class TestSyncCommand:
    """Test the top-level sync command."""

    def test_sync_help(self, runner):
        """Test that sync --help works."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert result.exit_code == 0
        assert "Sync roadmap with remote repository" in output
        assert "--dry-run" in output
        assert "--backend" in output

    def test_sync_help_mentions_backends(self, runner):
        """Test that help text mentions available backends."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert "github" in output
        assert "git" in output

    def test_sync_help_mentions_conflict_resolution(self, runner):
        """Test that help mentions conflict resolution strategies."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output).lower()
        assert "conflict" in output or "three-way" in output

    def test_sync_option_force_local(self, runner):
        """Test that --force-local option exists."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert "--force-local" in output

    def test_sync_option_force_remote(self, runner):
        """Test that --force-remote option exists."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert "--force-remote" in output

    def test_sync_option_verbose(self, runner):
        """Test that --verbose option exists."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert "--verbose" in output

    def test_sync_option_backend_override(self, runner):
        """Test that --backend option allows override."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert "--backend" in output
        # Check it mentions the choices
        assert "github" in output
        assert "git" in output
