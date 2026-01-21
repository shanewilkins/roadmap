#!/usr/bin/env python3
"""
Enforce cyclomatic complexity thresholds.
Fails if any function exceeds the configured maximum complexity.
"""

import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class ComplexityViolation:
    """Represents a function that violates complexity threshold."""

    module: str
    function: str
    line: int
    cc_numeric: int
    grade: str


def parse_radon_output(output: str) -> list[ComplexityViolation]:
    """Parse radon cc output and extract violations."""
    violations = []
    current_file = None

    # Grade to numeric CC mapping
    grade_to_cc = {
        "A": 5,
        "B": 10,
        "C": 20,
        "D": 30,
        "E": 40,
        "F": 50,
    }

    lines = output.strip().split("\n")

    for line in lines:
        # File header lines (start without leading spaces)
        if line and not line.startswith("    "):
            current_file = line.strip()
            continue

        # Function/method lines: "    M 268:4 MilestoneService.delete_milestone - C"
        match = re.search(r"^\s+[MFC]\s+(\d+):[0-9]+\s+(.+?)\s+-\s+([A-F])$", line)
        if match:
            line_num = int(match.group(1))
            func_name = match.group(2)
            grade = match.group(3)
            cc_numeric = grade_to_cc.get(grade, 0)

            violations.append(
                ComplexityViolation(
                    module=current_file or "unknown",
                    function=func_name,
                    line=line_num,
                    cc_numeric=cc_numeric,
                    grade=grade,
                )
            )

    return violations


def enforce_threshold(
    violations: list[ComplexityViolation], max_grade: str = "B"
) -> int:
    """
    Check if any violations exceed the maximum allowed grade.

    Returns:
        0 if all violations are acceptable (at or below max_grade)
        1 if any violation exceeds max_grade
    """
    grade_order = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "F": 0}
    max_grade_order = grade_order.get(max_grade, 3)

    violations_found = []
    for v in violations:
        if grade_order.get(v.grade, 0) < max_grade_order:
            violations_found.append(v)

    if violations_found:
        print(f"❌ Complexity threshold violation: Max grade {max_grade} exceeded\n")
        print("| Function | Grade | CC | Module | Line |")
        print("|----------|-------|----|---------|----|")
        for v in violations_found:
            print(
                f"| `{v.function}` | {v.grade} | {v.cc_numeric} | "
                f"`{v.module}` | {v.line} |"
            )
        print(
            f"\nFound {len(violations_found)} violations (run `scripts/complexity_table.py` to see all)"
        )
        return 1

    return 0


def main():
    """Run radon, parse output, and enforce thresholds."""
    # Get threshold from environment or use default
    max_grade = "B"  # Default: no functions worse than B-grade (CC <= 10)

    # Run radon (show all grades to see violations)
    try:
        result = subprocess.run(
            ["poetry", "run", "radon", "cc", "roadmap", "--exclude=tests"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print(
            "Error: poetry not found. Please ensure Poetry is installed.",
            file=sys.stderr,
        )
        sys.exit(1)

    if result.returncode not in (0, 2):  # 2 means some files had issues
        print(f"Error running radon: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Parse and enforce
    violations = parse_radon_output(result.stdout)

    if enforce_threshold(violations, max_grade):
        print(f"\nThreshold policy: Functions must be {max_grade} grade or better")
        sys.exit(1)
    else:
        print(
            f"✅ All functions comply with {max_grade}-grade threshold ({len(violations)} C/D/E/F functions monitored)"
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
