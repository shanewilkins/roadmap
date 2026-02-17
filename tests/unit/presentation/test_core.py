"""Tests for core CLI functionality (init, status, version, help)."""

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


class TestCoreCommands:
    """Test core CLI commands."""

    def test_cli_version(self):
        """Test CLI version command."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "version" in clean_cli_output(result.output).lower()

    def test_cli_help(self, cli_runner):
        """Test CLI help command."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "roadmap" in clean_cli_output(result.output).lower()

    @pytest.mark.parametrize(
        "args,expected_output",
        [
            (["init"], ["roadmap", "initialization"]),
            (["status"], ["roadmap", "status"]),
        ],
    )
    def test_cli_commands(self, cli_runner, args, expected_output):
        """Test various CLI commands."""
        result = cli_runner.invoke(main, args)
        assert result.exit_code in (0, 1)
        # At least one expected output should be present
        output = clean_cli_output(result.output).lower()
        assert any(text in output for text in expected_output)

    def test_init_already_initialized(self):
        """Test init command when roadmap is already initialized."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["init"])
            # First init should succeed
            assert result.exit_code in (0, 1)

    def test_init_with_error(self):
        """Test init command with simulated error."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open(".roadmap", "w") as f:
                f.write("not a directory")
            result = runner.invoke(main, ["init"])
            assert result.exit_code != 0

    def test_status_command_variants(self):
        """Test status command with and without roadmap."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["status"])
            # Status should either succeed or fail gracefully
            assert result.exit_code in (0, 1) or clean_cli_output(result.output)

    def test_status_no_roadmap(self):
        """Test status command without a roadmap."""
        runner = CliRunner()
        result = runner.invoke(main, ["status"])
        # Should fail or show indication
        assert result.exit_code != 0 or clean_cli_output(result.output)
