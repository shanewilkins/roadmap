#!/usr/bin/env python3
"""Generate batch 4 refactoring operations."""

import re
from pathlib import Path


def find_project_replacements():
    """Find all Project() -> ProjectBuilder() replacements for test_project.py."""

    filepath = "tests/unit/core/domain/test_project.py"
    content = Path(filepath).read_text()

    # Pattern: "        variable = Project(...)"
    # We need to handle both single-line and multi-line cases

    pattern = r"(\s+)(\w+)\s*=\s*Project\(([^)]*(?:\([^)]*\)[^)]*)*)\)"

    replacements = []
    for match in re.finditer(pattern, content, re.DOTALL):
        indent = match.group(1)
        var_name = match.group(2)
        params = match.group(3).strip()

        # Build the old and new strings
        old_code = match.group(0)

        # Parse parameters into with_* calls
        # Simple approach: split by comma at top level
        param_parts = []
        current = ""
        depth = 0
        for char in params:
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif char == "," and depth == 0:
                if current.strip():
                    param_parts.append(current.strip())
                current = ""
                continue
            current += char
        if current.strip():
            param_parts.append(current.strip())

        # Build builder chain
        builder_chain = ["ProjectBuilder()"]
        for param in param_parts:
            if "=" in param:
                key, val = param.split("=", 1)
                key = key.strip()
                val = val.strip()
                builder_chain.append(f".with_{key}({val})")
        builder_chain.append(".build()")

        new_code = indent + var_name + " = " + "".join(builder_chain)

        replacements.append((old_code, new_code))

    return replacements


reps = find_project_replacements()
print(f"Found {len(reps)} Project creations")
print("\nFirst 3 samples:\n")
for i, (old, new) in enumerate(reps[:3]):
    print(f"--- {i+1} ---")
    print(f"OLD: {repr(old[:60])}")
    print(f"NEW: {repr(new[:60])}")
    print()
