#!/usr/bin/env python3
"""Generate a comprehensive baseline report of all layer violations.

This script uses import-linter to detect violations across all 6-layer architecture
and produces a CSV report for tracking remediation progress.
"""

import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple


class Violation(NamedTuple):
    """A single import violation."""

    from_module: str
    to_module: str
    from_layer: str
    to_layer: str
    violation_type: str


def get_layer(module: str) -> str:
    """Determine the layer of a module.

    6-layer architecture:
    1. Domain (roadmap/domain)
    2. Common (roadmap/common)
    3. Infrastructure (roadmap/infrastructure)
    4. Core (roadmap/core)
    5. Adapters (roadmap/adapters)
    6. Presentation (roadmap/adapters/cli + roadmap/adapters/api)
    """
    if module.startswith("roadmap.domain"):
        return "Domain"
    elif module.startswith("roadmap.common"):
        return "Common"
    elif module.startswith("roadmap.infrastructure"):
        return "Infrastructure"
    elif module.startswith("roadmap.core"):
        return "Core"
    elif module.startswith("roadmap.adapters"):
        # Further distinguish between CLI and other adapters
        if ".cli" in module:
            return "Presentation (CLI)"
        elif ".api" in module:
            return "Presentation (API)"
        else:
            return "Adapters"
    else:
        return "Unknown"


def parse_linter_output() -> list[Violation]:
    """Parse import-linter output to extract violations."""
    result = subprocess.run(
        ["poetry", "run", "lint-imports"],
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    violations = []

    # Parse the violation output
    # Format: "- source -> target (l.XXX)"
    lines = output.split("\n")

    for line in lines:
        # Check for contract header
        if line.strip().startswith("- "):
            # This is a violation line
            # Format: "- source -> target -> ... (l.XXX)"
            parts = line.strip()[2:].split(" -> ")

            # Extract the final target and source
            if len(parts) >= 2:
                # The first part is the source
                source = parts[0].strip()

                # The last part is the target (may have line number)
                target_part = parts[-1].strip()
                # Remove line number if present
                target = re.sub(r"\s+\(l\.\d+\)$", "", target_part)

                violations.append(
                    Violation(
                        from_module=source,
                        to_module=target,
                        from_layer=get_layer(source),
                        to_layer=get_layer(target),
                        violation_type="forbidden_import",
                    )
                )

    return violations


def generate_report(violations: list[Violation]) -> None:
    """Generate and save a comprehensive violation report."""

    # Group violations by contract (from_layer -> to_layer)
    by_contract = defaultdict(list)
    for v in violations:
        contract = f"{v.from_layer} -> {v.to_layer}"
        by_contract[contract].append(v)

    # Print summary
    print("\n" + "=" * 80)
    print("LAYER VIOLATION BASELINE REPORT")
    print("=" * 80)

    print(f"\nTotal Violations: {len(violations)}")
    print(f"Unique Contracts: {len(by_contract)}")

    # Print by contract
    print("\n" + "-" * 80)
    print("VIOLATIONS BY LAYER CONTRACT")
    print("-" * 80)

    for contract in sorted(by_contract.keys()):
        violations_in_contract = by_contract[contract]
        print(f"\n{contract}: {len(violations_in_contract)} violations")

        # Group by source module
        by_source = defaultdict(list)
        for v in violations_in_contract:
            by_source[v.from_module].append(v.to_module)

        for source_module in sorted(by_source.keys()):
            targets = sorted(set(by_source[source_module]))
            print(f"  {source_module}")
            for target in targets:
                print(f"    -> {target}")

    # Save detailed CSV
    csv_path = Path("violation_baseline.csv")
    with open(csv_path, "w") as f:
        f.write("from_module,to_module,from_layer,to_layer,violation_type,status\n")
        for v in sorted(violations, key=lambda x: (x.from_layer, x.from_module)):
            f.write(
                f"{v.from_module},{v.to_module},{v.from_layer},{v.to_layer},{v.violation_type},grandfathered\n"
            )

    print(f"\n✓ Detailed report saved to: {csv_path}")
    print(f"  {len(violations)} violations recorded")


if __name__ == "__main__":
    violations = parse_linter_output()
    generate_report(violations)
