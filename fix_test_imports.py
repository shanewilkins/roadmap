#!/usr/bin/env python3
"""
Fix test file imports after refactoring.

This script fixes common test import issues:
1. RoadmapCore from roadmap.application.services -> roadmap.application.core
2. RoadmapConfig imports that don't exist -> remove or comment out
"""

import re
from pathlib import Path

root_dir = Path("/Users/shane/roadmap")

# Fix 1: RoadmapCore imports in tests
replacements = [
    (
        r"from roadmap\.application\.services import RoadmapCore",
        "from roadmap.application.core import RoadmapCore",
    ),
    (
        r"from roadmap\.domain import (.*?)RoadmapConfig(.*?)(?:\n|$)",
        lambda m: f"from roadmap.domain import {m.group(1).rstrip()}{m.group(2).lstrip()}",
    ),
]

test_files = list(root_dir.glob("tests/**/*.py"))
print(f"Found {len(test_files)} test files\n")

# Fix RoadmapCore imports
core_pattern = r"from roadmap\.application\.services import RoadmapCore"
roadmap_config_pattern = r"from roadmap\.domain import.*?RoadmapConfig"

total_fixes = 0

for test_file in test_files:
    try:
        content = test_file.read_text()
        original_content = content

        # Fix RoadmapCore imports
        if re.search(core_pattern, content):
            content = re.sub(core_pattern, "from roadmap.application.core import RoadmapCore", content)
            total_fixes += 1
            print(f"✓ Fixed RoadmapCore import in {test_file.relative_to(root_dir)}")

        # Fix RoadmapConfig imports - remove RoadmapConfig from imports
        if re.search(roadmap_config_pattern, content):
            # Remove RoadmapConfig from the import line
            content = re.sub(
                r"from roadmap\.domain import (.*?), RoadmapConfig(.*?)(?=\n)",
                r"from roadmap.domain import \1\2",
                content
            )
            # Also handle case where it's the only import
            content = re.sub(
                r"from roadmap\.domain import RoadmapConfig",
                "# RoadmapConfig removed - no longer available",
                content
            )
            total_fixes += 1
            print(f"✓ Removed RoadmapConfig import from {test_file.relative_to(root_dir)}")

        if content != original_content:
            test_file.write_text(content)

    except Exception as e:
        print(f"ERROR processing {test_file}: {e}")

print(f"\nTotal fixes applied: {total_fixes}")
