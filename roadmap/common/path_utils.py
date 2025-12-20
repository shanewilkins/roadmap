"""Shared utilities for roadmap directory path construction."""

from pathlib import Path
from typing import Any


def build_roadmap_paths(
    root_path: Path, roadmap_dir_name: str = ".roadmap"
) -> dict[str, Any]:
    """Build all standard roadmap directory and file paths.

    Consolidates the common pattern of constructing roadmap paths
    used across the application (core, initialization, etc).

    Args:
        root_path: Root directory of the project
        roadmap_dir_name: Name of the roadmap directory (default: .roadmap)

    Returns:
        Dictionary containing all standard roadmap paths
    """
    roadmap_dir = root_path / roadmap_dir_name

    return {
        "root_path": root_path,
        "roadmap_dir_name": roadmap_dir_name,
        "roadmap_dir": roadmap_dir,
        "issues_dir": roadmap_dir / "issues",
        "milestones_dir": roadmap_dir / "milestones",
        "projects_dir": roadmap_dir / "projects",
        "templates_dir": roadmap_dir / "templates",
        "artifacts_dir": roadmap_dir / "artifacts",
        "config_file": roadmap_dir / "config.yaml",
        "db_dir": roadmap_dir / "db",
    }


__all__ = ["build_roadmap_paths"]
