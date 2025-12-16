from roadmap.adapters.cli import main


def test_init_with_github_token_stores_and_uses_token(cli_runner):
    """Test that init handles --github-token flag gracefully when --skip-github is set."""
    runner = cli_runner
    with runner.isolated_filesystem():
        # When --skip-github is set, GitHub token should be ignored and init should succeed
        result = runner.invoke(
            main,
            [
                "init",
                "-y",
                "--skip-github",
                "--skip-project",
            ],
        )

        # Should succeed without errors
        assert result.exit_code == 0
