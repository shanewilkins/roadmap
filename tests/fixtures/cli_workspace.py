"""Real-storage CLI workspace fixtures and postcondition helpers."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from roadmap.adapters.outbound.persistence.canonical import CanonicalUnitOfWork
from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.bootstrap import cli
from roadmap.bootstrap.core import create_core
from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import Timestamp
from tests.fixtures.ansi import clean_cli_output

NOW = Timestamp(datetime(2026, 10, 6, tzinfo=UTC))


@pytest.fixture
def workspace(tmp_path, monkeypatch, cli_runner):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.chdir(tmp_path)
    result = cli_runner.invoke(cli, ["init", "--skip-project", "--non-interactive"])
    assert result.exit_code == 0, clean_cli_output(result.output)
    return create_core(tmp_path)


def run(runner, *arguments, code=0, **kwargs):
    result = runner.invoke(cli, list(arguments), **kwargs)
    assert result.exit_code == code, clean_cli_output(result.output)
    return result


def seed(core, *values):
    repository = DocumentRepository(core.roadmap_dir)
    projection = SQLiteProjection(core.roadmap_dir / "db/projection.db", repository)
    with CanonicalUnitOfWork(repository, projection) as unit:
        for value in values:
            {
                Issue: unit.save_issue,
                Milestone: unit.save_milestone,
                Project: unit.save_project,
            }[type(value)](value)
        unit.commit()


def canonical_bytes(core):
    return {p: p.read_bytes() for p in core.roadmap_dir.rglob("*.md")}
