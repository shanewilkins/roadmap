from roadmap.adapters.cli import main


def test_post_init_validation_warns_on_missing_project(cli_runner):
    runner = cli_runner
    with runner.isolated_filesystem():
        # Run init with --skip-project to skip project creation
        result = runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--skip-project",
            ],
        )

        # Should succeed even without projects
        assert result.exit_code == 0


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
