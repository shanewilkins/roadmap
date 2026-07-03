#!/usr/bin/env python3
"""
Generate a table of functions sorted by cyclomatic complexity.
Parses radon cc output and displays top N functions with highest complexity.
"""

import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class ComplexityFunction:
    """Represents a function with its complexity metrics."""

    module: str
    function: str
    line: int
    cc_numeric: int
    grade: str

    def cc_display(self) -> str:
        """Return CC value with grade for display."""
        return f"{self.cc_numeric} ({self.grade})"


def parse_radon_output(output: str, min_grade: str = "C") -> list[ComplexityFunction]:
    """Parse radon cc output and extract function complexity data."""
    functions = []
    current_file = None

    # Grade to numeric CC mapping (using upper bounds)
    grade_to_cc = {
        "A": 5,
        "B": 10,
        "C": 20,
        "D": 30,
        "E": 40,
        "F": 50,
    }

    # Grade ordering for sorting (D, E, F first, then C, B, A)
    grade_order = {"D": 0, "E": 1, "F": 2, "C": 3, "B": 4, "A": 5}

    lines = output.strip().split("\n")

    for line in lines:
        # File header lines (start without leading spaces after strip, but we need to detect them)
        if line and not line.startswith("    "):
            current_file = line.strip()
            continue

        # Function/method lines: "    M 268:4 MilestoneService.delete_milestone - C"
        match = re.search(r"^\s+[MFC]\s+(\d+):[0-9]+\s+(.+?)\s+-\s+([A-F])$", line)
        if match:
            line_num = int(match.group(1))
            func_name = match.group(2)
            grade = match.group(3)

            # Only include functions at or above minimum grade threshold
            if grade_order.get(grade, 6) <= grade_order.get(min_grade, 6):
                cc_numeric = grade_to_cc.get(grade, 0)
                functions.append(
                    ComplexityFunction(
                        module=current_file or "unknown",
                        function=func_name,
                        line=line_num,
                        cc_numeric=cc_numeric,
                        grade=grade,
                    )
                )

    return functions


def sort_by_complexity(functions: list[ComplexityFunction]) -> list[ComplexityFunction]:
    """Sort functions by complexity (worst first)."""
    # Sort by: grade order (D/E/F worst), then by CC value descending, then by function name
    grade_order = {"D": 0, "E": 1, "F": 2, "C": 3, "B": 4, "A": 5}
    return sorted(
        functions,
        key=lambda f: (grade_order.get(f.grade, 6), -f.cc_numeric, f.function),
    )


def format_table(functions: list[ComplexityFunction], limit: int | None = None) -> str:
    """Format functions as a markdown table."""
    if limit:
        functions = functions[:limit]

    lines = [
        "| # | CC | Grade | Module | Function | Line |",
        "|---|----|----|--------|----------|------|",
    ]

    for i, func in enumerate(functions, 1):
        lines.append(
            f"| {i} | {func.cc_numeric} | {func.grade} | "
            f"`{func.module}` | `{func.function}` | {func.line} |"
        )

    return "\n".join(lines)


def main():
    """Run radon, parse output, and display table."""
    # Parse arguments
    limit = 25
    min_grade = "C"

    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [limit]", file=sys.stderr)
            sys.exit(1)

    # Run radon
    try:
        result = subprocess.run(
            [
                "uv",
                "run",
                "radon",
                "cc",
                "roadmap",
                "--exclude=tests",
                "--min",
                min_grade,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print(
            "Error: uv not found. Please ensure uv is installed.",
            file=sys.stderr,
        )
        sys.exit(1)

    if (
        result.returncode != 0 and result.returncode != 2
    ):  # 2 means some files had issues
        print(f"Error running radon: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Parse and display
    functions = parse_radon_output(result.stdout, min_grade)
    functions = sort_by_complexity(functions)

    if not functions:
        print(f"No functions found with grade {min_grade} or worse.")
        sys.exit(0)

    print(format_table(functions, limit))
    print(
        f"\nTotal: {len(functions)} functions (showing {min(limit, len(functions))} of {len(functions)})"
    )


if __name__ == "__main__":
    main()
