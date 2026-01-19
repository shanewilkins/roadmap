#!/usr/bin/env python3
"""Find duplicate code blocks using token-based comparison."""

import os
import re
from collections import defaultdict
from pathlib import Path


def tokenize_code(code: str) -> list[str]:
    """Tokenize Python code into meaningful chunks."""
    # Remove comments and docstrings
    code = re.sub(r"#.*$", "", code, flags=re.MULTILINE)
    code = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code = re.sub(r"'''.*?'''", "", code, flags=re.DOTALL)

    # Normalize whitespace
    code = re.sub(r"\s+", " ", code).strip()

    # Tokenize
    tokens = re.findall(r"\w+|[^\w\s]", code)
    return tokens


def get_code_blocks(
    file_path: Path, min_lines: int = 5, min_tokens: int = 50
) -> list[tuple[int, int, list[str]]]:
    """Extract code blocks from a file."""
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
            blocks.append((i + 1, i + min_lines + 1, tokens))

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
        # Remove excluded directories from dirnames in-place
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for filename in filenames:
            if filename.endswith(".py"):
                python_files.append(Path(dirpath) / filename)

    return python_files


def main():
    root_dir = "/Users/shane/roadmap"
    min_lines = 5
    min_tokens = 50

    print(f"Scanning Python files in {root_dir}...")
    python_files = find_python_files(root_dir)
    print(f"Found {len(python_files)} Python files\n")

    # Map token sequences to file locations
    block_map = defaultdict(list)

    for file_path in python_files:
        blocks = get_code_blocks(file_path, min_lines, min_tokens)
        for start_line, end_line, tokens in blocks:
            # Use tuple of tokens as key
            token_key = tuple(tokens)
            block_map[token_key].append((str(file_path), start_line, end_line))

    # Find duplicates
    duplicates = [
        block_info for block_info in block_map.values() if len(block_info) > 1
    ]
    duplicates.sort(key=lambda x: len(x), reverse=True)

    print(f"Found {len(duplicates)} duplicate blocks\n")

    # Filter for roadmap and tests only
    roadmap_duplicates = []
    for dup_group in duplicates:
        # Check if any are in roadmap/ or tests/
        roadmap_files = [
            d for d in dup_group if "/roadmap/" in d[0] or "/tests/" in d[0]
        ]
        if len(roadmap_files) > 1:
            roadmap_duplicates.append(dup_group)

    print(f"Duplicates in roadmap/ and tests/: {len(roadmap_duplicates)}\n")

    # Show top duplicates
    print("Top 20 duplicate blocks:\n")
    for i, dup_group in enumerate(roadmap_duplicates[:20], 1):
        print(f"{i}. Found in {len(dup_group)} locations:")
        for file_path, start_line, end_line in dup_group[:3]:  # Show first 3 locations
            # Make path relative
            rel_path = file_path.replace("/Users/shane/roadmap/", "")
            print(f"   - {rel_path}:{start_line}-{end_line}")
        if len(dup_group) > 3:
            print(f"   ... and {len(dup_group) - 3} more")
        print()


if __name__ == "__main__":
    main()
