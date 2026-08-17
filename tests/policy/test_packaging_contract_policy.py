"""Policy tests for the installable distribution contract."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = PROJECT_ROOT / "pyproject.toml"

DEVELOPMENT_ONLY_PACKAGES = {
    "bandit",
    "import-linter",
    "mkdocs",
    "mkdocs-click",
    "mkdocs-material",
    "myst-parser",
    "pre-commit",
    "pydocstyle",
    "pylint",
    "pyright",
    "pytest",
    "pytest-aiohttp",
    "pytest-asyncio",
    "pytest-benchmark",
    "pytest-cov",
    "pytest-mock",
    "pytest-xdist",
    "radon",
    "ruff",
    "sphinx",
    "sphinx-click",
    "sphinx-rtd-theme",
    "vulture",
    "xenon",
}


def _configuration() -> dict:
    with PYPROJECT.open("rb") as pyproject:
        return tomllib.load(pyproject)


def _dependency_name(requirement: str) -> str:
    """Return a normalized distribution name from a PEP 508 requirement."""
    name = re.split(r"[<>=!~;\[\s]", requirement, maxsplit=1)[0]
    return re.sub(r"[-_.]+", "-", name).lower()


def test_distribution_and_console_script_names_are_distinct() -> None:
    """The PyPI distribution must not collide with the import namespace."""
    project = _configuration()["project"]

    assert project["name"] == "roadmap-cli"
    assert project["scripts"] == {"roadmap": "roadmap.bootstrap:main"}


def test_runtime_dependencies_exclude_namespace_collision_and_dev_tools() -> None:
    """User installs must contain only libraries required at runtime."""
    project = _configuration()["project"]
    runtime_dependencies = {
        _dependency_name(requirement) for requirement in project["dependencies"]
    }

    assert "roadmap" not in runtime_dependencies
    assert runtime_dependencies.isdisjoint(DEVELOPMENT_ONLY_PACKAGES)


def test_repository_metadata_uses_the_canonical_remote() -> None:
    """Built metadata must direct users to the repository they installed."""
    urls = _configuration()["project"]["urls"]

    assert urls["Repository"] == "https://github.com/shanewilkins/roadmap"
    assert urls["Issues"] == "https://github.com/shanewilkins/roadmap/issues"
