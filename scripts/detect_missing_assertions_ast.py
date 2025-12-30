#!/usr/bin/env python3
"""
AST-based test assertion detector.

Uses Python's ast module to reliably identify test functions that have
no assertions. Outputs a clean list of files and functions that need fixing.

Usage:
    python3 scripts/detect_missing_assertions_ast.py
    python3 scripts/detect_missing_assertions_ast.py > missing_assertions.txt
"""

import ast
import sys
from pathlib import Path


class AssertionDetector(ast.NodeVisitor):
    """Visit AST nodes to detect if a test function has assertions."""

    def __init__(self):
        self.has_assertion = False
        self.in_test_function = False

    def visit_Assert(self, node: ast.Assert) -> None:
        """Detect assert statements."""
        if self.in_test_function:
            self.has_assertion = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Detect .assert_* method calls and pytest.raises."""
        if self.in_test_function:
            # Check for .assert_* methods (mock assertions)
            if isinstance(node.func, ast.Attribute):
                if node.func.attr.startswith("assert_"):
                    self.has_assertion = True
            # Check for pytest.raises, pytest.warns
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ("raises", "warns"):
                    self.has_assertion = True
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """Detect pytest.raises/warns context managers."""
        if self.in_test_function:
            for item in node.items:
                context = item.context_expr
                # Check for pytest.raises or pytest.warns
                if isinstance(context, ast.Call):
                    if isinstance(context.func, ast.Attribute):
                        if context.func.attr in ("raises", "warns"):
                            self.has_assertion = True
        self.generic_visit(node)


def has_assertions(test_func_node: ast.FunctionDef) -> bool:
    """Check if a test function has any assertions."""
    detector = AssertionDetector()
    detector.in_test_function = True
    detector.visit(test_func_node)
    return detector.has_assertion


def find_test_functions(file_path: Path) -> list[tuple[str, int]]:
    """
    Find all test functions in a file and check for assertions.

    Returns:
        List of (function_name, line_number) tuples for functions with no assertions.
    """
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
    except SyntaxError:
        return []

    missing_assertions = []

    for node in ast.walk(tree):
        # Look for test functions (methods in classes and standalone functions)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            if not has_assertions(node):
                missing_assertions.append((node.name, node.lineno))

    return missing_assertions


def main():
    """Scan all test files and report functions with missing assertions."""
    test_dir = Path("tests")

    if not test_dir.exists():
        print("ERROR: tests/ directory not found")
        sys.exit(1)

    results: dict[Path, list[tuple[str, int]]] = {}
    total_tests = 0
    total_missing = 0

    # Scan all test files
    for test_file in sorted(test_dir.rglob("test_*.py")):
        missing = find_test_functions(test_file)
        if missing:
            results[test_file] = missing
            total_missing += len(missing)
        total_tests += len(missing)  # This will be wrong, but we'll fix display

    # Count total tests by collecting all test functions
    total_test_functions = 0
    for test_file in test_dir.rglob("test_*.py"):
        try:
            with open(test_file) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    total_test_functions += 1
        except SyntaxError:
            pass

    # Print results
    print("=" * 100)
    print("TEST ASSERTION AUDIT (AST-based)")
    print("=" * 100)
    print()
    print(f"Total test functions found: {total_test_functions}")
    print(f"Test functions WITHOUT assertions: {total_missing}")
    if total_test_functions > 0:
        percentage = (total_missing / total_test_functions) * 100
        print(f"Percentage: {percentage:.1f}%")
    print()

    if not results:
        print("✓ All test functions have assertions!")
        return

    print("-" * 100)
    print("FUNCTIONS NEEDING ASSERTIONS")
    print("-" * 100)
    print()

    for file_path in sorted(results.keys()):
        rel_path = file_path.relative_to(".")
        functions = results[file_path]
        print(f"{rel_path}")
        for func_name, line_num in sorted(functions, key=lambda x: x[1]):
            print(f"  Line {line_num:4d}: {func_name}")
        print()

    print("=" * 100)
    print(f"SUMMARY: {total_missing} test functions need assertions")
    print("=" * 100)
    print()
    print("To fix these tests:")
    print("1. Open each file listed above")
    print("2. Navigate to the line number shown")
    print("3. Add meaningful assertions that verify the function's behavior")
    print()


if __name__ == "__main__":
    main()
