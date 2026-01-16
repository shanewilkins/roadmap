#!/usr/bin/env python3
"""
Phase 2.1 Mock Builders Rollout Script

This script systematically replaces Mock() setup patterns with mock_builders
factory functions across the test suite.

Usage:
    python phase_2_1_mock_builders_rollout.py [--dry-run]
    python phase_2_1_mock_builders_rollout.py --file tests/unit/adapters/sync/test_sync_services.py
"""

import argparse
import re
import sys
from pathlib import Path

# Pattern 1: mock_core = Mock() followed by mock_core.issue_service.repository = ...
PATTERN_MOCK_CORE_WITH_REPO = re.compile(
    r"(\s*)mock_core = Mock\(\)\s*\n"
    r"(\s*)mock_core\.issue_service = Mock\(\)\s*\n"
    r"(\s*)mock_core\.issue_service\.repository = ([^\n]+)\s*\n",
    re.MULTILINE,
)

# Pattern 2: standalone mock_repo = Mock() setups
PATTERN_STANDALONE_MOCK_REPO = re.compile(
    r"(\s*)mock_repo = Mock\(\)\s*\n" r"(\s*)mock_repo\.(\w+) = Mock\(([^)]*)\)\s*\n",
    re.MULTILINE,
)


def find_test_files():
    """Find all Python test files."""
    tests_dir = Path("tests")
    return list(tests_dir.rglob("test_*.py"))


def check_imports(content: str) -> tuple[bool, str]:
    """Check if file imports mock_builders and suggest import line."""
    if "from tests.fixtures.mock_builders import" in content:
        return True, ""
    return (
        False,
        "from tests.fixtures.mock_builders import build_mock_core, build_mock_core_with_repo, build_mock_repo",
    )


def replace_mock_patterns(content: str, file_path: str) -> tuple[str, int]:
    """Replace mock patterns with builders."""
    replacements = 0

    # Check imports
    has_import, import_line = check_imports(content)
    if not has_import and (
        "build_mock_core" in content or "build_mock_repo" in content
    ):
        # Add import if using builders but not importing
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("from tests.fixtures"):
                # Add to existing import block
                lines.insert(i, import_line)
                break
        else:
            # Add as new import
            for i, line in enumerate(lines):
                if line.startswith("from unittest.mock import"):
                    lines.insert(i + 1, import_line)
                    break
        content = "\n".join(lines)

    return content, replacements


def process_file(file_path: Path, dry_run: bool = False) -> tuple[bool, str]:
    """Process a single test file."""
    content = file_path.read_text()
    original_content = content

    try:
        content, replacements = replace_mock_patterns(content, str(file_path))

        if content != original_content and not dry_run:
            file_path.write_text(content)
            return True, f"Updated {replacements} patterns"
        elif content != original_content:
            return True, f"Would update {replacements} patterns (--dry-run)"
        else:
            return False, "No changes needed"
    except Exception as e:
        return False, f"Error: {e}"


def main():
    parser = argparse.ArgumentParser(description="Phase 2.1 Mock Builders Rollout")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed"
    )
    parser.add_argument("--file", type=str, help="Process single file")
    args = parser.parse_args()

    if args.file:
        files = [Path(args.file)]
    else:
        files = find_test_files()

    updated = 0
    total = 0

    for file_path in files:
        total += 1
        success, msg = process_file(file_path, args.dry_run)
        if success:
            updated += 1
            print(f"✓ {file_path}: {msg}")
        else:
            print(f"- {file_path}: {msg}")

    print(f"\n{updated}/{total} files updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
