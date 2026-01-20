#!/usr/bin/env python3
"""Scan codebase for DRY violations (code duplication).

Identifies:
- Repeated test fixtures and setup code
- Duplicated service/utility functions
- Similar code blocks that could be extracted
"""

import re
from collections import defaultdict
from pathlib import Path

# Common DRY violation patterns
PATTERNS = {
    "mock_setup": r"mock_\w+\s*=\s*MagicMock\(",
    "temp_directory": r"TemporaryDirectory\(\)",
    "issue_creation": r"Issue\(\s*id=",
    "fixture_repeat": r"@pytest\.fixture.*def\s+(\w+)",
    "patch_pattern": r"@patch\(",
    "mock_persistence": r"MagicMock\(spec=PersistenceInterface\)",
    "roadmap_core_init": r"RoadmapCore\(\)",
}

# Track similar code blocks
similar_blocks: dict[str, list[tuple[str, int]]] = defaultdict(list)
fixture_names: set[str] = set()
duplicate_patterns: dict[str, list[tuple[str, int, str]]] = defaultdict(list)


def scan_file(filepath: Path) -> None:
    """Scan a Python file for DRY violations."""
    try:
        with open(filepath) as f:
            lines = f.readlines()
    except Exception:
        return

    rel_path = str(filepath.relative_to(Path.cwd()))

    # Check for repeated patterns
    for pattern_name, pattern in PATTERNS.items():
        matches = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line):
                matches.append((rel_path, i, line.strip()[:60]))

        if len(matches) > 2:  # Only report if appears 3+ times
            for file_path, lineno, code in matches:
                duplicate_patterns[f"{pattern_name}"].append((file_path, lineno, code))

    # Look for fixture definitions
    for _i, line in enumerate(lines, 1):
        fixture_match = re.search(r"@pytest\.fixture.*def\s+(\w+)", line)
        if fixture_match:
            fixture_names.add(fixture_match.group(1))


# Scan all Python files
for py_file in Path(".").rglob("*.py"):
    if "__pycache__" in str(py_file) or "venv" in str(py_file):
        continue
    scan_file(py_file)

# Print results
print("=" * 90)
print("DRY VIOLATION ANALYSIS - CODE DUPLICATION SCAN")
print("=" * 90)
print()

if not duplicate_patterns:
    print("✅ No significant code duplication patterns detected!")
else:
    print(f"⚠️  Found {len(duplicate_patterns)} repeated code patterns\n")

    for pattern_name in sorted(duplicate_patterns.keys()):
        occurrences = duplicate_patterns[pattern_name]
        if len(occurrences) >= 3:
            print(
                f"\n{pattern_name.replace('_', ' ').title()}: {len(occurrences)} occurrences"
            )
            print("-" * 90)
            for filepath, lineno, code in occurrences[:8]:
                print(f"  {filepath}:{lineno}")
                print(f"    {code}...")
            if len(occurrences) > 8:
                print(f"  ... and {len(occurrences) - 8} more")

print()
print("=" * 90)
print(
    f"\nTotal DRY Pattern Occurrences: {sum(len(v) for v in duplicate_patterns.values())}"
)
print(f"Pattern Types Found: {len(duplicate_patterns)}")
print()

# Specific DRY anti-patterns to highlight
print("\n" + "=" * 90)
print("SPECIFIC DRY VIOLATIONS TO ADDRESS")
print("=" * 90)

if duplicate_patterns.get("mock_persistence", []):
    print(
        "\n⚠️  Mock Persistence Setup Pattern appears "
        + str(len(duplicate_patterns.get("mock_persistence", [])))
        + " times"
    )
    print(
        "   💡 SUGGESTION: Create a @pytest.fixture for common mock_persistence setup"
    )
    print("      Example: Create tests/conftest.py with:")
    print(
        """
        @pytest.fixture
        def mock_persistence():
            return MagicMock(spec=PersistenceInterface)
        """
    )

if duplicate_patterns.get("temp_directory", []):
    print(
        "\n⚠️  TemporaryDirectory Pattern appears "
        + str(len(duplicate_patterns.get("temp_directory", [])))
        + " times"
    )
    print("   💡 SUGGESTION: Create a fixture for temporary test directories")
    print("      Example: @pytest.fixture def temp_dir(tmp_path): return tmp_path")

if duplicate_patterns.get("issue_creation", []):
    print(
        "\n⚠️  Issue Creation Pattern appears "
        + str(len(duplicate_patterns.get("issue_creation", [])))
        + " times"
    )
    print("   💡 SUGGESTION: Create an IssueFactory or test_data_factory module")
    print("""
      Example:
      class IssueFactory:
          @staticmethod
          def create_default(id='test-1', **kwargs):
              return Issue(id=id, title='Test', ...)
    """)

if duplicate_patterns.get("patch_pattern", []):
    print(
        "\n⚠️  Patch Pattern appears "
        + str(len(duplicate_patterns.get("patch_pattern", [])))
        + " times"
    )
    print(
        "   💡 SUGGESTION: Consolidate patches into conftest.py or use pytest-mock plugin"
    )

print()
print("=" * 90)
