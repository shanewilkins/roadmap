#!/usr/bin/env python3
"""
Automated import fixer for roadmap refactoring.

This script systematically fixes all deprecated imports across the codebase,
replacing them with the new layered architecture imports.

Usage:
    python fix_imports.py                      # Dry run - shows what would change
    python fix_imports.py --apply              # Apply the fixes
    python fix_imports.py --apply --verbose    # Apply with detailed output
"""

import re
import sys
from pathlib import Path

# Define the import replacements
IMPORT_REPLACEMENTS = [
    # Category 1: roadmap.models -> roadmap.domain
    {
        "pattern": r"from roadmap\.models import",
        "replacement": "from roadmap.domain import",
        "description": "Migrate models to domain",
        "files": ["roadmap/**/*.py", "tests/**/*.py"],
    },
    # Category 2: roadmap.error_handling -> roadmap.shared.errors
    {
        "pattern": r"from roadmap\.error_handling import",
        "replacement": "from roadmap.shared.errors import",
        "description": "Migrate error handling to shared.errors",
        "files": ["roadmap/**/*.py", "tests/**/*.py"],
    },
    # Category 3: roadmap.github_client -> roadmap.infrastructure.github
    {
        "pattern": r"from roadmap\.github_client import",
        "replacement": "from roadmap.infrastructure.github import",
        "description": "Migrate GitHub client to infrastructure",
        "files": ["roadmap/**/*.py", "tests/**/*.py"],
    },
    # Category 4: roadmap.core -> roadmap.application.core
    {
        "pattern": r"from roadmap\.core import",
        "replacement": "from roadmap.application.core import",
        "description": "Migrate core to application",
        "files": ["roadmap/**/*.py", "tests/**/*.py"],
    },
    # Category 5: roadmap.cli -> roadmap.presentation.cli
    {
        "pattern": r"from roadmap\.cli import",
        "replacement": "from roadmap.presentation.cli import",
        "description": "Migrate CLI to presentation",
        "files": ["roadmap/**/*.py", "tests/**/*.py"],
    },
    # Category 6: roadmap.git_integration -> roadmap.infrastructure.git
    {
        "pattern": r"from roadmap\.git_integration import",
        "replacement": "from roadmap.infrastructure.git import",
        "description": "Migrate git integration to infrastructure",
        "files": ["roadmap/**/*.py", "tests/**/*.py"],
    },
]


def find_files(root_dir: Path, patterns: list[str]) -> list[Path]:
    """Find all Python files matching the patterns."""
    files = set()
    for pattern in patterns:
        for file in root_dir.glob(pattern):
            if file.is_file() and file.suffix == ".py":
                files.add(file)
    return sorted(files)


def apply_replacements(file_path: Path, verbose: bool = False) -> tuple[int, bool]:
    """
    Apply import replacements to a single file.

    Returns:
        Tuple of (number of replacements made, whether file was modified)
    """
    try:
        content = file_path.read_text()
        original_content = content
        replacement_count = 0

        for replacement in IMPORT_REPLACEMENTS:
            pattern = replacement["pattern"]
            replacement_text = replacement["replacement"]

            matches = list(re.finditer(pattern, content))
            if matches:
                content = re.sub(pattern, replacement_text, content)
                replacement_count += len(matches)

                if verbose:
                    print(
                        f"  - {replacement['description']}: {len(matches)} replacement(s)"
                    )

        file_modified = content != original_content

        return replacement_count, file_modified

    except Exception as e:
        print(f"ERROR processing {file_path}: {e}")
        return 0, False


def main():
    """Main entry point."""
    apply_changes = "--apply" in sys.argv
    verbose = "--verbose" in sys.argv

    root_dir = Path("/Users/shane/roadmap")

    # Find all Python files
    patterns = ["roadmap/**/*.py", "tests/**/*.py"]
    files_to_process = find_files(root_dir, patterns)

    print(f"Found {len(files_to_process)} Python files to process\n")

    total_replacements = 0
    files_modified = 0
    files_with_changes = []

    for file_path in files_to_process:
        replacement_count, was_modified = apply_replacements(file_path, verbose=verbose)

        if replacement_count > 0:
            total_replacements += replacement_count
            if was_modified:
                files_modified += 1
                files_with_changes.append((file_path, replacement_count))

                if verbose or apply_changes:
                    rel_path = file_path.relative_to(root_dir)
                    print(f"\n✓ {rel_path}")
                    print(f"  {replacement_count} import(s) to update")

    # If --apply flag, write the changes
    if apply_changes:
        print("\n" + "=" * 60)
        print("APPLYING CHANGES...")
        print("=" * 60 + "\n")

        total_applied = 0
        for file_path in files_to_process:
            try:
                content = file_path.read_text()
                original_content = content

                for replacement in IMPORT_REPLACEMENTS:
                    pattern = replacement["pattern"]
                    replacement_text = replacement["replacement"]
                    content = re.sub(pattern, replacement_text, content)

                if content != original_content:
                    file_path.write_text(content)
                    rel_path = file_path.relative_to(root_dir)
                    changes = sum(
                        len(re.findall(r.get("pattern", ""), original_content))
                        for r in IMPORT_REPLACEMENTS
                    )
                    print(f"✓ Updated {rel_path} ({changes} import(s))")
                    total_applied += changes

            except Exception as e:
                print(f"ERROR applying changes to {file_path}: {e}")

        print(f"\n{'=' * 60}")
        print(f"Total imports updated: {total_applied}")
        print(f"Files modified: {len(files_with_changes)}")
        print(f"{'=' * 60}\n")

    else:
        # Dry run mode
        print(f"{'=' * 60}")
        print("DRY RUN - No changes applied")
        print(f"Total replacements needed: {total_replacements}")
        print(f"Files that would be modified: {len(files_with_changes)}")
        print(f"{'=' * 60}\n")

        if files_with_changes:
            print("Files with import issues:\n")
            for file_path, count in sorted(files_with_changes):
                rel_path = file_path.relative_to(root_dir)
                print(f"  {rel_path}: {count} import(s)")

        print("\nRun with --apply to fix these imports")
        print("Run with --apply --verbose for detailed output\n")


if __name__ == "__main__":
    main()
