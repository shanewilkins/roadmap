"""Shared fixtures for the retained architecture and command journeys."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def workspace_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Give each CLI scenario a fresh cwd and restore it even after a failure."""

    @contextmanager
    def directory() -> Generator[Path]:
        with TemporaryDirectory(dir=tmp_path) as temporary:
            with monkeypatch.context() as context:
                path = Path(temporary)
                context.chdir(path)
                yield path

    return directory
