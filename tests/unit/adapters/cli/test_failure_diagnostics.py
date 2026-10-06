"""Failure diagnostics remain visible without contaminating command results."""

from types import SimpleNamespace

import click
import pytest
from click.testing import CliRunner

from roadmap.adapters.inbound.cli.cli_command_helpers import projection_warning
from roadmap.bootstrap import BootstrapInputs, build_cli
from roadmap.domain.failures import DomainFailure


@pytest.mark.parametrize("debug", [False, True])
@pytest.mark.parametrize("stage", ["load", "startup", "command"])
def test_unexpected_failures_have_nonzero_stderr_and_opt_in_traceback(debug, stage):
    def broken(*args):
        raise RuntimeError("injected diagnostic failure")

    command = build_cli(
        BootstrapInputs(
            core_builder=broken if stage == "startup" else lambda *a: object()
        ),
        command_registry={"probe": ("roadmap.nonexistent_command", "probe", "Probe")}
        if stage == "load"
        else {},
    )
    if stage != "load":
        command.add_command(click.Command("probe", callback=broken))
    result = CliRunner().invoke(command, (["--debug"] if debug else []) + ["probe"])
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Error:" in result.stderr
    assert "No such command" not in result.stderr
    assert ("Traceback" in result.stderr) == debug


def test_unknown_command_remains_usage_error():
    result = CliRunner().invoke(build_cli(), ["unknown-command"])
    assert result.exit_code == 2
    assert "No such command" in result.stderr


def test_debug_keeps_expected_failures_concise():
    def invalid():
        raise DomainFailure("invalid transition")

    command = build_cli(
        BootstrapInputs(core_builder=lambda *a: object()), command_registry={}
    )
    command.add_command(click.Command("probe", callback=invalid))
    result = CliRunner().invoke(command, ["--debug", "probe"])
    assert result.exit_code == 1
    assert "invalid transition" in result.stderr
    assert "Traceback" not in result.stderr


def test_projection_warning_keeps_script_output_clean():
    @click.command()
    def command():
        click.echo("created-id")
        projection_warning(SimpleNamespace(projection_stale=True))

    result = CliRunner().invoke(command)
    assert result.exit_code == 0
    assert result.stdout == "created-id\n"
    assert "canonical Markdown was saved" in result.stderr
    assert "--dry-run" in result.stderr
