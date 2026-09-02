"""Policy tests for what actually ends up inside the built wheel and sdist."""

from __future__ import annotations

import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_SDIST_TOP_LEVEL = {
    ".gitignore",
    "CHANGELOG.md",
    "LICENSE.md",
    "PKG-INFO",
    "README.md",
    "pyproject.toml",
    "roadmap",
}


def _project_version() -> str:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject:
        return tomllib.load(pyproject)["project"]["version"]


def _build(tmp_path: Path) -> tuple[Path, Path]:
    """Build the wheel and sdist into tmp_path and return their paths."""
    subprocess.run(
        ["uv", "build", "--out-dir", str(tmp_path)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    version = _project_version()
    wheel = tmp_path / f"roadmap_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"roadmap_cli-{version}.tar.gz"
    assert wheel.is_file(), f"expected wheel not built: {wheel.name}"
    assert sdist.is_file(), f"expected sdist not built: {sdist.name}"
    return wheel, sdist


def test_wheel_contains_only_the_package_and_its_dist_info(tmp_path: Path) -> None:
    """The wheel must ship exactly the importable package plus standard metadata."""
    wheel, _sdist = _build(tmp_path)
    version = _project_version()
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()

    dist_info = f"roadmap_cli-{version}.dist-info"
    expected_dist_info = {
        f"{dist_info}/METADATA",
        f"{dist_info}/RECORD",
        f"{dist_info}/WHEEL",
        f"{dist_info}/entry_points.txt",
        f"{dist_info}/licenses/LICENSE.md",
    }
    package_files = {name for name in names if name.startswith("roadmap/")}
    other_files = {name for name in names if not name.startswith("roadmap/")}

    assert package_files, "wheel must contain the roadmap package"
    assert other_files == expected_dist_info, (
        "unexpected wheel entries outside roadmap/ and dist-info: "
        f"{other_files - expected_dist_info}"
    )
    assert not any(name.endswith(".pyc") or "__pycache__" in name for name in names)
    assert not any("tests" in name.split("/") for name in names)


def test_sdist_top_level_is_the_reviewed_allow_list(tmp_path: Path) -> None:
    """The sdist must not leak dev tooling, docs, or repository scaffolding."""
    _wheel, sdist = _build(tmp_path)
    version = _project_version()
    prefix = f"roadmap_cli-{version}/"
    with tarfile.open(sdist) as archive:
        names = archive.getnames()

    top_level = {
        name.removeprefix(prefix).split("/", 1)[0]
        for name in names
        if name != prefix.rstrip("/") and name.startswith(prefix)
    }
    assert top_level == ALLOWED_SDIST_TOP_LEVEL, (
        f"unexpected top-level sdist entries: {top_level - ALLOWED_SDIST_TOP_LEVEL}"
    )
    assert not any(name.endswith(".pyc") or "__pycache__" in name for name in names)
