#!/usr/bin/env python3
"""Batch consolidate all MagicMock patterns with builders."""

from pathlib import Path


def get_files_by_pattern(spec_name):
    """Get files that use MagicMock(spec=X)."""
    files = []
    for py_file in Path("tests").rglob("*.py"):
        if "__pycache__" in str(py_file) or "conftest" in str(py_file):
            continue
        try:
            with open(py_file) as f:
                content = f.read()
            if f"MagicMock(spec={spec_name})" in content:
                files.append(py_file)
        except Exception:
            pass
    return files


# Top consolidation targets
targets = {
    "RoadmapCore": ("build_mock_roadmap_core", 10),
    "PersistenceInterface": ("build_mock_persistence_interface", 4),
    "TableData": ("build_mock_table_data", 4),
    "IssueParserInterface": ("build_mock_issue_parser_interface", 3),
    "Project": ("build_mock_project", 2),
}

print("=" * 60)
print("DRY VIOLATIONS CONSOLIDATION TARGETS")
print("=" * 60)

for spec_name, (builder, count) in targets.items():
    files = get_files_by_pattern(spec_name)
    print(f"\n{spec_name}: {len(files)} files")
    print(f"  Builder: {builder}()")
    print(f"  Expected instances: ~{count}")
    for f in sorted(files)[:3]:
        rel = f.relative_to(Path("."))
        print(f"    - {rel}")
    if len(files) > 3:
        print(f"    ... and {len(files) - 3} more")

print("\n" + "=" * 60)
print(
    f"Total files to consolidate: {sum(len(get_files_by_pattern(s)) for s in targets)}"
)
print("=" * 60)
