#!/usr/bin/env python3
"""Batch consolidate DRY violations using fixtures and builders."""

import re
from pathlib import Path

# Test files that use RoadmapCore() directly (should use fixtures instead)
ROADMAP_CORE_FILES = [
    "tests/unit/domain/test_estimated_time.py",
    "tests/unit/presentation/test_enhanced_list_command.py",
    "tests/unit/presentation/test_milestone_commands.py",
    "tests/unit/application/test_core_edge_cases.py",
]


def consolidate_roadmap_core():
    """Replace RoadmapCore() instantiations with fixtures."""
    count = 0

    for filepath_str in ROADMAP_CORE_FILES:
        filepath = Path(filepath_str)
        if not filepath.exists():
            continue

        with open(filepath) as f:
            content = f.read()

        # Check if it's an integration test
        is_integration = "integration" in filepath_str
        fixture_name = (
            "integration_roadmap_core" if is_integration else "unit_roadmap_core"
        )

        # Skip if already using fixture
        if fixture_name in content:
            continue

        # Pattern: core = RoadmapCore() followed by core.initialize()
        pattern = r"(\s+)core = RoadmapCore\(\)\s+core\.initialize\(\)"
        if re.search(pattern, content):
            # This needs manual inspection - don't auto-replace
            continue

        # Pattern: core = RoadmapCore() without initialize
        pattern = r"(\s+)core = RoadmapCore\(\)"
        if re.search(pattern, content):
            # Add fixture parameter to test function
            # This requires function signature changes - complex
            continue

    return count


def find_magic_mock_patterns():
    """Find most common MagicMock patterns."""
    patterns = {}

    for py_file in Path("tests").rglob("*.py"):
        if "__pycache__" in str(py_file) or "conftest" in str(py_file):
            continue

        try:
            with open(py_file) as f:
                content = f.read()
        except Exception:
            continue

        # Find MagicMock(spec=...) patterns
        matches = re.findall(r"MagicMock\(spec=([^)]+)\)", content)
        for match in matches:
            spec = match.strip()
            patterns[spec] = patterns.get(spec, 0) + 1

    return patterns


if __name__ == "__main__":
    print("Finding MagicMock patterns...")
    patterns = find_magic_mock_patterns()

    print("\nTop MagicMock spec patterns:")
    for spec, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {spec}: {count}")
