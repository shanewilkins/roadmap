#!/usr/bin/env python3
"""Auto-consolidate MagicMock(spec=X) with builders."""

import re
from pathlib import Path


def add_import_if_missing(filepath, builder_name):
    """Add builder import if not present."""
    with open(filepath) as f:
        content = f.read()

    if f"build_mock_{builder_name}" in content:
        return  # Already imported

    # Find where to add import
    if "from tests.fixtures import" in content:
        # Add to existing import
        pattern = r"(from tests\.fixtures import \([^)]*\n)([ ]*)"
        match = re.search(pattern, content)
        if match:
            indent = match.group(2)
            builder = f"build_mock_{builder_name}," if builder_name != "none" else ""
            content = re.sub(pattern, f"\\1{indent}{builder}\n\\2", content, count=1)
    else:
        # Add new import after last from/import
        lines = content.split("\n")
        last_import = 0
        for i, line in enumerate(lines):
            if line.startswith(("from ", "import ")):
                last_import = i
        lines.insert(
            last_import + 1, f"from tests.fixtures import build_mock_{builder_name}"
        )
        content = "\n".join(lines)

    with open(filepath, "w") as f:
        f.write(content)


files_to_fix = [
    ("tests/unit/adapters/test_git_hooks_manager_fix.py", "RoadmapCore", 3),
    (
        "tests/integration/git/test_git_integration_advanced_coverage.py",
        "RoadmapCore",
        1,
    ),
    (
        "tests/integration/git/test_git_integration_repository_issues.py",
        "RoadmapCore",
        1,
    ),
]

for filepath, spec, count in files_to_fix:
    print(f"Processing {filepath}...")
    p = Path(filepath)
    if not p.exists():
        print("  Skipped - not found")
        continue

    with open(filepath) as f:
        content = f.read()

    # Count matches
    pattern = f"MagicMock(spec={spec})"
    matches = content.count(pattern)
    print(f"  Found {matches} instances (expected ~{count})")

    # Add import
    builder_name = spec
    add_import_if_missing(filepath, builder_name)
    print(f"  Added import for build_mock_{builder_name}")

print("\nManual next steps needed:")
print("1. Review each file for MagicMock setups and customize builder calls")
print("2. Run tests to verify")
