#!/usr/bin/env python3
"""Detailed DRY violations analysis with code snippets."""

import os
import re
from collections import defaultdict
from pathlib import Path


def tokenize_code(code: str) -> list[str]:
    """Tokenize Python code into meaningful chunks."""
    code = re.sub(r"#.*$", "", code, flags=re.MULTILINE)
    code = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code = re.sub(r"'''.*?'''", "", code, flags=re.DOTALL)
    code = re.sub(r"\s+", " ", code).strip()
    tokens = re.findall(r"\w+|[^\w\s]", code)
    return tokens


def get_code_blocks(
    file_path: Path, min_lines: int = 5, min_tokens: int = 50
) -> list[tuple[int, int, list[str], str]]:
    """Extract code blocks from a file with original code."""
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return []

    blocks = []
    for i in range(len(lines) - min_lines + 1):
        block_lines = lines[i : i + min_lines]
        block_code = "".join(block_lines)
        tokens = tokenize_code(block_code)

        if len(tokens) >= min_tokens:
            original_code = "".join(block_lines)
            blocks.append((i + 1, i + min_lines + 1, tokens, original_code))

    return blocks


def find_python_files(root_dir: str) -> list[Path]:
    """Find all Python files in a directory."""
    exclude_dirs = {
        ".venv",
        ".git",
        "__pycache__",
        ".pytest_cache",
        "htmlcov",
        "build",
        "dist",
    }
    python_files = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for filename in filenames:
            if filename.endswith(".py"):
                python_files.append(Path(dirpath) / filename)

    return python_files


def extract_patterns(code: str) -> str:
    """Extract pattern description from code."""
    lines = code.strip().split("\n")
    pattern = " ".join(lines[:3])  # First 3 lines as pattern description
    if len(pattern) > 80:
        pattern = pattern[:77] + "..."
    return pattern


def main():
    root_dir = "/Users/shane/roadmap"
    min_lines = 5
    min_tokens = 50

    print("=" * 100)
    print("DRY VIOLATIONS ANALYSIS USING JSCPD-LIKE APPROACH")
    print("=" * 100)
    print()

    python_files = find_python_files(root_dir)
    print(f"Scanning {len(python_files)} Python files...\n")

    block_map = defaultdict(list)

    for file_path in python_files:
        blocks = get_code_blocks(file_path, min_lines, min_tokens)
        for start_line, end_line, tokens, original_code in blocks:
            token_key = tuple(tokens)
            block_map[token_key].append(
                {
                    "file": str(file_path),
                    "start": start_line,
                    "end": end_line,
                    "code": original_code,
                }
            )

    # Find duplicates in our code
    duplicates = [
        block_info for block_info in block_map.values() if len(block_info) > 1
    ]
    duplicates.sort(key=lambda x: len(x), reverse=True)

    # Filter for roadmap and tests
    roadmap_duplicates = []
    for dup_group in duplicates:
        roadmap_files = [
            d for d in dup_group if "/roadmap/" in d["file"] or "/tests/" in d["file"]
        ]
        if len(roadmap_files) > 1:
            roadmap_duplicates.append(dup_group)

    print(f"Total duplicates found: {len(roadmap_duplicates)}\n")

    # Categorize by type
    issue_creation = []
    roadmap_init = []
    temp_dir = []
    patch_decorator = []
    other = []

    for dup_group in roadmap_duplicates:
        code_sample = dup_group[0]["code"]

        if (
            "temp_dir_context" in code_sample
            or "TemporaryDirectory" in code_sample
            or "tempfile" in code_sample
        ):
            temp_dir.append(dup_group)
        elif "Issue(" in code_sample or "Issue.create" in code_sample:
            issue_creation.append(dup_group)
        elif "RoadmapCore(" in code_sample or "RoadmapCore.create" in code_sample:
            roadmap_init.append(dup_group)
        elif "@patch" in code_sample:
            patch_decorator.append(dup_group)
        else:
            other.append(dup_group)

    print("CATEGORIZED DUPLICATES:")
    print("-" * 100)
    print(f"  1. Temp Directory Setup Patterns:      {len(temp_dir)} violations")
    print(f"  2. Issue Creation Patterns:           {len(issue_creation)} violations")
    print(f"  3. RoadmapCore Init Patterns:         {len(roadmap_init)} violations")
    print(f"  4. Patch Decorator Patterns:          {len(patch_decorator)} violations")
    print(f"  5. Other Patterns:                    {len(other)} violations")
    print()
    print("=" * 100)
    print()

    # Show examples for each category
    categories = [
        ("TEMP DIRECTORY SETUP", temp_dir),
        ("ISSUE CREATION", issue_creation),
        ("ROADMAPCORE INIT", roadmap_init),
        ("PATCH DECORATORS", patch_decorator),
        ("OTHER PATTERNS", other),
    ]

    for cat_name, cat_list in categories:
        if not cat_list:
            continue

        print(f"\n{cat_name} ({len(cat_list)} violations)")
        print("-" * 100)

        for i, dup_group in enumerate(cat_list[:3], 1):  # Show top 3 per category
            print(f"\n{i}. Found in {len(dup_group)} locations:")

            for j, location in enumerate(dup_group[:2], 1):
                rel_path = location["file"].replace("/Users/shane/roadmap/", "")
                print(f"   [{j}] {rel_path}:{location['start']}-{location['end']}")

            if len(dup_group) > 2:
                print(f"   ... and {len(dup_group) - 2} more locations")

            print("\n   Code Sample:")
            code_lines = location["code"].strip().split("\n")
            for line in code_lines[:4]:  # Show first 4 lines
                print(f"       {line}")
            if len(code_lines) > 4:
                print("       ...")

        if len(cat_list) > 3:
            print(
                f"\n   ... and {len(cat_list) - 3} more duplicate blocks in this category"
            )

    print("\n" + "=" * 100)
    print("\nRECOMMENDATIONS:")
    print("-" * 100)
    print("1. Extract temp directory setup to shared fixture (5+ occurrences)")
    print(
        "2. Create IssueFactory for consistent Issue() creation (see Phase 3 recommendations)"
    )
    print("3. Consolidate RoadmapCore initialization patterns")
    print("4. Consider centralizing @patch decorators in conftest.py")
    print()


if __name__ == "__main__":
    main()
