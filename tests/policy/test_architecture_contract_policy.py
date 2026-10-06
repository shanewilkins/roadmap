"""Architecture contracts, governance metadata, and the type checking gate."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures" / "architecture"
POLICY = tomllib.loads((ROOT / "architecture.toml").read_text())["architecture"]
EXECUTION_PLAN = ROOT / "docs" / "architecture" / "refactor-execution-plan.md"
ARCHITECTURE_INDEX = ROOT / "docs" / "architecture" / "README.md"
CHECKPOINTS = ROOT / "docs" / "architecture" / "checkpoints"


def test_governance_phase_state_is_consistent() -> None:
    """The policy, execution plan, index, and accepted checkpoint cannot drift."""
    plan = EXECUTION_PLAN.read_text(encoding="utf-8")
    index = ARCHITECTURE_INDEX.read_text(encoding="utf-8")
    header = "\n".join(plan.splitlines()[:12])
    phases = {
        int(match.group(1))
        for match in re.finditer(r"^## Phase (\d+) —", plan, flags=re.MULTILINE)
    }

    assert phases == set(range(POLICY["final_phase"] + 1))
    assert (
        f"Execution status: Phase {POLICY['current_phase']} checkpoint passed" in header
    )
    if POLICY["current_phase"] < POLICY["final_phase"]:
        assert f"approval before Phase {POLICY['current_phase'] + 1}" in header
    else:
        assert "separate authorization before release" in header
    assert f"Accepted checkpoint: Phase {POLICY['current_phase']}" in index
    assert f"Final planned implementation phase: Phase {POLICY['final_phase']}" in index

    checkpoints = sorted(CHECKPOINTS.glob(f"phase-{POLICY['current_phase']}-*.md"))
    assert len(checkpoints) == 1
    checkpoint = checkpoints[0].read_text(encoding="utf-8")
    assert "Decision: **GO**" in checkpoint
    if POLICY["current_phase"] < POLICY["final_phase"]:
        assert f"before Phase {POLICY['current_phase'] + 1}" in checkpoint
    else:
        assert "Separate authorization is required" in checkpoint
    assert checkpoints[0].name in index


def test_ty_configuration_keeps_meaningful_error_rules() -> None:
    """Type-check success cannot come from disabling core correctness checks."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "tool"
    ]["ty"]
    for rule in (
        "unresolved-import",
        "unresolved-reference",
        "invalid-argument-type",
        "invalid-assignment",
        "invalid-return-type",
        "possibly-missing-attribute",
    ):
        assert config["rules"][rule] == "error"
    assert config["environment"]["python-version"] == "3.12"
    assert config["src"]["include"] == ["roadmap", "tests"]
    assert config["src"]["exclude"] == ["tests/policy/fixtures/architecture"]


@pytest.mark.parametrize(
    "source, diagnostic",
    [
        ("def value() -> int:\n    return 'wrong'\n", "invalid-return-type"),
        ("import missing_roadmap_gate_dependency\n", "unresolved-import"),
        (
            "def upper(value: str | None) -> str:\n    return value.upper()\n",
            "unresolved-attribute",
        ),
    ],
)
def test_ty_rejects_known_correctness_errors(tmp_path, source, diagnostic):
    """The sole type gate must actually fail on representative mistakes."""
    path = tmp_path / "incorrect.py"
    path.write_text(source)
    executable = shutil.which("ty")
    assert executable is not None
    result = subprocess.run(
        [executable, "check", "--project", str(ROOT), str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert diagnostic in result.stdout + result.stderr


def run_gate(root):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "tests/policy/architecture_checker.py"),
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


def fixture_tree(tmp_path, fixture=None):
    shutil.copytree(FIXTURES / "valid" / "roadmap", tmp_path / "roadmap")
    if fixture:
        shutil.copytree(
            FIXTURES / fixture / "roadmap", tmp_path / "roadmap", dirs_exist_ok=True
        )
    # Old AST fixtures referenced these missing modules. Materialize them so
    # Grimp can test real graph edges instead of ignoring unresolved imports.
    for relative in ("adapters/inbound/http", "adapters/outbound/sqlite"):
        (tmp_path / "roadmap" / relative).mkdir(parents=True, exist_ok=True)
    for directory in [tmp_path / "roadmap", *(tmp_path / "roadmap").rglob("*")]:
        if directory.is_dir():
            (directory / "__init__.py").touch()
    for name in (".importlinter", "architecture.toml", "architecture-baseline.toml"):
        shutil.copy2(ROOT / name, tmp_path / name)
    return tmp_path


@pytest.mark.parametrize("fixture", [None, "requirements_domain_stub"])
def test_allowed_architecture_and_new_features_pass(tmp_path, fixture):
    result = run_gate(fixture_tree(tmp_path, fixture))
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "fixture",
    [
        "domain_dependencies",
        "application_dependencies",
        "inbound_adapter_dependencies",
        "outbound_adapter_dependencies",
        "bootstrap_only_adapter_wiring",
        "zone_cycle",
        "removed_namespace",
    ],
)
def test_every_original_negative_fixture_still_fails(tmp_path, fixture):
    result = run_gate(fixture_tree(tmp_path, "invalid/" + fixture))
    assert result.returncode == 1, result.stdout + result.stderr
    assert (
        "BROKEN" in result.stdout
        or "-dependencies:" in result.stdout
        or "removed-namespace:" in result.stdout
    )


@pytest.mark.parametrize(
    "source",
    [
        "from ..outbound import sqlite",  # Relative imports are resolved by Grimp.
        "from roadmap.adapters.outbound import sqlite",  # Import-from aliases.
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from roadmap.adapters.outbound import sqlite",
    ],
)
def test_alias_relative_and_type_checking_imports_cannot_evade_wiring(tmp_path, source):
    root = fixture_tree(tmp_path)
    (root / "roadmap/adapters/inbound/bad.py").write_text(source)
    result = run_gate(root)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "BROKEN" in result.stdout


def test_real_repository_passes():
    result = run_gate(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_retired_migration_baseline_cannot_be_broadened(tmp_path):
    root = fixture_tree(tmp_path)
    (root / "architecture-baseline.toml").write_text(
        'version = 1\nviolations = ["exception"]\n'
    )
    result = run_gate(root)
    assert result.returncode != 0
    assert "permits no exceptions" in result.stderr


@pytest.mark.parametrize(
    "module,source",
    [
        ("domain/bad.py", "import uninstalled_framework"),
        ("application/bad.py", "import uninstalled_framework"),
        ("application/bad.py", "from .. import common"),
        ("domain/bad.py", "from .. import utility"),
        ("domain/__init__.py", "from roadmap import utility"),
        ("adapters/inbound/cli/bad.py", "from .... import utility"),
    ],
)
def test_unknown_dependencies_and_relative_retired_imports_fail(
    tmp_path, module, source
):
    root = fixture_tree(tmp_path)
    (root / "roadmap" / module).write_text(source)
    result = run_gate(root)
    assert result.returncode == 1, result.stdout + result.stderr
    assert (
        "-dependencies:" in result.stdout
        or "unzoned-dependency:" in result.stdout
        or "removed-namespace:" in result.stdout
    )
