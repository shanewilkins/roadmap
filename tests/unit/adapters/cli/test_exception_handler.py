"""Unit tests for centralized CLI exception handling."""

import click
import pytest

from roadmap.adapters.inbound.cli.exception_handler import handle_cli_exception
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.domain.failures import DomainFailure


def _context() -> click.Context:
    return click.Context(click.Command("test"))


@pytest.mark.parametrize(
    "error",
    [
        ApplicationFailure(FailureCategory.NOT_FOUND, "issue not found"),
        DomainFailure("invalid transition"),
        ValueError("bad value"),
    ],
    ids=["application-failure", "domain-failure", "value-error"],
)
def test_known_failures_print_plain_message_and_exit_1(capsys, error) -> None:
    with pytest.raises(click.exceptions.Exit) as excinfo:
        handle_cli_exception(_context(), error)
    assert excinfo.value.exit_code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() == f"Error: {error}"
    assert "Traceback" not in captured.err


def test_unexpected_exception_hides_traceback_by_default(capsys) -> None:
    error = RuntimeError("boom")
    with pytest.raises(click.exceptions.Exit) as excinfo:
        handle_cli_exception(_context(), error, show_traceback=False)
    assert excinfo.value.exit_code == 1
    captured = capsys.readouterr()
    assert "Error: boom" in captured.err
    assert "Traceback" not in captured.err


def test_unexpected_exception_shows_traceback_when_requested(capsys) -> None:
    try:
        raise RuntimeError("boom")
    except RuntimeError as error:
        with pytest.raises(click.exceptions.Exit) as excinfo:
            handle_cli_exception(_context(), error, show_traceback=True)
    assert excinfo.value.exit_code == 1
    captured = capsys.readouterr()
    assert "Error: boom" in captured.err
    assert "Traceback" in captured.err
    assert "RuntimeError" in captured.err
