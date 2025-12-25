"""Tests for post-initialization validation."""

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


@pytest.fixture
def cli_runner():
    """Provide a Click test runner."""
    return CliRunner()


class TestPostInitValidation:
    """Test post-initialization validation checks."""

    @pytest.mark.parametrize(
        "skip_project,expected_in_output",
        [
            (True, None),  # Skip project validation
            (False, "No project files found"),  # Check for warning
        ],
    )
    def test_post_init_validation(self, cli_runner, skip_project, expected_in_output):
        """Test that post-init validation handles missing projects appropriately."""
        with cli_runner.isolated_filesystem():
            args = [
                "init",
                "--non-interactive",
                "--skip-github",
            ]
            if skip_project:
                args.append("--skip-project")
            else:
                args.extend(["--project-name", "Test Project"])

            result = cli_runner.invoke(main, args)

            assert result.exit_code == 0
            if expected_in_output:
                assert expected_in_output not in result.output
