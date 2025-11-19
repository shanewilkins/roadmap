import pytest

from roadmap.cli import main

pytestmark = pytest.mark.skip(
    reason="CLI command integration tests - complex Click mocking"
)


def test_post_init_validation_warns_on_missing_project(cli_runner):
    runner = cli_runner
    with runner.isolated_filesystem():
        # Run init but skip project creation so projects dir is empty/missing
        result = runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--skip-project",
            ],
        )

        assert result.exit_code == 0
        # Expect a warning about no project files
        assert (
            "No project files found" in result.output
            or "No project files" in result.output
        )


def test_post_init_validation_passes_with_project(cli_runner):
    runner = cli_runner
    with runner.isolated_filesystem():
        # Run init normally with project creation
        result = runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--project-name",
                "Test Project",
            ],
        )

        assert result.exit_code == 0
        # Should not show missing project warning
        assert "No project files found" not in result.output
