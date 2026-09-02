"""AST-based enforcement for Roadmap's target dependency architecture."""

from __future__ import annotations

import argparse
import ast
import sys
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RULE_IDS = {
    "domain-dependencies",
    "application-dependencies",
    "inbound-adapter-dependencies",
    "outbound-adapter-dependencies",
    "bootstrap-only-adapter-wiring",
    "zone-cycle",
    "removed-namespace",
}
RULE_KINDS = {
    "zone_dependencies",
    "adapter_dependencies",
    "bootstrap_only_wiring",
    "zone_cycle",
    "removed_namespace",
}
BASELINE_FIELDS = {
    "source",
    "target",
    "rule",
    "reason",
    "owner",
    "removal_phase",
}
POLICY_TOP_LEVEL_FIELDS = {"architecture", "zones", "rules"}
ARCHITECTURE_FIELDS = {
    "version",
    "current_phase",
    "final_phase",
    "production_root",
    "baseline",
}
ZONE_FIELDS = {"id", "prefix", "boundary_depth"}
RULE_FIELDS = {
    "id",
    "kind",
    "source_zone",
    "allowed_zones",
    "allow_standard_library",
    "allow_external",
    "active_phase",
    "namespaces",
}
EXPECTED_RULE_IDENTITIES = {
    "domain-dependencies": ("zone_dependencies", "domain"),
    "application-dependencies": ("zone_dependencies", "application"),
    "inbound-adapter-dependencies": ("adapter_dependencies", "inbound"),
    "outbound-adapter-dependencies": ("adapter_dependencies", "outbound"),
    "bootstrap-only-adapter-wiring": ("bootstrap_only_wiring", None),
    "zone-cycle": ("zone_cycle", None),
    "removed-namespace": ("removed_namespace", None),
}


class ArchitectureConfigurationError(ValueError):
    """The policy or exception baseline is malformed."""


@dataclass(frozen=True, order=True)
class Violation:
    """One exact import or namespace violation."""

    source: str
    target: str
    rule: str

    @property
    def key(self) -> tuple[str, str, str]:
        """Return the stable baseline identity."""
        return self.source, self.target, self.rule

    def render(self) -> str:
        """Return one deterministic diagnostic line."""
        return f"{self.rule}: {self.source} -> {self.target}"


@dataclass(frozen=True)
class BaselineEntry:
    """A reviewed temporary exception for one current violation."""

    source: str
    target: str
    rule: str
    reason: str
    owner: str
    removal_phase: int

    @property
    def key(self) -> tuple[str, str, str]:
        """Return the exact violation identity."""
        return self.source, self.target, self.rule


@dataclass(frozen=True)
class Zone:
    """One target architecture namespace."""

    id: str
    prefix: str
    boundary_depth: int = 0


@dataclass(frozen=True)
class Rule:
    """One configured dependency rule."""

    id: str
    kind: str
    source_zone: str | None = None
    allowed_zones: tuple[str, ...] = ()
    allow_standard_library: bool = False
    allow_external: bool = False
    active_phase: int | None = None
    namespaces: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArchitecturePolicy:
    """Parsed architecture rules."""

    version: int
    current_phase: int
    final_phase: int
    production_root: str
    baseline: str
    zones: tuple[Zone, ...]
    rules: tuple[Rule, ...]

    def rule(self, kind: str, source_zone: str | None = None) -> Rule:
        """Return the unique rule matching a kind and optional source zone."""
        matches = [
            rule
            for rule in self.rules
            if rule.kind == kind
            and (source_zone is None or rule.source_zone == source_zone)
        ]
        if len(matches) != 1:
            raise ArchitectureConfigurationError(
                f"Expected one {kind!r} rule for {source_zone!r}; found {len(matches)}"
            )
        return matches[0]


@dataclass(frozen=True)
class ImportRecord:
    """One normalized import edge."""

    source: str
    target: str


@dataclass(frozen=True)
class CheckResult:
    """Comparison between actual violations and the reviewed baseline."""

    violations: tuple[Violation, ...]
    new: tuple[Violation, ...]
    stale: tuple[BaselineEntry, ...]

    @property
    def passed(self) -> bool:
        """Return whether the exact baseline matches the current tree."""
        return not self.new and not self.stale

    def render(self) -> str:
        """Render deterministic actionable diagnostics."""
        lines: list[str] = []
        if self.new:
            lines.append("Unbaselined architecture violations:")
            lines.extend(f"  {item.render()}" for item in self.new)
        if self.stale:
            lines.append("Stale architecture baseline entries:")
            lines.extend(
                f"  {item.rule}: {item.source} -> {item.target}" for item in self.stale
            )
        return "\n".join(lines) or "Architecture contract passed."


def _table(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ArchitectureConfigurationError(f"{key!r} must be a TOML table")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArchitectureConfigurationError(f"{label} must be a non-empty string")
    return value


def _string_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ArchitectureConfigurationError(f"{label} must be a string array")
    return tuple(value)


def load_policy(path: Path) -> ArchitecturePolicy:
    """Load and strictly validate the machine-readable architecture policy."""
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if set(data) != POLICY_TOP_LEVEL_FIELDS:
        raise ArchitectureConfigurationError(
            f"policy must contain exactly {sorted(POLICY_TOP_LEVEL_FIELDS)}"
        )
    architecture = _table(data, "architecture")
    if set(architecture) != ARCHITECTURE_FIELDS:
        raise ArchitectureConfigurationError(
            f"architecture must contain exactly {sorted(ARCHITECTURE_FIELDS)}"
        )
    version = architecture.get("version")
    current_phase = architecture.get("current_phase")
    final_phase = architecture.get("final_phase")
    if version != 1:
        raise ArchitectureConfigurationError("architecture.version must be 1")
    if not isinstance(current_phase, int) or current_phase < 1:
        raise ArchitectureConfigurationError(
            "architecture.current_phase must be a positive integer"
        )
    if not isinstance(final_phase, int) or final_phase < current_phase:
        raise ArchitectureConfigurationError(
            "architecture.final_phase must not precede current_phase"
        )

    raw_zones = data.get("zones")
    if not isinstance(raw_zones, list) or not raw_zones:
        raise ArchitectureConfigurationError("zones must be a non-empty table array")
    for index, item in enumerate(raw_zones):
        if not isinstance(item, dict) or not {"id", "prefix"} <= set(item):
            raise ArchitectureConfigurationError(
                f"zone {index} must contain id and prefix"
            )
        if not set(item) <= ZONE_FIELDS:
            raise ArchitectureConfigurationError(
                f"zone {index} contains unsupported fields"
            )
    zones = tuple(
        Zone(
            id=_string(item.get("id"), "zones.id"),
            prefix=_string(item.get("prefix"), "zones.prefix"),
            boundary_depth=item.get("boundary_depth", 0),
        )
        for item in raw_zones
    )
    if any(
        not isinstance(zone.boundary_depth, int) or zone.boundary_depth < 0
        for zone in zones
    ):
        raise ArchitectureConfigurationError(
            "zones.boundary_depth must be a non-negative integer"
        )
    zone_ids = {zone.id for zone in zones}
    if len(zone_ids) != len(zones) or len({zone.prefix for zone in zones}) != len(
        zones
    ):
        raise ArchitectureConfigurationError("zone IDs and prefixes must be unique")
    if zone_ids != {"domain", "application", "inbound", "outbound", "bootstrap"}:
        raise ArchitectureConfigurationError("the five target zones must be declared")

    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ArchitectureConfigurationError("rules must be a non-empty table array")
    rules: list[Rule] = []
    for index, item in enumerate(raw_rules):
        if not isinstance(item, dict) or not {"id", "kind"} <= set(item):
            raise ArchitectureConfigurationError(
                f"rule {index} must contain id and kind"
            )
        if not set(item) <= RULE_FIELDS:
            raise ArchitectureConfigurationError(
                f"rule {index} contains unsupported fields"
            )
        rule = Rule(
            id=_string(item.get("id"), "rules.id"),
            kind=_string(item.get("kind"), "rules.kind"),
            source_zone=item.get("source_zone"),
            allowed_zones=_string_list(
                item.get("allowed_zones", []), "rules.allowed_zones"
            ),
            allow_standard_library=item.get("allow_standard_library", False),
            allow_external=item.get("allow_external", False),
            active_phase=item.get("active_phase"),
            namespaces=_string_list(item.get("namespaces", []), "rules.namespaces"),
        )
        if rule.kind not in RULE_KINDS:
            raise ArchitectureConfigurationError(f"unknown rule kind: {rule.kind}")
        if rule.source_zone is not None and rule.source_zone not in zone_ids:
            raise ArchitectureConfigurationError(
                f"unknown source zone in {rule.id}: {rule.source_zone}"
            )
        if not set(rule.allowed_zones) <= zone_ids:
            raise ArchitectureConfigurationError(
                f"unknown allowed zone in {rule.id}: {rule.allowed_zones}"
            )
        if not isinstance(rule.allow_standard_library, bool) or not isinstance(
            rule.allow_external, bool
        ):
            raise ArchitectureConfigurationError(
                f"boolean flags are malformed for {rule.id}"
            )
        if rule.active_phase is not None and (
            type(rule.active_phase) is not int
            or not 0 <= rule.active_phase <= final_phase
        ):
            raise ArchitectureConfigurationError(
                f"active_phase is malformed for {rule.id}"
            )
        rules.append(rule)
    if {rule.id for rule in rules} != RULE_IDS or len(rules) != len(RULE_IDS):
        raise ArchitectureConfigurationError(
            "architecture rules must contain every required ID exactly once"
        )
    for rule in rules:
        if (rule.kind, rule.source_zone) != EXPECTED_RULE_IDENTITIES[rule.id]:
            raise ArchitectureConfigurationError(
                f"rule identity is malformed for {rule.id}"
            )

    return ArchitecturePolicy(
        version=version,
        current_phase=current_phase,
        final_phase=final_phase,
        production_root=_string(
            architecture.get("production_root"), "architecture.production_root"
        ),
        baseline=_string(architecture.get("baseline"), "architecture.baseline"),
        zones=zones,
        rules=tuple(rules),
    )


def load_baseline(path: Path, policy: ArchitecturePolicy) -> tuple[BaselineEntry, ...]:
    """Load a strict exact exception baseline."""
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if data.get("version") != 1:
        raise ArchitectureConfigurationError("baseline version must be 1")
    raw_entries = data.get("violations")
    if not isinstance(raw_entries, list):
        raise ArchitectureConfigurationError("violations must be a TOML table array")

    entries: list[BaselineEntry] = []
    for index, item in enumerate(raw_entries):
        if set(item) != BASELINE_FIELDS:
            raise ArchitectureConfigurationError(
                f"baseline entry {index} must contain exactly {sorted(BASELINE_FIELDS)}"
            )
        entry = BaselineEntry(
            source=_string(item["source"], f"violations[{index}].source"),
            target=_string(item["target"], f"violations[{index}].target"),
            rule=_string(item["rule"], f"violations[{index}].rule"),
            reason=_string(item["reason"], f"violations[{index}].reason"),
            owner=_string(item["owner"], f"violations[{index}].owner"),
            removal_phase=item["removal_phase"],
        )
        if entry.rule not in RULE_IDS:
            raise ArchitectureConfigurationError(
                f"unknown rule in baseline entry {index}: {entry.rule}"
            )
        if len(entry.reason) < 20:
            raise ArchitectureConfigurationError(
                f"baseline entry {index} needs a human-readable reason"
            )
        if entry.owner != "Maintainer":
            raise ArchitectureConfigurationError(
                f"baseline entry {index} needs the accountable owner"
            )
        if not isinstance(entry.removal_phase, int) or not (
            policy.current_phase < entry.removal_phase <= policy.final_phase
        ):
            raise ArchitectureConfigurationError(
                f"baseline entry {index} has an invalid removal phase"
            )
        entries.append(entry)

    keys = [entry.key for entry in entries]
    if len(set(keys)) != len(keys):
        raise ArchitectureConfigurationError("baseline contains duplicate entries")
    if keys != sorted(keys):
        raise ArchitectureConfigurationError("baseline entries must be sorted")
    return tuple(entries)


def _module_name(path: Path, production_root: Path) -> tuple[str, bool]:
    relative = path.relative_to(production_root.parent)
    parts = list(relative.with_suffix("").parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts.pop()
    return ".".join(parts), is_package


def _resolve_relative(
    source: str, is_package: bool, level: int, module: str | None
) -> str:
    package_parts = source.split(".") if is_package else source.split(".")[:-1]
    keep = len(package_parts) - (level - 1)
    base = package_parts[: max(keep, 0)]
    if module:
        base.extend(module.split("."))
    return ".".join(base)


def collect_imports(production_root: Path) -> tuple[set[str], tuple[ImportRecord, ...]]:
    """Parse Python files and return module names and normalized import edges."""
    modules: set[str] = set()
    records: set[ImportRecord] = set()
    for path in sorted(production_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        source, is_package = _module_name(path, production_root)
        modules.add(source)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as error:
            raise ArchitectureConfigurationError(
                f"cannot parse {path}: {error}"
            ) from error
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                records.update(ImportRecord(source, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    target = _resolve_relative(
                        source, is_package, node.level, node.module
                    )
                else:
                    target = node.module or ""
                if target:
                    records.add(ImportRecord(source, target))
    return modules, tuple(sorted(records, key=lambda item: (item.source, item.target)))


def _matches(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def _zone_for(module: str, policy: ArchitecturePolicy) -> Zone | None:
    matches = [zone for zone in policy.zones if _matches(module, zone.prefix)]
    if not matches:
        return None
    return max(matches, key=lambda zone: len(zone.prefix))


def _boundary(module: str, zone: Zone) -> str | None:
    remainder = module.removeprefix(zone.prefix).lstrip(".")
    parts = remainder.split(".") if remainder else []
    if len(parts) < zone.boundary_depth:
        return None
    return ".".join(parts[: zone.boundary_depth])


def _is_standard_library(module: str) -> bool:
    return module.split(".", 1)[0] in sys.stdlib_module_names | {"__future__"}


def _dependency_violations(
    imports: Sequence[ImportRecord], policy: ArchitecturePolicy
) -> set[Violation]:
    violations: set[Violation] = set()
    for record in imports:
        source_zone = _zone_for(record.source, policy)
        if source_zone is None:
            continue
        applicable = [
            rule
            for rule in policy.rules
            if rule.kind in {"zone_dependencies", "adapter_dependencies"}
            and rule.source_zone == source_zone.id
        ]
        if not applicable:
            continue
        rule = applicable[0]
        target_zone = _zone_for(record.target, policy)
        allowed = False
        if _is_standard_library(record.target):
            allowed = rule.allow_standard_library
        elif not record.target.startswith("roadmap"):
            allowed = rule.allow_external
        elif target_zone and target_zone.id in rule.allowed_zones:
            allowed = True
        elif target_zone and target_zone.id == source_zone.id:
            allowed = rule.kind == "zone_dependencies" or _boundary(
                record.source, source_zone
            ) == _boundary(record.target, target_zone)
        if not allowed:
            violations.add(Violation(record.source, record.target, rule.id))
    return violations


def _bootstrap_wiring_violations(
    imports: Sequence[ImportRecord], policy: ArchitecturePolicy
) -> set[Violation]:
    rule = policy.rule("bootstrap_only_wiring")
    violations: set[Violation] = set()
    for record in imports:
        source_zone = _zone_for(record.source, policy)
        target_zone = _zone_for(record.target, policy)
        if target_zone is None or target_zone.id not in {"inbound", "outbound"}:
            continue
        if source_zone and source_zone.id == "bootstrap":
            continue
        if (
            source_zone
            and source_zone.id == target_zone.id
            and _boundary(record.source, source_zone)
            == _boundary(record.target, target_zone)
        ):
            continue
        violations.add(Violation(record.source, record.target, rule.id))
    return violations


def _path_exists(start: str, target: str, graph: Mapping[str, set[str]]) -> bool:
    pending = [start]
    visited: set[str] = set()
    while pending:
        node = pending.pop()
        if node == target:
            return True
        if node in visited:
            continue
        visited.add(node)
        pending.extend(graph.get(node, set()) - visited)
    return False


def _cycle_violations(
    imports: Sequence[ImportRecord], policy: ArchitecturePolicy
) -> set[Violation]:
    rule = policy.rule("zone_cycle")
    zone_edges: set[tuple[str, str]] = set()
    architectural: list[tuple[ImportRecord, str, str]] = []
    for record in imports:
        source_zone = _zone_for(record.source, policy)
        target_zone = _zone_for(record.target, policy)
        if not source_zone or not target_zone or source_zone.id == target_zone.id:
            continue
        zone_edges.add((source_zone.id, target_zone.id))
        architectural.append((record, source_zone.id, target_zone.id))
    graph: dict[str, set[str]] = {}
    for source, target in zone_edges:
        graph.setdefault(source, set()).add(target)
    return {
        Violation(record.source, record.target, rule.id)
        for record, source, target in architectural
        if _path_exists(target, source, graph)
    }


def _removed_namespace_violations(
    modules: Iterable[str],
    imports: Sequence[ImportRecord],
    policy: ArchitecturePolicy,
    current_phase: int,
) -> set[Violation]:
    rule = policy.rule("removed_namespace")
    if rule.active_phase is None or current_phase < rule.active_phase:
        return set()
    violations: set[Violation] = set()
    for module in modules:
        for namespace in rule.namespaces:
            if _matches(module, namespace):
                violations.add(Violation(module, namespace, rule.id))
    for record in imports:
        for namespace in rule.namespaces:
            if _matches(record.target, namespace):
                violations.add(Violation(record.source, record.target, rule.id))
    return violations


def find_violations(
    production_root: Path,
    policy: ArchitecturePolicy,
    *,
    current_phase: int | None = None,
) -> tuple[Violation, ...]:
    """Return every target-architecture violation in deterministic order."""
    modules, imports = collect_imports(production_root)
    phase = policy.current_phase if current_phase is None else current_phase
    violations = (
        _dependency_violations(imports, policy)
        | _bootstrap_wiring_violations(imports, policy)
        | _cycle_violations(imports, policy)
        | _removed_namespace_violations(modules, imports, policy, phase)
    )
    return tuple(sorted(violations))


def compare_baseline(
    violations: Sequence[Violation], baseline: Sequence[BaselineEntry]
) -> CheckResult:
    """Compare actual violations to exact reviewed exceptions."""
    actual = {violation.key: violation for violation in violations}
    expected = {entry.key: entry for entry in baseline}
    return CheckResult(
        violations=tuple(sorted(violations)),
        new=tuple(actual[key] for key in sorted(actual.keys() - expected.keys())),
        stale=tuple(expected[key] for key in sorted(expected.keys() - actual.keys())),
    )


def check_repository(root: Path) -> CheckResult:
    """Run the checked-in policy and baseline against a repository root."""
    policy = load_policy(root / "architecture.toml")
    baseline = load_baseline(root / policy.baseline, policy)
    violations = find_violations(root / policy.production_root, policy)
    return compare_baseline(violations, baseline)


def main() -> int:
    """Run the architecture gate without converting failures to success."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--without-baseline",
        action="store_true",
        help="print every current violation and fail when any exist",
    )
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    policy = load_policy(root / "architecture.toml")
    violations = find_violations(root / policy.production_root, policy)
    if arguments.without_baseline:
        for violation in violations:
            print(violation.render())
        return int(bool(violations))
    result = compare_baseline(violations, load_baseline(root / policy.baseline, policy))
    print(result.render())
    return int(not result.passed)


if __name__ == "__main__":
    raise SystemExit(main())
