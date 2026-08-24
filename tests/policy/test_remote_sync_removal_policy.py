"""Executable contracts for the Phase 11 remote-sync removal."""

from __future__ import annotations

import sqlite3
import tomllib
from pathlib import Path

from click.testing import CliRunner

from roadmap.adapters.persistence.database_manager import DatabaseManager
from roadmap.bootstrap import cli
from roadmap.common.configuration import RoadmapConfig, UserConfig

ROOT = Path(__file__).resolve().parents[2]
REMOVED_NAMESPACES = (
    "roadmap/adapters/github",
    "roadmap/adapters/sync",
    "roadmap/core/services/baseline",
    "roadmap/core/services/github",
    "roadmap/core/services/sync",
    "roadmap/common/configuration/github",
    "roadmap/common/initialization/github",
    "roadmap/infrastructure/github_gateway.py",
    "roadmap/infrastructure/sync_gateway.py",
)
PROVIDER_TABLES = {
    "issue_remote_links",
    "sync_metrics",
    "sync_base_state",
    "sync_metadata",
    "file_sync_state",
}
REMOVED_DIRECT_DEPENDENCIES = {
    "asyncclick",
    "dynaconf",
    "keyring",
    "requests",
    "tabulate",
    "urllib3",
}


def test_removed_namespaces_are_physically_absent() -> None:
    """Deleted protocols cannot survive behind compatibility facades."""
    assert [
        path
        for path in REMOVED_NAMESPACES
        if (ROOT / path).is_file()
        or ((ROOT / path).is_dir() and any((ROOT / path).rglob("*.py")))
    ] == []


def test_removed_commands_are_unknown_without_lazy_load_warning() -> None:
    """The old entry points fail with Click's normal unknown-command contract."""
    runner = CliRunner()
    for command in ("sync", "validate-links"):
        result = runner.invoke(cli, [command])
        assert result.exit_code == 2
        assert f"No such command '{command}'" in result.output
        assert "Failed to load command" not in result.output


def test_retained_command_help_has_no_provider_controls() -> None:
    """Initialization, issues, and local Git expose no provider protocol."""
    runner = CliRunner()
    for arguments, forbidden in (
        (
            ["init", "--help"],
            ("--skip-github", "--sync-backend", "--github-token", "--github-repo"),
        ),
        (
            ["issue", "--help"],
            ("link-github", "unlink-github", "lookup-github", "sync-status"),
        ),
        (["git", "--help"], ("sync", "push", "pull")),
    ):
        result = runner.invoke(cli, arguments)
        assert result.exit_code == 0, result.exception
        assert not any(item in result.output for item in forbidden)
        assert "Failed to load command" not in result.output


def test_configuration_schema_has_only_local_product_settings() -> None:
    """Provider, credential, and transport policy are not Roadmap config."""
    config = RoadmapConfig(user=UserConfig(name="local-user")).to_dict()
    assert set(config) == {"user", "paths", "display", "behavior"}


def test_provider_dependencies_are_not_direct_runtime_dependencies() -> None:
    """Provider/network libraries do not return through project metadata."""
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    direct = {
        requirement.split("[", 1)[0].split("<", 1)[0].split(">", 1)[0].lower()
        for requirement in metadata["project"]["dependencies"]
    }
    assert direct.isdisjoint(REMOVED_DIRECT_DEPENDENCIES)


def test_opening_legacy_database_drops_provider_protocol_tables(tmp_path: Path) -> None:
    """The bounded legacy cleanup removes only obsolete derived/provider state."""
    db_path = tmp_path / "state.db"
    with sqlite3.connect(db_path) as connection:
        for table in PROVIDER_TABLES:
            connection.execute(f'CREATE TABLE "{table}" (id INTEGER)')

    manager = DatabaseManager(db_path)
    try:
        with sqlite3.connect(db_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert tables.isdisjoint(PROVIDER_TABLES)
        assert {"projects", "milestones", "issues"} <= tables
    finally:
        manager.close()
