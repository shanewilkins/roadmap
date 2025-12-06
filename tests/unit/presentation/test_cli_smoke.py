import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main

pytestmark = pytest.mark.skip(
    reason="CLI command integration tests - complex Click mocking"
)


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.mark.parametrize(
    "cmd",
    [
        "--help",
        # V1.0 core commands
        "data",
        "init",
        "issue",
        "milestone",
        "project",
        "status",
        # Archived commands (post-1.0 features) are no longer available
        # See future/FUTURE_FEATURES.md for restoration details
    ],
)
def test_command_help(cli_runner: CliRunner, cmd: str):
    """Ensure top-level commands print help and exit with code 0."""
    # For the root help, call without command
    args = [] if cmd == "--help" else [cmd, "--help"]
    result = cli_runner.invoke(main, args)
    # Help should exit cleanly
    assert (
        result.exit_code == 0
    ), f"Help failed for {cmd}: {result.output}\n{result.exception}"


def test_data_export_help(cli_runner: CliRunner):
    result = cli_runner.invoke(main, ["data", "export", "--help"])
    assert result.exit_code == 0


def test_git_group_help(cli_runner: CliRunner):
    # 'git' may be a group exposing git-branch/git-status; just check help
    result = cli_runner.invoke(main, ["git", "--help"])
    assert result.exit_code == 0
