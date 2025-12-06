#!/usr/bin/env python3
"""Update imports to match new architecture."""

import re
from pathlib import Path

# Import mapping rules (order matters - more specific first)
IMPORT_MAPPINGS = [
    # Domain models (without sub-package)
    (r"from roadmap\.domain import", "from roadmap.core.domain import"),
    (r"from roadmap\.domain\.", "from roadmap.core.domain."),
    # Application core -> keep infrastructure location for now
    (
        r"from roadmap\.application\.core import",
        "from roadmap.infrastructure.core import",
    ),
    # Application health -> keep infrastructure location for now
    (
        r"from roadmap\.application\.health import",
        "from roadmap.infrastructure.health import",
    ),
    # Application services -> core services
    (
        r"from roadmap\.application\.services import",
        "from roadmap.core.services import",
    ),
    (r"from roadmap\.application\.services\.", "from roadmap.core.services."),
    # Application orchestrators -> core orchestrators
    (r"from roadmap\.application\.orchestrators\.", "from roadmap.core.orchestrators."),
    # Infrastructure security -> keep in infrastructure
    (
        r"from roadmap\.infrastructure\.security\.",
        "from roadmap.infrastructure.security.",
    ),
    # Infrastructure file enumeration -> keep in infrastructure
    (
        r"from roadmap\.infrastructure\.file_enumeration import",
        "from roadmap.infrastructure.file_enumeration import",
    ),
    # Infrastructure persistence -> adapters persistence
    (
        r"from roadmap\.infrastructure\.persistence\.",
        "from roadmap.adapters.persistence.",
    ),
    # Infrastructure github -> adapters github
    (
        r"from roadmap\.infrastructure\.github import",
        "from roadmap.adapters.github.github import",
    ),
    # Infrastructure git -> adapters git
    (
        r"from roadmap\.infrastructure\.git import",
        "from roadmap.adapters.git.git import",
    ),
    (
        r"from roadmap\.infrastructure\.git_hooks import",
        "from roadmap.adapters.git.git_hooks import",
    ),
    # Infrastructure storage -> adapters persistence storage
    (
        r"from roadmap\.infrastructure\.storage import",
        "from roadmap.adapters.persistence.storage import",
    ),
    # Presentation CLI -> adapters CLI
    (r"from roadmap\.presentation\.cli\.", "from roadmap.adapters.cli."),
    # CLI -> adapters CLI
    (r"from roadmap\.cli\.", "from roadmap.adapters.cli."),
    # Shared -> common
    (r"from roadmap\.shared\.", "from roadmap.common."),
]


def update_file_imports(filepath: Path) -> tuple[int, list[str]]:
    """Update imports in a single file."""
    with open(filepath) as f:
        content = f.read()

    original_content = content
    changes = []

    for pattern, replacement in IMPORT_MAPPINGS:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            changes.extend([f"  {pattern} -> {replacement}"])

    if content != original_content:
        with open(filepath, "w") as f:
            f.write(content)
        return len(changes), changes

    return 0, []


def main():
    """Update all imports in the codebase."""
    repo_root = Path(__file__).parent.parent
    roadmap_dir = repo_root / "roadmap"
    tests_dir = repo_root / "tests"

    total_files = 0
    total_changes = 0

    print("Updating imports in roadmap/...")
    for py_file in roadmap_dir.rglob("*.py"):
        if "future" in str(py_file):
            continue

        num_changes, changes = update_file_imports(py_file)
        if num_changes > 0:
            total_files += 1
            total_changes += num_changes
            print(f"\n{py_file.relative_to(repo_root)}: {num_changes} changes")
            for change in changes[:3]:  # Show first 3 changes
                print(change)
            if len(changes) > 3:
                print(f"  ... and {len(changes) - 3} more")

    print("\n\nUpdating imports in tests/...")
    for py_file in tests_dir.rglob("*.py"):
        num_changes, changes = update_file_imports(py_file)
        if num_changes > 0:
            total_files += 1
            total_changes += num_changes
            print(f"\n{py_file.relative_to(repo_root)}: {num_changes} changes")
            for change in changes[:3]:
                print(change)
            if len(changes) > 3:
                print(f"  ... and {len(changes) - 3} more")

    print(f"\n\n{'='*60}")
    print(f"SUMMARY: Updated {total_files} files with {total_changes} import changes")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
