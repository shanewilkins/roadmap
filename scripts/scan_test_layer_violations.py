#!/usr/bin/env python3
"""Scan test directory for layer violations.

Tests should ideally follow similar layer rules as production code:
- Unit tests for layer X should primarily test that layer
- However, tests can import implementations they're testing
- Integration tests can import across layers

This scanner identifies tests that break isolation patterns.
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# Define test layer mappings - mirrors production layers
TEST_LAYERS = {
    "unit/adapters": "Adapters Tests",
    "unit/core": "Core Tests",
    "unit/common": "Common Tests",
    "unit/infrastructure": "Infrastructure Tests",
    "unit/domain": "Domain Tests",
    "unit/presentation": "Presentation Tests",
    "integration": "Integration Tests",
}

# Define allowed imports for test layers
# Tests can be more permissive than production code since they're testing implementations
TEST_ALLOWED = {
    "unit/adapters": {"core", "common", "infrastructure", "adapters"},
    "unit/core": {"core", "common", "infrastructure"},
    "unit/common": {"common", "infrastructure"},
    "unit/infrastructure": {"infrastructure", "common", "core"},
    "unit/domain": {"core", "domain"},
    "unit/presentation": {"adapters", "core", "common", "presentation"},
    "integration": {"adapters", "core", "common", "infrastructure", "domain"},
}

violations = []


def get_test_layer(path_str):
    """Determine which test layer a file belongs to."""
    parts = path_str.split(os.sep)
    if "tests" not in parts:
        return None

    idx = parts.index("tests")
    if idx + 1 < len(parts):
        # Build layer name like "unit/core"
        if parts[idx + 1] == "unit" and idx + 2 < len(parts):
            layer = f"unit/{parts[idx + 2]}"
            if layer in TEST_LAYERS:
                return layer
        elif parts[idx + 1] == "integration":
            return "integration"

    return None


def normalize_module_path(module_path):
    """Normalize module paths for comparison."""
    parts = module_path.split(".")
    if len(parts) >= 2 and parts[0] == "roadmap" and parts[1] == "infrastructure":
        # All infrastructure subdirectories map to infrastructure layer
        return ".".join(parts[:2])
    return module_path


def extract_imports(file_path):
    """Extract all imports from a Python file."""
    imports = []
    try:
        with open(file_path) as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            # Match 'from X import Y' or 'import X'
            from_match = re.match(r"^\s*from\s+([\w\.]+)\s+import", line)
            import_match = re.match(r"^\s*import\s+([\w\.]+)", line)

            if from_match:
                imports.append((i, from_match.group(1)))
            elif import_match:
                imports.append((i, import_match.group(1)))
    except Exception as e:  # noqa: E722
        print(f"Failed to extract imports from {file_path}: {e}", file=sys.stderr)

    return imports


def check_test_violation(from_test_layer, to_module):
    """Check if a test import violates layer rules."""
    # Only check roadmap imports
    if not to_module.startswith("roadmap"):
        return False

    # Normalize the module path
    to_module = normalize_module_path(to_module)

    # Extract the layer from the import
    parts = to_module.split(".")
    if len(parts) < 2 or parts[0] != "roadmap":
        return False

    to_layer = parts[1]  # e.g., "core", "adapters", "infrastructure"

    # Check if this import is allowed for this test layer
    if to_layer not in TEST_ALLOWED.get(from_test_layer, set()):
        return True

    return False


# Scan all test Python files
test_path = Path("tests")
for py_file in test_path.rglob("*.py"):
    if "__pycache__" in str(py_file) or py_file.name == "conftest.py":
        continue

    from_test_layer = get_test_layer(str(py_file))
    if not from_test_layer:
        continue

    imports = extract_imports(str(py_file))

    for line_no, import_module in imports:
        if check_test_violation(from_test_layer, import_module):
            # Extract target layer
            parts = import_module.split(".")
            to_layer = parts[1] if len(parts) > 1 else None

            violations.append(
                {
                    "file": str(py_file),
                    "line": line_no,
                    "from_test_layer": from_test_layer,
                    "import": import_module,
                    "to_layer": to_layer,
                }
            )

# Sort violations by layer and file
violations.sort(key=lambda x: (x["from_test_layer"], x["file"]))

# Print summary
print("=" * 90)
print("TEST LAYER VIOLATION ANALYSIS")
print("=" * 90)
print()

if not violations:
    print("✅ No test layer violations found!")
else:
    print(f"⚠️  Found {len(violations)} test layer violations\n")

    # Group by source test layer
    by_layer = defaultdict(list)
    for v in violations:
        by_layer[v["from_test_layer"]].append(v)

    for layer in sorted(by_layer.keys()):
        violations_in_layer = by_layer[layer]
        print(
            f"\n{TEST_LAYERS.get(layer, layer)} importing from forbidden layers ({len(violations_in_layer)} violations):"
        )
        print("-" * 90)

        for v in violations_in_layer[:15]:  # Show first 15
            print(f"  {v['file']}:{v['line']}")
            print(f"    → from {v['import']}")

        if len(violations_in_layer) > 15:
            print(f"  ... and {len(violations_in_layer) - 15} more")

print()
print("=" * 90)

# Print statistics
print("\nSummary by test layer:")
print("-" * 90)
for layer in sorted(TEST_LAYERS.keys()):
    count = len([v for v in violations if v["from_test_layer"] == layer])
    print(f"  {TEST_LAYERS[layer]:.<50} {count:>3} violations")

print()
print(f"TOTAL: {len(violations)} test layer violations")
print()
