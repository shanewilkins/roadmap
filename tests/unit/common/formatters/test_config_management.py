"""Tests for local-only project configuration."""

from pathlib import Path

import pytest
import yaml

from roadmap.common.configuration import (
    ConfigManager,
    PathsConfig,
    RoadmapConfig,
    UserConfig,
)


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    """Return an isolated config path."""
    return tmp_path / "config.yaml"


def test_loads_local_user_and_paths(config_path: Path) -> None:
    config_path.write_text(
        yaml.safe_dump(
            {
                "user": {"name": "alice", "email": "alice@example.test"},
                "paths": {"db_dir": ".roadmap/local-db"},
            }
        )
    )

    config = ConfigManager(config_path).load()

    assert config.user.name == "alice"
    assert config.user.email == "alice@example.test"
    assert config.paths.db_dir == ".roadmap/local-db"


def test_local_override_merges_without_provider_configuration(
    config_path: Path,
) -> None:
    config_path.write_text(
        yaml.safe_dump(
            {
                "user": {"name": "team", "email": "team@example.test"},
                "display": {"table_width": 100},
            }
        )
    )
    local_path = config_path.with_suffix(".yaml.local")
    local_path.write_text(
        yaml.safe_dump({"user": {"name": "bob"}, "display": {"table_width": 120}})
    )

    config = ConfigManager(config_path).load()

    assert config.user.name == "bob"
    assert config.user.email == "team@example.test"
    assert config.display.table_width == 120


def test_save_round_trip_contains_only_local_schema(config_path: Path) -> None:
    manager = ConfigManager(config_path)
    original = RoadmapConfig(
        user=UserConfig(name="alice", email="alice@example.test"),
        paths=PathsConfig(db_dir=".roadmap/cache"),
    )

    manager.save(original)
    saved = yaml.safe_load(config_path.read_text())

    assert set(saved) == {"user", "paths", "display", "behavior"}
    assert manager.load() == original


def test_deep_merge_keeps_unmodified_nested_values() -> None:
    merged = ConfigManager._deep_merge(
        {"user": {"name": "team", "email": "team@example.test"}},
        {"user": {"name": "alice"}},
    )

    assert merged == {"user": {"name": "alice", "email": "team@example.test"}}
