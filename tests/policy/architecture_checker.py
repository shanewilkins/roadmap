"""Import Linter gate plus narrow namespace and core dependency guards.

Stock contracts own graph traversal, layers, and adapter isolation. This guard
only checks imports that Grimp omits (uninstalled dependencies/removed modules)
and rejects retired namespaces even when nobody imports them.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

ZONE_PREFIXES = (
    "roadmap.domain",
    "roadmap.application",
    "roadmap.adapters.inbound",
    "roadmap.adapters.outbound",
    "roadmap.bootstrap",
)


def matches(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + ".")


def guard_violations(root: Path) -> tuple[str, ...]:
    policy = tomllib.loads((root / "architecture.toml").read_text())
    namespaces = policy["guards"]["removed_namespaces"]
    violations: set[str] = set()
    for path in (root / "roadmap").rglob("*.py"):
        module = ".".join(path.relative_to(root).with_suffix("").parts).removesuffix(
            ".__init__"
        )
        for namespace in namespaces:
            if module == namespace or module.startswith(namespace + "."):
                violations.add(f"removed-namespace: {module} -> {namespace}")
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                package = (
                    module if path.name == "__init__.py" else module.rpartition(".")[0]
                )
                target = (
                    importlib.util.resolve_name(
                        "." * node.level + (node.module or ""), package
                    )
                    if node.level
                    else (node.module or "")
                )
                targets = [
                    *([] if target in {"roadmap", "roadmap.adapters"} else [target]),
                    *(f"{target}.{alias.name}" for alias in node.names),
                ]
            for target in targets:
                if (
                    any(matches(module, zone) for zone in ZONE_PREFIXES[:-1])
                    and matches(target, "roadmap")
                    and not any(matches(target, zone) for zone in ZONE_PREFIXES)
                ):
                    violations.add(f"unzoned-dependency: {module} -> {target}")
                for namespace in namespaces:
                    if target == namespace or target.startswith(namespace + "."):
                        violations.add(f"removed-namespace: {module} -> {target}")
                layer = next(
                    (
                        name
                        for name in ("domain", "application")
                        if module == f"roadmap.{name}"
                        or module.startswith(f"roadmap.{name}.")
                    ),
                    None,
                )
                if layer and target.split(".")[0] not in sys.stdlib_module_names | {
                    "__future__",
                    "roadmap",
                }:
                    violations.add(f"{layer}-dependencies: {module} -> {target}")
    return tuple(sorted(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    baseline = tomllib.loads((root / "architecture-baseline.toml").read_text())
    if baseline != {"version": 1, "violations": []}:
        raise ValueError("The completed architecture migration permits no exceptions")
    violations = guard_violations(root)
    for violation in violations:
        print(violation, flush=True)
    result = subprocess.run(
        [
            str(Path(sys.executable).with_name("lint-imports")),
            "--config",
            str(root / ".importlinter"),
            "--no-cache",
            "--no-logo",
        ],
        cwd=root,
        check=False,
    )
    return int(bool(violations) or result.returncode != 0)


if __name__ == "__main__":
    raise SystemExit(main())
