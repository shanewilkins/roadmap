#!/usr/bin/env python3
"""Direct replacement for test_project.py - replace all 22 Project() with ProjectBuilder()."""

import re
from pathlib import Path

filepath = "tests/unit/core/domain/test_project.py"
content = Path(filepath).read_text()

# Direct regex replacement strategy:
# For simple cases like: variable = Project(name="value")
# For complex multiline cases, handle separately


def replace_project_creations(text):
    """Replace Project(...) with ProjectBuilder()...build()."""

    # Pattern 1: Single-line Project(name="...")
    text = re.sub(
        r'(\w+)\s*=\s*Project\(name="([^"]*)"\)',
        r'\1 = ProjectBuilder().with_name("\2").build()',
        text,
    )

    # Pattern 2: Project(name="...", milestones=[...])
    text = re.sub(
        r'(\w+)\s*=\s*Project\(name="([^"]*)",\s*milestones=\[(.*?)\]\)',
        lambda m: f'{m.group(1)} = ProjectBuilder().with_name("{m.group(2)}").with_milestones([{m.group(3)}]).build()',
        text,
        flags=re.DOTALL,
    )

    # Pattern 3: Project(name="...", comments=[])
    text = re.sub(
        r'(\w+)\s*=\s*Project\(name="([^"]*)",\s*comments=\[\]\)',
        r'\1 = ProjectBuilder().with_name("\2").with_comments([]).build()',
        text,
    )

    # Pattern 4: Multiline Project with many fields - needs manual handling
    # Let's list all remaining patterns
    return text


result = replace_project_creations(content)

# Count replacements
original_count = content.count(" = Project(")
new_count = result.count(" = ProjectBuilder(")

print(f"Original Project() creations: {original_count}")
print(f"New ProjectBuilder() creations: {new_count}")
print(f"Replaced: {original_count - result.count(' = Project(')}")

# Show a few examples
for line in result.split("\n"):
    if "ProjectBuilder" in line:
        print(f"  {line.strip()}")
        if result.count("ProjectBuilder") >= 5:
            break
