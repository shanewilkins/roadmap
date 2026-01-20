#!/usr/bin/env python3
"""Batch replace MagicMock patterns with builders."""

import re
from pathlib import Path


def replace_in_file(filepath, old, new):
    """Replace text in file."""
    with open(filepath) as f:
        content = f.read()

    if old in content:
        content = content.replace(old, new)
        with open(filepath, "w") as f:
            f.write(content)
        return True
    return False


# Target: Replace MagicMock(spec=RoadmapCore) with build_mock_roadmap_core()
files_to_fix = [
    (
        "tests/unit/cli/test_project_initialization_service.py",
        [
            (
                '        mock_core = MagicMock(spec=RoadmapCore)\n        mock_core.roadmap_dir = tmp_path / ".roadmap"',
                '        mock_core = build_mock_roadmap_core(roadmap_dir=tmp_path / ".roadmap")',
            ),
        ],
    ),
]

changed_count = 0

for filepath_str, replacements in files_to_fix:
    filepath = Path(filepath_str)
    if not filepath.exists():
        print(f"  Skipping {filepath_str} - not found")
        continue

    # Check if file imports builder
    with open(filepath) as f:
        content = f.read()

    if "build_mock_roadmap_core" not in content:
        # Add import
        if "from tests.fixtures import" in content:
            # Has fixtures import, add to it
            pattern = r"from tests\.fixtures import \(([^)]+)\)"
            match = re.search(pattern, content)
            if match:
                imports = match.group(1)
                if "build_mock_roadmap_core" not in imports:
                    new_imports = imports.rstrip() + "\n    build_mock_roadmap_core,"
                    content = re.sub(
                        pattern, f"from tests.fixtures import ({new_imports})", content
                    )
        else:
            # Add new import
            lines = content.split("\n")
            # Find last import line
            last_import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("from ") or line.startswith("import "):
                    last_import_idx = i
            lines.insert(
                last_import_idx + 1,
                "from tests.fixtures import build_mock_roadmap_core",
            )
            content = "\n".join(lines)

        with open(filepath, "w") as f:
            f.write(content)
        print(f"Added import to {filepath_str}")

    # Do replacements
    for old, new in replacements:
        if replace_in_file(filepath, old, new):
            changed_count += 1
            print(f"  Replaced in {filepath_str}")

print(f"\nTotal replacements: {changed_count}")
