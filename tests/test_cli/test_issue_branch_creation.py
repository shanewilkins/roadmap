from click.testing import CliRunner

from roadmap.cli import main


def test_create_issue_with_git_branch_flag(cli_runner):
    runner = cli_runner
    with runner.isolated_filesystem():
        # TODO: implement test scaffolding for branch creation; this will be fleshed out
        # once the git integration helpers are finalized. For now, just ensure CLI runs.
        result = runner.invoke(
            main,
            [
                'issue',
                'create',
                'Test branch creation',
                '--git-branch',
                '--no-checkout',
            ],
        )
        # The CLI should exit gracefully even if git isn't present
        assert result.exit_code == 0
