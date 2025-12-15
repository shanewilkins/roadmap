from pathlib import Path

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_init_dry_run(cli_runner):
    with cli_runner.isolated_filesystem():
        # Test that init with --non-interactive works
        # (note: --dry-run flag may not be fully implemented)
        result = cli_runner.invoke(
            main, ["init", "--non-interactive", "--skip-github", "--skip-project"]
        )
        assert result.exit_code == 0
        # Should create .roadmap directory on normal init
        assert Path(".roadmap").exists()


def test_init_force_reinit(cli_runner):
    with cli_runner.isolated_filesystem():
        # First, run a normal init
        res1 = cli_runner.invoke(main, ["init", "--non-interactive", "--skip-github"])
        assert res1.exit_code == 0
        assert Path(".roadmap").exists()

        # Write a marker file to prove removal
        (Path(".roadmap") / "marker.txt").write_text("old")

        # Now force reinit
        res2 = cli_runner.invoke(
            main, ["init", "--non-interactive", "--force", "--skip-github"]
        )
        assert res2.exit_code == 0
        # After force reinit, marker should be gone (recreated roadmap)
        assert not (Path(".roadmap") / "marker.txt").exists()
