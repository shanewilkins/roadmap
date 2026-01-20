#!/usr/bin/env python3
"""Migrate a single file from unittest.mock to pytest-mock."""

import re
import sys
from pathlib import Path


def migrate_file(file_path):
    """Migrate a file to pytest-mock."""
    path = Path(file_path)
    content = path.read_text()
    original = content

    # Step 1: Replace all `with patch(...) as var:` with `var = mocker.patch(...)`
    # Handle both single-line and multi-line patches
    pattern = r"        with patch\(([^)]+)\) as (\w+):"
    content = re.sub(pattern, r"        \2 = mocker.patch(\1)", content)

    # Step 2: Add mocker parameter to test methods that use patches
    lines = content.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a test method definition
        if re.match(r"\s*def test_\w+\(", line):
            # Look ahead to see if mocker is used in the next ~30 lines
            next_lines = "\n".join(lines[i : min(i + 30, len(lines))])
            uses_mocker = "mocker." in next_lines or "mocker)" in next_lines

            if uses_mocker:
                # Check if mocker param already exists
                if ", mocker" not in line and "(mocker)" not in line:
                    # Add mocker parameter before closing paren
                    if line.rstrip().endswith(":"):
                        # Handle: def test_name(self):
                        if (
                            r"def test_\w+\(self\)" in line
                            or r"def test_\w+\(self," in line
                        ):
                            line = line.rstrip(":")
                            if line.endswith(")"):
                                line = line[:-1] + ", mocker):"
                            else:
                                line = line + ", mocker):"

        result.append(line)
        i += 1

    content = "\n".join(result)

    # Step 3: Remove old imports
    content = content.replace(
        "from unittest.mock import patch, ", "from unittest.mock import "
    )
    content = content.replace("from unittest.mock import patch\n", "")

    if content != original:
        path.write_text(content)
        print(f"✅ Migrated {file_path}")
        return True
    else:
        print(f"⚠️  No changes needed for {file_path}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate_file.py <filepath>")
        sys.exit(1)

    migrate_file(sys.argv[1])
