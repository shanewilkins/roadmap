#!/usr/bin/env python3
"""
Audit script: Comprehensive test assertion analysis.

Analyzes all test functions for:
1. Missing assertions (tests with zero assertions)
2. Weak assertions (vague or incomplete checks)
3. Excessive mocking (>5 decorators)
4. Large test functions (>70 LOC)
5. Test parameterization stats

Usage:
    python3 scripts/audit_missing_assertions.py
    python3 scripts/audit_missing_assertions.py --weak-assertions
    python3 scripts/audit_missing_assertions.py --excessive-mocks
"""

import re
import sys
from collections import defaultdict
from pathlib import Path


def find_test_files() -> list[Path]:
    """Find all pytest test files."""
    test_dir = Path("tests")
    if not test_dir.exists():
        print("ERROR: tests/ directory not found")
        sys.exit(1)
    return sorted(test_dir.rglob("test_*.py"))


def extract_test_functions(file_path: Path) -> list[tuple[str, int, int, str]]:
    """
    Extract test function names, line ranges, and full content.
    Returns list of (function_name, start_line, end_line, content).
    """
    with open(file_path) as f:
        lines = f.readlines()

    test_functions = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for test function definition
        match = re.match(r"^def (test_\w+)\(", line)
        if match:
            func_name = match.group(1)
            start_line = i + 1  # 1-indexed for display

            # Find end of function (next def or class at same indentation level)
            indent = len(line) - len(line.lstrip())
            end_line = i + 1

            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                if next_line.strip() == "":
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())

                # Check if we've hit another function/class at same level
                if next_indent <= indent and (
                    next_line.strip().startswith("def ")
                    or next_line.strip().startswith("class ")
                ):
                    end_line = j
                    break
                end_line = j + 1

            func_content = "".join(lines[start_line - 1 : end_line])
            test_functions.append((func_name, start_line, end_line, func_content))
            i = end_line
        else:
            i += 1

    return test_functions


def has_assertion(content: str) -> bool:
    """Check if function has any assert statements."""
    assertion_patterns = [
        r"\bassert\s+",  # assert statement
        r"\.assert_called",  # mock assertions
        r"\.assert_raises",  # pytest raises
        r"\.assert_",  # other assertion methods
        r"pytest\.raises",  # pytest.raises context manager
        r"pytest\.warns",  # pytest.warns context manager
    ]

    for pattern in assertion_patterns:
        if re.search(pattern, content):
            return True

    return False


def count_assertions(content: str) -> int:
    """Count number of assertions in function."""
    count = 0
    # Count basic asserts
    count += len(re.findall(r"\bassert\s+", content))
    # Count mock assertions
    count += len(re.findall(r"\.assert_", content))
    # Count pytest assertions
    count += len(re.findall(r"pytest\.(raises|warns)", content))
    return count


def has_weak_assertions(content: str) -> bool:
    """Check for vague/weak assertion patterns."""
    weak_patterns = [
        r"\bassert\s+\w+\s*$",  # assert variable_name (just truthy check)
        r"\.assert_called\(\)",  # .assert_called() without verifying args
        r"\.call_count\s*[<>]=\s*[0-9]",  # .call_count >= 1 (loose bounds)
        r"\bassert\s+(result|value|data|response|output|ret)\s*$",  # assert common var names
    ]

    count = 0
    for pattern in weak_patterns:
        count += len(re.findall(pattern, content, re.MULTILINE))
    return count > 0


def count_decorators(content: str) -> int:
    """Count decorator lines before function definition."""
    lines = content.split("\n")
    count = 0
    for line in lines:
        if line.strip().startswith("@"):
            count += 1
        elif line.strip().startswith("def test_"):
            break
    return count


def count_mocks(content: str) -> int:
    """Count mock/patch decorators."""
    return len(re.findall(r"@(patch|patch\.object|Mock|MagicMock)", content))


def is_parameterized(content: str) -> bool:
    """Check if test is parameterized."""
    return "@pytest.mark.parametrize" in content


def get_loc(content: str) -> int:
    """Get lines of code (excluding empty lines and comments)."""
    lines = content.split("\n")
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def main():
    """Main audit routine."""
    print("=" * 90)
    print("COMPREHENSIVE TEST ASSERTION AUDIT")
    print("=" * 90)
    print()

    test_files = find_test_files()
    print(f"Scanning {len(test_files)} test files...\n")

    missing_assertions = []
    weak_assertions = []
    excessive_mocks = []
    large_tests = []
    parameterized_tests = []

    total_tests = 0
    total_assertions = 0

    for test_file in test_files:
        test_functions = extract_test_functions(test_file)

        for func_name, start_line, _end_line, content in test_functions:
            total_tests += 1
            loc = get_loc(content)
            decorators = count_decorators(content)
            mock_count = count_mocks(content)
            assertion_count = count_assertions(content)

            total_assertions += assertion_count

            # Check for missing assertions
            if not has_assertion(content):
                missing_assertions.append(
                    (test_file, func_name, start_line, loc, decorators)
                )

            # Check for weak assertions
            if assertion_count > 0 and has_weak_assertions(content):
                weak_assertions.append(
                    (test_file, func_name, start_line, assertion_count, loc)
                )

            # Check for excessive mocks
            if mock_count > 5:
                excessive_mocks.append(
                    (test_file, func_name, start_line, mock_count, loc)
                )

            # Check for large tests
            if loc > 70:
                large_tests.append((test_file, func_name, start_line, loc, decorators))

            # Check parameterization
            if is_parameterized(content):
                parameterized_tests.append(test_file)

    # Print summary
    print("=" * 90)
    print("SUMMARY")
    print("=" * 90)
    print(f"Total tests:               {total_tests:,}")
    print(f"Total assertions:          {total_assertions:,}")
    print(
        f"Avg assertions per test:   {total_assertions/total_tests if total_tests > 0 else 0:.2f}"
    )
    print()
    print(
        f"Missing assertions:        {len(missing_assertions)} ({100*len(missing_assertions)/total_tests:.1f}%)"
    )
    print(
        f"Weak assertions:           {len(weak_assertions)} ({100*len(weak_assertions)/total_tests:.1f}%)"
    )
    print(
        f"Excessive mocks (>5):      {len(excessive_mocks)} ({100*len(excessive_mocks)/total_tests:.1f}%)"
    )
    print(
        f"Large tests (>70 LOC):     {len(large_tests)} ({100*len(large_tests)/total_tests:.1f}%)"
    )
    print(f"Parameterized:             {len(set(parameterized_tests))} files")
    print("=" * 90)

    # Print missing assertions (PHASE 1)
    if missing_assertions:
        print("\n" + "-" * 90)
        print(f"PHASE 1: MISSING ASSERTIONS ({len(missing_assertions)} tests)")
        print("-" * 90)

        by_file = defaultdict(list)
        for test_file, func_name, start_line, loc, decorators in missing_assertions:
            by_file[test_file].append((func_name, start_line, loc, decorators))

        for test_file in sorted(by_file.keys()):
            tests = by_file[test_file]
            print(f"\n{test_file}:")
            for func_name, start_line, loc, decorators in tests:
                deco_str = f" [{decorators} decorators]" if decorators > 0 else ""
                print(f"  {start_line:4d}: {func_name:45s} ({loc:2d} LOC){deco_str}")

    # Print weak assertions (PHASE 2)
    if weak_assertions:
        print("\n" + "-" * 90)
        print(
            f"PHASE 2: WEAK ASSERTIONS ({len(weak_assertions)} tests with vague checks)"
        )
        print("-" * 90)

        by_file = defaultdict(list)
        for test_file, func_name, start_line, assertion_count, loc in weak_assertions:
            by_file[test_file].append((func_name, start_line, assertion_count, loc))

        file_count = 0
        for test_file in sorted(by_file.keys())[:5]:  # Show first 5 files
            tests = by_file[test_file]
            print(f"\n{test_file}:")
            for func_name, start_line, assertion_count, loc in tests[
                :3
            ]:  # Show first 3 tests per file
                print(
                    f"  {start_line:4d}: {func_name:45s} ({assertion_count} assertions, {loc} LOC)"
                )
            file_count += 1

        remaining_files = len(by_file) - file_count
        if remaining_files > 0:
            print(f"\n  ... and {remaining_files} more files with weak assertions")

    # Print excessive mocks (PHASE 3)
    if excessive_mocks:
        print("\n" + "-" * 90)
        print(f"PHASE 3: EXCESSIVE MOCKS ({len(excessive_mocks)} tests with >5 mocks)")
        print("-" * 90)

        by_file = defaultdict(list)
        for test_file, func_name, start_line, mock_count, loc in excessive_mocks:
            by_file[test_file].append((func_name, start_line, mock_count, loc))

        file_count = 0
        for test_file in sorted(by_file.keys())[:5]:  # Show first 5 files
            tests = by_file[test_file]
            print(f"\n{test_file}:")
            for func_name, start_line, mock_count, loc in tests[
                :3
            ]:  # Show first 3 tests per file
                print(
                    f"  {start_line:4d}: {func_name:45s} ({mock_count} mocks, {loc} LOC)"
                )
            file_count += 1

        remaining_files = len(by_file) - file_count
        if remaining_files > 0:
            print(f"\n  ... and {remaining_files} more files with excessive mocks")

    # Print large tests
    if large_tests:
        print("\n" + "-" * 90)
        print(f"LARGE TESTS ({len(large_tests)} tests >70 LOC)")
        print("-" * 90)

        by_file = defaultdict(list)
        for test_file, func_name, start_line, loc, decorators in large_tests:
            by_file[test_file].append((func_name, start_line, loc, decorators))

        file_count = 0
        for test_file in sorted(by_file.keys())[:5]:  # Show first 5 files
            tests = by_file[test_file]
            print(f"\n{test_file}:")
            for func_name, start_line, loc, _decorators in tests[
                :3
            ]:  # Show first 3 tests per file
                print(f"  {start_line:4d}: {func_name:45s} ({loc:2d} LOC)")
            file_count += 1

        remaining_files = len(by_file) - file_count
        if remaining_files > 0:
            print(f"\n  ... and {remaining_files} more files with large tests")

    print("\n" + "=" * 90)


if __name__ == "__main__":
    main()
