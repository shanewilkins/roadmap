"""Shared fixtures for the retained architecture and command journeys."""

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()
