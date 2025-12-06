#!/usr/bin/env python3
"""Fix all imports in adapters directory."""

import re
from pathlib import Path


def fix_file(filepath):
    """Fix imports in a single file."""
    with open(filepath) as f:
        content = f.read()

    original = content

    # Fix broken imports first
    content = re.sub(r"from roadmapshared\b", "from roadmap.common", content)
    content = re.sub(r"from roadmapdomain\b", "from roadmap.core.domain", content)
    content = re.sub(r"from roadmap/shared\b", "from roadmap.common", content)
    content = re.sub(r"from roadmap/domain\b", "from roadmap.core.domain", content)

    # Fix relative imports
    content = re.sub(r"from \.\.\.shared\.", "from roadmap.common.", content)
    content = re.sub(r"from \.\.\.domain\.", "from roadmap.core.domain.", content)
    content = re.sub(
        r"from \.\.\.domain import", "from roadmap.core.domain import", content
    )
    content = re.sub(r"from \.\.\.infrastructure\.", "from roadmap.adapters.", content)

    # Fix two-dot relative imports
    content = re.sub(r"from \.\.shared\.", "from roadmap.common.", content)
    content = re.sub(r"from \.\.domain\.", "from roadmap.core.domain.", content)
    content = re.sub(
        r"from \.\.domain import", "from roadmap.core.domain import", content
    )

    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        return True
    return False


def main():
    adapters_dir = Path(__file__).parent.parent / "roadmap" / "adapters"
    fixed = 0

    for py_file in adapters_dir.rglob("*.py"):
        if fix_file(py_file):
            print(f"Fixed: {py_file}")
            fixed += 1

    print(f"\nFixed {fixed} files")


if __name__ == "__main__":
    main()
