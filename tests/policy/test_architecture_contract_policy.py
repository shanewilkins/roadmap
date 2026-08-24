"""Executable policy tests for Roadmap's target architecture."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.policy.architecture_checker import (
    ArchitectureConfigurationError,
    BaselineEntry,
    Violation,
    check_repository,
    compare_baseline,
    find_violations,
    load_baseline,
    load_policy,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures" / "architecture"
POLICY = load_policy(ROOT / "architecture.toml")
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

    assert phases == set(range(POLICY.final_phase + 1))
    assert f"Execution status: Phase {POLICY.current_phase} checkpoint passed" in header
    assert f"approval before Phase {POLICY.current_phase + 1}" in header
    assert f"Accepted checkpoint: Phase {POLICY.current_phase}" in index
    assert f"Final planned implementation phase: Phase {POLICY.final_phase}" in index

    checkpoints = sorted(CHECKPOINTS.glob(f"phase-{POLICY.current_phase}-*.md"))
    assert len(checkpoints) == 1
    checkpoint = checkpoints[0].read_text(encoding="utf-8")
    assert "Decision: **GO**" in checkpoint
    assert f"before Phase {POLICY.current_phase + 1}" in checkpoint
    assert checkpoints[0].name in index


def test_valid_fixture_obeys_every_architecture_rule() -> None:
    """The complete allowed dependency direction produces no violations."""
    assert find_violations(FIXTURES / "valid" / "roadmap", POLICY) == ()


@pytest.mark.parametrize(
    ("fixture", "phase", "expected"),
    [
        (
            "domain_dependencies",
            2,
            Violation("roadmap.domain.bad", "click", "domain-dependencies"),
        ),
        (
            "application_dependencies",
            2,
            Violation(
                "roadmap.application.bad", "structlog", "application-dependencies"
            ),
        ),
        (
            "inbound_adapter_dependencies",
            2,
            Violation(
                "roadmap.adapters.inbound.cli.bad",
                "roadmap.adapters.inbound.http",
                "inbound-adapter-dependencies",
            ),
        ),
        (
            "outbound_adapter_dependencies",
            2,
            Violation(
                "roadmap.adapters.outbound.documents.bad",
                "roadmap.adapters.outbound.sqlite",
                "outbound-adapter-dependencies",
            ),
        ),
        (
            "bootstrap_only_adapter_wiring",
            2,
            Violation(
                "roadmap.legacy",
                "roadmap.adapters.outbound.sqlite",
                "bootstrap-only-adapter-wiring",
            ),
        ),
        (
            "zone_cycle",
            2,
            Violation("roadmap.domain.bad", "roadmap.application", "zone-cycle"),
        ),
        (
            "removed_namespace",
            12,
            Violation(
                "roadmap.adapters.sync.legacy",
                "roadmap.adapters.sync",
                "removed-namespace",
            ),
        ),
    ],
)
def test_each_focused_invalid_fixture_reports_exact_violation(
    fixture: str, phase: int, expected: Violation
) -> None:
    """Every configured rule is proven by a focused negative fixture."""
    violations = find_violations(
        FIXTURES / "invalid" / fixture / "roadmap",
        POLICY,
        current_phase=phase,
    )
    assert expected in violations


def test_unchanged_production_tree_matches_only_the_exact_reviewed_baseline() -> None:
    """The current migration debt passes only through reviewed exact entries."""
    result = check_repository(ROOT)
    assert result.passed, result.render()
    assert result.violations == ()


def test_unused_baseline_entry_is_stale() -> None:
    """Exceptions cannot survive after their violating import disappears."""
    violations = find_violations(ROOT / POLICY.production_root, POLICY)
    baseline = load_baseline(ROOT / POLICY.baseline, POLICY)
    unused = BaselineEntry(
        source="roadmap.domain.removed",
        target="click",
        rule="domain-dependencies",
        reason="A deliberately unused entry for the stale-baseline negative proof.",
        owner="Maintainer",
        removal_phase=4,
    )
    result = compare_baseline(violations, [*baseline, unused])
    assert result.stale == (unused,)
    assert not result.passed


@pytest.mark.parametrize(
    "body",
    [
        """version = 1
[[violations]]
source = "roadmap.domain.bad"
target = "click"
rule = "domain-dependencies"
reason = "Missing required ownership and removal phase fields."
""",
        """version = 1
[[violations]]
source = "roadmap.domain.bad"
target = "click"
rule = "domain-dependencies"
reason = "First duplicate architecture exception for a negative proof."
owner = "Maintainer"
removal_phase = 4
[[violations]]
source = "roadmap.domain.bad"
target = "click"
rule = "domain-dependencies"
reason = "Second duplicate architecture exception for a negative proof."
owner = "Maintainer"
removal_phase = 4
        """,
    ],
    ids=["missing-fields", "duplicate"],
)
def test_malformed_or_duplicate_baseline_fails(tmp_path: Path, body: str) -> None:
    """The exception file permits no wildcard, malformed, or duplicate rows."""
    path = tmp_path / "baseline.toml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ArchitectureConfigurationError):
        load_baseline(path, POLICY)


def test_removed_namespace_rule_is_inactive_before_its_declared_phase() -> None:
    """Scheduled removal does not rewrite the unchanged Phase 2 tree."""
    fixture = FIXTURES / "invalid" / "removed_namespace" / "roadmap"
    assert find_violations(fixture, POLICY, current_phase=11) == ()


def test_pyright_configuration_keeps_meaningful_error_rules() -> None:
    """Pyright success cannot come from disabling core correctness checks."""
    config = json.loads((ROOT / "pyrightconfig.json").read_text(encoding="utf-8"))
    assert config["typeCheckingMode"] in {"basic", "standard", "strict"}
    for rule in (
        "reportMissingImports",
        "reportUndefinedVariable",
        "reportGeneralTypeIssues",
        "reportOptionalMemberAccess",
        "reportOptionalSubscript",
    ):
        assert config[rule] == "error"
    assert "extraPaths" not in config
    assert config["venv"] == ".venv"
    assert config["exclude"][-1] == "tests/policy/fixtures/architecture/invalid"


def test_policy_rejects_a_nonfuture_removal_phase(tmp_path: Path) -> None:
    """Removal phases are exact future obligations, never open-ended patterns."""
    path = tmp_path / "baseline.toml"
    path.write_text(
        f"""version = 1
[[violations]]
source = "roadmap.domain.bad"
target = "click"
rule = "domain-dependencies"
reason = "This exception deliberately has a nonfuture removal phase."
owner = "Maintainer"
removal_phase = {POLICY.current_phase}
""",
        encoding="utf-8",
    )
    with pytest.raises(ArchitectureConfigurationError, match="removal phase"):
        load_baseline(path, POLICY)


def test_policy_rejects_unreviewed_configuration_fields(tmp_path: Path) -> None:
    """Policy typos cannot silently weaken or alter the declared contract."""
    body = (ROOT / "architecture.toml").read_text(encoding="utf-8")
    path = tmp_path / "architecture.toml"
    path.write_text(body.replace("version = 1", "version = 1\nignored = true", 1))
    with pytest.raises(ArchitectureConfigurationError, match="exactly"):
        load_policy(path)


def test_policy_rejects_a_rule_id_bound_to_the_wrong_kind(tmp_path: Path) -> None:
    """Required IDs cannot pass validation while enforcing a different rule."""
    body = (ROOT / "architecture.toml").read_text(encoding="utf-8")
    path = tmp_path / "architecture.toml"
    path.write_text(
        body.replace('kind = "zone_cycle"', 'kind = "bootstrap_only_wiring"', 1),
        encoding="utf-8",
    )
    with pytest.raises(ArchitectureConfigurationError, match="identity"):
        load_policy(path)


def test_checker_process_returns_failure_for_a_real_violation(tmp_path: Path) -> None:
    """No command wrapper converts an architecture failure into success."""
    shutil.copy2(ROOT / "architecture.toml", tmp_path / "architecture.toml")
    (tmp_path / "architecture-baseline.toml").write_text(
        "version = 1\nviolations = []\n", encoding="utf-8"
    )
    shutil.copytree(
        FIXTURES / "invalid" / "domain_dependencies" / "roadmap",
        tmp_path / "roadmap",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("architecture_checker.py")),
            "--root",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "domain-dependencies: roadmap.domain.bad -> click" in result.stdout
