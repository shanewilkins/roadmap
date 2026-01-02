"""Tests for the top-level sync command."""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock

from roadmap.adapters.cli.sync import sync


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
        assert result.exit_code == 0
        assert "Sync roadmap with remote repository" in result.output
        assert "--dry-run" in result.output
        assert "--backend" in result.output

    def test_sync_help_mentions_backends(self, runner):
        """Test that help text mentions available backends."""
        result = runner.invoke(sync, ["--help"])
        assert "github" in result.output
        assert "git" in result.output

    def test_sync_help_mentions_conflict_resolution(self, runner):
        """Test that help mentions conflict resolution strategies."""
        result = runner.invoke(sync, ["--help"])
        assert "conflict" in result.output.lower() or "three-way" in result.output.lower()

    def test_sync_option_force_local(self, runner):
        """Test that --force-local option exists."""
        result = runner.invoke(sync, ["--help"])
        assert "--force-local" in result.output

    def test_sync_option_force_remote(self, runner):
        """Test that --force-remote option exists."""
        result = runner.invoke(sync, ["--help"])
        assert "--force-remote" in result.output

    def test_sync_option_verbose(self, runner):
        """Test that --verbose option exists."""
        result = runner.invoke(sync, ["--help"])
        assert "--verbose" in result.output

    def test_sync_option_backend_override(self, runner):
        """Test that --backend option allows override."""
        result = runner.invoke(sync, ["--help"])
        assert "--backend" in result.output
        # Check it mentions the choices
        assert "github" in result.output
        assert "git" in result.output
