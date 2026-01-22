#!/usr/bin/env python3
"""Phase 7a: Audit error handling and logging patterns."""

import os
import re


def analyze_file(filepath):
    """Analyze a Python file for error handling patterns."""
    results = {
        "path": filepath,
        "except_handlers": 0,
        "has_logging": False,
        "bare_except": False,
        "except_pass": False,
        "except_continue": False,
        "except_return": False,
    }

    try:
        with open(filepath) as f:
            content = f.read()

        # Count except handlers
        results["except_handlers"] = len(re.findall(r"except\s", content))

        # Check for logging
        results["has_logging"] = bool(
            re.search(r"(logger\.|get_logger|structlog)", content)
        )

        # Check for specific patterns
        results["bare_except"] = bool(re.search(r"except\s*:", content))
        results["except_pass"] = bool(re.search(r"except\s+\w+.*:\s*pass", content))
        results["except_continue"] = bool(
            re.search(r"except\s+\w+.*:\s*continue", content)
        )
        results["except_return"] = bool(re.search(r"except\s+\w+.*:\s*return", content))

    except Exception as e:
        results["error"] = str(e)

    return results


def main():
    roadmap_files = []

    for root, dirs, files in os.walk("roadmap"):
        # Skip test and cache directories
        dirs[:] = [
            d
            for d in dirs
            if d not in [".git", "__pycache__", ".venv", ".pytest_cache", "tests"]
        ]

        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                roadmap_files.append(filepath)

    # Analyze all files
    results = []
    for filepath in sorted(roadmap_files):
        results.append(analyze_file(filepath))

    # Print audit report
    print("=" * 80)
    print("PHASE 7a: ERROR HANDLING & LOGGING AUDIT REPORT")
    print("=" * 80)
    print()

    # Summary statistics
    files_with_except = sum(1 for r in results if r["except_handlers"] > 0)
    files_with_logging = sum(1 for r in results if r["has_logging"])
    files_with_bare_except = sum(1 for r in results if r["bare_except"])
    files_with_pass = sum(1 for r in results if r["except_pass"])
    files_with_continue = sum(1 for r in results if r["except_continue"])
    files_with_return = sum(1 for r in results if r["except_return"])

    print(f"Total Python files: {len(roadmap_files)}")
    print(f"Files with exception handlers: {files_with_except}")
    print(f"  - With logging: {files_with_logging}")
    print(f"  - Without logging: {files_with_except - files_with_logging}")
    print()

    print("PROBLEMATIC PATTERNS:")
    print(f"  - Bare except clauses: {files_with_bare_except}")
    print(f"  - Except with pass: {files_with_pass}")
    print(f"  - Except with continue: {files_with_continue}")
    print(f"  - Except with return: {files_with_return}")
    print()

    # List files without logging
    print("=" * 80)
    print("FILES WITH EXCEPTION HANDLERS BUT NO LOGGING:")
    print("=" * 80)

    no_logging = [
        r for r in results if r["except_handlers"] > 0 and not r["has_logging"]
    ]
    if no_logging:
        for r in no_logging[:20]:  # Show first 20
            print(f"  {r['path']} ({r['except_handlers']} handlers)")
        if len(no_logging) > 20:
            print(f"  ... and {len(no_logging) - 20} more")
    else:
        print("  None - All files with exceptions have logging!")

    print()
    print("=" * 80)
    print("HIGH-RISK FILES (with problematic patterns):")
    print("=" * 80)

    high_risk = [
        r
        for r in results
        if any([r["bare_except"], r["except_pass"], r["except_continue"]])
    ]
    if high_risk:
        for r in high_risk[:15]:  # Show first 15
            patterns = []
            if r["bare_except"]:
                patterns.append("bare_except")
            if r["except_pass"]:
                patterns.append("except_pass")
            if r["except_continue"]:
                patterns.append("except_continue")
            print(f"  {r['path']}: {', '.join(patterns)}")
        if len(high_risk) > 15:
            print(f"  ... and {len(high_risk) - 15} more")
    else:
        print("  None found!")

    print()
    print("=" * 80)
    print("FILES WITH STRUCTLOG:")
    print("=" * 80)

    structlog_count = sum(
        1 for r in results if "structlog" in open(r["path"]).read() if r["path"]
    )
    print(f"  Total files using structlog: ~{structlog_count}")

    print()
    print("=" * 80)
    print("RECOMMENDATIONS FOR PHASE 7:")
    print("=" * 80)
    print()
    print("1. Priority 1 - Add logging to silent failures:")
    print(
        f"   - {files_with_except - files_with_logging} files need logging in exception handlers"
    )
    print()
    print("2. Priority 2 - Fix problematic patterns:")
    print(f"   - {files_with_bare_except} files have bare except clauses")
    print(f"   - {files_with_pass} files have except...pass patterns")
    print(f"   - {files_with_continue} files have except...continue patterns")
    print()
    print("3. Priority 3 - Migrate to structlog:")
    print("   - Standardize on structlog across all modules")
    print("   - Remove generic logging imports")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
